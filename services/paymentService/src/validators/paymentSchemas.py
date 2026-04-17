from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CreatePaymentRequest(BaseModel):
    booking_id: int = Field(gt=0)
    amount: Decimal = Field(gt=Decimal("0"))
    return_url: Optional[str] = None


class CreatePaymentResponse(BaseModel):
    payment_id: int
    payment_url: str
    status: str


class ConfirmPaymentRequest(BaseModel):
    success: bool


class PaymentDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    booking_id: int
    amount: Decimal
    status: str
    provider: str
    payment_url: Optional[str]
    provider_txn_id: Optional[str]
    created_at: datetime
    updated_at: datetime
