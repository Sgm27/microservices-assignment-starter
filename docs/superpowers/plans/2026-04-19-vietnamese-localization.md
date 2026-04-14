# Vietnamese Localization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the cinema booking app to Vietnamese end-to-end — UI strings, currency (`120.000 đ`), dates (`19/04/2026 19:00`), backend `HTTPException` details, voucher messages, notification email content, and seed descriptions. Status codes (`PENDING`, `CONFIRMED`, ...) stay English so logic and tests still work.

**Architecture:** Frontend gets a small `utils/format.ts` module exporting `formatVND`, `formatDateVi`, and `statusLabel`. Every view replaces hardcoded English with Vietnamese strings and uses the formatters. Each backend service gets its `HTTPException(detail=...)` strings translated in one focused commit per service. The booking workflow's notification subject + body templates are translated. Tests do NOT assert on detail strings (verified by grep), so backend changes don't break existing test suites.

**Tech Stack:** React + Vite + TypeScript (frontend), FastAPI + Python 3.11 (backend), Temporal (booking workflow), Docker Compose for orchestration.

**Spec:** `docs/superpowers/specs/2026-04-19-vietnamese-localization-design.md`

---

## File map

**Frontend (10 files):**
- Create: `frontend/src/utils/format.ts`
- Modify: `frontend/src/components/NavBar.tsx`, `SeatGrid.tsx`
- Modify: `frontend/src/views/Login.tsx`, `MovieList.tsx`, `MovieDetail.tsx`, `ShowtimeBooking.tsx`, `MyBookings.tsx`, `PaymentResult.tsx`, `MockPay.tsx`

**Backend (8 files):**
- `services/authService/src/controllers/authController.py`
- `services/userService/src/controllers/userController.py`
- `services/movieService/src/controllers/movieController.py`
- `services/movieService/src/controllers/seatController.py`
- `services/voucherService/src/controllers/voucherController.py`
- `services/bookingService/src/controllers/bookingController.py`
- `services/bookingService/src/workflows/bookingWorkflow.py`
- `services/paymentService/src/controllers/paymentController.py`

**Data:**
- `services/movieService/seed.py`

**Verification only (no edit):**
- `make test-service s=<svc>` per touched backend service.

---

## Task 1: Add frontend formatter utility

**Files:**
- Create: `frontend/src/utils/format.ts`

- [ ] **Step 1: Create the formatter module**

Write `frontend/src/utils/format.ts`:

```ts
export function formatVND(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "0 đ";
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

const STATUS_LABELS: Record<string, string> = {
  PENDING: "Đang chờ",
  ACTIVE: "Hoàn tất",
  CONFIRMED: "Đã xác nhận",
  SUCCESS: "Thành công",
  FAILED: "Thất bại",
  CANCELLED: "Đã hủy",
  AVAILABLE: "Còn trống",
  BOOKED: "Đã đặt",
  AWAITING_PAYMENT: "Chờ thanh toán",
};

export function statusLabel(status: string | undefined | null): string {
  if (!status) return "";
  return STATUS_LABELS[status.toUpperCase()] ?? status;
}
```

- [ ] **Step 2: Type-check via build**

```bash
docker compose build frontend
```
Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/utils/format.ts
git commit -m "feat(frontend): add formatVND, formatDateVi, statusLabel utils"
```

---

## Task 2: Translate NavBar

**Files:**
- Modify: `frontend/src/components/NavBar.tsx`

- [ ] **Step 1: Apply text edits**

In `frontend/src/components/NavBar.tsx`, replace the link labels and button text:

Replace:
```tsx
        <NavLink to="/" className="brand" end>
          🎬 CinemaBox
        </NavLink>
        <NavLink
          to="/"
          end
          className={({ isActive }) => (isActive ? "active" : "")}
        >
          Home
        </NavLink>
        {isAuthenticated && (
          <NavLink
            to="/bookings"
            className={({ isActive }) => (isActive ? "active" : "")}
          >
            My Bookings
          </NavLink>
        )}
```
With:
```tsx
        <NavLink to="/" className="brand" end>
          🎬 CinemaBox
        </NavLink>
        <NavLink
          to="/"
          end
          className={({ isActive }) => (isActive ? "active" : "")}
        >
          Trang chủ
        </NavLink>
        {isAuthenticated && (
          <NavLink
            to="/bookings"
            className={({ isActive }) => (isActive ? "active" : "")}
          >
            Đơn của tôi
          </NavLink>
        )}
```

Replace:
```tsx
            <button
              type="button"
              onClick={handleLogout}
              className="btn btn-ghost"
            >
              Logout
            </button>
```
With:
```tsx
            <button
              type="button"
              onClick={handleLogout}
              className="btn btn-ghost"
            >
              Đăng xuất
            </button>
```

Replace:
```tsx
          <NavLink to="/login" className="btn btn-primary">
            Login
          </NavLink>
```
With:
```tsx
          <NavLink to="/login" className="btn btn-primary">
            Đăng nhập
          </NavLink>
```

- [ ] **Step 2: Type-check via build**

```bash
docker compose build frontend
```
Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/NavBar.tsx
git commit -m "i18n(frontend): NavBar to Vietnamese"
```

