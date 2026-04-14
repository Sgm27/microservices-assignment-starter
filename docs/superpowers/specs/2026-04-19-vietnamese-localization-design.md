# Vietnamese Localization — Full-Stack

**Date:** 2026-04-19
**Scope:** Frontend (all hardcoded user-facing text + currency/date formatting) and backend (HTTPException details, voucher messages, notification email content, seed descriptions, plus matching test updates).
**Goal:** Application becomes Vietnamese-only end-to-end. Status codes (`PENDING`, `CONFIRMED`, ...) stay English so logic, DB queries, and tests still work; only display labels are translated. Currency renders as `120.000 đ`. Dates render as `19/04/2026 19:00` (vi-VN locale).

## Motivation

The cinema booking app demos a Vietnamese cinema flow but UI and backend messages are English. Single-language Vietnamese (no i18n library, no language switcher) is enough — this is a school assignment, not a multi-region product.

## Decisions

1. **Vietnamese-only.** No `i18next`/`react-intl`. Hardcoded Vietnamese strings.
2. **Status codes unchanged.** `PENDING`, `CONFIRMED`, `ACTIVE`, `FAILED`, `CANCELLED`, `SUCCESS`, `AVAILABLE`, `BOOKED` remain in DB, API responses, and tests. Only display labels in the frontend are translated, via a small `statusLabel(code)` helper.
3. **Currency format `120.000 đ`.** Vietnamese-style thousands separator (`.`), space, lowercase `đ`. Backend continues to store `Decimal` (whole VND, no fractional cents). Frontend formats via `formatVND(value)`.
4. **Date format `dd/MM/yyyy HH:mm`** using `toLocaleString("vi-VN", ...)`. Frontend-only.
5. **Backend error messages translated.** Vietnamese strings in `HTTPException(detail=...)` for all user-facing services. Test assertions are updated together (no dual-language fallback).
6. **Notification email** subject + body translated to Vietnamese. Mock mode — no real SMTP impact.
7. **Seed movie descriptions translated.** Title and `genre` stay English (proper nouns / display label is fine in English here, e.g., "Sci-Fi"). If we want to localize `genre` later, that's a follow-up.

## Frontend changes

### New utility module

`frontend/src/utils/format.ts`:

```ts
export function formatVND(value: number | string): string {
  const n = typeof value === "string" ? Number(value) : value;
  if (!Number.isFinite(n)) return "0 đ";
  return `${Math.round(n).toLocaleString("vi-VN")} đ`;
}

export function formatDateVi(iso: string): string {
  try {
    return new Date(iso).toLocaleString("vi-VN", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  } catch {
    return iso;
  }
}

export function statusLabel(status: string): string {
  const map: Record<string, string> = {
    PENDING: "Đang chờ",
    ACTIVE: "Hoàn tất",
    CONFIRMED: "Đã xác nhận",
    SUCCESS: "Thành công",
    FAILED: "Thất bại",
    CANCELLED: "Đã hủy",
    AVAILABLE: "Còn trống",
    BOOKED: "Đã đặt",
  };
  return map[status?.toUpperCase()] ?? status;
}
```

### View-level string translations

Translate every hardcoded English string in:

