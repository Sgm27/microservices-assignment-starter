# Booking Saga Refactor — Design

- **Date:** 2026-04-21
- **Scope:** Booking Service (Temporal workflow, activities, controller) + Payment Service (new cancel endpoint, outbound signal on confirm)
- **HTTP contract:** Unchanged for BookingService; additive for PaymentService

## 1. Problem

Current implementation deviates from `CLAUDE.md` saga spec:
1. `reserve_seat`, `validate_voucher`, `create_payment` run in [bookingController.create_booking](services/bookingService/src/controllers/bookingController.py) before the workflow starts — they are not Temporal activities. Temporal does not orchestrate retry/compensation for these steps.
2. Workflow polls `check_payment_status` every 5s instead of waiting for a `payment_completed` signal.
3. No `cancel_payment` compensation activity: failed/timed-out bookings leave the payment row in `PENDING`.
4. `POST /payments/{id}/vnpay-return` is a skeleton (out of scope for this refactor).

## 2. Goals

- Move the three setup steps into Temporal activities owned by `BookingWorkflow`.
- Replace payment polling with a `payment_completed` signal sent by the PaymentService `/confirm` endpoint.
- Add `cancel_payment` compensation activity + backing endpoint `POST /payments/{id}/cancel`.
- Preserve all existing HTTP request/response schemas and status codes.

## 3. Non-goals

- VNPay return webhook (`GET /payments/vnpay-return`) remains a skeleton.
- Booking-side `POST /bookings/{id}/cancel` keeps its current synchronous behavior. Relies on workflow's 5-minute timeout to trigger payment compensation via the normal timeout path.
- No change to `GET /bookings/{id}`, `GET /bookings/user/{uid}`, or any other unrelated endpoint.
- No frontend changes required.

## 4. Design decisions (resolved during brainstorming)

| Decision | Choice | Reason |
|---|---|---|
| How does controller return `payment_url` synchronously? | Workflow Query (`get_setup_result`) polled from controller after `start_workflow` | Keeps HTTP contract, pure Temporal pattern, no extra DB read loop |
| Who sends `payment_completed` signal? | Only `POST /payments/{id}/confirm` (skeleton webhook ignored) | Matches current scope; user-explicit decision |
| How does `cancel_payment` activity cancel a payment? | New endpoint `POST /payments/{id}/cancel` | Clean REST semantics; idempotent; avoids breaking existing `/confirm` schema |
| Preserve HTTP error codes? | Yes, 100% | Spec-locked; frontend depends on them |

## 5. Payment Service changes

### 5.1 New endpoint — `POST /payments/{payment_id}/cancel`

Idempotent cancellation used by the booking workflow's compensation branch.

| Current status | Response | New status |
|---|---|---|
| `PENDING` | 200 + `PaymentDetail` | `CANCELLED` |
| `CANCELLED` | 200 + `PaymentDetail` (no-op) | `CANCELLED` |
| `FAILED` | 200 + `PaymentDetail` | `CANCELLED` |
| `SUCCESS` | 409 `"Không thể huỷ payment đã hoàn tất"` | unchanged |
| not found | 404 `"Không tìm thấy đơn thanh toán"` | — |

Files touched:
- `services/paymentService/src/routes/paymentRoutes.py` — add route
- `services/paymentService/src/controllers/paymentController.py` — add `cancel_payment`
- `services/paymentService/src/validators/paymentSchemas.py` — no new schema; reuse `PaymentDetail`

### 5.2 `POST /payments/{payment_id}/confirm` emits signal

After the existing DB update in [paymentController.confirm_payment](services/paymentService/src/controllers/paymentController.py:77), call the Temporal client to signal `BookingWorkflow`:

```python
from ..config.temporalClient import signal_payment_completed
try:
    signal_payment_completed(booking_id=payment.booking_id, success=payload.success)
except Exception as exc:
    logger.warning("Failed to signal workflow for booking %s: %s", payment.booking_id, exc)
    # Do not fail the HTTP call
```

Workflow id is deterministic: `f"booking-{booking_id}"` (matches [temporalClient.start_booking_workflow](services/bookingService/src/config/temporalClient.py:26)).

### 5.3 New module — `paymentService/src/config/temporalClient.py`

```python
async def get_temporal_client(): ...
async def signal_payment_completed_async(booking_id: int, success: bool): ...
def signal_payment_completed(booking_id: int, success: bool) -> None:
    asyncio.run(signal_payment_completed_async(booking_id, success))
```