---

## Task 3: Translate Login

**Files:**
- Modify: `frontend/src/views/Login.tsx`

- [ ] **Step 1: Apply edits**

Replace `"Authentication failed"` with `"Đăng nhập thất bại"`:
```tsx
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Authentication failed";
```
becomes:
```tsx
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Đăng nhập thất bại";
```

Replace the `<h1>` text:
```tsx
      <h1>{mode === "login" ? "Sign In" : "Create Account"}</h1>
```
becomes:
```tsx
      <h1>{mode === "login" ? "Đăng nhập" : "Tạo tài khoản"}</h1>
```

Replace `Email` label (keep word "Email" — same in Vietnamese) — no change.

Replace `Password` label:
```tsx
        <label>
          Password
          <input
```
becomes:
```tsx
        <label>
          Mật khẩu
          <input
```

Replace `Full name` label:
```tsx
            <label>
              Full name
              <input
```
becomes:
```tsx
            <label>
              Họ tên
              <input
```

Replace `Phone (optional)` label:
```tsx
            <label>
              Phone (optional)
              <input
```
becomes:
```tsx
            <label>
              Số điện thoại (tùy chọn)
              <input
```

Replace the submit button label:
```tsx
          {loading
            ? "Please wait…"
            : mode === "login"
              ? "Sign In"
              : "Register"}
```
becomes:
```tsx
          {loading
            ? "Đang xử lý…"
            : mode === "login"
              ? "Đăng nhập"
              : "Đăng ký"}
```

Replace the toggle paragraph:
```tsx
      <p className="muted">
        {mode === "login" ? "No account yet?" : "Already have an account?"}{" "}
        <button
          type="button"
          className="btn btn-link"
          onClick={() => setMode(mode === "login" ? "register" : "login")}
        >
          {mode === "login" ? "Register" : "Sign in"}
        </button>
      </p>
```
becomes:
```tsx
      <p className="muted">
        {mode === "login" ? "Chưa có tài khoản?" : "Đã có tài khoản?"}{" "}
        <button
          type="button"
          className="btn btn-link"
          onClick={() => setMode(mode === "login" ? "register" : "login")}
        >
          {mode === "login" ? "Đăng ký" : "Đăng nhập"}
        </button>
      </p>
```

- [ ] **Step 2: Type-check**

```bash
docker compose build frontend
```
Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/Login.tsx
git commit -m "i18n(frontend): Login/Register to Vietnamese"
```

---

## Task 4: Translate MovieList + use formatters

**Files:**
- Modify: `frontend/src/views/MovieList.tsx`

- [ ] **Step 1: Replace the file**

Overwrite `frontend/src/views/MovieList.tsx` with:

```tsx
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listMovies } from "../api/movies";
import MoviePoster from "../components/MoviePoster";
import type { Movie } from "../types";

