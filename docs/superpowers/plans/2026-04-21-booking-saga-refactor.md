# Booking Saga Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align `BookingWorkflow` with CLAUDE.md saga spec — move `reserve_seats`, `validate_voucher`, `create_payment` into Temporal activities; replace payment polling with `payment_completed` signal sent by PaymentService; add `cancel_payment` compensation backed by a new `POST /payments/{id}/cancel` endpoint.

**Architecture:** Booking controller creates a `PENDING` booking row and starts `BookingWorkflow`. Workflow runs setup activities (reserve → voucher → create_payment → persist), transitions to `awaiting_payment`, then waits on `@workflow.signal payment_completed` with a 5-minute timeout. Controller polls `@workflow.query get_setup_result` for up to 15s to return `payment_url` synchronously in HTTP response. PaymentService `/confirm` emits the signal to `booking-{booking_id}`. Failure branches run `release_seats` and (when applicable) `cancel_payment` compensations.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy + PyMySQL (SQLite in tests), temporalio 1.7.1, pytest, httpx, respx.

**Spec reference:** [docs/superpowers/specs/2026-04-21-booking-saga-refactor-design.md](docs/superpowers/specs/2026-04-21-booking-saga-refactor-design.md)

---

## File map

**Payment Service**
- Modify: [services/paymentService/src/config/settings.py](services/paymentService/src/config/settings.py) — add Temporal env vars
- Create: [services/paymentService/src/config/temporalClient.py](services/paymentService/src/config/temporalClient.py) — Temporal client + `signal_payment_completed`
- Modify: [services/paymentService/src/controllers/paymentController.py](services/paymentService/src/controllers/paymentController.py) — add `cancel_payment`; emit signal in `confirm_payment`
- Modify: [services/paymentService/src/routes/paymentRoutes.py](services/paymentService/src/routes/paymentRoutes.py) — register `POST /payments/{id}/cancel`
- Modify: [services/paymentService/requirements.txt](services/paymentService/requirements.txt) — add `temporalio==1.7.1`
- Modify: [services/paymentService/tests/test_payments.py](services/paymentService/tests/test_payments.py) — tests for cancel + signal
- Modify: [services/paymentService/tests/conftest.py](services/paymentService/tests/conftest.py) — auto-patch `signal_payment_completed`
- Modify: [docs/api-specs/PaymentService.yaml](docs/api-specs/PaymentService.yaml) — add `cancelPayment`
- Modify: [docker-compose.yaml](docker-compose.yaml) — add `TEMPORAL_*` env to `payment-service`

**Booking Service**
- Modify: [services/bookingService/src/helpers/bookingHelpers.py](services/bookingService/src/helpers/bookingHelpers.py) — add `cancel_payment`
- Modify: [services/bookingService/src/activities/bookingActivities.py](services/bookingService/src/activities/bookingActivities.py) — 5 new activities; remove `check_payment_status`
- Modify: [services/bookingService/src/workflows/bookingWorkflow.py](services/bookingService/src/workflows/bookingWorkflow.py) — full rewrite with signal + query
- Modify: [services/bookingService/src/controllers/bookingController.py](services/bookingService/src/controllers/bookingController.py) — refactor `create_booking`; add `_wait_for_setup`
- Modify: [services/bookingService/src/config/temporalClient.py](services/bookingService/src/config/temporalClient.py) — add `query_setup_result_async` helper
- Modify: [services/bookingService/tests/test_activities.py](services/bookingService/tests/test_activities.py) — tests for new activities; remove `check_payment_status`
- Create: [services/bookingService/tests/test_workflow.py](services/bookingService/tests/test_workflow.py) — end-to-end workflow tests
- Modify: [services/bookingService/tests/test_bookings_api.py](services/bookingService/tests/test_bookings_api.py) — update happy path; add error-mapping tests
- Modify: [services/bookingService/tests/conftest.py](services/bookingService/tests/conftest.py) — also patch `_wait_for_setup`

---

## Task 1: Payment Service — add `POST /payments/{id}/cancel`

**Files:**
- Modify: `services/paymentService/src/controllers/paymentController.py`
- Modify: `services/paymentService/src/routes/paymentRoutes.py`
- Modify: `services/paymentService/tests/test_payments.py`

- [ ] **Step 1.1: Write failing tests for cancel behavior**

Append to `services/paymentService/tests/test_payments.py`:

```python
def test_cancel_pending_payment(client):
    created = _create(client, booking_id=1001, amount="100000.00").json()

    r = client.post(f"/payments/{created['payment_id']}/cancel")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == created["payment_id"]
    assert body["status"] == "CANCELLED"


def test_cancel_idempotent_when_already_cancelled(client):
    created = _create(client, booking_id=1002, amount="100000.00").json()

    first = client.post(f"/payments/{created['payment_id']}/cancel")
    assert first.status_code == 200

    second = client.post(f"/payments/{created['payment_id']}/cancel")
    assert second.status_code == 200
    assert second.json()["status"] == "CANCELLED"


def test_cancel_failed_payment(client):
    created = _create(client, booking_id=1003, amount="100000.00").json()

    # Mark FAILED via confirm
    r1 = client.post(f"/payments/{created['payment_id']}/confirm", json={"success": False})
    assert r1.status_code == 200
    assert r1.json()["status"] == "FAILED"

    r2 = client.post(f"/payments/{created['payment_id']}/cancel")
    assert r2.status_code == 200
    assert r2.json()["status"] == "CANCELLED"


def test_cancel_success_rejected(client):
    created = _create(client, booking_id=1004, amount="100000.00").json()

    r1 = client.post(f"/payments/{created['payment_id']}/confirm", json={"success": True})
    assert r1.status_code == 200

    r2 = client.post(f"/payments/{created['payment_id']}/cancel")
    assert r2.status_code == 409


def test_cancel_not_found(client):
    r = client.post("/payments/99999/cancel")
    assert r.status_code == 404
```

- [ ] **Step 1.2: Run tests to verify they fail**

Run: `docker compose run --rm payment-service pytest tests/test_payments.py -k cancel -v`
Expected: 5 FAILs with 404 (route not registered).

- [ ] **Step 1.3: Add `cancel_payment` controller**

Insert at end of `services/paymentService/src/controllers/paymentController.py`:

```python
def cancel_payment(db: Session, payment_id: int) -> PaymentDetail:
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy đơn thanh toán",
        )
    if payment.status == "SUCCESS":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Không thể huỷ payment đã hoàn tất",
        )
    if payment.status != "CANCELLED":
        payment.status = "CANCELLED"
        db.add(payment)
        db.commit()
        db.refresh(payment)
    return _to_detail(payment)
```

- [ ] **Step 1.4: Register route**

In `services/paymentService/src/routes/paymentRoutes.py`, add route next to `confirm`:

```python
@router.post("/payments/{payment_id}/cancel", response_model=PaymentDetail)
def cancel(payment_id: int, db: Session = Depends(get_db)):
    return paymentController.cancel_payment(db, payment_id)
```

Verify imports already include `paymentController` and `PaymentDetail`; add them if not.

- [ ] **Step 1.5: Run cancel tests — expect pass**

Run: `docker compose run --rm payment-service pytest tests/test_payments.py -k cancel -v`
Expected: 5 PASS.

- [ ] **Step 1.6: Full test run — expect no regression**

Run: `docker compose run --rm payment-service pytest -v`
Expected: all PASS (existing tests unaffected).

- [ ] **Step 1.7: Commit**

