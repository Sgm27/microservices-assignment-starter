import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getShowtime, getShowtimeSeats } from "../api/movies";
import { validateVoucher } from "../api/vouchers";
import { createBooking } from "../api/bookings";
import { useAuth } from "../context/AuthContext";
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
            (err as { message?: string })?.message ?? "Failed to load showtime",
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
      setVoucherError("Pick at least one seat first.");
      return;
    }
    try {
      const result = await validateVoucher(voucherCode.trim(), baseAmount);
      setVoucher(result);
      if (!result.valid) {
        setVoucherError(result.message ?? "Voucher not valid.");
      }
    } catch (err) {
      setVoucherError(
        (err as { message?: string })?.message ?? "Voucher check failed",
      );
    }
  };

  const handleBook = async () => {
    if (!id || !user) return;
    if (selected.length === 0) {
      setError("Pick at least one seat.");
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
          "Booking failed",
      );
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <p>Loading showtime…</p>;
  if (error && !showtime) return <p className="error">{error}</p>;
  if (!showtime) return <p>Showtime not found.</p>;

  return (
    <section className="booking-page">
      <h1>Book Seats</h1>
      <p className="muted">
        Room {showtime.room} — {new Date(showtime.starts_at).toLocaleString()} —
        Base ${Number(showtime.base_price).toFixed(2)}
      </p>

      <h2>Choose seats</h2>
      <SeatGrid seats={seats} selected={selected} onToggle={toggleSeat} />

      <div className="seat-legend">
        <span className="legend-box seat-available" /> Available
        <span className="legend-box seat-pending" /> Pending
        <span className="legend-box seat-booked" /> Booked
        <span className="legend-box seat-selected" /> Selected
      </div>

      <div className="voucher-row">
        <input
          type="text"
          placeholder="Voucher code (optional)"
          value={voucherCode}
          onChange={(e) => setVoucherCode(e.target.value)}
        />
        <button type="button" onClick={applyVoucher} className="btn btn-ghost">
          Apply
        </button>
      </div>
      {voucherError && <p className="error">{voucherError}</p>}
      {voucher?.valid && (
        <p className="success">
          Voucher applied. Discount ${voucher.discount_amount.toFixed(2)}.
        </p>
      )}

      <div className="booking-summary">
        <p>Selected: {selected.length ? selected.join(", ") : "none"}</p>
        <p>Base total: ${baseAmount.toFixed(2)}</p>
        <p>
          <strong>Final: ${finalAmount.toFixed(2)}</strong>
        </p>
      </div>

      {error && <p className="error">{error}</p>}

      <button
        type="button"
        onClick={handleBook}
        disabled={submitting || selected.length === 0}
        className="btn btn-primary"
      >
        {submitting ? "Booking…" : "Book"}
      </button>
    </section>
  );
}
