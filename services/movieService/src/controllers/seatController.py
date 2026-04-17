from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..models.seatModel import Seat
from ..models.showtimeModel import Showtime
from ..validators.seatSchemas import (
    ConfirmSeatsRequest,
    ConfirmSeatsResponse,
    ReleaseSeatsRequest,
    ReleaseSeatsResponse,
    ReserveSeatsRequest,
    ReserveSeatsResponse,
    SeatItem,
)


def list_seats(db: Session, showtime_id: int) -> list[SeatItem]:
    showtime = db.query(Showtime).filter(Showtime.id == showtime_id).first()
    if not showtime:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="showtime not found")

    seats = (
        db.query(Seat)
        .filter(Seat.showtime_id == showtime_id)
        .order_by(Seat.seat_number)
        .all()
    )
    return [SeatItem.model_validate(s) for s in seats]


def reserve_seats(db: Session, payload: ReserveSeatsRequest) -> ReserveSeatsResponse:
    showtime = db.query(Showtime).filter(Showtime.id == payload.showtime_id).first()
    if not showtime:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="showtime not found")

    seats = (
        db.query(Seat)
        .filter(
            Seat.showtime_id == payload.showtime_id,
            Seat.seat_number.in_(payload.seat_numbers),
        )
        .with_for_update()
        .all()
    )

    found_numbers = {s.seat_number for s in seats}
    missing = [n for n in payload.seat_numbers if n not in found_numbers]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"seats not found: {missing}",
        )

    unavailable = [s.seat_number for s in seats if s.status != "AVAILABLE"]
    if unavailable:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"seats not available: {unavailable}",
        )

    for seat in seats:
        seat.status = "PENDING"
        seat.booking_id = payload.booking_id
    db.commit()

    return ReserveSeatsResponse(
        showtime_id=payload.showtime_id,
        booking_id=payload.booking_id,
        seat_numbers=list(payload.seat_numbers),
        status="PENDING",
    )


def confirm_seats(db: Session, payload: ConfirmSeatsRequest) -> ConfirmSeatsResponse:
    seats = (
        db.query(Seat)
        .filter(Seat.booking_id == payload.booking_id, Seat.status == "PENDING")
        .all()
    )
    if not seats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="no pending seats for booking_id",
        )

    for seat in seats:
        seat.status = "BOOKED"
    db.commit()

    return ConfirmSeatsResponse(
        booking_id=payload.booking_id,
        confirmed=len(seats),
        status="BOOKED",
    )


def release_seats(db: Session, payload: ReleaseSeatsRequest) -> ReleaseSeatsResponse:
    seats = (
        db.query(Seat)
        .filter(Seat.booking_id == payload.booking_id, Seat.status == "PENDING")
        .all()
    )

    for seat in seats:
        seat.status = "AVAILABLE"
        seat.booking_id = None
    db.commit()

    return ReleaseSeatsResponse(
        booking_id=payload.booking_id,
        released=len(seats),
        status="AVAILABLE",
    )