```bash
git add services/paymentService/src/controllers/paymentController.py \
        services/paymentService/src/routes/paymentRoutes.py \
        services/paymentService/tests/test_payments.py
git commit -m "feat(payment): add POST /payments/{id}/cancel with idempotent behavior"
```

---

## Task 2: Payment Service — Temporal client + signal on confirm

**Files:**
- Modify: `services/paymentService/src/config/settings.py`
- Create: `services/paymentService/src/config/temporalClient.py`
- Modify: `services/paymentService/src/controllers/paymentController.py`
- Modify: `services/paymentService/requirements.txt`
- Modify: `services/paymentService/tests/conftest.py`
- Modify: `services/paymentService/tests/test_payments.py`
- Modify: `docker-compose.yaml`

- [ ] **Step 2.1: Write failing tests for signal emission**

Append to `services/paymentService/tests/test_payments.py`:

```python
def test_confirm_sends_signal_on_success(client, monkeypatch):
    calls = []

    def _fake_signal(booking_id: int, success: bool) -> None:
        calls.append((booking_id, success))

    from src.config import temporalClient

    monkeypatch.setattr(temporalClient, "signal_payment_completed", _fake_signal)

    created = _create(client, booking_id=2001, amount="100000.00").json()

    r = client.post(f"/payments/{created['payment_id']}/confirm", json={"success": True})
    assert r.status_code == 200
    assert calls == [(2001, True)]


def test_confirm_sends_signal_on_failure(client, monkeypatch):
    calls = []

    def _fake_signal(booking_id: int, success: bool) -> None:
        calls.append((booking_id, success))

    from src.config import temporalClient

    monkeypatch.setattr(temporalClient, "signal_payment_completed", _fake_signal)

    created = _create(client, booking_id=2002, amount="100000.00").json()

    r = client.post(f"/payments/{created['payment_id']}/confirm", json={"success": False})
    assert r.status_code == 200
    assert calls == [(2002, False)]


def test_confirm_signal_failure_does_not_break_api(client, monkeypatch):
    def _raising(booking_id: int, success: bool) -> None:
        raise RuntimeError("temporal unreachable")

    from src.config import temporalClient

    monkeypatch.setattr(temporalClient, "signal_payment_completed", _raising)

    created = _create(client, booking_id=2003, amount="100000.00").json()

    r = client.post(f"/payments/{created['payment_id']}/confirm", json={"success": True})
    assert r.status_code == 200
    assert r.json()["status"] == "SUCCESS"
```

- [ ] **Step 2.2: Run tests — expect ImportError**

Run: `docker compose run --rm payment-service pytest tests/test_payments.py -k signal -v`
Expected: FAIL — `ModuleNotFoundError: src.config.temporalClient`.

- [ ] **Step 2.3: Add Temporal settings**

Append to `services/paymentService/src/config/settings.py` (inside `Settings` class, before the `@property database_url`):

```python
    TEMPORAL_HOST: str = "temporal:7233"
    TEMPORAL_NAMESPACE: str = "default"
    TEMPORAL_TASK_QUEUE: str = "booking-task-queue"
```

- [ ] **Step 2.4: Create `temporalClient.py`**

Create `services/paymentService/src/config/temporalClient.py`:

```python
"""Temporal client helpers for paymentService — used to signal BookingWorkflow."""
from __future__ import annotations

import asyncio

from .settings import get_settings


async def get_temporal_client():
    from temporalio.client import Client

    settings = get_settings()
    return await Client.connect(
        settings.TEMPORAL_HOST,
        namespace=settings.TEMPORAL_NAMESPACE,
    )


async def signal_payment_completed_async(booking_id: int, success: bool) -> None:
    client = await get_temporal_client()
    handle = client.get_workflow_handle(f"booking-{booking_id}")
    await handle.signal("payment_completed", success)


def signal_payment_completed(booking_id: int, success: bool) -> None:
    """Sync wrapper for FastAPI handlers — tests monkey-patch this symbol."""
    asyncio.run(signal_payment_completed_async(booking_id, success))
```

- [ ] **Step 2.5: Emit signal from `confirm_payment`**

In `services/paymentService/src/controllers/paymentController.py`, add logger + signal call. Replace the existing `confirm_payment` function with:

```python
import logging

from ..config.temporalClient import signal_payment_completed

log = logging.getLogger(__name__)


def confirm_payment(
    db: Session, payment_id: int, payload: ConfirmPaymentRequest
) -> PaymentDetail:
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy đơn thanh toán",
        )
    if payment.status in FINAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Đơn thanh toán đã được hoàn tất",
        )

    payment.status = "SUCCESS" if payload.success else "FAILED"
    payment.provider_txn_id = f"vnpay-{payment.id}"
    db.add(payment)
    db.commit()
    db.refresh(payment)

    try:
        signal_payment_completed(payment.booking_id, payload.success)
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "Failed to signal BookingWorkflow for booking %s: %s",
            payment.booking_id,
            exc,
        )

    return _to_detail(payment)
```

- [ ] **Step 2.6: Add `temporalio` dependency**

Edit `services/paymentService/requirements.txt` — add:

```
temporalio==1.7.1
```

Rebuild: `docker compose build payment-service`
Expected: build succeeds (may take ~1 min for fresh pip install).

- [ ] **Step 2.7: Auto-patch signal in conftest to silence existing confirm tests**

Edit `services/paymentService/tests/conftest.py` — replace the `client` fixture with:

```python
@pytest.fixture
def client(monkeypatch):
    # Silence Temporal signal so existing tests don't hit a real server.
    from src.config import temporalClient

    monkeypatch.setattr(
        temporalClient,
        "signal_payment_completed",
        lambda booking_id, success: None,
    )

    from src.app import app
    from src.config.database import Base, engine

    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)
```

- [ ] **Step 2.8: Run signal tests — expect pass**

Run: `docker compose run --rm payment-service pytest tests/test_payments.py -k signal -v`
Expected: 3 PASS.

- [ ] **Step 2.9: Full test run — expect no regression**

Run: `docker compose run --rm payment-service pytest -v`
Expected: all PASS.

- [ ] **Step 2.10: Add Temporal env vars to docker-compose**

In `docker-compose.yaml`, under the `payment-service` → `environment:` block (lines 194-205), add:

```yaml
      TEMPORAL_HOST: ${TEMPORAL_HOST:-temporal:7233}
      TEMPORAL_NAMESPACE: ${TEMPORAL_NAMESPACE:-default}
      TEMPORAL_TASK_QUEUE: ${TEMPORAL_TASK_QUEUE:-booking-task-queue}
```

Under `depends_on:`, add (keep existing `mysql-db` entry):

```yaml
    depends_on:
      mysql-db:
        condition: service_healthy
      temporal:
        condition: service_started
```

- [ ] **Step 2.11: Commit**

```bash
git add services/paymentService/src/config/settings.py \
        services/paymentService/src/config/temporalClient.py \
        services/paymentService/src/controllers/paymentController.py \
        services/paymentService/requirements.txt \
        services/paymentService/tests/conftest.py \
        services/paymentService/tests/test_payments.py \
        docker-compose.yaml
git commit -m "feat(payment): signal BookingWorkflow on payment confirm

Adds temporalClient module and fires payment_completed signal after
updating payment status. Signal failures are logged but do not fail
the HTTP request."
```

---

## Task 3: PaymentService spec update

**Files:**
- Modify: `docs/api-specs/PaymentService.yaml`

