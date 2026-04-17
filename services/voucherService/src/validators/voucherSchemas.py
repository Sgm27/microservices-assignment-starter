from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class VoucherCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    discount_percent: int = Field(ge=0, le=100)
    max_uses: int = Field(default=100, ge=1)
    valid_from: datetime
    valid_to: datetime


class VoucherResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    discount_percent: int
    max_uses: int
    used_count: int
    valid_from: datetime
    valid_to: datetime
    created_at: datetime


class VoucherValidateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    base_amount: float = Field(ge=0)


class VoucherValidateResponse(BaseModel):
    valid: bool
    discount_amount: float
    final_amount: float
    message: Optional[str] = None


class VoucherRedeemRequest(BaseModel):
    code: str = Field(min_length=1, max_length=64)


class VoucherRedeemResponse(BaseModel):
    code: str
    used_count: int
    max_uses: int
