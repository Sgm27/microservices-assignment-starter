#  Báo cáo công việc — Thành Viên 3

**Phạm vi phụ trách:**
- Phân tích & thiết kế hệ thống cho luồng nghiệp vụ đặt vé.
- Implement **Payment Service** (port 5006) — tạo VNPay payment URL, nhận kết quả, expose trạng thái payment cho các service khác.
- Implement **Booking Service** (port 5005) — **Temporal saga orchestrator** điều phối toàn bộ flow đặt vé: giữ ghế → áp voucher → tạo payment → chờ thanh toán → xác nhận / compensate.

> Stack: Python 3.11 + FastAPI + SQLAlchemy + PyMySQL + Pydantic v2 + Temporal Python SDK (temporalio 1.7.1).

---

## 1. Phân tích & thiết kế (Analysis & Design)

### 1.1 Bài toán

Luồng "đặt vé xem phim" là một **distributed transaction** — nó đụng tới nhiều service khác nhau (movie, voucher, payment, notification) nhưng phải đảm bảo tính nhất quán: nếu thanh toán thất bại thì ghế phải được nhả; nếu thanh toán thành công thì ghế phải được confirm và voucher phải được redeem.

### 1.2 Lựa chọn thiết kế: Saga Orchestration bằng Temporal

Thành viên 3 chọn pattern **Saga Orchestration** thay cho **Choreography (event-driven)** với các lý do:

| Tiêu chí | Orchestration (Temporal) | Choreography |
| --- | --- | --- |
| Khả năng quan sát flow | Tập trung 1 workflow, xem trên Temporal UI | Phải trace log qua nhiều service |
| Compensation logic | Viết tường minh trong workflow | Mỗi service tự viết reverse event |
| Thời gian chờ lâu (human-in-the-loop) | Temporal hỗ trợ native (sleep/timer) | Cần state store riêng |

Temporal đảm nhiệm:
- Lưu trữ state của workflow (nếu worker chết vẫn resume).
- Retry tự động cho mỗi activity.
- Timeout cho bước chờ thanh toán (5 phút).

### 1.3 Các bước của Saga

```
POST /bookings (sync HTTP trong controller)
 ├─ Step 1: fetch showtime          → movieService
 ├─ Step 2: persist booking PENDING → booking_db
 ├─ Step 3: reserve seats           → movieService   (compensate: release_seats)
 ├─ Step 4: validate voucher        → voucherService (compensate: release_seats)
 ├─ Step 5: create payment          → paymentService (compensate: release_seats)
 ├─ Step 6: persist AWAITING_PAYMENT
 └─ Step 7: start Temporal workflow → trả payment_url cho client

[Worker] BookingWorkflow (async)
 ├─ Poll check_payment_status mỗi 5s, tối đa 300s
 ├─ SUCCESS  → confirm_seats + redeem_voucher + send_notification + finalize(ACTIVE)
 └─ FAIL/TIMEOUT → release_seats + finalize(CANCELLED)
```

### 1.4 Hai thành phần triển khai (deployment split)

