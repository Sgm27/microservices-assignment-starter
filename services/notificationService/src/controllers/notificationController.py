from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..config.settings import get_settings
from ..models.notificationModel import Notification
from ..services import emailSender
from ..validators.notificationSchemas import (
    NotificationResponse,
    SendNotificationRequest,
)


def send_notification(
    db: Session, payload: SendNotificationRequest
) -> NotificationResponse:
    settings = get_settings()

    notification = Notification(
        user_id=payload.user_id,
        email=payload.email,
        subject=payload.subject,
        body=payload.body,
        status="PENDING",
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)

    success, error_message = emailSender.send_email(
        to=payload.email,
        subject=payload.subject,
        body=payload.body,
        mock=settings.EMAIL_MOCK,
        user=settings.EMAIL_USER,
        password=settings.EMAIL_PASS,
        host=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
    )

    if success:
        notification.status = "SENT"
        notification.sent_at = datetime.utcnow()
        notification.error = None
    else:
        notification.status = "FAILED"
        notification.error = (error_message or "unknown error")[:512]

    db.commit()
    db.refresh(notification)

    return NotificationResponse.model_validate(notification)


def list_notifications(db: Session) -> list[NotificationResponse]:
    rows = (
        db.query(Notification)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .all()
    )
    return [NotificationResponse.model_validate(row) for row in rows]


def get_notification(db: Session, notification_id: int) -> NotificationResponse:
    row = db.query(Notification).filter(Notification.id == notification_id).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="notification not found",
        )
    return NotificationResponse.model_validate(row)