Settings — reuse env vars already present in `docker-compose.yml`:
- `TEMPORAL_HOST=temporal:7233`
- `TEMPORAL_NAMESPACE=default`

Add `temporalio==1.7.1` to `paymentService/requirements.txt`.

### 5.4 Spec update — `docs/api-specs/PaymentService.yaml`

Add `POST /payments/{payment_id}/cancel`:
- operationId: `cancelPayment`
- responses: 200 (`PaymentDetail`), 404, 409

No changes to request body schemas.

## 6. Booking Service — Workflow

### 6.1 Input (changed)

```python
{
  "booking_id": int,
  "user_id": int,
  "showtime_id": int,
  "seat_numbers": list[str],
  "voucher_code": str | None,
  "email": str,
  "original_amount": str,   # Decimal serialized to str for JSON
}
```

`payment_id` and `final_amount` are no longer inputs — the workflow produces them.

### 6.2 Signal, Query, state

```python
@workflow.defn(name="BookingWorkflow")
class BookingWorkflow:
    def __init__(self):
        self._state = "setting_up"
        self._payment_id: int | None = None
        self._payment_url: str | None = None
        self._error_code: str | None = None
        self._error_message: str | None = None
        self._payment_result: bool | None = None

    @workflow.signal
    def payment_completed(self, success: bool) -> None:
        self._payment_result = success

    @workflow.query
    def get_setup_result(self) -> dict:
        return {
            "state": self._state,
            "payment_id": self._payment_id,
            "payment_url": self._payment_url,
            "error_code": self._error_code,
            "error_message": self._error_message,
        }
```

`state` transitions: `setting_up` → (`awaiting_payment` | `failed`) → terminal.

### 6.3 Execution pseudocode

```
@workflow.run
async def run(self, input):
    try:
        await activity reserve_seats_activity(booking_id, showtime_id, seat_numbers)
    except ActivityError:
        self._state, self._error_code = "failed", "seat_conflict"
        self._error_message = str(exc)
        return "FAILED_SETUP"   # no compensation

    discount = Decimal(0)
    if voucher_code:
        try:
            v = await activity validate_voucher_activity(voucher_code, original_amount)
        except DownstreamError:
            await activity release_seats_activity(booking_id)
            self._state, self._error_code = "failed", "downstream_voucher"
            return "FAILED_SETUP"
        if not v["valid"]:
            await activity release_seats_activity(booking_id)
            self._state, self._error_code = "failed", "voucher_invalid"
            self._error_message = v.get("message") or "Mã giảm giá không hợp lệ"
            return "FAILED_SETUP"
        discount = Decimal(v["discount_amount"])

    final_amount = max(Decimal(0), Decimal(original_amount) - discount)

    try:
        pay = await activity create_payment_activity(booking_id, str(final_amount))
    except DownstreamError:
        await activity release_seats_activity(booking_id)
        self._state, self._error_code = "failed", "downstream_payment"
        return "FAILED_SETUP"

    self._payment_id = pay["payment_id"]
    self._payment_url = pay["payment_url"]

    await activity persist_setup_activity(booking_id, self._payment_id, str(discount), str(final_amount))
    self._state = "awaiting_payment"

    # Wait up to 5 min for payment_completed signal
    try:
        await workflow.wait_condition(lambda: self._payment_result is not None, timeout=timedelta(seconds=300))
    except asyncio.TimeoutError:
        self._payment_result = False
        reason = "payment timeout"
    else:
        reason = None if self._payment_result else "payment failed"

    if self._payment_result:
        await activity confirm_seats_activity(booking_id)
        if voucher_code:
            await activity redeem_voucher_activity(voucher_code)
        await activity send_notification_activity(user_id, email, subject, body)
        await activity finalize_booking_activity(booking_id, "ACTIVE", None)
        return "ACTIVE"

    await activity release_seats_activity(booking_id)
    await activity cancel_payment_activity(self._payment_id)
    await activity finalize_booking_activity(booking_id, "CANCELLED", reason)
    return "CANCELLED"
```

### 6.4 Activities

| Activity | Action |
|---|---|
| `reserve_seats_activity` | **NEW** — wrap `svc.reserve_seats(showtime_id, seat_numbers, booking_id)` |
| `validate_voucher_activity` | **NEW** — wrap `svc.validate_voucher(code, amount)`, returns `{valid, discount_amount, message}` |
| `create_payment_activity` | **NEW** — wrap `svc.create_payment(booking_id, amount)`, returns `{payment_id, payment_url}` |
| `persist_setup_activity` | **NEW** — update `bookings` row with `payment_id`, `discount_amount`, `final_amount`, `status="AWAITING_PAYMENT"` |
| `cancel_payment_activity` | **NEW** — call `POST /payments/{id}/cancel` (idempotent) |
| `check_payment_status` | **DELETE** |
| `confirm_seats_activity` | keep |
| `release_seats_activity` | keep |
| `redeem_voucher_activity` | keep |
| `send_notification_activity` | keep |
| `finalize_booking_activity` | keep |

