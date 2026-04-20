# Đối chiếu OpenAPI specs vs code thực tế — Booking & Payment Service

**Trạng thái hiện tại**: 2 file YAML trong [docs/api-specs/](../docs/api-specs/) đã được **đồng bộ lại** theo code thực tế sau refactor. Tài liệu này giữ lại bảng đối chiếu để sau này có thêm endpoint thì biết check ở đâu.

---

## 1. BookingService — đã khớp

### 1.1 Endpoints

| Endpoint | YAML | Code | Trạng thái |
| --- | --- | --- | --- |
| `GET /health` | 200 | 200 | ✅ |
| `POST /bookings` | 201 / 400 / 404 / 409 / 502 / 422 | 201 / 400 / 404 / 409 / 502 | ✅ |
| `GET /bookings/{booking_id}` | 200 / 404, id=integer | 200 / 404, id=integer | ✅ |
| `GET /bookings/user/{user_id}` | 200, user_id=integer | 200, user_id=integer | ✅ |
| `POST /bookings/{booking_id}/cancel` | 200 / 400 / 404 | 200 / 400 / 404 | ✅ |

**Chứng cứ code:**
- `POST /bookings` `status_code=201` tại [bookingRoutes.py:15](../services/bookingService/src/routes/bookingRoutes.py#L15).
- 404 showtime tại [bookingController.py:33](../services/bookingService/src/controllers/bookingController.py#L33).
- 502 downstream tại [bookingController.py:74](../services/bookingService/src/controllers/bookingController.py#L74), [bookingController.py:95](../services/bookingService/src/controllers/bookingController.py#L95).
- 400 cancel tại [bookingController.py:153](../services/bookingService/src/controllers/bookingController.py#L153).

### 1.2 Schema `BookingCreateRequest`

| YAML field | Code (`CreateBookingRequest`) | Trạng thái |
| --- | --- | --- |
| `user_id: integer (min 1)` | `user_id: int (ge=1)` | ✅ |
| `showtime_id: integer (min 1)` | `showtime_id: int (ge=1)` | ✅ |
| `seat_numbers: array (min 1, max 10)` | `seat_numbers: list[str]` | ✅ |
| `email: email` | `email: EmailStr` | ✅ |
| `voucher_code: string?` | `voucher_code: Optional[str]` | ✅ |

Định nghĩa chuẩn: [bookingSchemas.py:8-13](../services/bookingService/src/validators/bookingSchemas.py#L8-L13).

### 1.3 Schema `BookingCreateResponse`

| YAML | Code (`CreateBookingResponse`) | Trạng thái |
| --- | --- | --- |
| `booking_id: integer` | `booking_id: int` | ✅ |
| `workflow_id: string?` | `workflow_id: Optional[str]` | ✅ |
| `payment_id: integer` | `payment_id: int` | ✅ |
| `payment_url: string` | `payment_url: str` | ✅ |
| `status: string` | `status: str` | ✅ |
| `final_amount: number` | `final_amount: Decimal` | ✅ |

Định nghĩa chuẩn: [bookingSchemas.py:16-22](../services/bookingService/src/validators/bookingSchemas.py#L16-L22).

### 1.4 Schema `Booking` (detail)

Khớp hoàn toàn với [bookingSchemas.py:25-42](../services/bookingService/src/validators/bookingSchemas.py#L25-L42) + các giá trị status model hỗ trợ (`PENDING`, `AWAITING_PAYMENT`, `ACTIVE`, `CANCELLED`, `FAILED`). `failure_reason` được expose đầy đủ.

### 1.5 ErrorResponse

YAML dùng `{ detail: string }` — khớp với FastAPI `HTTPException` default. ✅

---

## 2. PaymentService — đã khớp

### 2.1 Endpoints

| Endpoint | YAML | Code | Trạng thái |
| --- | --- | --- | --- |
| `GET /health` | 200 | 200 | ✅ |
| `POST /payments/create` | 201 / 409 / 422 | 201 / 409 | ✅ |
| `GET /payments/{payment_id}` | 200 / 404, id=integer | 200 / 404, id=integer | ✅ |
| `GET /payments/by-booking/{booking_id}` | 200 / 404, booking_id=integer | 200 / 404, booking_id=integer | ✅ |
| `POST /payments/{payment_id}/confirm` | 200 / 400 / 404, id=integer | 200 / 400 / 404, id=integer | ✅ |
| `GET /payments/{payment_id}/checkout` | 200 / 404 HTML | 200 / 404 HTML | ✅ |
| `GET /payments/vnpay-return` | 200 + query params | 200 (skeleton) | ⚠ Skeleton — chờ tích hợp VNPay thật để verify signature |

**Chứng cứ code:**
- `status_code=201` tại [paymentRoutes.py:18](../services/paymentService/src/routes/paymentRoutes.py#L18).
- 409 duplicate booking tại [paymentController.py:30](../services/paymentService/src/controllers/paymentController.py#L30).
- 400 already finalized tại [paymentController.py:85](../services/paymentService/src/controllers/paymentController.py#L85).

### 2.2 Schema `PaymentCreateRequest`

| YAML | Code (`CreatePaymentRequest`) | Trạng thái |
| --- | --- | --- |
| `booking_id: integer (min 1)` | `booking_id: int (gt=0)` | ✅ |
| `amount: number > 0` | `amount: Decimal (gt=0)` | ✅ |
| `return_url: string?` | `return_url: Optional[str]` | ✅ |

Định nghĩa chuẩn: [paymentSchemas.py:8-11](../services/paymentService/src/validators/paymentSchemas.py#L8-L11).

### 2.3 Schema `PaymentCreateResponse`

| YAML | Code (`CreatePaymentResponse`) | Trạng thái |
| --- | --- | --- |
| `payment_id: integer` | `payment_id: int` | ✅ |
| `payment_url: string` | `payment_url: str` | ✅ |
| `status: string` | `status: str` | ✅ |

Định nghĩa chuẩn: [paymentSchemas.py:14-17](../services/paymentService/src/validators/paymentSchemas.py#L14-L17).

### 2.4 Schema `ConfirmPaymentRequest`

| YAML | Code (`ConfirmPaymentRequest`) | Trạng thái |
| --- | --- | --- |
| `{ success: boolean }` | `{ success: bool }` | ✅ |

Định nghĩa chuẩn: [paymentSchemas.py:20-21](../services/paymentService/src/validators/paymentSchemas.py#L20-L21).

### 2.5 Schema `Payment` (detail)

| YAML | Code (`PaymentDetail`) | Trạng thái |
| --- | --- | --- |
| `id: integer` | `id: int` | ✅ |
| `booking_id: integer` | `booking_id: int` | ✅ |
| `amount` | `amount` | ✅ |
| `status: enum[PENDING, SUCCESS, FAILED, CANCELLED]` | Khớp với `FINAL_STATUSES` tại [paymentController.py:14](../services/paymentService/src/controllers/paymentController.py#L14) | ✅ |
| `provider: string` | `provider: str` (giá trị `"vnpay"`) | ✅ |
| `payment_url: string?` | `payment_url: Optional[str]` | ✅ |
| `provider_txn_id: string?` | `provider_txn_id: Optional[str]` | ✅ |
| `created_at`, `updated_at` | khớp | ✅ |

Định nghĩa chuẩn: [paymentSchemas.py:24-35](../services/paymentService/src/validators/paymentSchemas.py#L24-L35) + model [paymentModel.py:10-28](../services/paymentService/src/models/paymentModel.py#L10-L28).

### 2.6 ErrorResponse

YAML dùng `{ detail: string }` — khớp với FastAPI `HTTPException` default. ✅

---

## 3. Ghi chú duy trì

- **Khi thêm endpoint mới** cho 1 trong 2 service: cập nhật YAML tương ứng ngay trong cùng PR. Kiểm tra status code, kiểu path param, tên field trong schema.
- **Error body luôn là `{ detail: string }`**: đây là default FastAPI trả qua `HTTPException`. Đừng đổi tên key trong YAML nếu không muốn lệch client.
- **ID luôn là integer**: DB dùng auto-increment INT, không phải UUID.
- **`/payments/vnpay-return` hiện tại là skeleton**: khi hoàn thiện signature verification thì cập nhật lại YAML cho đúng — hiện `response` chỉ là JSON với `redirect_url`+`status`.
- **Regenerate từ runtime** (tuỳ chọn): mỗi service FastAPI expose `GET /openapi.json` — có thể so sánh nhanh bằng `curl http://localhost:5005/openapi.json | jq` để spot-check khi nghi ngờ lệch.
