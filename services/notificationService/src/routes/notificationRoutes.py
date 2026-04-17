from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..config.database import get_db
from ..controllers import notificationController
from ..validators.notificationSchemas import (
    NotificationResponse,
    SendNotificationRequest,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("/send", response_model=NotificationResponse, status_code=201)
def send(
    payload: SendNotificationRequest,
    db: Session = Depends(get_db),
) -> NotificationResponse:
    return notificationController.send_notification(db, payload)


@router.get("", response_model=list[NotificationResponse])
def list_all(db: Session = Depends(get_db)) -> list[NotificationResponse]:
    return notificationController.list_notifications(db)


@router.get("/{notification_id}", response_model=NotificationResponse)
def get_one(
    notification_id: int,
    db: Session = Depends(get_db),
) -> NotificationResponse:
    return notificationController.get_notification(db, notification_id)