Each activity: `start_to_close_timeout=30s`. Retry policy: Temporal SDK default (exponential backoff, unlimited attempts unless `max_attempts` set) — same as current workflow, no per-activity override.

### 6.5 Compensation rules

- Fail at step 1 (`reserve_seats`): no seats were reserved → no compensation.
- Fail at steps 2–4 (`validate_voucher`, `create_payment`): seats were reserved → call `release_seats`.
- Fail/timeout after step 6 (`wait_condition`): call `release_seats` + `cancel_payment`.

Both `release_seats` (movieService side) and `cancel_payment` (paymentService side) must be idempotent.

## 7. Booking Service — Controller

### 7.1 `create_booking` refactored

```python
def create_booking(db, payload):
    # Pre-workflow: validate showtime + compute original amount
    try:
        showtime = svc.fetch_showtime(payload.showtime_id)
    except svc.DownstreamError as exc:
        raise HTTPException(404, str(exc)) from exc
    original_amount = _price_of_showtime(showtime) * len(payload.seat_numbers)

    # Insert booking row (PENDING)
    booking = Booking(
        user_id=payload.user_id,
        showtime_id=payload.showtime_id,
        seat_numbers=list(payload.seat_numbers),
        voucher_code=payload.voucher_code,
        email=payload.email,
        original_amount=original_amount,
        discount_amount=Decimal(0),
        final_amount=original_amount,
        status="PENDING",
    )
    db.add(booking); db.commit(); db.refresh(booking)

    # Start workflow
    workflow_id = _start_workflow_sync({
        "booking_id": booking.id,
        "user_id": payload.user_id,
        "showtime_id": payload.showtime_id,
        "seat_numbers": list(payload.seat_numbers),
        "voucher_code": payload.voucher_code,
        "email": payload.email,
        "original_amount": str(original_amount),
    })
    booking.workflow_id = workflow_id
    db.commit()

    # Poll workflow query until setup finished (max 15s)
    result = _wait_for_setup(workflow_id, timeout_s=15)

    if result["state"] == "awaiting_payment":
        db.refresh(booking)   # activity persisted payment_id + final_amount
        return CreateBookingResponse(
            booking_id=booking.id,
            workflow_id=booking.workflow_id,
            payment_id=booking.payment_id,
            payment_url=result["payment_url"],
            status=booking.status,
            final_amount=booking.final_amount,
        )

    code_map = {
        "seat_conflict":      409,
        "voucher_invalid":    400,
        "downstream_voucher": 502,
        "downstream_payment": 502,
        "setup_timeout":      502,
    }
    status_code = code_map.get(result.get("error_code"), 502)
    raise HTTPException(
        status_code=status_code,
        detail=result.get("error_message") or "Booking setup failed",
    )
```

### 7.2 `_wait_for_setup` helper

```python
async def _wait_for_setup_async(workflow_id: str, timeout_s: int) -> dict:
    from ..config.temporalClient import get_temporal_client
    client = await get_temporal_client()
    handle = client.get_workflow_handle(workflow_id)
    deadline = asyncio.get_event_loop().time() + timeout_s
    while True:
        try:
            result = await handle.query("get_setup_result")
        except Exception:
            result = {"state": "setting_up"}
        if result.get("state") in ("awaiting_payment", "failed"):
            return result
        if asyncio.get_event_loop().time() >= deadline:
            return {
                "state": "failed",
                "error_code": "setup_timeout",
                "error_message": "Workflow setup timeout",
            }
        await asyncio.sleep(0.2)


def _wait_for_setup(workflow_id: str, timeout_s: int = 15) -> dict:
    return asyncio.run(_wait_for_setup_async(workflow_id, timeout_s))
```

### 7.3 Other endpoints — unchanged

- `GET /bookings/{id}` — unchanged (DB read).
- `GET /bookings/user/{uid}` — unchanged.
- `POST /bookings/{id}/cancel` — unchanged. Workflow will hit its 5-minute timeout and run compensation (including `cancel_payment`).

### 7.4 HTTP error behavior — spec compliance

