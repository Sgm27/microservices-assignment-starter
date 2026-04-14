# Analysis and Design — Domain-Driven Design Approach

> **Goal**: Phân tích business process "Đặt vé xem phim online" và thiết kế giải pháp hướng dịch vụ theo DDD.
> **Alternative to**: [`analysis-and-design.md`](analysis-and-design.md) (SOA — Thomas Erl step-by-step action approach).
> Nhóm chọn **một** trong hai approach.

**References:**

1. *Domain-Driven Design: Tackling Complexity in the Heart of Software* — Eric Evans
2. *Implementing Domain-Driven Design* — Vaughn Vernon
3. *Microservices Patterns* — Chris Richardson
4. *Bài tập — Phát triển phần mềm hướng dịch vụ* — Hung Dang

---

## 1. 🎯 Problem Statement

- **Domain**: Entertainment — Cinema Booking.
- **Actors**: Khách hàng (customer).
- **Core business capability**: Khách hàng có thể đặt vé xem phim online, chọn suất chiếu cụ thể và giữ ghế trong khi thanh toán, hệ thống tự động xác nhận ghế khi thanh toán thành công và release ghế khi thất bại.

> Chi tiết in-scope / out-of-scope xem [`analysis-and-design.md#1--problem-statement`](analysis-and-design.md#1--problem-statement).

---

## 2. 🧠 Strategic Design — Bounded Contexts

Phân rã domain thành các **Bounded Context** dựa trên semantic boundary nghiệp vụ (không phải theo technical layer).

| Bounded Context | Core Responsibility | Ubiquitous Language (chính) |
|-----------------|---------------------|------------------------------|
| **Identity & Access** | Xác thực và quản lý identity của khách hàng. | User, Customer, Credential, Token (JWT), Session |
| **Movie Catalog** | Quản lý phim, suất chiếu và ghế. Data owner của inventory bán vé. | Movie, Showtime, Seat, Room, SeatStatus (AVAILABLE / PENDING / BOOKED) |
| **Pricing & Promotion** | Quản lý voucher, tính giá cuối cùng. | Voucher, DiscountPercentage, ValidationResult, Redemption |
| **Booking** | Orchestrate toàn bộ luồng đặt vé; chủ của Booking aggregate và lifecycle. | Booking, BookingStatus (AWAITING_PAYMENT / ACTIVE / CANCELLED), BookingSaga, Workflow |
| **Payment** | Tích hợp gateway bên thứ ba, xử lý giao dịch tiền. | Payment, PaymentMethod (MOCK / VNPAY), PaymentStatus (PENDING / SUCCESS / FAILED), IPN |
| **Notification** | Gửi thông báo kết quả đặt vé. | Notification, Channel (EMAIL), Subject, Body |

### Context Map

| Relationship | Upstream | Downstream | Pattern |
|--------------|----------|-----------|---------|
| Identity & Access → Booking | Identity & Access | Booking | Customer / Supplier (Booking phụ thuộc JWT cấp bởi Identity) |
| Movie Catalog ↔ Booking | Movie Catalog | Booking | Customer / Supplier (Booking orchestrate reserve/confirm/release) |
| Pricing & Promotion → Booking | Pricing & Promotion | Booking | Conformist (Booking dùng trực tiếp validate response) |
| Payment ↔ Booking | Payment | Booking | Open Host Service (Payment expose REST để Booking poll) |
| Booking → Notification | Booking | Notification | Open Host Service (Notification được Booking call khi saga success) |
| Payment → VNPay (external) | VNPay | Payment | Anti-Corruption Layer (Payment adapt VNPay contract thành domain model nội bộ) |

---

## 3. 🧱 Tactical Design — Aggregates

### 3.1 Identity & Access

- **Aggregate Root**: `User`
    - Invariant: email unique; password hash-only (không lưu plaintext).
    - Lifecycle: `Created` → `Active` (deletion not in scope).

### 3.2 Movie Catalog

- **Aggregate Root**: `Showtime`
    - Chứa collection `Seat` (child entity).
    - Invariant: một `Seat` chỉ có một trong ba status AVAILABLE / PENDING / BOOKED tại một thời điểm; state transition AVAILABLE → PENDING → BOOKED / AVAILABLE.
    - Operation: `reserve(seat_ids)`, `confirm(seat_ids)`, `release(seat_ids)` — phải atomic trên aggregate.
- **Aggregate Root**: `Movie`
    - Chứa thông tin phim + danh sách reference đến `Showtime`.

### 3.3 Pricing & Promotion

- **Aggregate Root**: `Voucher`
    - Invariant: `used_count ≤ max_uses`; `expires_at` chưa qua; `code` unique.
    - Operation: `validate(original_price)` → `discount_amount`; `redeem()` → tăng `used_count`.

### 3.4 Booking

- **Aggregate Root**: `Booking`
    - State machine: `AWAITING_PAYMENT` → `ACTIVE` (payment SUCCESS) hoặc `AWAITING_PAYMENT` → `CANCELLED` (payment FAILED/timeout/user cancel).
    - Invariant: một `Booking` luôn gắn với một `Payment` và một tập `Seat` đang ở trạng thái PENDING khi `AWAITING_PAYMENT`.
    - **Process Manager / Saga**: `BookingWorkflow` (Temporal) — orchestrate reserve → create payment → poll → confirm/release + notification.

### 3.5 Payment

- **Aggregate Root**: `Payment`
    - State machine: `PENDING` → `SUCCESS` / `FAILED`.
    - Invariant: chỉ transition được một lần; amount ≥ 0.
    - External ACL: `VNPayReturnAdapter` map VNPay response → domain event.

### 3.6 Notification

- **Aggregate Root**: `Notification`
    - State machine: `QUEUED` → `SENT` / `FAILED`.
    - Không có invariant phức tạp; là side-channel.

---

## 4. 📬 Domain Events

| Event | Publisher (Context) | Subscriber(s) | Trigger |
|-------|---------------------|---------------|---------|
| `BookingRequested` | Booking | — | `POST /bookings` received |
| `SeatsReserved` | Movie Catalog | Booking | Sau khi `/seats/reserve` success |
| `VoucherValidated` | Pricing & Promotion | Booking | Sau khi `/vouchers/validate` |
| `PaymentCreated` | Payment | Booking | Sau khi `/payments/create` |
| `PaymentSucceeded` | Payment | Booking (workflow poll detects) | IPN hoặc mock confirm SUCCESS |
| `PaymentFailed` | Payment | Booking (workflow poll detects) | IPN hoặc mock confirm FAILED |
| `SeatsConfirmed` | Movie Catalog | Booking | Sau confirm activity trong saga |
| `SeatsReleased` | Movie Catalog | Booking | Sau compensation trong saga |
| `VoucherRedeemed` | Pricing & Promotion | Booking | Sau redeem activity |
| `BookingActivated` | Booking | Notification | Saga hoàn thành success |
| `BookingCancelled` | Booking | — | Saga compensation / user cancel |
| `NotificationSent` | Notification | — | Email gửi xong |

> Trong starter implementation hiện tại, events là **logical events** bên trong Temporal workflow. Có thể nâng lên event-driven thật (broker) như một hướng mở rộng.

---

## 5. 🗺️ Service Boundary mapping

| Bounded Context | Service / Component |
|-----------------|---------------------|
| Identity & Access | `authService`, `userService` |
| Movie Catalog | `movieService` |
| Pricing & Promotion | `voucherService` |
| Booking | `bookingService` (+ Temporal worker) |
| Payment | `paymentService` |
| Notification | `notificationService` |

Cross-cutting: `gateway` là API composition layer (không thuộc bounded context nào).

---

## 6. 📎 Liên quan

- [System Architecture](architecture.md) — pattern selection, deployment.
- API specs: [`docs/api-specs/`](api-specs/).
- Comparison với SOA approach: [`analysis-and-design.md`](analysis-and-design.md).