- [ ] **Step 3.1: Add `cancelPayment` operation**

In `docs/api-specs/PaymentService.yaml`, after the `/payments/{payment_id}/confirm` block, add:

```yaml
  /payments/{payment_id}/cancel:
    post:
      operationId: cancelPayment
      summary: Huỷ payment (idempotent)
      description: |
        Đánh dấu payment là CANCELLED. Dùng bởi BookingWorkflow compensation
        khi workflow fail / timeout. Idempotent: gọi lại với payment đã
        CANCELLED trả 200 no-op. Không được dùng cho payment đã SUCCESS.
      parameters:
        - name: payment_id
          in: path
          required: true
          schema:
            type: integer
      responses:
        "200":
          description: Payment đã ở trạng thái CANCELLED
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/PaymentDetail"
        "404":
          description: Không tìm thấy đơn thanh toán
        "409":
          description: Không thể huỷ payment đã hoàn tất
```

- [ ] **Step 3.2: Commit**

```bash
git add docs/api-specs/PaymentService.yaml
git commit -m "docs(api-spec): add POST /payments/{id}/cancel endpoint"
```

---

## Task 4: Booking Service — `cancel_payment` helper + activities

**Files:**
- Modify: `services/bookingService/src/helpers/bookingHelpers.py`
- Modify: `services/bookingService/src/activities/bookingActivities.py`
- Modify: `services/bookingService/tests/test_activities.py`

- [ ] **Step 4.1: Write failing test for `cancel_payment` helper**

Append to `services/bookingService/tests/test_activities.py`:

```python
def test_cancel_payment_helper_calls_endpoint(respx_mock):
    from src.helpers import bookingHelpers as svc

    route = respx_mock.post("http://payment-service.test/payments/42/cancel").respond(
        200, json={"id": 42, "status": "CANCELLED"}
    )

    svc.cancel_payment(42)

    assert route.called
```

(Assumes `respx_mock` fixture already present; if not, add `from respx import MockRouter` pattern matching other tests in this file.)

- [ ] **Step 4.2: Run test — expect AttributeError**

Run: `docker compose run --rm booking-service pytest tests/test_activities.py -k cancel_payment_helper -v`
Expected: FAIL — `AttributeError: module 'src.helpers.bookingHelpers' has no attribute 'cancel_payment'`.

- [ ] **Step 4.3: Add `cancel_payment` helper**

Append to `services/bookingService/src/helpers/bookingHelpers.py` (end of Payment section):

```python
def cancel_payment(payment_id: int) -> None:
    s = _settings()
    r = httpx.post(
        f"{s.PAYMENT_SERVICE_URL}/payments/{payment_id}/cancel",
        timeout=s.HTTP_TIMEOUT_SECONDS,
    )
    if r.status_code not in (200, 404):
        raise DownstreamError(f"cancel_payment failed: {r.status_code} {r.text}")
```

Rationale: `404` means payment row disappeared → compensation considered done (no-op).

- [ ] **Step 4.4: Run helper test — expect pass**

Run: `docker compose run --rm booking-service pytest tests/test_activities.py -k cancel_payment_helper -v`
Expected: PASS.

- [ ] **Step 4.5: Write failing tests for new activities**

Append to `services/bookingService/tests/test_activities.py`:

```python
import pytest


@pytest.mark.asyncio
async def test_reserve_seats_activity_success(monkeypatch):
    from src.activities import bookingActivities

    called = {}

    def _fake_reserve(showtime_id, seat_numbers, booking_id):
        called["args"] = (showtime_id, seat_numbers, booking_id)

    monkeypatch.setattr(bookingActivities.svc, "reserve_seats", _fake_reserve)

    await bookingActivities.reserve_seats_activity(1, 11, ["A1", "A2"])
    assert called["args"] == (11, ["A1", "A2"], 1)


@pytest.mark.asyncio
async def test_reserve_seats_activity_propagates_error(monkeypatch):
    from src.activities import bookingActivities
    from src.helpers.bookingHelpers import DownstreamError

    def _raise(*a, **kw):
        raise DownstreamError("seat conflict")

    monkeypatch.setattr(bookingActivities.svc, "reserve_seats", _raise)

    with pytest.raises(DownstreamError):
        await bookingActivities.reserve_seats_activity(1, 11, ["A1"])


@pytest.mark.asyncio
async def test_validate_voucher_activity_returns_dict(monkeypatch):
    from src.activities import bookingActivities

    def _fake(code, base):
        return {"valid": True, "discount_amount": "10000", "message": "ok"}

    monkeypatch.setattr(bookingActivities.svc, "validate_voucher", _fake)

    result = await bookingActivities.validate_voucher_activity("SUMMER", "100000")
    assert result == {"valid": True, "discount_amount": "10000", "message": "ok"}


@pytest.mark.asyncio
async def test_create_payment_activity_returns_id_and_url(monkeypatch):
    from src.activities import bookingActivities

    def _fake(booking_id, amount):
        return {"payment_id": 77, "payment_url": "http://x/pay/77", "status": "PENDING"}

    monkeypatch.setattr(bookingActivities.svc, "create_payment", _fake)

    result = await bookingActivities.create_payment_activity(1, "50000")
    assert result == {"payment_id": 77, "payment_url": "http://x/pay/77"}


@pytest.mark.asyncio
async def test_persist_setup_activity_updates_row(db_session):
    from decimal import Decimal

    from src.activities import bookingActivities
    from src.models.bookingModel import Booking

    b = Booking(
        user_id=1, showtime_id=11, seat_numbers=["A1"], email="x@y.z",
        original_amount=Decimal("100"), discount_amount=Decimal("0"),
        final_amount=Decimal("100"), status="PENDING",
    )
    db_session.add(b); db_session.commit(); db_session.refresh(b)

    await bookingActivities.persist_setup_activity(b.id, 77, "10", "90")

    db_session.refresh(b)
    assert b.payment_id == 77
    assert str(b.discount_amount) == "10.00" or str(b.discount_amount) == "10"
    assert str(b.final_amount) == "90.00" or str(b.final_amount) == "90"
    assert b.status == "AWAITING_PAYMENT"


@pytest.mark.asyncio
async def test_cancel_payment_activity_calls_helper(monkeypatch):
    from src.activities import bookingActivities

    called = []

    def _fake(payment_id):
        called.append(payment_id)

    monkeypatch.setattr(bookingActivities.svc, "cancel_payment", _fake)

    await bookingActivities.cancel_payment_activity(77)
    assert called == [77]
```

If `db_session` fixture doesn't exist, add to `tests/conftest.py`:

```python
@pytest.fixture
def db_session():
    from src.config.database import Base, SessionLocal, engine

    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
```

Also ensure `pytest-asyncio` is in `requirements.txt` (check first — if missing, add `pytest-asyncio==0.23.5` and rebuild).

- [ ] **Step 4.6: Run activity tests — expect fail**

Run: `docker compose run --rm booking-service pytest tests/test_activities.py -k "reserve_seats_activity or validate_voucher_activity or create_payment_activity or persist_setup_activity or cancel_payment_activity" -v`
Expected: FAIL — activities not defined.

- [ ] **Step 4.7: Rewrite `bookingActivities.py`**

Replace `services/bookingService/src/activities/bookingActivities.py` with:

```python
"""Temporal activities for BookingWorkflow.

Each activity is a thin wrapper around `helpers.bookingHelpers`. Some also
update the local `bookings` table (persist_setup, finalize_booking) so the
HTTP API reflects workflow progress.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from temporalio import activity

from ..config.database import SessionLocal
from ..helpers import bookingHelpers as svc
from ..models.bookingModel import Booking


def _update_booking(booking_id: int, **fields) -> None:
    db = SessionLocal()
    try:
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if booking is None:
            return
        for k, v in fields.items():
            setattr(booking, k, v)
        db.commit()
    finally:
        db.close()


# --- Setup activities --------------------------------------------------------


@activity.defn(name="reserve_seats_activity")
async def reserve_seats_activity(
    booking_id: int, showtime_id: int, seat_numbers: list[str]
) -> None:
    svc.reserve_seats(showtime_id, seat_numbers, booking_id)


@activity.defn(name="validate_voucher_activity")
async def validate_voucher_activity(code: str, base_amount: str) -> dict:
    result = svc.validate_voucher(code, Decimal(base_amount))
    return {
        "valid": bool(result.get("valid")),
        "discount_amount": str(result.get("discount_amount") or "0"),
        "message": result.get("message") or "",
    }


@activity.defn(name="create_payment_activity")
async def create_payment_activity(booking_id: int, amount: str) -> dict:
    result = svc.create_payment(booking_id, Decimal(amount))
    return {
        "payment_id": int(result["payment_id"]),
        "payment_url": str(result["payment_url"]),
    }


@activity.defn(name="persist_setup_activity")
async def persist_setup_activity(
    booking_id: int, payment_id: int, discount_amount: str, final_amount: str
) -> None:
    _update_booking(
        booking_id,
        payment_id=payment_id,
        discount_amount=Decimal(discount_amount),
        final_amount=Decimal(final_amount),
        status="AWAITING_PAYMENT",
    )


# --- Compensation / completion activities ------------------------------------


@activity.defn(name="confirm_seats_activity")
async def confirm_seats_activity(booking_id: int) -> None:
    svc.confirm_seats(booking_id)


@activity.defn(name="release_seats_activity")
async def release_seats_activity(booking_id: int) -> None:
    svc.release_seats(booking_id)


@activity.defn(name="redeem_voucher_activity")
async def redeem_voucher_activity(code: Optional[str]) -> None:
    if code:
        svc.redeem_voucher(code)


@activity.defn(name="cancel_payment_activity")
async def cancel_payment_activity(payment_id: int) -> None:
    svc.cancel_payment(payment_id)


@activity.defn(name="send_notification_activity")
async def send_notification_activity(
    user_id: int, email: str, subject: str, body: str
) -> None:
    svc.send_notification(user_id, email, subject, body)


@activity.defn(name="finalize_booking_activity")
async def finalize_booking_activity(
    booking_id: int, status_value: str, reason: Optional[str] = None
) -> None:
    _update_booking(booking_id, status=status_value, failure_reason=reason)


ALL_ACTIVITIES = [
    reserve_seats_activity,
    validate_voucher_activity,
    create_payment_activity,
    persist_setup_activity,
    confirm_seats_activity,
    release_seats_activity,
    redeem_voucher_activity,
    cancel_payment_activity,
    send_notification_activity,
    finalize_booking_activity,
]
```

Note the removal of `check_payment_status` and `_load_booking`.

- [ ] **Step 4.8: Remove obsolete `check_payment_status` tests**

In `services/bookingService/tests/test_activities.py`, delete any test using `check_payment_status` or `_load_booking`. Search with: `grep -n check_payment_status services/bookingService/tests/test_activities.py` and remove those test functions.

- [ ] **Step 4.9: Run all activity tests — expect pass**

Run: `docker compose run --rm booking-service pytest tests/test_activities.py -v`
Expected: all PASS.

- [ ] **Step 4.10: Commit**

```bash
git add services/bookingService/src/helpers/bookingHelpers.py \
        services/bookingService/src/activities/bookingActivities.py \
        services/bookingService/tests/test_activities.py \
        services/bookingService/tests/conftest.py
git commit -m "feat(booking): add saga activities (reserve, validate_voucher, create_payment, persist_setup, cancel_payment)

Remove obsolete check_payment_status; add cancel_payment helper that
tolerates 404 for idempotent compensation."
```

---

## Task 5: Booking Service — workflow rewrite

**Files:**
- Modify: `services/bookingService/src/workflows/bookingWorkflow.py`

- [ ] **Step 5.1: Rewrite `bookingWorkflow.py`**

Replace the entire file with:

```python
"""BookingWorkflow — saga orchestrator per CLAUDE.md.

Setup activities: reserve_seats → validate_voucher → create_payment → persist_setup.
Then waits for `payment_completed` signal (timeout 5 min), then either confirms
or compensates (release_seats + cancel_payment).
"""
from __future__ import annotations

import asyncio
from datetime import timedelta
from decimal import Decimal
from typing import Any, Optional

from temporalio import workflow
from temporalio.exceptions import ActivityError

with workflow.unsafe.imports_passed_through():
    from ..activities.bookingActivities import (
        cancel_payment_activity,
        confirm_seats_activity,
        create_payment_activity,
        finalize_booking_activity,
        persist_setup_activity,
        redeem_voucher_activity,
        release_seats_activity,
        reserve_seats_activity,
        send_notification_activity,
        validate_voucher_activity,
    )


PAYMENT_TIMEOUT_SECONDS = 300  # 5 minutes
ACTIVITY_TIMEOUT = timedelta(seconds=30)


@workflow.defn(name="BookingWorkflow")
class BookingWorkflow:
    def __init__(self) -> None:
        self._state: str = "setting_up"
        self._payment_id: Optional[int] = None
        self._payment_url: Optional[str] = None
        self._error_code: Optional[str] = None
        self._error_message: Optional[str] = None
        self._payment_result: Optional[bool] = None

    @workflow.signal
    def payment_completed(self, success: bool) -> None:
        self._payment_result = bool(success)

    @workflow.query
    def get_setup_result(self) -> dict[str, Any]:
        return {
            "state": self._state,
            "payment_id": self._payment_id,
            "payment_url": self._payment_url,
            "error_code": self._error_code,
            "error_message": self._error_message,
        }

    def _fail(self, code: str, message: str) -> None:
        self._state = "failed"
        self._error_code = code
        self._error_message = message

    @workflow.run
    async def run(self, input: dict[str, Any]) -> str:
        booking_id: int = int(input["booking_id"])
        user_id: int = int(input["user_id"])
        showtime_id: int = int(input["showtime_id"])
        seat_numbers: list[str] = list(input["seat_numbers"])
        voucher_code: Optional[str] = input.get("voucher_code")
        email: str = str(input["email"])
        original_amount = Decimal(str(input["original_amount"]))

        # 1. Reserve seats
        try:
            await workflow.execute_activity(
                reserve_seats_activity,
                args=[booking_id, showtime_id, seat_numbers],
                start_to_close_timeout=ACTIVITY_TIMEOUT,
            )
        except ActivityError as exc:
            self._fail("seat_conflict", str(exc.cause) if exc.cause else str(exc))
            await workflow.execute_activity(
                finalize_booking_activity,
                args=[booking_id, "FAILED", f"reserve_seats: {self._error_message}"],
                start_to_close_timeout=ACTIVITY_TIMEOUT,
            )
            return "FAILED_SETUP"

        # 2. Validate voucher (optional)
        discount = Decimal(0)
        if voucher_code:
            try:
                v = await workflow.execute_activity(
                    validate_voucher_activity,
                    args=[voucher_code, str(original_amount)],
                    start_to_close_timeout=ACTIVITY_TIMEOUT,
                )
            except ActivityError as exc:
                await workflow.execute_activity(
                    release_seats_activity,
                    booking_id,
                    start_to_close_timeout=ACTIVITY_TIMEOUT,
                )
                self._fail("downstream_voucher", str(exc.cause) if exc.cause else str(exc))
                await workflow.execute_activity(
                    finalize_booking_activity,
                    args=[booking_id, "FAILED", f"voucher: {self._error_message}"],
                    start_to_close_timeout=ACTIVITY_TIMEOUT,
                )
                return "FAILED_SETUP"

            if not v["valid"]:
                await workflow.execute_activity(
                    release_seats_activity,
                    booking_id,
                    start_to_close_timeout=ACTIVITY_TIMEOUT,
                )
                self._fail("voucher_invalid", v.get("message") or "Mã giảm giá không hợp lệ")
                await workflow.execute_activity(
                    finalize_booking_activity,
                    args=[booking_id, "FAILED", f"voucher invalid: {self._error_message}"],
                    start_to_close_timeout=ACTIVITY_TIMEOUT,
                )
                return "FAILED_SETUP"

            discount = Decimal(v["discount_amount"])

        final_amount = original_amount - discount
        if final_amount < 0:
            final_amount = Decimal(0)

        # 3. Create payment
        try:
            pay = await workflow.execute_activity(
                create_payment_activity,
                args=[booking_id, str(final_amount)],
                start_to_close_timeout=ACTIVITY_TIMEOUT,
            )
        except ActivityError as exc:
            await workflow.execute_activity(
                release_seats_activity,
                booking_id,
                start_to_close_timeout=ACTIVITY_TIMEOUT,
            )
            self._fail("downstream_payment", str(exc.cause) if exc.cause else str(exc))
            await workflow.execute_activity(
                finalize_booking_activity,
                args=[booking_id, "FAILED", f"payment: {self._error_message}"],
                start_to_close_timeout=ACTIVITY_TIMEOUT,
            )
            return "FAILED_SETUP"

        self._payment_id = int(pay["payment_id"])
        self._payment_url = str(pay["payment_url"])

        # 4. Persist setup results on booking row
        await workflow.execute_activity(
            persist_setup_activity,
            args=[booking_id, self._payment_id, str(discount), str(final_amount)],
            start_to_close_timeout=ACTIVITY_TIMEOUT,
        )
        self._state = "awaiting_payment"

        # 5. Wait for payment_completed signal or timeout
        try:
            await workflow.wait_condition(
                lambda: self._payment_result is not None,
                timeout=timedelta(seconds=PAYMENT_TIMEOUT_SECONDS),
            )
        except asyncio.TimeoutError:
            self._payment_result = False
            reason = "payment timeout"
        else:
            reason = None if self._payment_result else "payment failed"

        if self._payment_result:
            await workflow.execute_activity(
                confirm_seats_activity,
                booking_id,
                start_to_close_timeout=ACTIVITY_TIMEOUT,
            )
            if voucher_code:
                await workflow.execute_activity(
                    redeem_voucher_activity,
                    voucher_code,
                    start_to_close_timeout=ACTIVITY_TIMEOUT,
                )
            await workflow.execute_activity(
                send_notification_activity,
                args=[
                    user_id,
                    email,
                    "Xác nhận đặt vé",
                    f"Đơn đặt vé {booking_id} đã được xác nhận. Chúc bạn xem phim vui vẻ!",
                ],
                start_to_close_timeout=ACTIVITY_TIMEOUT,
            )
            await workflow.execute_activity(
                finalize_booking_activity,
                args=[booking_id, "ACTIVE", None],
                start_to_close_timeout=ACTIVITY_TIMEOUT,
            )
            return "ACTIVE"

        # Compensation: release seats + cancel payment + finalize
        await workflow.execute_activity(
            release_seats_activity,
            booking_id,
            start_to_close_timeout=ACTIVITY_TIMEOUT,
        )
        await workflow.execute_activity(
            cancel_payment_activity,
            self._payment_id,
            start_to_close_timeout=ACTIVITY_TIMEOUT,
        )
        await workflow.execute_activity(
            finalize_booking_activity,
            args=[booking_id, "CANCELLED", reason],
            start_to_close_timeout=ACTIVITY_TIMEOUT,
        )
        return "CANCELLED"
```

- [ ] **Step 5.2: Verify worker imports still work**

Run: `docker compose build booking-service`
Expected: build succeeds.

- [ ] **Step 5.3: Verify worker.py uses `ALL_ACTIVITIES` list**

Confirm `services/bookingService/src/worker.py` imports `ALL_ACTIVITIES` (it does — line 10). No change needed, but verify with `grep ALL_ACTIVITIES services/bookingService/src/worker.py`.

- [ ] **Step 5.4: Commit**

```bash
git add services/bookingService/src/workflows/bookingWorkflow.py
git commit -m "feat(booking): rewrite BookingWorkflow as proper Temporal saga

Setup activities (reserve/validate_voucher/create_payment/persist) run
inside the workflow. Payment waits on signal instead of polling, with
5-minute timeout. Adds @workflow.query get_setup_result for controller
to read payment_url synchronously."
```

---

## Task 6: Booking Service — workflow tests

**Files:**
- Create: `services/bookingService/tests/test_workflow.py`

- [ ] **Step 6.1: Verify `temporalio.testing` available**

Run: `docker compose run --rm booking-service python -c "from temporalio.testing import WorkflowEnvironment; print('ok')"`
Expected: prints `ok`. If ImportError, temporalio was installed without test extras — no extra install needed for `WorkflowEnvironment`, but if this check fails, investigate before proceeding.

- [ ] **Step 6.2: Write workflow tests**

Create `services/bookingService/tests/test_workflow.py`:

```python
"""End-to-end tests for BookingWorkflow using Temporal's time-skipping env.

Activities are replaced by no-op stubs / raising stubs — we only verify
workflow orchestration, not the activity bodies (those are in test_activities).
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
from temporalio import activity
from temporalio.client import Client
from temporalio.exceptions import ApplicationError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker


TASK_QUEUE = "booking-task-queue-test"


def _stub_activities(overrides: dict | None = None) -> list:
    """Build a list of stub activities named to match production ones.

    `overrides` maps activity name → async callable that replaces the default
    no-op stub.
    """
    overrides = overrides or {}
    names = [
        "reserve_seats_activity",
        "validate_voucher_activity",
        "create_payment_activity",
        "persist_setup_activity",
        "confirm_seats_activity",
        "release_seats_activity",
        "redeem_voucher_activity",
        "cancel_payment_activity",
        "send_notification_activity",
        "finalize_booking_activity",
    ]
    stubs = []
    for name in names:
        impl = overrides.get(name, AsyncMock(return_value=None))

        # Wrap in an activity.defn so Temporal recognises it by name
        @activity.defn(name=name)
        async def _stub(*args, _impl=impl, **kwargs):
            return await _impl(*args, **kwargs)

        stubs.append(_stub)
    return stubs


async def _start(
    activity_overrides: dict | None = None,
    voucher_code: str | None = None,
):
    env = await WorkflowEnvironment.start_time_skipping()
    client: Client = env.client
    from src.workflows.bookingWorkflow import BookingWorkflow

    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[BookingWorkflow],
        activities=_stub_activities(activity_overrides),
    )

    wf_input = {
        "booking_id": 1,
        "user_id": 100,
        "showtime_id": 11,
        "seat_numbers": ["A1"],
        "voucher_code": voucher_code,
        "email": "x@y.z",
        "original_amount": "100000",
    }
    return env, client, worker, wf_input


@pytest.mark.asyncio
async def test_happy_path_signal_success():
    create_payment = AsyncMock(return_value={"payment_id": 77, "payment_url": "http://x/77"})
    confirm = AsyncMock()
    send_notif = AsyncMock()
    finalize = AsyncMock()

    env, client, worker, wf_input = await _start({
        "create_payment_activity": create_payment,
        "confirm_seats_activity": confirm,
        "send_notification_activity": send_notif,
        "finalize_booking_activity": finalize,
    })

    async with worker:
        from src.workflows.bookingWorkflow import BookingWorkflow

        handle = await client.start_workflow(
            BookingWorkflow.run, wf_input,
            id=f"booking-{uuid.uuid4()}", task_queue=TASK_QUEUE,
        )
        # Wait for workflow to reach awaiting_payment
        for _ in range(50):
            result = await handle.query("get_setup_result")
            if result["state"] == "awaiting_payment":
                break
        assert result["state"] == "awaiting_payment"
        assert result["payment_url"] == "http://x/77"

        await handle.signal("payment_completed", True)
        assert await handle.result() == "ACTIVE"
        assert confirm.await_count == 1
        assert send_notif.await_count == 1
        finalize.assert_any_await(1, "ACTIVE", None)

    await env.shutdown()


@pytest.mark.asyncio
async def test_signal_failure_triggers_compensation():
    create_payment = AsyncMock(return_value={"payment_id": 77, "payment_url": "http://x/77"})
    release = AsyncMock()
    cancel_pay = AsyncMock()

    env, client, worker, wf_input = await _start({
        "create_payment_activity": create_payment,
        "release_seats_activity": release,
        "cancel_payment_activity": cancel_pay,
    })

    async with worker:
        from src.workflows.bookingWorkflow import BookingWorkflow

        handle = await client.start_workflow(
            BookingWorkflow.run, wf_input,
            id=f"booking-{uuid.uuid4()}", task_queue=TASK_QUEUE,
        )
        for _ in range(50):
            if (await handle.query("get_setup_result"))["state"] == "awaiting_payment":
                break
        await handle.signal("payment_completed", False)
        assert await handle.result() == "CANCELLED"
        assert release.await_count == 1
        assert cancel_pay.await_count == 1

    await env.shutdown()


@pytest.mark.asyncio
async def test_payment_timeout_triggers_compensation():
    create_payment = AsyncMock(return_value={"payment_id": 77, "payment_url": "http://x/77"})
    release = AsyncMock()
    cancel_pay = AsyncMock()

    env, client, worker, wf_input = await _start({
        "create_payment_activity": create_payment,
        "release_seats_activity": release,
        "cancel_payment_activity": cancel_pay,
    })

    async with worker:
        from src.workflows.bookingWorkflow import BookingWorkflow

        handle = await client.start_workflow(
            BookingWorkflow.run, wf_input,
            id=f"booking-{uuid.uuid4()}", task_queue=TASK_QUEUE,
        )
        # Skip past the 5-min timeout — env.sleep skips workflow time instantly
        await env.sleep(310)
        assert await handle.result() == "CANCELLED"
        assert release.await_count == 1
        assert cancel_pay.await_count == 1

    await env.shutdown()


@pytest.mark.asyncio
async def test_seat_conflict_no_compensation():
    async def _conflict(*a, **kw):
        raise ApplicationError("seat conflict")

    release = AsyncMock()

    env, client, worker, wf_input = await _start({
        "reserve_seats_activity": _conflict,
        "release_seats_activity": release,
    })

    async with worker:
        from src.workflows.bookingWorkflow import BookingWorkflow

        handle = await client.start_workflow(
            BookingWorkflow.run, wf_input,
            id=f"booking-{uuid.uuid4()}", task_queue=TASK_QUEUE,
        )
        assert await handle.result() == "FAILED_SETUP"
        result = await handle.query("get_setup_result")
        assert result["state"] == "failed"
        assert result["error_code"] == "seat_conflict"
        assert release.await_count == 0

    await env.shutdown()


@pytest.mark.asyncio
async def test_voucher_invalid_releases_seats():
    voucher = AsyncMock(return_value={"valid": False, "discount_amount": "0", "message": "expired"})
    release = AsyncMock()

    env, client, worker, wf_input = await _start(
        {"validate_voucher_activity": voucher, "release_seats_activity": release},
        voucher_code="BAD",
    )

    async with worker:
        from src.workflows.bookingWorkflow import BookingWorkflow

        handle = await client.start_workflow(
            BookingWorkflow.run, wf_input,
            id=f"booking-{uuid.uuid4()}", task_queue=TASK_QUEUE,
        )
        assert await handle.result() == "FAILED_SETUP"
        result = await handle.query("get_setup_result")
        assert result["error_code"] == "voucher_invalid"
        assert release.await_count == 1

    await env.shutdown()


@pytest.mark.asyncio
async def test_payment_downstream_releases_seats():
    async def _fail_payment(*a, **kw):
        raise ApplicationError("payment service down")

    release = AsyncMock()

    env, client, worker, wf_input = await _start({
        "create_payment_activity": _fail_payment,
        "release_seats_activity": release,
    })

    async with worker:
        from src.workflows.bookingWorkflow import BookingWorkflow

        handle = await client.start_workflow(
            BookingWorkflow.run, wf_input,
            id=f"booking-{uuid.uuid4()}", task_queue=TASK_QUEUE,
        )
        assert await handle.result() == "FAILED_SETUP"
        result = await handle.query("get_setup_result")
        assert result["error_code"] == "downstream_payment"
        assert release.await_count == 1

    await env.shutdown()
```

- [ ] **Step 6.3: Run workflow tests**

Run: `docker compose run --rm booking-service pytest tests/test_workflow.py -v`
Expected: 6 PASS. First run may be slow (time-skipping server startup).

Troubleshooting: if activities raise `NonRetryableError` differences, the default Temporal retry policy will try multiple attempts before giving up. Tests that intentionally fail setup activities may be slow — if flaky, add `retry_policy=RetryPolicy(maximum_attempts=1)` to the relevant `execute_activity` calls in the workflow.

- [ ] **Step 6.4: Commit**

```bash
git add services/bookingService/tests/test_workflow.py
git commit -m "test(booking): add end-to-end workflow tests with Temporal time-skipping env

Covers happy path, signal failure, timeout, seat conflict, voucher invalid,
payment downstream error."
```

---

## Task 7: Booking Service — controller refactor + `_wait_for_setup`

**Files:**
- Modify: `services/bookingService/src/config/temporalClient.py`
- Modify: `services/bookingService/src/controllers/bookingController.py`
- Modify: `services/bookingService/tests/conftest.py`
- Modify: `services/bookingService/tests/test_bookings_api.py`

- [ ] **Step 7.1: Add `query_setup_result_async` helper**

Append to `services/bookingService/src/config/temporalClient.py`:

```python
async def query_setup_result_async(workflow_id: str) -> dict:
    client = await get_temporal_client()
    handle = client.get_workflow_handle(workflow_id)
    return await handle.query("get_setup_result")
```

- [ ] **Step 7.2: Update conftest to patch `_wait_for_setup`**

In `services/bookingService/tests/conftest.py`, update the `client` fixture. Default behavior = setup succeeds with payment_url:

```python
@pytest.fixture
def client(monkeypatch):
    async def _fake_start(workflow_input: dict) -> str:
        return f"booking-{workflow_input['booking_id']}-wf"

    def _fake_wait_for_setup(workflow_id: str, timeout_s: int = 15) -> dict:
        # Default success response — individual tests override via monkeypatch.
        return {
            "state": "awaiting_payment",
            "payment_id": 777,
            "payment_url": "http://payment-service.test/payments/777/checkout",
            "error_code": None,
            "error_message": None,
        }

    from src.config import temporalClient
    from src.controllers import bookingController

    monkeypatch.setattr(temporalClient, "start_booking_workflow", _fake_start)
    monkeypatch.setattr(bookingController, "_wait_for_setup", _fake_wait_for_setup)

    from src.app import app
    from src.config.database import Base, engine

    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)
```

Note: tests that need different setup results will `monkeypatch.setattr(bookingController, "_wait_for_setup", ...)` after getting `client`.

- [ ] **Step 7.3: Write failing controller tests**

Replace the existing happy-path test in `services/bookingService/tests/test_bookings_api.py` and add error-mapping tests. Consult the current file first with `grep -n "def test_" services/bookingService/tests/test_bookings_api.py`; rewrite `test_create_booking_happy_path` to also verify payment flow via `/wait_for_setup`. Then append the error-mapping tests:

```python
def test_create_booking_happy_path(client, respx_mock):
    # fetch_showtime is still called in controller
    respx_mock.get("http://movie-service.test/showtimes/11").respond(
        200, json={"id": 11, "base_price": 50000}
    )

    payload = {
        "user_id": 1, "showtime_id": 11, "seat_numbers": ["A1"],
        "voucher_code": None, "email": "x@y.z",
    }
    r = client.post("/bookings", json=payload)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["booking_id"] >= 1
    assert body["payment_id"] == 777
    assert body["payment_url"].endswith("/payments/777/checkout")
    assert body["status"] == "AWAITING_PAYMENT"


def _override_setup(monkeypatch, result: dict):
    from src.controllers import bookingController

    monkeypatch.setattr(bookingController, "_wait_for_setup", lambda *a, **kw: result)


def test_create_booking_seat_conflict_returns_409(client, respx_mock, monkeypatch):
    respx_mock.get("http://movie-service.test/showtimes/11").respond(
        200, json={"id": 11, "base_price": 50000}
    )
    _override_setup(monkeypatch, {
        "state": "failed",
        "payment_id": None,
        "payment_url": None,
        "error_code": "seat_conflict",
        "error_message": "Ghế A1 đã được đặt",
    })

    r = client.post("/bookings", json={
        "user_id": 1, "showtime_id": 11, "seat_numbers": ["A1"],
        "voucher_code": None, "email": "x@y.z",
    })
    assert r.status_code == 409
    assert "A1" in r.json()["detail"]


def test_create_booking_voucher_invalid_returns_400(client, respx_mock, monkeypatch):
    respx_mock.get("http://movie-service.test/showtimes/11").respond(
        200, json={"id": 11, "base_price": 50000}
    )
    _override_setup(monkeypatch, {
        "state": "failed",
        "error_code": "voucher_invalid",
        "error_message": "Mã giảm giá không hợp lệ",
        "payment_id": None, "payment_url": None,
    })

    r = client.post("/bookings", json={
        "user_id": 1, "showtime_id": 11, "seat_numbers": ["A1"],
        "voucher_code": "BAD", "email": "x@y.z",
    })
    assert r.status_code == 400


def test_create_booking_voucher_downstream_returns_502(client, respx_mock, monkeypatch):
    respx_mock.get("http://movie-service.test/showtimes/11").respond(
        200, json={"id": 11, "base_price": 50000}
    )
    _override_setup(monkeypatch, {
        "state": "failed", "error_code": "downstream_voucher",
        "error_message": "voucher-service 500", "payment_id": None, "payment_url": None,
    })

    r = client.post("/bookings", json={
        "user_id": 1, "showtime_id": 11, "seat_numbers": ["A1"],
        "voucher_code": "X", "email": "x@y.z",
    })
    assert r.status_code == 502


def test_create_booking_payment_downstream_returns_502(client, respx_mock, monkeypatch):
    respx_mock.get("http://movie-service.test/showtimes/11").respond(
        200, json={"id": 11, "base_price": 50000}
    )
    _override_setup(monkeypatch, {
        "state": "failed", "error_code": "downstream_payment",
        "error_message": "payment 503", "payment_id": None, "payment_url": None,
    })

    r = client.post("/bookings", json={
        "user_id": 1, "showtime_id": 11, "seat_numbers": ["A1"],
        "voucher_code": None, "email": "x@y.z",
    })
    assert r.status_code == 502


def test_create_booking_setup_timeout_returns_502(client, respx_mock, monkeypatch):
    respx_mock.get("http://movie-service.test/showtimes/11").respond(
        200, json={"id": 11, "base_price": 50000}
    )
    _override_setup(monkeypatch, {
        "state": "failed", "error_code": "setup_timeout",
        "error_message": "Workflow setup timeout", "payment_id": None, "payment_url": None,
    })

    r = client.post("/bookings", json={
        "user_id": 1, "showtime_id": 11, "seat_numbers": ["A1"],
        "voucher_code": None, "email": "x@y.z",
    })
    assert r.status_code == 502


def test_create_booking_showtime_not_found_returns_404(client, respx_mock):
    respx_mock.get("http://movie-service.test/showtimes/99").respond(404)

    r = client.post("/bookings", json={
        "user_id": 1, "showtime_id": 99, "seat_numbers": ["A1"],
        "voucher_code": None, "email": "x@y.z",
    })
    assert r.status_code == 404
```

Preserve existing `GET /bookings/{id}`, `cancel`, `list_bookings_by_user` tests; they should still pass.

- [ ] **Step 7.4: Run tests — expect fails on error-mapping**

Run: `docker compose run --rm booking-service pytest tests/test_bookings_api.py -v`
Expected: happy path may still pass (if current controller hits `create_payment` helper before workflow). Error-mapping tests will fail until controller refactored.

- [ ] **Step 7.5: Refactor `bookingController.create_booking`**

Replace the contents of `services/bookingService/src/controllers/bookingController.py` with:

