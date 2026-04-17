from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..config.database import get_db
from ..controllers import bookingController
from ..validators.bookingSchemas import (
    BookingDetail,
    CreateBookingRequest,
    CreateBookingResponse,
)

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("", response_model=CreateBookingResponse, status_code=201)
def create(payload: CreateBookingRequest, db: Session = Depends(get_db)) -> CreateBookingResponse:
    return bookingController.create_booking(db, payload)


@router.get("/{booking_id}", response_model=BookingDetail)
def get_one(booking_id: int, db: Session = Depends(get_db)) -> BookingDetail:
    return BookingDetail.model_validate(bookingController.get_booking(db, booking_id))


@router.get("/user/{user_id}", response_model=list[BookingDetail])
def list_for_user(user_id: int, db: Session = Depends(get_db)) -> list[BookingDetail]:
    bookings = bookingController.list_bookings_by_user(db, user_id)
    return [BookingDetail.model_validate(b) for b in bookings]


@router.post("/{booking_id}/cancel", response_model=BookingDetail)
def cancel(booking_id: int, db: Session = Depends(get_db)) -> BookingDetail:
    return BookingDetail.model_validate(bookingController.cancel_booking(db, booking_id))
