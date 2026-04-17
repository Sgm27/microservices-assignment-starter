from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SendNotificationRequest(BaseModel):
    user_id: int = Field(ge=1)
    email: EmailStr
    subject: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1)


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    email: EmailStr
    subject: str
    body: str
    status: str
    error: Optional[str] = None
    sent_at: Optional[datetime] = None
    created_at: datetime