Trong [docker-compose.yaml:213-267](../docker-compose.yaml#L213-L267), Booking Service được chạy thành **2 container**:

| Container | Command | Vai trò |
| --- | --- | --- |
| `bookingService` | `uvicorn src.app:app` | HTTP API (POST /bookings, GET, cancel) |
| `bookingWorker` | `python -m src.worker` | Temporal worker xử lý BookingWorkflow + activities |

Cả hai cùng dùng cùng 1 image Docker, cùng DB, cùng kết nối Temporal task queue `booking-task-queue` — tách process để API không block mà vẫn chia sẻ model.

---

## 2. Payment Service (port 5006)

### 2.1 Cấu trúc thư mục

```
services/paymentService/
  Dockerfile
  requirements.txt
  seed.py
  src/
    app.py                    # FastAPI factory
    main.py                   # uvicorn entry
    config/
      database.py             # SQLAlchemy engine + get_db()
      settings.py             # pydantic-settings (VNPAY_*, SELF_BASE_URL)
    controllers/paymentController.py
    helpers/vnpayHelper.py    # build_payment_url
    models/paymentModel.py    # bảng payments
    routes/paymentRoutes.py
    validators/paymentSchemas.py
    static/vnpay-qr.png
  tests/
    conftest.py
    test_health.py
    test_payments.py          # 9 test cases
```

### 2.2 Model dữ liệu — bảng `payments`

Khai báo tại [services/paymentService/src/models/paymentModel.py:10-28](../services/paymentService/src/models/paymentModel.py#L10-L28):

| Cột | Kiểu | Ghi chú |
| --- | --- | --- |
| `id` | INT PK auto | |
| `booking_id` | INT UNIQUE | 1 booking = 1 payment (chống double-charge) |
| `amount` | NUMERIC(12,2) | |
| `status` | VARCHAR(16) | `PENDING` / `SUCCESS` / `FAILED` / `CANCELLED` |
| `provider` | VARCHAR(32) | `vnpay` |
| `payment_url` | VARCHAR(1024) | URL dẫn tới trang thanh toán |
| `provider_txn_id` | VARCHAR(128) | Mã giao dịch phía provider |
| `created_at` / `updated_at` | DATETIME | `onupdate=datetime.utcnow` |

Constraint `booking_id UNIQUE` (dòng 14) là đường biên chống việc tạo 2 payment cho cùng 1 booking — logic này còn được kiểm tra lại trong controller (409 Conflict).

### 2.3 Pydantic schemas (validation)

Tại [services/paymentService/src/validators/paymentSchemas.py](../services/paymentService/src/validators/paymentSchemas.py):

- `CreatePaymentRequest` (dòng 8-11): `booking_id > 0`, `amount > 0`.
- `CreatePaymentResponse` (dòng 14-17): `payment_id`, `payment_url`, `status`.
- `ConfirmPaymentRequest` (dòng 20-21): chỉ có `success: bool`.
- `PaymentDetail` (dòng 24-35): full view, bật `from_attributes=True` để map từ ORM.

### 2.4 Danh sách API endpoint

| Method | Path | Handler (route) | Controller |
| --- | --- | --- | --- |
| GET | `/health` | [app.py:28-30](../services/paymentService/src/app.py#L28-L30) | inline |
| POST | `/payments/create` | [paymentRoutes.py:18-22](../services/paymentService/src/routes/paymentRoutes.py#L18-L22) | `paymentController.create_payment` |
| GET | `/payments/vnpay-return` | [paymentRoutes.py:25-34](../services/paymentService/src/routes/paymentRoutes.py#L25-L34) | skeleton — trả JSON redirect |
| GET | `/payments/by-booking/{booking_id}` | [paymentRoutes.py:37-39](../services/paymentService/src/routes/paymentRoutes.py#L37-L39) | `paymentController.get_by_booking_id` |
| GET | `/payments/{payment_id}/checkout` | [paymentRoutes.py:42-186](../services/paymentService/src/routes/paymentRoutes.py#L42-L186) | controller `get_by_id` + render HTML inline |
| POST | `/payments/{payment_id}/confirm` | [paymentRoutes.py:189-195](../services/paymentService/src/routes/paymentRoutes.py#L189-L195) | `paymentController.confirm_payment` |
| GET | `/payments/{payment_id}` | [paymentRoutes.py:198-200](../services/paymentService/src/routes/paymentRoutes.py#L198-L200) | `paymentController.get_by_id` |

> Router được mount với prefix `/payments` tại [paymentRoutes.py:15](../services/paymentService/src/routes/paymentRoutes.py#L15) và include vào FastAPI app tại [app.py:32](../services/paymentService/src/app.py#L32).

### 2.5 Chi tiết implementation từng API

#### 2.5.1 `GET /health`
- **File / dòng**: [src/app.py:28-30](../services/paymentService/src/app.py#L28-L30).
- **Logic**: trả `{"status": "ok"}`. Dùng cho Docker healthcheck + CLAUDE.md yêu cầu mọi service phải có.

#### 2.5.2 `POST /payments/create`
- **Route**: [paymentRoutes.py:18-22](../services/paymentService/src/routes/paymentRoutes.py#L18-L22) — `status_code=201`, response model `CreatePaymentResponse`.
- **Controller**: `create_payment` tại [paymentController.py:21-52](../services/paymentService/src/controllers/paymentController.py#L21-L52).
- **Flow**:
  1. Query Payment theo `booking_id`; nếu tồn tại → raise 409 (“Đơn thanh toán đã tồn tại cho đơn đặt vé này”).
  2. Insert row `Payment(status="PENDING", provider="vnpay")` → commit → refresh lấy `id`.
  3. Build URL bằng [vnpayHelper.build_payment_url](../services/paymentService/src/helpers/vnpayHelper.py#L7-L9) → `{SELF_BASE_URL}/payments/{id}/checkout`.
  4. Cập nhật `payment_url` vào DB (2-phase: insert rồi mới biết id để build URL).
  5. Trả `CreatePaymentResponse`.

#### 2.5.3 `GET /payments/{payment_id}`
- **Route**: [paymentRoutes.py:198-200](../services/paymentService/src/routes/paymentRoutes.py#L198-L200).
- **Controller**: `get_by_id` tại [paymentController.py:55-62](../services/paymentService/src/controllers/paymentController.py#L55-L62) — query theo PK, 404 nếu không có.
- **Ý nghĩa**: đây là endpoint **booking workflow poll** để biết payment đã SUCCESS/FAILED chưa.

#### 2.5.4 `GET /payments/by-booking/{booking_id}`
- **Route**: [paymentRoutes.py:37-39](../services/paymentService/src/routes/paymentRoutes.py#L37-L39).
- **Controller**: `get_by_booking_id` tại [paymentController.py:65-72](../services/paymentService/src/controllers/paymentController.py#L65-L72).
- **Ý nghĩa**: tiện cho UI/booking service lookup theo booking_id.

#### 2.5.5 `GET /payments/{payment_id}/checkout`
- **File / dòng**: [paymentRoutes.py:42-186](../services/paymentService/src/routes/paymentRoutes.py#L42-L186) (trả về `HTMLResponse`).
- **Logic**: render 1 trang HTML inline tiếng Việt — giao diện VNPay với số tiền, ảnh QR tĩnh `/static/vnpay-qr.png` (mount tại [app.py:26](../services/paymentService/src/app.py#L26)), 2 nút "Đã thanh toán" / "Huỷ". Nút gọi AJAX `POST /payments/{id}/confirm`. Mã JS embed trong response HTML.

#### 2.5.6 `POST /payments/{payment_id}/confirm`
- **Route**: [paymentRoutes.py:189-195](../services/paymentService/src/routes/paymentRoutes.py#L189-L195).
- **Controller**: `confirm_payment` tại [paymentController.py:75-95](../services/paymentService/src/controllers/paymentController.py#L75-L95).
- **Flow**:
  1. Tìm payment → 404 nếu không có.
  2. Kiểm tra `status in FINAL_STATUSES = {SUCCESS, FAILED, CANCELLED}` → 400 (chặn confirm 2 lần — idempotency).
  3. Cập nhật `status = SUCCESS|FAILED`, `provider_txn_id = f"vnpay-{id}"` → commit.
- **Đây là điểm trigger kết quả** — khi confirm_payment chạy xong, workflow poll tiếp theo sẽ nhận được `SUCCESS`/`FAILED` và thoát vòng lặp.

#### 2.5.7 `GET /payments/vnpay-return`
- **File / dòng**: [paymentRoutes.py:25-34](../services/paymentService/src/routes/paymentRoutes.py#L25-L34).
- **Trạng thái**: **skeleton** — hiện trả `{"redirect_url": ..., "status": "success"}`. Phần verify `vnp_SecureHash` và cập nhật DB sẽ được hoàn thiện ở bước tích hợp VNPay thật.

### 2.6 Cấu hình (settings)

[services/paymentService/src/config/settings.py:7-35](../services/paymentService/src/config/settings.py#L7-L35):
- `VNPAY_TMN_CODE`, `VNPAY_HASH_SECRET`, `VNPAY_PAYMENT_URL`, `VNPAY_RETURN_URL`, `VNPAY_FRONTEND_RETURN_URL`.
- `SELF_BASE_URL` — URL base của service, dùng để build payment URL (do container cần URL client-accessible, không phải `http://payment-service:5006`).
- `@lru_cache def get_settings()` tại dòng 38-40 — cache để tránh re-parse env mỗi request.

### 2.7 Test coverage

[tests/test_payments.py](../services/paymentService/tests/test_payments.py) — 9 test:
- `test_create_payment_returns_url`
- `test_create_payment_duplicate_booking_id` (409)
- `test_get_payment_by_id`
- `test_get_payment_by_booking_id`
- `test_get_payment_not_found` (404)
- `test_confirm_payment_success` (status=SUCCESS + provider_txn_id)
- `test_confirm_payment_failure` (status=FAILED)
- `test_confirm_payment_already_finalized` (400 khi confirm lần 2)
- `test_checkout_page_renders` (HTML 200)

Fixture tại [tests/conftest.py:1-26](../services/paymentService/tests/conftest.py#L1-L26) — dùng SQLite in-memory, `SELF_BASE_URL=http://testserver`.

---

## 3. Booking Service (port 5005) — Temporal Saga Orchestrator

### 3.1 Cấu trúc thư mục (đặc thù có `workflows/`, `activities/`, `worker.py`)

```
services/bookingService/
  src/
    app.py                         # FastAPI factory (HTTP API container)
    main.py                        # uvicorn entry
    worker.py                      # Temporal worker entry (bookingWorker container)
    config/
      database.py
      settings.py                  # TEMPORAL_HOST, TEMPORAL_TASK_QUEUE, *_SERVICE_URL
      temporalClient.py            # start/cancel workflow helper
    controllers/bookingController.py
    helpers/bookingHelpers.py      # HTTP client tới tất cả downstream services
    models/bookingModel.py         # bảng bookings
    routes/bookingRoutes.py
    validators/bookingSchemas.py
    workflows/bookingWorkflow.py   # @workflow.defn BookingWorkflow
    activities/bookingActivities.py# 6 @activity.defn
  tests/
    conftest.py
    test_health.py
    test_bookings_api.py           # 8 test API
    test_activities.py             # 4 test activity
```

### 3.2 Model — bảng `bookings`

[src/models/bookingModel.py:10-33](../services/bookingService/src/models/bookingModel.py#L10-L33):

| Cột | Kiểu | Ghi chú |
| --- | --- | --- |
| `id` | INT PK | |
| `user_id` | INT | index |
| `showtime_id` | INT | index |
| `seat_numbers` | JSON | list các ghế, tối đa 10 (validator) |
| `voucher_code` | VARCHAR(64) nullable | |
| `email` | VARCHAR(255) | dùng gửi notification |
| `original_amount` / `discount_amount` / `final_amount` | NUMERIC(12,2) | |
| `payment_id` | INT nullable | FK logic tới payment_db.payments |
| `workflow_id` | VARCHAR(128) nullable | ID Temporal workflow (format `booking-{id}`) |
| `status` | VARCHAR(24) | `PENDING`→`AWAITING_PAYMENT`→`ACTIVE`/`CANCELLED`/`FAILED` |
| `failure_reason` | VARCHAR(512) | log lý do fail |
| `created_at` / `updated_at` | DATETIME | |

### 3.3 Pydantic schemas

[src/validators/bookingSchemas.py](../services/bookingService/src/validators/bookingSchemas.py):
- `CreateBookingRequest` (dòng 8-13): validate `user_id`/`showtime_id >= 1`, `seat_numbers` min=1 max=10, `email: EmailStr`.
- `CreateBookingResponse` (dòng 16-22): trả `booking_id`, `workflow_id`, `payment_id`, `payment_url`, `status`, `final_amount`.
- `BookingDetail` (dòng 25-42): full view; `ConfigDict(from_attributes=True)` để map ORM.

### 3.4 Danh sách API endpoint

| Method | Path | Handler (route) | Controller |
| --- | --- | --- | --- |
| GET | `/health` | [app.py:21-23](../services/bookingService/src/app.py#L21-L23) | inline |
| POST | `/bookings` | [bookingRoutes.py:15-17](../services/bookingService/src/routes/bookingRoutes.py#L15-L17) | `bookingController.create_booking` |
| GET | `/bookings/{booking_id}` | [bookingRoutes.py:20-22](../services/bookingService/src/routes/bookingRoutes.py#L20-L22) | `bookingController.get_booking` |
| GET | `/bookings/user/{user_id}` | [bookingRoutes.py:25-28](../services/bookingService/src/routes/bookingRoutes.py#L25-L28) | `bookingController.list_bookings_by_user` |
| POST | `/bookings/{booking_id}/cancel` | [bookingRoutes.py:31-33](../services/bookingService/src/routes/bookingRoutes.py#L31-L33) | `bookingController.cancel_booking` |

### 3.5 Chi tiết implementation từng API

#### 3.5.1 `POST /bookings` — khởi tạo saga
- **Route**: [bookingRoutes.py:15-17](../services/bookingService/src/routes/bookingRoutes.py#L15-L17) (status=201).
- **Controller**: `create_booking` tại [bookingController.py:28-131](../services/bookingService/src/controllers/bookingController.py#L28-L131).
- **Flow (7 bước trong 1 HTTP handler, đoạn tiền-workflow)**:

| Bước | Dòng | Mô tả | Nếu lỗi |
| --- | --- | --- | --- |
| 1. Fetch showtime | [31-33](../services/bookingService/src/controllers/bookingController.py#L31-L33) | Gọi `svc.fetch_showtime(showtime_id)` → lấy `base_price` | 404 "showtime not found" |
| 2. Tính amount | [35-37](../services/bookingService/src/controllers/bookingController.py#L35-L37) | `original_amount = unit_price * seat_count` | — |
| 3. Persist PENDING | [40-53](../services/bookingService/src/controllers/bookingController.py#L40-L53) | Insert `Booking(status="PENDING", discount=0, final=original)` | — |
| 4. Reserve seats | [56-62](../services/bookingService/src/controllers/bookingController.py#L56-L62) | `svc.reserve_seats(showtime_id, seat_numbers, booking_id)` | status=FAILED + 409 |
| 5. Validate voucher | [65-81](../services/bookingService/src/controllers/bookingController.py#L65-L81) | Chỉ gọi khi có `voucher_code`. Nếu voucher invalid **release_seats (compensate)** rồi raise 400 | status=FAILED + compensate |
| 6. Tính final_amount | [83-85](../services/bookingService/src/controllers/bookingController.py#L83-L85) | `(original - discount).quantize(0.01)`, clamp ≥ 0 | — |
| 7. Create payment | [88-95](../services/bookingService/src/controllers/bookingController.py#L88-L95) | `svc.create_payment(booking_id, final_amount)` → nhận `payment_id`, `payment_url` | **release_seats** rồi raise 502 |
| 8. Persist AWAITING | [97-102](../services/bookingService/src/controllers/bookingController.py#L97-L102) | Update discount/final/payment_id, `status = AWAITING_PAYMENT` | — |
| 9. Start Temporal | [105-122](../services/bookingService/src/controllers/bookingController.py#L105-L122) | `_start_workflow_sync` → gọi `temporalClient.start_booking_workflow` | log failure_reason, **không fail HTTP** (client đã có `payment_url`) |
| 10. Response | [124-131](../services/bookingService/src/controllers/bookingController.py#L124-L131) | Trả `CreateBookingResponse(booking_id, workflow_id, payment_id, payment_url, status, final_amount)` | — |

**Điểm kỹ thuật quan trọng:**
- `_start_workflow_sync` tại [bookingController.py:18-25](../services/bookingService/src/controllers/bookingController.py#L18-L25) dùng `asyncio.run()` để gọi async Temporal client từ **sync handler** (FastAPI sync route). Comment giải thích rõ `import lazy` để test dễ `monkeypatch`.
- Các compensating action (`release_seats`) được gọi inline trong controller trước khi workflow kịp chạy — bởi tại thời điểm này chưa có Temporal workflow nào tồn tại để rollback.

#### 3.5.2 `GET /bookings/{booking_id}`
- **Route**: [bookingRoutes.py:20-22](../services/bookingService/src/routes/bookingRoutes.py#L20-L22).
- **Controller**: `get_booking` tại [bookingController.py:134-138](../services/bookingService/src/controllers/bookingController.py#L134-L138) — 404 nếu không tồn tại.
- **Ý nghĩa**: UI dùng để polling trạng thái booking (AWAITING_PAYMENT → ACTIVE/CANCELLED).

#### 3.5.3 `GET /bookings/user/{user_id}`
- **Route**: [bookingRoutes.py:25-28](../services/bookingService/src/routes/bookingRoutes.py#L25-L28).
- **Controller**: `list_bookings_by_user` tại [bookingController.py:141-147](../services/bookingService/src/controllers/bookingController.py#L141-L147) — trả list order by `created_at DESC`.

#### 3.5.4 `POST /bookings/{booking_id}/cancel`
- **Route**: [bookingRoutes.py:31-33](../services/bookingService/src/routes/bookingRoutes.py#L31-L33).
- **Controller**: `cancel_booking` tại [bookingController.py:150-165](../services/bookingService/src/controllers/bookingController.py#L150-L165).
- **Flow**:
  1. Lấy booking (404 nếu không có).
  2. Chặn hủy nếu status là `ACTIVE`/`CANCELLED` — 400.
  3. Best-effort `release_seats` (swallow `DownstreamError` — idempotent).
  4. Set `status=CANCELLED`, `failure_reason="cancelled by user"`, commit.

### 3.6 Helpers — HTTP client tới downstream services

[src/helpers/bookingHelpers.py](../services/bookingService/src/helpers/bookingHelpers.py) — **điểm hội tụ giao tiếp liên service**:

| Hàm | Dòng | Gọi tới |
| --- | --- | --- |
| `fetch_showtime` | [27-35](../services/bookingService/src/helpers/bookingHelpers.py#L27-L35) | `GET {MOVIE}/showtimes/{id}` |
| `reserve_seats` | [38-46](../services/bookingService/src/helpers/bookingHelpers.py#L38-L46) | `POST {MOVIE}/seats/reserve` |
| `confirm_seats` | [49-57](../services/bookingService/src/helpers/bookingHelpers.py#L49-L57) | `POST {MOVIE}/seats/confirm` |
| `release_seats` | [60-68](../services/bookingService/src/helpers/bookingHelpers.py#L60-L68) | `POST {MOVIE}/seats/release` |
| `validate_voucher` | [74-83](../services/bookingService/src/helpers/bookingHelpers.py#L74-L83) | `POST {VOUCHER}/vouchers/validate` |
| `redeem_voucher` | [86-94](../services/bookingService/src/helpers/bookingHelpers.py#L86-L94) | `POST {VOUCHER}/vouchers/redeem` |
| `create_payment` | [100-109](../services/bookingService/src/helpers/bookingHelpers.py#L100-L109) | `POST {PAYMENT}/payments/create` |
| `fetch_payment` | [112-120](../services/bookingService/src/helpers/bookingHelpers.py#L112-L120) | `GET {PAYMENT}/payments/{id}` |
| `send_notification` | [126-134](../services/bookingService/src/helpers/bookingHelpers.py#L126-L134) | `POST {NOTIFICATION}/notifications/send` |

Tất cả dùng **httpx synchronous** (để dùng chung cả controller sync + activity) và raise `DownstreamError` khi non-2xx (class định nghĩa tại dòng 16-17). Nhờ vậy test dùng `respx` stub được thẳng HTTP.

### 3.7 Temporal Workflow — `BookingWorkflow`

[src/workflows/bookingWorkflow.py:25-92](../services/bookingService/src/workflows/bookingWorkflow.py#L25-L92):

**Config**:
- `POLL_INTERVAL_SECONDS = 5` (dòng 21)
- `PAYMENT_TIMEOUT_SECONDS = 300` (dòng 22) — 5 phút.

**Run method** (dòng 27-92):

```
INPUT: {booking_id, payment_id, user_id, email, voucher_code}

1. Poll loop (dòng 36-48):
   while elapsed < 300:
     status = execute_activity(check_payment_status, timeout=30s)
     if status in (SUCCESS, FAILED, CANCELLED): break
     await asyncio.sleep(5)
     elapsed += 5

2. Branch SUCCESS (dòng 51-78):
   - execute_activity(confirm_seats_activity, booking_id)
   - if voucher_code: execute_activity(redeem_voucher_activity, voucher_code)
   - execute_activity(send_notification_activity,
       args=[user_id, email, "Xác nhận đặt vé",
             f"Đơn đặt vé {booking_id} đã được xác nhận..."])
   - execute_activity(finalize_booking_activity, args=[booking_id, "ACTIVE", None])
   → return "ACTIVE"

3. Branch FAIL/TIMEOUT (dòng 81-92):
   reason = "payment failed/cancelled" or "payment timeout"
   - execute_activity(release_seats_activity, booking_id)       ← COMPENSATE
   - execute_activity(finalize_booking_activity, args=[booking_id, "CANCELLED", reason])
   → return "CANCELLED"
```

**Ghi chú kỹ thuật**:
- Mọi activity đều có `start_to_close_timeout=30s`.
- Import activities đặt trong `workflow.unsafe.imports_passed_through()` (dòng 10-18) — yêu cầu của Temporal sandbox để tránh side-effect khi replay.
- Workflow là **deterministic** — dùng `asyncio.sleep` Temporal-aware, không phải time thực.

### 3.8 Activities — 6 hàm `@activity.defn`

[src/activities/bookingActivities.py](../services/bookingService/src/activities/bookingActivities.py):

| Activity | Dòng | Công việc |
| --- | --- | --- |
| `check_payment_status(payment_id)` | [39-43](../services/bookingService/src/activities/bookingActivities.py#L39-L43) | `svc.fetch_payment` → trả `status` |
| `confirm_seats_activity(booking_id)` | [46-48](../services/bookingService/src/activities/bookingActivities.py#L46-L48) | Gọi movieService `/seats/confirm` |
| `release_seats_activity(booking_id)` | [51-53](../services/bookingService/src/activities/bookingActivities.py#L51-L53) | **Compensate** — movieService `/seats/release` |
| `redeem_voucher_activity(code)` | [56-59](../services/bookingService/src/activities/bookingActivities.py#L56-L59) | Gọi voucherService `/vouchers/redeem` (no-op nếu `None`) |
| `send_notification_activity(user_id, email, subject, body)` | [62-66](../services/bookingService/src/activities/bookingActivities.py#L62-L66) | Gọi notificationService `/notifications/send` |
| `finalize_booking_activity(booking_id, status, reason)` | [69-73](../services/bookingService/src/activities/bookingActivities.py#L69-L73) | Ghi `status` + `failure_reason` vào `booking_db` |

Helpers nội bộ:
- `_load_booking` (dòng 18-23) — mở `SessionLocal` để query trong activity.
- `_update_booking` (dòng 26-36) — pattern open/commit/close từng activity (vì `get_db` là FastAPI dependency, không dùng được trong worker).

Export `ALL_ACTIVITIES` tại dòng 76-83 — được worker đọc để register.

### 3.9 Temporal Client wrapper

[src/config/temporalClient.py](../services/bookingService/src/config/temporalClient.py):

| Hàm | Dòng | Công việc |
| --- | --- | --- |
| `get_temporal_client()` | [13-17](../services/bookingService/src/config/temporalClient.py#L13-L17) | `Client.connect(TEMPORAL_HOST, namespace=TEMPORAL_NAMESPACE)` |
| `start_booking_workflow(input)` | [20-33](../services/bookingService/src/config/temporalClient.py#L20-L33) | `start_workflow(BookingWorkflow.run, input, id=f"booking-{id}", task_queue=...)` |
| `cancel_booking_workflow(workflow_id)` | [36-39](../services/bookingService/src/config/temporalClient.py#L36-L39) | `handle.cancel()` |

**Design note**: `workflow_id = f"booking-{booking_id}"` — dùng booking_id làm ID ⇒ tự động idempotent (Temporal sẽ reject nếu gọi 2 lần với cùng ID).

### 3.10 Worker process

[src/worker.py](../services/bookingService/src/worker.py) — file entry riêng cho container `bookingWorker`:

1. Dòng 21: `Base.metadata.create_all(bind=engine)` — đảm bảo schema tồn tại.
2. Dòng 24: connect Temporal.
3. Dòng 26-31: khởi tạo `Worker(client, task_queue, workflows=[BookingWorkflow], activities=ALL_ACTIVITIES)`.
4. Dòng 33: `worker.run()` — block forever.

Chạy qua command trong docker-compose: `python -m src.worker` ([docker-compose.yaml:248](../docker-compose.yaml#L248)).

### 3.11 Settings

[src/config/settings.py:7-45](../services/bookingService/src/config/settings.py#L7-L45):
- Downstream URLs: `MOVIE_SERVICE_URL`, `VOUCHER_SERVICE_URL`, `PAYMENT_SERVICE_URL`, `NOTIFICATION_SERVICE_URL`.
- Temporal: `TEMPORAL_HOST=temporal:7233`, `TEMPORAL_NAMESPACE=default`, `TEMPORAL_TASK_QUEUE=booking-task-queue`.
- Polling tunables: `PAYMENT_POLL_INTERVAL_SECONDS=5`, `PAYMENT_TIMEOUT_SECONDS=300`.
- `HTTP_TIMEOUT_SECONDS: float = 10.0` cho mọi request httpx.

### 3.12 Test coverage

[tests/test_bookings_api.py](../services/bookingService/tests/test_bookings_api.py) — 8 test API:
- `test_create_booking_happy_path_no_voucher` — verify 2 ghế × 100000 → 200000, workflow được gọi.
- `test_create_booking_with_valid_voucher` — discount 20000 → final 180000.
- `test_create_booking_invalid_voucher_releases_seats` — chứng minh **compensate release_seats**.
- `test_create_booking_seat_conflict` — 409.
- `test_create_booking_showtime_not_found` — 404.
- `test_get_booking_and_list_by_user`, `test_get_booking_not_found`.
- `test_cancel_booking_releases_seats` — verify cancel gọi release.

[tests/test_activities.py](../services/bookingService/tests/test_activities.py) — 4 test activity chạy dưới dạng coroutine:
- `test_check_payment_status_returns_remote_status`.
- `test_confirm_and_release_seats_call_movie_service`.
- `test_redeem_voucher_noop_when_none_and_calls_when_set` — chứng minh no-op khi voucher=None.
- `test_send_notification_posts_payload`.

Test dùng `respx.mock` stub HTTP + `monkeypatch` `start_booking_workflow` (conftest dòng 19-27) để không cần Temporal server thật.

---

## 4. Tích hợp Docker Compose

**Payment Service** — [docker-compose.yaml:186-211](../docker-compose.yaml#L186-L211):
- Build từ `./services/paymentService`.
- Expose `PAYMENT_SERVICE_PORT` (5006).
- Env: `VNPAY_*`, `BOOKING_SERVICE_URL`.
- Depends on: `mysql-db` (healthy).

**Booking Service + Worker** — [docker-compose.yaml:213-267](../docker-compose.yaml#L213-L267):
- `booking-service`: HTTP API, expose 5005, depends_on `mysql-db` + `temporal`.
- `booking-worker`: cùng image, khác command `python -m src.worker`, depends_on `booking-service` + `temporal`.
- Cả hai đều biết URL của 4 service downstream (movie, voucher, payment, notification) để gọi HTTP.

**Temporal stack** — [docker-compose.yaml:28-76](../docker-compose.yaml#L28-L76):
- `temporal-postgres` (backend) → `temporal` (server 7233) → `temporal-ui` (8088→8080).

---

## 5. OpenAPI specs

Thành viên 3 cũng duy trì 2 file OpenAPI tại [docs/api-specs/](../docs/api-specs/):
- [BookingService.yaml](../docs/api-specs/BookingService.yaml) — describe 5 endpoint + schemas.
- [PaymentService.yaml](../docs/api-specs/PaymentService.yaml) — describe 7 endpoint + schemas.

---

## 6. Tổng kết đóng góp của Thành Viên 3

| Hạng mục | Số file | Số dòng chính | File quan trọng nhất |
| --- | --- | --- | --- |
| Payment Service — source | 9 `.py` | ~220 dòng logic | [paymentController.py](../services/paymentService/src/controllers/paymentController.py), [paymentRoutes.py](../services/paymentService/src/routes/paymentRoutes.py) (có cả checkout page) |
| Payment Service — tests | 2 | ~100 dòng | [test_payments.py](../services/paymentService/tests/test_payments.py) |
| Booking Service — source | 13 `.py` | ~470 dòng logic | [bookingController.py](../services/bookingService/src/controllers/bookingController.py) (saga sync), [bookingWorkflow.py](../services/bookingService/src/workflows/bookingWorkflow.py) (Temporal), [bookingActivities.py](../services/bookingService/src/activities/bookingActivities.py), [bookingHelpers.py](../services/bookingService/src/helpers/bookingHelpers.py) |
| Booking Service — tests | 3 | ~220 dòng | [test_bookings_api.py](../services/bookingService/tests/test_bookings_api.py), [test_activities.py](../services/bookingService/tests/test_activities.py) |
| Docker / compose | 2 block + 2 Dockerfile | — | [docker-compose.yaml:186-267](../docker-compose.yaml#L186-L267) |
| OpenAPI specs | 2 | — | [BookingService.yaml](../docs/api-specs/BookingService.yaml), [PaymentService.yaml](../docs/api-specs/PaymentService.yaml) |

**Tổng API đã implement**: 12 endpoint (5 Booking + 7 Payment) + 1 Temporal workflow + 6 Temporal activities.

**Đặc thù khó nhất**:
1. **Sync controller gọi async Temporal**: giải bằng `asyncio.run` trong wrapper `_start_workflow_sync` ([bookingController.py:18-25](../services/bookingService/src/controllers/bookingController.py#L18-L25)).
2. **Compensating transaction**: được chia 2 lớp — lỗi trước khi start workflow ⇒ controller tự compensate; lỗi sau khi start ⇒ workflow compensate qua activity.
3. **Idempotent payment**: `booking_id UNIQUE` ở DB + check 409 ở controller; workflow_id = `booking-{id}` giúp Temporal tự dedupe.
4. **Checkout page render server-side**: render 1 trang HTML đầy đủ có QR + JS AJAX ngay trong paymentRoutes.py để luồng thanh toán có thể vận hành kể cả khi frontend offline.