```python
from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..helpers import bookingHelpers as svc
from ..models.bookingModel import Booking
from ..validators.bookingSchemas import CreateBookingRequest, CreateBookingResponse


_ERROR_CODE_TO_STATUS = {
    "seat_conflict":      409,
    "voucher_invalid":    400,
    "downstream_voucher": 502,
    "downstream_payment": 502,
    "setup_timeout":      502,
}


def _price_of_showtime(showtime: dict) -> Decimal:
    return Decimal(str(showtime.get("base_price") or 0))


def _start_workflow_sync(workflow_input: dict) -> str:
    from ..config import temporalClient

    return asyncio.run(temporalClient.start_booking_workflow(workflow_input))


async def _wait_for_setup_async(workflow_id: str, timeout_s: int) -> dict[str, Any]:
    from ..config.temporalClient import query_setup_result_async

    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout_s
    while True:
        try:
            result = await query_setup_result_async(workflow_id)
        except Exception:
            result = {"state": "setting_up"}
        state = result.get("state")
        if state in ("awaiting_payment", "failed"):
            return result
        if loop.time() >= deadline:
            return {
                "state": "failed",
                "payment_id": None,
                "payment_url": None,
                "error_code": "setup_timeout",
                "error_message": "Workflow setup timeout",
            }
        await asyncio.sleep(0.2)


def _wait_for_setup(workflow_id: str, timeout_s: int = 15) -> dict[str, Any]:
    return asyncio.run(_wait_for_setup_async(workflow_id, timeout_s))


def create_booking(db: Session, payload: CreateBookingRequest) -> CreateBookingResponse:
    # 1. Fetch showtime (validate + base price)
    try:
        showtime = svc.fetch_showtime(payload.showtime_id)
    except svc.DownstreamError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    seat_count = len(payload.seat_numbers)
    original_amount = _price_of_showtime(showtime) * seat_count

    # 2. Insert booking row (PENDING)
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
    db.add(booking)
    db.commit()
    db.refresh(booking)

    # 3. Start Temporal workflow
    try:
        workflow_id = _start_workflow_sync({
            "booking_id": booking.id,
            "user_id": payload.user_id,
            "showtime_id": payload.showtime_id,
            "seat_numbers": list(payload.seat_numbers),
            "voucher_code": payload.voucher_code,
            "email": payload.email,
            "original_amount": str(original_amount),
        })
    except Exception as exc:
        booking.status = "FAILED"
        booking.failure_reason = f"workflow start failed: {exc}"
        db.commit()
        raise HTTPException(status_code=502, detail="Không thể khởi tạo workflow") from exc

    booking.workflow_id = workflow_id
    db.commit()

    # 4. Wait for setup activities to finish
    result = _wait_for_setup(workflow_id, timeout_s=15)

    # 5. Map to HTTP
    if result.get("state") == "awaiting_payment":
        db.refresh(booking)
        return CreateBookingResponse(
            booking_id=booking.id,
            workflow_id=booking.workflow_id,
            payment_id=booking.payment_id,
            payment_url=result["payment_url"],
            status=booking.status,
            final_amount=booking.final_amount,
        )

    status_code = _ERROR_CODE_TO_STATUS.get(result.get("error_code"), 502)
    raise HTTPException(
        status_code=status_code,
        detail=result.get("error_message") or "Booking setup failed",
    )


def get_booking(db: Session, booking_id: int) -> Booking:
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if booking is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn đặt vé")
    return booking


def list_bookings_by_user(db: Session, user_id: int) -> list[Booking]:
    return (
        db.query(Booking)
        .filter(Booking.user_id == user_id)
        .order_by(Booking.created_at.desc())
        .all()
    )


def cancel_booking(db: Session, booking_id: int) -> Booking:
    booking = get_booking(db, booking_id)
    if booking.status in ("ACTIVE", "CANCELLED"):
        raise HTTPException(
            status_code=400,
            detail=f"Không thể hủy đơn ở trạng thái {booking.status}",
        )

    try:
        svc.release_seats(booking.id)
    except svc.DownstreamError:
        pass

    booking.status = "CANCELLED"
    booking.failure_reason = "cancelled by user"
    db.commit()
    db.refresh(booking)
    return booking
```

- [ ] **Step 7.6: Run bookings API tests — expect pass**

Run: `docker compose run --rm booking-service pytest tests/test_bookings_api.py -v`
Expected: all PASS.

- [ ] **Step 7.7: Full test sweep**

Run: `docker compose run --rm booking-service pytest -v`
Expected: all PASS (activities + workflow + API).

- [ ] **Step 7.8: Commit**

```bash
git add services/bookingService/src/controllers/bookingController.py \
        services/bookingService/src/config/temporalClient.py \
        services/bookingService/tests/conftest.py \
        services/bookingService/tests/test_bookings_api.py
git commit -m "refactor(booking): controller starts workflow, polls query for payment_url

Removes inline reserve_seats/validate_voucher/create_payment calls;
workflow now owns these via activities. Controller polls
get_setup_result query up to 15s, then maps workflow error_code to HTTP
status code (409/400/502 preserved)."
```

---

## Task 8: End-to-end smoke test via docker compose

**Files:** none (manual verification)

- [ ] **Step 8.1: Clean build**

Run: `docker compose build booking-service payment-service`
Expected: both succeed.

- [ ] **Step 8.2: Bring up the stack**

Run: `docker compose up -d mysql-db temporal temporal-ui payment-service booking-service movie-service voucher-service notification-service`
Wait ~30s for services to boot.
Run: `docker compose ps`
Expected: all containers `Up`.

- [ ] **Step 8.3: Seed test data**

If a seed script exists, run it. Otherwise use movie-service endpoints to create a showtime. (Plan doesn't prescribe — reuse whatever teacher template expects.)

- [ ] **Step 8.4: Happy-path booking**

```bash
# Create booking
curl -s -X POST http://localhost:5005/bookings \
  -H 'Content-Type: application/json' \
  -d '{"user_id":1,"showtime_id":1,"seat_numbers":["A1"],"voucher_code":null,"email":"x@y.z"}' | tee /tmp/booking.json

# Extract payment_id
PAY=$(python -c 'import json; print(json.load(open("/tmp/booking.json"))["payment_id"])')

# Confirm payment SUCCESS → should signal workflow
curl -s -X POST http://localhost:5006/payments/$PAY/confirm \
  -H 'Content-Type: application/json' -d '{"success": true}'

# Wait ~2s, then check booking status
sleep 2
BOOKING_ID=$(python -c 'import json; print(json.load(open("/tmp/booking.json"))["booking_id"])')
curl -s http://localhost:5005/bookings/$BOOKING_ID
```

Expected final booking status: `"ACTIVE"`.

- [ ] **Step 8.5: Cancel-path booking**

```bash
curl -s -X POST http://localhost:5005/bookings \
  -H 'Content-Type: application/json' \
  -d '{"user_id":1,"showtime_id":1,"seat_numbers":["A2"],"voucher_code":null,"email":"x@y.z"}' | tee /tmp/booking2.json

PAY=$(python -c 'import json; print(json.load(open("/tmp/booking2.json"))["payment_id"])')
curl -s -X POST http://localhost:5006/payments/$PAY/confirm \
  -H 'Content-Type: application/json' -d '{"success": false}'

sleep 2
BOOKING_ID=$(python -c 'import json; print(json.load(open("/tmp/booking2.json"))["booking_id"])')
curl -s http://localhost:5005/bookings/$BOOKING_ID
curl -s http://localhost:5006/payments/$PAY
```

Expected: booking `status=CANCELLED`, payment `status=CANCELLED`.

- [ ] **Step 8.6: Inspect workflow in Temporal UI**

Open http://localhost:8088 → find workflow `booking-<id>` → verify saga activities executed in order (reserve → validate_voucher skipped → create_payment → persist_setup → confirm_seats → send_notification → finalize_booking, OR the compensation branch for the failed case).

- [ ] **Step 8.7: Tear down**

Run: `docker compose down`

- [ ] **Step 8.8: Final commit (if no code changes were needed)**

Nothing to commit unless smoke tests revealed issues; if they did, loop back to the relevant task.

---

## Done criteria

- [ ] All Task 1–7 test steps pass
- [ ] `docker compose build payment-service booking-service` succeeds
- [ ] Task 8 smoke tests produce expected booking/payment statuses
- [ ] Spec `docs/api-specs/PaymentService.yaml` includes `cancelPayment`
- [ ] No references remain to `check_payment_status` (grep sanity: `grep -r check_payment_status services/bookingService`)
