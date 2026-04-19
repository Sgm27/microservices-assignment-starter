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