| Scenario | Before | After | Spec OK? |
|---|---|---|---|
| Showtime not found | 404 | 404 | ✓ |
| Seat conflict | 409 | 409 | ✓ |
| Voucher invalid | 400 | 400 | ✓ |
| Voucher service down | 502 | 502 | ✓ |
| Payment service down | 502 | 502 | ✓ |
| Workflow setup timeout | n/a | 502 | ✓ (gateway-class error) |
| Pydantic validation | 422 | 422 | ✓ |

## 8. Testing

### 8.1 Payment Service — [services/paymentService/tests/test_payments.py](services/paymentService/tests/test_payments.py)

Add:
- `test_cancel_pending_payment` → 200, status → CANCELLED
- `test_cancel_idempotent_when_cancelled` → 200, still CANCELLED
- `test_cancel_failed_payment` → 200, status → CANCELLED
- `test_cancel_success_rejected` → 409
- `test_cancel_not_found` → 404
- `test_confirm_sends_signal` — monkey-patch `temporalClient.signal_payment_completed`, assert called with `(booking_id, True)`
- `test_confirm_signal_failure_does_not_break_api` — patched signal raises; endpoint still 200

### 8.2 Booking Service — activities [services/bookingService/tests/test_activities.py](services/bookingService/tests/test_activities.py)

Monkey-patch `helpers.bookingHelpers` calls. Add:
- `test_reserve_seats_activity_success` / `_conflict_raises`
- `test_validate_voucher_activity_valid` / `_invalid` / `_downstream_error`
- `test_create_payment_activity_returns_ids_and_url`
- `test_persist_setup_activity_updates_booking_row`
- `test_cancel_payment_activity_calls_endpoint` / `_idempotent_on_cancelled`

Delete `check_payment_status` tests.

### 8.3 Booking Service — workflow tests (NEW) [services/bookingService/tests/test_workflow.py](services/bookingService/tests/test_workflow.py)

Use `temporalio.testing.WorkflowEnvironment.start_time_skipping()` + `Worker` with mocked activities. Cases:
1. **Happy path** — setup succeeds → signal(True) → state awaiting_payment → ACTIVE; all success activities invoked
2. **Signal failure** — signal(False) → CANCELLED; `release_seats` + `cancel_payment` called
3. **Timeout** — no signal; time-skip 5+ min → CANCELLED; `release_seats` + `cancel_payment` called
4. **Seat conflict** — `reserve_seats` raises → state=failed/seat_conflict; no compensation
5. **Voucher invalid** — state=failed/voucher_invalid; `release_seats` called
6. **Voucher downstream** — state=failed/downstream_voucher; `release_seats` called
7. **Payment downstream** — state=failed/downstream_payment; `release_seats` called
8. **Query returns `setting_up` before transition**, then `awaiting_payment` after `persist_setup_activity`

### 8.4 Booking Service — API tests [services/bookingService/tests/test_bookings_api.py](services/bookingService/tests/test_bookings_api.py)

Monkey-patch `_start_workflow_sync` and `_wait_for_setup` (or the async form):
- `test_create_booking_happy_path` → 201, payment_url present
- `test_create_booking_seat_conflict` → 409
- `test_create_booking_voucher_invalid` → 400
- `test_create_booking_voucher_downstream` → 502
- `test_create_booking_payment_downstream` → 502
- `test_create_booking_setup_timeout` → 502
- Keep existing `GET /bookings/{id}` / `cancel` / list tests

## 9. Spec & doc updates

- `docs/api-specs/PaymentService.yaml` — add `POST /payments/{payment_id}/cancel`.
- `docs/api-specs/BookingService.yaml` — no contract change (description update optional).
- `services/bookingService/readme.md` / `services/paymentService/readme.md` — note the new saga flow + cancel endpoint.

## 10. Rollout

Single repo, single docker-compose deployment, no feature flag. One PR containing:
1. Booking workflow refactor + activities
2. Booking controller refactor
3. Payment `/cancel` endpoint + signal emission on `/confirm`
4. Payment `temporalClient` module + requirements bump
5. Tests (activities, workflow, API)
6. Spec update for `PaymentService.yaml`

## 11. Out of scope (explicitly deferred)

- `GET /payments/vnpay-return` remains skeleton.
- Booking `POST /bookings/{id}/cancel` still uses direct seat release + relies on workflow timeout for payment compensation. No sync workflow cancel pathway.
- No retry-policy customization per activity (keep Temporal defaults).
- No metrics/observability additions.