- `NavBar.tsx` — `Home → Trang chủ`, `My Bookings → Đơn của tôi`, `Login → Đăng nhập`, `Logout → Đăng xuất`. Brand stays `🎬 CinemaBox`.
- `Login.tsx` — `Sign In → Đăng nhập`, `Create Account → Tạo tài khoản`, `Email → Email`, `Password → Mật khẩu`, `Full name → Họ tên`, `Phone (optional) → Số điện thoại (tùy chọn)`, `Please wait… → Đang xử lý…`, `Register → Đăng ký`, `No account yet? → Chưa có tài khoản?`, `Already have an account? → Đã có tài khoản?`, `Sign in → Đăng nhập`, `Authentication failed → Đăng nhập thất bại`.
- `MovieList.tsx` — Hero `Now Showing → Đang chiếu`, subtitle `Pick a film and book your seat in seconds. → Chọn phim và đặt vé trong vài giây.`, `No movies available. → Chưa có phim nào.`, `Loading movies… → Đang tải phim…`, `Failed to load movies → Không tải được danh sách phim`, duration `X min → X phút`.
- `MovieDetail.tsx` — `Showtimes → Suất chiếu`, `No showtimes scheduled. → Chưa có suất chiếu.`, `Loading movie… → Đang tải phim…`, `Movie not found. → Không tìm thấy phim.`, room label `Room X → Phòng X`. Use `formatDateVi` and `formatVND` for the showtime row.
- `ShowtimeBooking.tsx` — `Book Seats → Đặt ghế`, `Choose seats → Chọn ghế`, status legend (`Available → Còn trống`, `Pending → Đang chờ`, `Booked → Đã đặt`, `Selected → Đang chọn`), `Voucher code (optional) → Mã giảm giá (tùy chọn)`, `Apply → Áp dụng`, `Pick at least one seat first. → Hãy chọn ít nhất một ghế.`, `Voucher not valid. → Mã không hợp lệ.`, `Voucher check failed → Không kiểm tra được mã`, `Voucher applied. Discount X. → Đã áp dụng. Giảm X.` (with `formatVND`), `Selected: → Đã chọn:`, `none → chưa có`, `Base total: → Tạm tính:`, `Final: → Tổng:`, `Pick at least one seat. → Hãy chọn ít nhất một ghế.`, `Booking failed → Đặt vé thất bại`, `Book → Đặt vé`, `Booking… → Đang đặt…`, `Loading showtime… → Đang tải suất chiếu…`, `Showtime not found. → Không tìm thấy suất chiếu.`. Header `Room X — datetime — Base $price` becomes `Phòng X — datetime — Giá X đ`.
- `MyBookings.tsx` — `My Bookings → Đơn đặt vé`, `Loading bookings… → Đang tải…`, `No bookings yet. → Chưa có đơn nào.`, `Failed to load bookings → Không tải được đơn`, field labels `Showtime → Suất chiếu`, `Seats → Ghế`, `Amount → Tổng tiền` (with `formatVND`), `Status → Trạng thái` (with `statusLabel`).
- `PaymentResult.tsx` — `Payment Result → Kết quả thanh toán`, `Waiting for payment confirmation… (X/N) → Đang chờ xác nhận thanh toán… (X/N)`, `Status → Trạng thái` (with `statusLabel`), `Showtime → Suất chiếu`, `Seats → Ghế`, `Amount → Tổng tiền` (with `formatVND`), `Booking X → Mã đơn X`, `Missing booking_id in URL. → Thiếu booking_id trên URL.`, `Failed to load booking → Không tải được đơn`, `My Bookings → Đơn của tôi`, `Back to Home → Về trang chủ`.
- `MockPay.tsx` — `Mock Payment → Thanh toán mô phỏng`, `Payment ID → Mã thanh toán`, `Booking ID → Mã đơn`, `Pay → Thanh toán`, `Cancel → Hủy`, `Processing… → Đang xử lý…`, `Cancelling… → Đang hủy…`, `Payment failed → Thanh toán thất bại`.
- `SeatGrid.tsx` — tooltip `${seat_number} — ${status}` becomes `${seat_number} — ${statusLabel(status)}`.

### Files touched (frontend)

- New: `frontend/src/utils/format.ts`.
- Modified: `frontend/src/components/{NavBar,SeatGrid}.tsx`, `frontend/src/views/{Login,MovieList,MovieDetail,ShowtimeBooking,MyBookings,PaymentResult,MockPay}.tsx`.

## Backend changes

Translate every user-facing message **only**: `HTTPException(detail=...)` and any field that the frontend renders to the user (e.g., `VoucherResult.message`, notification subject/body). Logger calls, exception types, internal helper exceptions, and OpenAPI metadata stay English.

### authService — `services/authService/src/controllers/authController.py`

- `email already registered` → `Email đã được đăng ký`
- `invalid email or password` → `Email hoặc mật khẩu không đúng`
- `invalid token: ...` → `Token không hợp lệ: ...` (preserve interpolation)

### userService — `services/userService/src/controllers/userController.py`

- `email already exists` → `Email đã tồn tại`
- `user id already exists` → `User ID đã tồn tại`
- `user not found` → `Không tìm thấy người dùng`

### movieService — `services/movieService/src/controllers/{movieController,seatController}.py`

- `movie not found` → `Không tìm thấy phim`
- `showtime not found` → `Không tìm thấy suất chiếu`
- Any seat-related detail (e.g., `seat not available`, `seat not found`) — translate. The implementation plan must enumerate the exact strings.