export default function MovieList() {
  const [movies, setMovies] = useState<Movie[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    listMovies()
      .then((data) => {
        if (mounted) setMovies(data);
      })
      .catch((err) => {
        if (mounted)
          setError(
            (err as { message?: string })?.message ?? "Không tải được danh sách phim",
          );
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  if (loading) return <p>Đang tải phim…</p>;
  if (error) return <p className="error">{error}</p>;

  return (
    <section>
      <div className="hero">
        <h1>Đang chiếu</h1>
        <p>Chọn phim và đặt vé trong vài giây.</p>
      </div>
      {movies.length === 0 ? (
        <p className="muted">Chưa có phim nào.</p>
      ) : (
        <div className="movie-grid">
          {movies.map((m) => (
            <Link key={m.id} to={`/movies/${m.id}`} className="movie-card">
              <MoviePoster src={m.poster_url} title={m.title} />
              <div className="movie-info">
                <h3>{m.title}</h3>
                <p className="muted">
                  {m.duration_minutes ? `${m.duration_minutes} phút` : ""}
                  {m.duration_minutes && (m as { genre?: string }).genre
                    ? " · "
                    : ""}
                  {(m as { genre?: string }).genre && (
                    <span className="genre-pill">
                      {(m as { genre?: string }).genre}
                    </span>
                  )}
                </p>
              </div>
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}
```

- [ ] **Step 2: Type-check**

```bash
docker compose build frontend
```
Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/MovieList.tsx
git commit -m "i18n(frontend): MovieList to Vietnamese"
```

---

## Task 5: Translate MovieDetail + use formatters

**Files:**
- Modify: `frontend/src/views/MovieDetail.tsx`

- [ ] **Step 1: Replace the file**

Overwrite `frontend/src/views/MovieDetail.tsx` with:

```tsx
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getMovie } from "../api/movies";
import MoviePoster from "../components/MoviePoster";
import { formatDateVi, formatVND } from "../utils/format";
import type { Movie } from "../types";

export default function MovieDetail() {
  const { id } = useParams<{ id: string }>();
  const [movie, setMovie] = useState<Movie | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let mounted = true;
    setLoading(true);
    getMovie(id)
      .then((data) => {
        if (mounted) setMovie(data);
      })
      .catch((err) => {
        if (mounted)
          setError(
            (err as { message?: string })?.message ?? "Không tải được phim",
          );
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, [id]);

  if (loading) return <p>Đang tải phim…</p>;
  if (error) return <p className="error">{error}</p>;
  if (!movie) return <p>Không tìm thấy phim.</p>;

  const showtimes = movie.showtimes ?? [];

  return (
    <section className="movie-detail">
      <div className="movie-detail-top">
        <MoviePoster
          src={movie.poster_url}
          title={movie.title}
          className="poster"
          fallbackClassName="large"
        />
        <div>
          <h1>{movie.title}</h1>
          {movie.duration_minutes && (
            <p className="muted">{movie.duration_minutes} phút</p>
          )}
          {movie.description && <p>{movie.description}</p>}
        </div>
      </div>

      <h2>Suất chiếu</h2>
      {showtimes.length === 0 ? (
        <p className="muted">Chưa có suất chiếu.</p>
      ) : (
        <ul className="showtime-list">
          {showtimes.map((s) => (
            <li key={s.id}>
              <Link
                to={`/showtimes/${s.id}/book`}
                className="showtime-card btn btn-ghost"
              >
                <span>{formatDateVi(s.starts_at)}</span>
                <span className="muted">Phòng {s.room}</span>
                <span>{formatVND(s.base_price)}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
```

- [ ] **Step 2: Type-check**

```bash
docker compose build frontend
```
Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/MovieDetail.tsx
git commit -m "i18n(frontend): MovieDetail to Vietnamese + VND/date formatters"
```

---

## Task 6: Translate ShowtimeBooking + use formatters

**Files:**
- Modify: `frontend/src/views/ShowtimeBooking.tsx`

- [ ] **Step 1: Replace the file**

Overwrite `frontend/src/views/ShowtimeBooking.tsx` with:

```tsx
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getShowtime, getShowtimeSeats } from "../api/movies";
import { validateVoucher } from "../api/vouchers";
import { createBooking } from "../api/bookings";
import { useAuth } from "../context/AuthContext";
import { formatDateVi, formatVND } from "../utils/format";
import type { Seat, Showtime, VoucherResult } from "../types";
import SeatGrid from "../components/SeatGrid";

export default function ShowtimeBooking() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [showtime, setShowtime] = useState<Showtime | null>(null);
  const [seats, setSeats] = useState<Seat[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [voucherCode, setVoucherCode] = useState("");
  const [voucher, setVoucher] = useState<VoucherResult | null>(null);
  const [voucherError, setVoucherError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!id) return;
    let mounted = true;
    setLoading(true);
    Promise.all([getShowtime(id), getShowtimeSeats(id)])
      .then(([st, seatList]) => {
        if (!mounted) return;
        setShowtime(st);
        setSeats(seatList);
      })
      .catch((err) => {
        if (mounted)
          setError(
            (err as { message?: string })?.message ?? "Không tải được suất chiếu",
          );
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, [id]);

  const basePrice = Number(showtime?.base_price ?? 0);
  const baseAmount = useMemo(
    () => selected.length * basePrice,
    [selected.length, basePrice],
  );

  const finalAmount = voucher?.valid ? voucher.final_amount : baseAmount;

  const toggleSeat = (seat: Seat) => {
    setSelected((prev) =>
      prev.includes(seat.seat_number)
        ? prev.filter((s) => s !== seat.seat_number)
        : [...prev, seat.seat_number],
    );
    setVoucher(null);
  };

  const applyVoucher = async () => {
    setVoucherError(null);
    if (!voucherCode.trim()) {
      setVoucher(null);
      return;
    }
    if (baseAmount <= 0) {
      setVoucherError("Hãy chọn ít nhất một ghế trước.");
      return;
    }
    try {
      const result = await validateVoucher(voucherCode.trim(), baseAmount);
      setVoucher(result);
      if (!result.valid) {
        setVoucherError(result.message ?? "Mã không hợp lệ.");
      }
    } catch (err) {
      setVoucherError(
        (err as { message?: string })?.message ?? "Không kiểm tra được mã",
      );
    }
  };

  const handleBook = async () => {
    if (!id || !user) return;
    if (selected.length === 0) {
      setError("Hãy chọn ít nhất một ghế.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const resp = await createBooking({
        user_id: user.user_id,
        showtime_id: id,
        seat_numbers: selected,
        voucher_code: voucher?.valid ? voucherCode.trim() : null,
        email: user.email,
      });
      navigate(
        `/mock-pay/${resp.payment_id}?booking_id=${resp.booking_id}`,
      );
    } catch (err) {
      setError(
        (err as { response?: { data?: { detail?: string } }; message?: string })
          ?.response?.data?.detail ??
          (err as { message?: string })?.message ??
          "Đặt vé thất bại",
      );
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <p>Đang tải suất chiếu…</p>;
  if (error && !showtime) return <p className="error">{error}</p>;
  if (!showtime) return <p>Không tìm thấy suất chiếu.</p>;

  return (
    <section className="booking-page">
      <h1>Đặt ghế</h1>
      <p className="muted">
        Phòng {showtime.room} — {formatDateVi(showtime.starts_at)} — Giá{" "}
        {formatVND(showtime.base_price)}
      </p>

      <h2>Chọn ghế</h2>
      <SeatGrid seats={seats} selected={selected} onToggle={toggleSeat} />

      <div className="seat-legend">
        <span className="legend-box seat-available" /> Còn trống
        <span className="legend-box seat-pending" /> Đang chờ
        <span className="legend-box seat-booked" /> Đã đặt
        <span className="legend-box seat-selected" /> Đang chọn
      </div>

      <div className="voucher-row">
        <input
          type="text"
          placeholder="Mã giảm giá (tùy chọn)"
          value={voucherCode}
          onChange={(e) => setVoucherCode(e.target.value)}
        />
        <button type="button" onClick={applyVoucher} className="btn btn-ghost">
          Áp dụng
        </button>
      </div>
      {voucherError && <p className="error">{voucherError}</p>}
      {voucher?.valid && (
        <p className="success">
          Đã áp dụng. Giảm {formatVND(voucher.discount_amount)}.
        </p>
      )}

      <div className="booking-summary">
        <p>Đã chọn: {selected.length ? selected.join(", ") : "chưa có"}</p>
        <p>Tạm tính: {formatVND(baseAmount)}</p>
        <p>
          <strong>Tổng: {formatVND(finalAmount)}</strong>
        </p>
      </div>

      {error && <p className="error">{error}</p>}

      <button
        type="button"
        onClick={handleBook}
        disabled={submitting || selected.length === 0}
        className="btn btn-primary"
      >
        {submitting ? "Đang đặt…" : "Đặt vé"}
      </button>
    </section>
  );
}
```

- [ ] **Step 2: Type-check**

```bash
docker compose build frontend
```
Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/ShowtimeBooking.tsx
git commit -m "i18n(frontend): ShowtimeBooking to Vietnamese + VND/date formatters"
```

---

## Task 7: Translate MyBookings + use formatters

**Files:**
- Modify: `frontend/src/views/MyBookings.tsx`

- [ ] **Step 1: Replace the file**

Overwrite `frontend/src/views/MyBookings.tsx` with:

```tsx
import { useEffect, useState } from "react";
import { listUserBookings } from "../api/bookings";
import { useAuth } from "../context/AuthContext";
import { formatDateVi, formatVND, statusLabel } from "../utils/format";
import type { Booking } from "../types";

export default function MyBookings() {
  const { user } = useAuth();
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    let mounted = true;
    setLoading(true);
    listUserBookings(user.user_id)
      .then((data) => {
        if (mounted) setBookings(data);
      })
      .catch((err) => {
        if (mounted)
          setError(
            (err as { message?: string })?.message ??
              "Không tải được đơn",
          );
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, [user]);

  if (loading) return <p>Đang tải…</p>;
  if (error) return <p className="error">{error}</p>;

  return (
    <section>
      <h1>Đơn đặt vé</h1>
      {bookings.length === 0 ? (
        <p className="muted">Chưa có đơn nào.</p>
      ) : (
        <ul className="booking-list">
          {bookings.map((b) => {
            const bid = b.booking_id ?? b.id ?? "";
            return (
              <li key={bid} className="booking-item">
                <div>
                  <strong>{bid}</strong>
                  {b.created_at && (
                    <span className="muted">
                      {" "}
                      · {formatDateVi(b.created_at)}
                    </span>
                  )}
                </div>
                {b.showtime_id && <div>Suất chiếu: {b.showtime_id}</div>}
                {b.seat_numbers && (
                  <div>Ghế: {b.seat_numbers.join(", ")}</div>
                )}
                {b.final_amount != null && (
                  <div>Tổng tiền: {formatVND(b.final_amount)}</div>
                )}
                <div>Trạng thái: {statusLabel(b.status)}</div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
```

- [ ] **Step 2: Type-check**

```bash
docker compose build frontend
```
Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/MyBookings.tsx
git commit -m "i18n(frontend): MyBookings to Vietnamese + VND/date/status formatters"
```

---

## Task 8: Translate PaymentResult + use formatters

**Files:**
- Modify: `frontend/src/views/PaymentResult.tsx`

- [ ] **Step 1: Replace the file**

Overwrite `frontend/src/views/PaymentResult.tsx` with:

```tsx
import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { getBooking } from "../api/bookings";
import { formatVND, statusLabel } from "../utils/format";
import type { Booking } from "../types";

const TERMINAL_STATUSES = new Set(["ACTIVE", "CANCELLED", "FAILED", "CONFIRMED"]);
const MAX_TRIES = 15;
const POLL_MS = 2000;

function statusClass(status: string): string {
  const up = status.toUpperCase();
  if (up === "ACTIVE" || up === "CONFIRMED") return "badge badge-success";
  if (up === "CANCELLED" || up === "FAILED") return "badge badge-error";
  return "badge";
}

export default function PaymentResult() {
  const [searchParams] = useSearchParams();
  const bookingId = searchParams.get("booking_id");
  const [booking, setBooking] = useState<Booking | null>(null);
  const [tries, setTries] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!bookingId) {
      setError("Thiếu booking_id trên URL.");
      setDone(true);
      return;
    }

    let cancelled = false;
    let attempt = 0;

    const poll = async () => {
      attempt += 1;
      setTries(attempt);
      try {
        const data = await getBooking(bookingId);
        if (cancelled) return;
        setBooking(data);
        const status = (data.status ?? "").toUpperCase();
        if (TERMINAL_STATUSES.has(status)) {
          setDone(true);
          return;
        }
      } catch (err) {
        if (cancelled) return;
        setError(
          (err as { message?: string })?.message ?? "Không tải được đơn",
        );
      }
      if (attempt >= MAX_TRIES) {
        setDone(true);
        return;
      }
      timer.current = setTimeout(poll, POLL_MS);
    };

    poll();

    return () => {
      cancelled = true;
      if (timer.current) clearTimeout(timer.current);
    };
  }, [bookingId]);

  const status = booking?.status ?? "";

  return (
    <div className="card">
      <h1>Kết quả thanh toán</h1>
      {!done && (
        <p className="muted">
          Đang chờ xác nhận thanh toán… ({tries}/{MAX_TRIES})
        </p>
      )}
      {error && <p className="error">{error}</p>}
      {booking && (
        <div className="booking-summary">
          <p>
            Trạng thái:{" "}
            <span className={statusClass(status)}>
              {statusLabel(status) || "—"}
            </span>
          </p>
          {booking.showtime_id && <p>Suất chiếu: {booking.showtime_id}</p>}
          {booking.seat_numbers && (
            <p>Ghế: {booking.seat_numbers.join(", ")}</p>
          )}
          {booking.final_amount != null && (
            <p>Tổng tiền: {formatVND(booking.final_amount)}</p>
          )}
          {booking.booking_id && (
            <p className="muted">Mã đơn {booking.booking_id}</p>
          )}
        </div>
      )}
      {done && (
        <div className="btn-row">
          <Link to="/bookings" className="btn btn-primary">
            Đơn của tôi
          </Link>
          <Link to="/" className="btn btn-ghost">
            Về trang chủ
          </Link>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Type-check**

```bash
docker compose build frontend
```
Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/PaymentResult.tsx
git commit -m "i18n(frontend): PaymentResult to Vietnamese + VND/status formatters"
```

---

## Task 9: Translate MockPay

**Files:**
- Modify: `frontend/src/views/MockPay.tsx`

- [ ] **Step 1: Replace the file**

Overwrite `frontend/src/views/MockPay.tsx` with:

```tsx
import { useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { confirmMockPayment } from "../api/payments";

export default function MockPay() {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const bookingId = searchParams.get("booking_id") ?? "";
  const [submitting, setSubmitting] = useState<"pay" | "cancel" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handle = async (success: boolean) => {
    if (!id) return;
    setSubmitting(success ? "pay" : "cancel");
    setError(null);
    try {
      await confirmMockPayment(id, success);
      navigate(`/booking/payment-result?booking_id=${bookingId}`);
    } catch (err) {
      setError(
        (err as { response?: { data?: { detail?: string } }; message?: string })
          ?.response?.data?.detail ??
          (err as { message?: string })?.message ??
          "Thanh toán thất bại",
      );
    } finally {
      setSubmitting(null);
    }
  };

  return (
    <div className="card narrow center">
      <h1>Thanh toán mô phỏng</h1>
      <p className="muted">Mã thanh toán: {id}</p>
      {bookingId && <p className="muted">Mã đơn: {bookingId}</p>}
      <div className="btn-row">
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => handle(true)}
          disabled={submitting !== null}
        >
          {submitting === "pay" ? "Đang xử lý…" : "Thanh toán"}
        </button>
        <button
          type="button"
          className="btn btn-ghost"
          onClick={() => handle(false)}
          disabled={submitting !== null}
        >
          {submitting === "cancel" ? "Đang hủy…" : "Hủy"}
        </button>
      </div>
      {error && <p className="error">{error}</p>}
    </div>
  );
}
```

- [ ] **Step 2: Type-check**

```bash
docker compose build frontend
```
Expected: build succeeds.

**Note:** Test in `services/paymentService/tests/test_payments.py:101` asserts `"Pay" in r.text` against the **payment-service mock-confirm HTML page** (NOT the frontend). It is unrelated to this view and must NOT be changed by this task.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/MockPay.tsx
git commit -m "i18n(frontend): MockPay to Vietnamese"
```

---

## Task 10: Translate SeatGrid tooltip

**Files:**
- Modify: `frontend/src/components/SeatGrid.tsx`

- [ ] **Step 1: Edit the tooltip**

Replace:
```tsx
import type { Seat } from "../types";
```
With:
```tsx
import { statusLabel } from "../utils/format";
import type { Seat } from "../types";
```

Replace:
```tsx
            title={`${seat.seat_number} — ${seat.status}`}
```
With:
```tsx
            title={`${seat.seat_number} — ${statusLabel(seat.status)}`}
```

- [ ] **Step 2: Type-check**

```bash
docker compose build frontend
```
Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/SeatGrid.tsx
git commit -m "i18n(frontend): SeatGrid tooltip to Vietnamese"
```

---

## Task 11: Translate authService details

**Files:**
- Modify: `services/authService/src/controllers/authController.py`

- [ ] **Step 1: Apply edits**

Replace `detail="email already registered"` with `detail="Email đã được đăng ký"`:
```python
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email already registered")
```
becomes:
```python
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email đã được đăng ký")
```

Replace `detail="invalid email or password"`:
```python
            detail="invalid email or password",
```
becomes:
```python
            detail="Email hoặc mật khẩu không đúng",
```

Replace `detail=f"invalid token: {exc}"`:
```python
            detail=f"invalid token: {exc}",
```
becomes:
```python
            detail=f"Token không hợp lệ: {exc}",
```

- [ ] **Step 2: Run authService tests**

The runtime image only contains `src/`, so we mount `tests/` at runtime:
```bash
docker compose run --rm --no-deps \
    -v "$(pwd)/services/authService/tests:/app/tests" \
    auth-service pytest -q
```
Expected: all tests pass (tests don't assert on `detail` strings — they assert on status codes and JSON fields).

- [ ] **Step 3: Commit**

```bash
git add services/authService/src/controllers/authController.py
git commit -m "i18n(authService): translate HTTPException details to Vietnamese"
```

---

## Task 12: Translate userService details

**Files:**
- Modify: `services/userService/src/controllers/userController.py`

- [ ] **Step 1: Apply edits**

Replace `detail="email already exists"`:
```python
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email already exists")
```
becomes:
```python
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email đã tồn tại")
```

Replace `detail="user id already exists"`:
```python
                detail="user id already exists",
```
becomes:
```python
                detail="User ID đã tồn tại",
```

Replace `detail="user not found"`:
```python
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
```
becomes:
```python
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy người dùng")
```

- [ ] **Step 2: Run userService tests**

```bash
docker compose run --rm --no-deps \
    -v "$(pwd)/services/userService/tests:/app/tests" \
    user-service pytest -q
```
Expected: all tests pass.

- [ ] **Step 3: Commit**

```bash
git add services/userService/src/controllers/userController.py
git commit -m "i18n(userService): translate HTTPException details to Vietnamese"
```

---

## Task 13: Translate movieService details (movie + seat)

**Files:**
- Modify: `services/movieService/src/controllers/movieController.py`
- Modify: `services/movieService/src/controllers/seatController.py`

- [ ] **Step 1: movieController — apply edits**

In `services/movieService/src/controllers/movieController.py`, replace each `detail="movie not found"`:
```python
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="movie not found")
```
becomes:
```python
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy phim")
```

Replace `detail="showtime not found"`:
```python
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="showtime not found")
```
becomes:
```python
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy suất chiếu")
```

- [ ] **Step 2: seatController — apply edits**

In `services/movieService/src/controllers/seatController.py`:

Replace BOTH occurrences of `detail="showtime not found"` (use `replace_all` or two Edit calls):
```python
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="showtime not found")
```
becomes:
```python
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy suất chiếu")
```

Replace `detail=f"seats not found: {missing}"`:
```python
            detail=f"seats not found: {missing}",
```
becomes:
```python
            detail=f"Không tìm thấy ghế: {missing}",
```

Replace `detail=f"seats not available: {unavailable}"`:
```python
            detail=f"seats not available: {unavailable}",
```
becomes:
```python
            detail=f"Ghế đã có người đặt: {unavailable}",
```

Replace `detail="no pending seats for booking_id"`:
```python
            detail="no pending seats for booking_id",
```
becomes:
```python
            detail="Không có ghế đang chờ cho đơn này",
```

- [ ] **Step 3: Run movieService tests**

```bash
docker compose run --rm --no-deps \
    -v "$(pwd)/services/movieService/tests:/app/tests" \
    movie-service pytest -q
```
Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add services/movieService/src/controllers/movieController.py services/movieService/src/controllers/seatController.py
git commit -m "i18n(movieService): translate HTTPException details to Vietnamese"
```

---

## Task 14: Translate voucherService details + messages

**Files:**
- Modify: `services/voucherService/src/controllers/voucherController.py`

- [ ] **Step 1: Apply edits**

Replace `detail="voucher code already exists"`:
```python
            detail="voucher code already exists",
```
becomes:
```python
            detail="Mã giảm giá đã tồn tại",
```

Replace `message="voucher not found"`:
```python
            message="voucher not found",
```
becomes:
```python
            message="Mã giảm giá không tồn tại",
```

Replace `message="voucher expired or not yet valid"`:
```python
            message="voucher expired or not yet valid",
```
becomes:
```python
            message="Mã giảm giá đã hết hạn hoặc chưa đến ngày áp dụng",
```

Replace `message="voucher has reached max uses"`:
```python
            message="voucher has reached max uses",
```
becomes:
```python
            message="Mã giảm giá đã hết lượt sử dụng",
```

Leave `message="ok"` unchanged (programmatic indicator, not displayed when voucher is valid — frontend shows the discount instead).

Replace `detail="voucher not found"`:
```python
            detail="voucher not found",
```
becomes:
```python
            detail="Mã giảm giá không tồn tại",
```

Replace `detail="voucher has reached max uses"`:
```python
            detail="voucher has reached max uses",
```
becomes:
```python
            detail="Mã giảm giá đã hết lượt sử dụng",
```

- [ ] **Step 2: Run voucherService tests**

```bash
docker compose run --rm --no-deps \
    -v "$(pwd)/services/voucherService/tests:/app/tests" \
    voucher-service pytest -q
```
Expected: all tests pass.

- [ ] **Step 3: Commit**

```bash
git add services/voucherService/src/controllers/voucherController.py
git commit -m "i18n(voucherService): translate details + validation messages to Vietnamese"
```

---

## Task 15: Translate bookingService details + workflow notification

**Files:**
- Modify: `services/bookingService/src/controllers/bookingController.py`
- Modify: `services/bookingService/src/workflows/bookingWorkflow.py`

- [ ] **Step 1: bookingController — apply edits**

Replace `detail="booking not found"`:
```python
        raise HTTPException(status_code=404, detail="booking not found")
```
becomes:
```python
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn đặt vé")
```

Replace the fallback message in:
```python
            raise HTTPException(status_code=400, detail=v.get("message") or "invalid voucher")
```
with:
```python
            raise HTTPException(status_code=400, detail=v.get("message") or "Mã giảm giá không hợp lệ")
```

Replace:
```python
        raise HTTPException(status_code=400, detail=f"cannot cancel booking in state {booking.status}")
```
with:
```python
        raise HTTPException(status_code=400, detail=f"Không thể hủy đơn ở trạng thái {booking.status}")
```

The other `HTTPException` calls in this file (`detail=str(exc)`) propagate downstream-service messages and need no change here — those services translate their own strings.

- [ ] **Step 2: bookingWorkflow — translate notification subject + body**

In `services/bookingService/src/workflows/bookingWorkflow.py`, replace:
```python
            await workflow.execute_activity(
                send_notification_activity,
                args=[
                    user_id,
                    email,
                    "Booking confirmed",
                    f"Booking {booking_id} confirmed. Enjoy the show!",
                ],
                start_to_close_timeout=timedelta(seconds=30),
            )
```
With:
```python
            await workflow.execute_activity(
                send_notification_activity,
                args=[
                    user_id,
                    email,
                    "Xác nhận đặt vé",
                    f"Đơn đặt vé {booking_id} đã được xác nhận. Chúc bạn xem phim vui vẻ!",
                ],
                start_to_close_timeout=timedelta(seconds=30),
            )
```

- [ ] **Step 3: Run bookingService tests**

```bash
docker compose run --rm --no-deps \
    -v "$(pwd)/services/bookingService/tests:/app/tests" \
    booking-service pytest -q
```
Expected: all tests pass. (Tests assert on status codes and structural fields, not the notification subject/body strings.)

- [ ] **Step 4: Commit**

```bash
git add services/bookingService/src/controllers/bookingController.py services/bookingService/src/workflows/bookingWorkflow.py
git commit -m "i18n(bookingService): translate details + workflow notification to Vietnamese"
```

---

## Task 16: Translate paymentService details

**Files:**
- Modify: `services/paymentService/src/controllers/paymentController.py`

- [ ] **Step 1: Apply edits**

Replace `detail="payment already exists for this booking"`:
```python
            detail="payment already exists for this booking",
```
becomes:
```python
            detail="Đơn thanh toán đã tồn tại cho đơn đặt vé này",
```

Replace BOTH occurrences of `detail="payment not found"` (use `replace_all` or three Edit calls — the string appears 3 times):
```python
            detail="payment not found",
```
becomes:
```python
            detail="Không tìm thấy đơn thanh toán",
```

Replace `detail="payment is already finalized"`:
```python
            detail="payment is already finalized",
```
becomes:
```python
            detail="Đơn thanh toán đã được hoàn tất",
```

- [ ] **Step 2: Run paymentService tests**

```bash
docker compose run --rm --no-deps \
    -v "$(pwd)/services/paymentService/tests:/app/tests" \
    payment-service pytest -q
```
Expected: all tests pass. (The mock-pay HTML page in payment-service still contains the English word "Pay" — that test isn't affected by these changes.)

- [ ] **Step 3: Commit**

```bash
git add services/paymentService/src/controllers/paymentController.py
git commit -m "i18n(paymentService): translate HTTPException details to Vietnamese"
```

---

## Task 17: Translate movie seed descriptions + re-seed

**Files:**
- Modify: `services/movieService/seed.py`

- [ ] **Step 1: Replace each English description with Vietnamese**

In `services/movieService/seed.py`, the `SEED_MOVIES` list has 4 movies. Translate each `description`:

| Title | New `description` |
| --- | --- |
| Oppenheimer | `Câu chuyện về J. Robert Oppenheimer và quả bom nguyên tử.` |
| Inside Out 2 | `Những cảm xúc tuổi teen của Riley dọn đến tổng hành dinh.` |
| Dune: Part Two | `Paul Atreides liên minh với người Fremen để báo thù.` |
| The Batman | `Batman truy lùng Riddler khắp các con phố Gotham.` |

Concrete edits — replace each of these four lines:
```python
        "description": "The story of J. Robert Oppenheimer and the atomic bomb.",
```
→
```python
        "description": "Câu chuyện về J. Robert Oppenheimer và quả bom nguyên tử.",
```

```python
        "description": "Riley's teenage emotions move into headquarters.",
```
→
```python
        "description": "Những cảm xúc tuổi teen của Riley dọn đến tổng hành dinh.",
```

```python
        "description": "Paul Atreides unites with the Fremen to seek revenge.",
```
→
```python
        "description": "Paul Atreides liên minh với người Fremen để báo thù.",
```

```python
        "description": "Batman tracks down the Riddler across the streets of Gotham.",
```
→
```python
        "description": "Batman truy lùng Riddler khắp các con phố Gotham.",
```

- [ ] **Step 2: Re-run the seed against the running stack**

```bash
docker compose up -d mysql-db movie-service
docker compose run --rm --no-deps \
    -v "$(pwd)/services/movieService/seed.py:/app/seed.py" \
    movie-service python seed.py
```
Expected: exit 0. The upsert logic added in the previous plan (Task 7) updates `description` on existing rows.

- [ ] **Step 3: Verify the API now serves Vietnamese descriptions**

```bash
curl -fsS http://localhost:5003/movies/1 | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['title'], '->', d['description'])"
```
Expected: a non-empty Vietnamese description (e.g., starts with `Paul Atreides`, `Câu chuyện`, `Những cảm xúc`, or `Batman truy lùng` depending on which id=1 maps to).

- [ ] **Step 4: Commit**

```bash
git add services/movieService/seed.py
git commit -m "i18n(movieService): seed movie descriptions in Vietnamese"
```

---

## Task 18: Build, restart, verify

**Files:**
- (none — runtime check)

- [ ] **Step 1: Rebuild the frontend image**

```bash
docker compose build frontend
```
Expected: build succeeds.

- [ ] **Step 2: Restart the frontend container**

```bash
docker compose up -d frontend
```
Expected: container starts, no error in `docker compose logs --tail=20 frontend`.

- [ ] **Step 3: Sanity check — frontend loads**

```bash
curl -fsS http://localhost:5173/ -o /dev/null -w "frontend HTTP %{http_code}\n"
```
Expected: `frontend HTTP 200`.

- [ ] **Step 4: Sanity check — backend services Vietnamese error**

Trigger a known error and check the response is Vietnamese.

User-not-found:
```bash
curl -s -o /tmp/r.json -w "%{http_code}\n" http://localhost:5002/users/999999
cat /tmp/r.json
```
Expected: HTTP 404, JSON `{"detail":"Không tìm thấy người dùng"}`.

Movie-not-found:
```bash
curl -s -o /tmp/r.json -w "%{http_code}\n" http://localhost:5003/movies/999999
cat /tmp/r.json
```
Expected: HTTP 404, JSON `{"detail":"Không tìm thấy phim"}`.

Voucher-not-found (validate):
```bash
curl -s -X POST -H "Content-Type: application/json" -d '{"code":"NOPE","base_amount":100000}' http://localhost:5004/vouchers/validate
```
Expected: JSON `{"valid":false,"discount_amount":0.0,"final_amount":100000.0,"message":"Mã giảm giá không tồn tại"}`.

- [ ] **Step 5: Manual visual verification (user)**

Open `http://localhost:5173/` in a browser and confirm:
- All NavBar links Vietnamese (Trang chủ, Đơn của tôi, Đăng nhập / Đăng xuất).
- Hero section reads "Đang chiếu" + Vietnamese subtitle.
- Movie cards show duration as "X phút" + genre pill.
- Click a movie → "Suất chiếu" heading, showtime row shows date `dd/MM/yyyy HH:mm` and price `120.000 đ`.
- Click a showtime → "Đặt ghế" page, seat legend Vietnamese, voucher input Vietnamese, summary `Tạm tính / Tổng / Đã chọn` with VND.
- Mock pay → "Thanh toán mô phỏng", buttons "Thanh toán" / "Hủy".
- Payment result → "Kết quả thanh toán", status badge Vietnamese (e.g., "Hoàn tất").
- My bookings → status `Hoàn tất / Đã hủy / Đang chờ`, amount in VND.

If anything still shows English, capture the file:line and add a follow-up commit.

---

## Out of scope (do NOT do in this plan)

- Adding an `i18n` library or language switcher.
- Localizing `genre` field values (`Drama`, `Sci-Fi`, ...).
- Localizing movie `title` fields.
- Translating OpenAPI summaries / Swagger metadata.
- Translating internal log / exception messages developers see in container logs.
- Translating fixture / mock strings in tests that simulate external services.
- Changing `payment-service`'s mock-confirm HTML page (the test asserts `"Pay" in r.text` against THAT page, not the React MockPay view; touching it would break the test).
