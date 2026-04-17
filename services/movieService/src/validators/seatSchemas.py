from pydantic import BaseModel, ConfigDict, Field


class SeatItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    seat_number: str
    status: str


class ReserveSeatsRequest(BaseModel):
    showtime_id: int
    seat_numbers: list[str] = Field(min_length=1)
    booking_id: int


class ReserveSeatsResponse(BaseModel):
    showtime_id: int
    booking_id: int
    seat_numbers: list[str]
    status: str = "PENDING"


class ConfirmSeatsRequest(BaseModel):
    booking_id: int


class ConfirmSeatsResponse(BaseModel):
    booking_id: int
    confirmed: int
    status: str = "BOOKED"


class ReleaseSeatsRequest(BaseModel):
    booking_id: int


class ReleaseSeatsResponse(BaseModel):
    booking_id: int
    released: int
    status: str = "AVAILABLE"