### voucherService — `services/voucherService/src/controllers/voucherController.py`

- `VoucherResult.message` values: `code not found` → `Mã không tồn tại`, `expired` → `Mã đã hết hạn`, `not yet active` → `Mã chưa đến ngày áp dụng`, `usage limit reached` → `Mã đã hết lượt sử dụng`, `min order amount not met` → `Đơn hàng chưa đạt giá trị tối thiểu`, etc. Plan must enumerate the actual list from the source.

### bookingService — `services/bookingService/src/{controllers,activities,workflows}/...`

- `booking not found` → `Không tìm thấy đơn đặt vé`
- Any `HTTPException(detail=...)` in controllers/activities — translate. Plan enumerates.
- Workflow-internal status strings (e.g., `SUCCESS`, `FAILED`) — DO NOT translate.

### paymentService — `services/paymentService/src/controllers/...`

- `payment not found` → `Không tìm thấy thanh toán`
- Plus any other `HTTPException(detail=...)` — plan enumerates.

### notificationService — email content

Mock mode is on, so changing email text is safe. Translate subject + body templates.

- Subject: `Booking confirmed: <id>` → `Xác nhận đặt vé: <id>`
- Body: translate the static template lines (greeting, "your booking is confirmed", seat list label, total label, footer).

### Seed descriptions — `services/movieService/seed.py`

| Title | Vietnamese description |
| --- | --- |
| Oppenheimer | `Câu chuyện về J. Robert Oppenheimer và quả bom nguyên tử.` |
| Inside Out 2 | `Những cảm xúc tuổi teen của Riley dọn đến tổng hành dinh.` |
| Dune: Part Two | `Paul Atreides liên minh với người Fremen để báo thù.` |
| The Batman | `Batman truy lùng Riddler khắp các con phố Gotham.` |

The seed's existing upsert (Task 7 in the previous plan) already updates `description` on existing rows. Re-running the seed updates the DB.

## Tests

Every test that asserts on a translated detail string must be updated **in the same commit as the source change** so the test suite stays green per service.

- Search for current English strings that get translated and update each assertion.
- Tests that assert HTTP status codes (e.g., `r.status_code == 404`) need no change.
- Tests that mock downstream `Response(409, json={"detail": "taken"})`: those simulate downstream behavior, leave them in English unless the actual downstream service is in this repo and was translated. Plan calls this out.

The implementation plan must include a `make test-service s=<svc>` (or `pytest` inside the container per `CLAUDE.md`) verification step for each backend service that's touched.

## Out of scope

- i18n library / language switcher.
- Localizing `genre` field values (`Drama`, `Sci-Fi`, ...).
- Localizing `title` fields (proper nouns).
- Translating OpenAPI/Swagger metadata at `/docs`.
- Translating internal log / exception messages developers see in container logs.
- Translating fixture / mock strings in tests that simulate external services.
- Pluralization rules (Vietnamese has no singular/plural distinction — "X phút" works for any X).

## Success criteria

1. Every visible string in the running app (login → list → detail → booking → mock pay → result → bookings) is Vietnamese.
2. Currency renders as `120.000 đ` everywhere — never `$120000.00` or `120000`.
3. Dates render as `19/04/2026 19:00` (vi-VN format).
4. Status badges render Vietnamese labels but DB rows / API JSON still return English status codes.
5. Triggering a backend error (e.g., wrong password, taken seat) returns Vietnamese `detail` text, displayed without further translation by the frontend.
6. `pytest` inside each touched service container exits 0 — no broken assertions on old English strings.
7. Re-running the movie seed leaves DB descriptions Vietnamese.

## Risks

- **High blast radius on tests.** Multiple services have tests that assert on `detail` strings. Plan must enumerate per service before changing source.
- **Some `detail` strings might leak to logs / monitoring** — acceptable for this assignment.
- **Decimal display**: `formatVND` rounds to whole VND. If any test or downstream assumes 2-decimal precision, that breaks. Today everything is VND-native (`Decimal("120000")`), so this is theoretical.
- **`new Date(iso)` parsing** in `formatDateVi`: backend returns naive ISO without timezone. Already-existing `MovieDetail`'s `formatDate` does the same — keep behavior.
