from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CreateUserRequest(BaseModel):
    id: int | None = Field(default=None, ge=1)
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=128)
    phone: str | None = Field(default=None, max_length=32)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    phone: str | None = None
    created_at: datetime
