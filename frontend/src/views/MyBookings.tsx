import { useEffect, useState } from "react";
import { listUserBookings } from "../api/bookings";
import { useAuth } from "../context/AuthContext";
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
              "Failed to load bookings",
          );
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, [user]);

  if (loading) return <p>Loading bookings…</p>;
  if (error) return <p className="error">{error}</p>;

  return (
    <section>
      <h1>My Bookings</h1>
      {bookings.length === 0 ? (
        <p className="muted">No bookings yet.</p>
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
                      · {new Date(b.created_at).toLocaleString()}
                    </span>
                  )}
                </div>
                {b.showtime_id && <div>Showtime: {b.showtime_id}</div>}
                {b.seat_numbers && (
                  <div>Seats: {b.seat_numbers.join(", ")}</div>
                )}
                {typeof b.final_amount === "number" && (
                  <div>Amount: ${b.final_amount.toFixed(2)}</div>
                )}
                <div>Status: {b.status}</div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
