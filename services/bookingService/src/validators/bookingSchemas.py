from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CreateBookingRequest(BaseModel):
    user_id: int = Field(ge=1)
    showtime_id: int = Field(ge=1)
    seat_numbers: list[str] = Field(min_length=1, max_length=10)
    voucher_code: Optional[str] = None
    email: EmailStr


class CreateBookingResponse(BaseModel):
    booking_id: int
    workflow_id: Optional[str] = None
    payment_id: int
    payment_url: str
    status: str
    final_amount: Decimal


class BookingDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    showtime_id: int
    seat_numbers: list[str]
    voucher_code: Optional[str]
    email: str
    original_amount: Decimal
    discount_amount: Decimal
    final_amount: Decimal
    payment_id: Optional[int]
    workflow_id: Optional[str]
    status: str
    failure_reason: Optional[str]
    created_at: datetime
    updated_at: datetime
