import { statusLabel } from "../utils/format";
import type { Seat } from "../types";

type Props = {
  seats: Seat[];
  selected: string[];
  onToggle: (seat: Seat) => void;
};

export default function SeatGrid({ seats, selected, onToggle }: Props) {
  return (
    <div className="seat-grid">
      {seats.map((seat) => {
        const isSelected = selected.includes(seat.seat_number);
        const disabled = seat.status !== "AVAILABLE";
        const classes = [
          "seat",
          `seat-${seat.status.toLowerCase()}`,
          isSelected ? "seat-selected" : "",
        ]
          .filter(Boolean)
          .join(" ");
        return (
          <button
            key={seat.seat_number}
            type="button"
            className={classes}
            onClick={() => !disabled && onToggle(seat)}
            disabled={disabled}
            aria-pressed={isSelected}
            title={`${seat.seat_number} — ${statusLabel(seat.status)}`}
          >
            {seat.seat_number}
          </button>
        );
      })}
    </div>
  );
}
