from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..config.database import get_db
from ..controllers import seatController
from ..validators.seatSchemas import (
    ConfirmSeatsRequest,
    ConfirmSeatsResponse,
    ReleaseSeatsRequest,
    ReleaseSeatsResponse,
    ReserveSeatsRequest,
    ReserveSeatsResponse,
    SeatItem,
)

showtime_seat_router = APIRouter(tags=["seats"])
seat_router = APIRouter(prefix="/seats", tags=["seats"])


@showtime_seat_router.get("/showtimes/{showtime_id}/seats", response_model=list[SeatItem])
def list_seats(showtime_id: int, db: Session = Depends(get_db)) -> list[SeatItem]:
    return seatController.list_seats(db, showtime_id)


@seat_router.post("/reserve", response_model=ReserveSeatsResponse)
def reserve_seats(
    payload: ReserveSeatsRequest, db: Session = Depends(get_db)
) -> ReserveSeatsResponse:
    return seatController.reserve_seats(db, payload)


@seat_router.post("/confirm", response_model=ConfirmSeatsResponse)
def confirm_seats(
    payload: ConfirmSeatsRequest, db: Session = Depends(get_db)
) -> ConfirmSeatsResponse:
    return seatController.confirm_seats(db, payload)


@seat_router.post("/release", response_model=ReleaseSeatsResponse)
def release_seats(
    payload: ReleaseSeatsRequest, db: Session = Depends(get_db)
) -> ReleaseSeatsResponse:
    return seatController.release_seats(db, payload)
