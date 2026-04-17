import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { getBooking } from "../api/bookings";
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
      setError("Missing booking_id in URL.");
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
          (err as { message?: string })?.message ?? "Failed to load booking",
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
      <h1>Payment Result</h1>
      {!done && (
        <p className="muted">
          Waiting for payment confirmation… ({tries}/{MAX_TRIES})
        </p>
      )}
      {error && <p className="error">{error}</p>}
      {booking && (
        <div className="booking-summary">
          <p>
            Status: <span className={statusClass(status)}>{status || "—"}</span>
          </p>
          {booking.showtime_id && <p>Showtime: {booking.showtime_id}</p>}
          {booking.seat_numbers && (
            <p>Seats: {booking.seat_numbers.join(", ")}</p>
          )}
          {typeof booking.final_amount === "number" && (
            <p>Amount: ${booking.final_amount.toFixed(2)}</p>
          )}
          {booking.booking_id && <p className="muted">Booking {booking.booking_id}</p>}
        </div>
      )}
      {done && (
        <div className="btn-row">
          <Link to="/bookings" className="btn btn-primary">
            My Bookings
          </Link>
          <Link to="/" className="btn btn-ghost">
            Back to Home
          </Link>
        </div>
      )}
    </div>
  );
}
