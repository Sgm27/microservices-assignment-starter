"""Temporal activities for the booking workflow.

Each activity is a thin wrapper around `helpers.bookingHelpers` that also
updates the local `bookings` table so the HTTP API reflects workflow progress.
Activities are imported by the worker (src/worker.py) and by tests.
"""
from __future__ import annotations

from typing import Optional

from temporalio import activity

from ..config.database import SessionLocal
from ..helpers import bookingHelpers as svc
from ..models.bookingModel import Booking


def _load_booking(booking_id: int) -> Booking | None:
    db = SessionLocal()
    try:
        return db.query(Booking).filter(Booking.id == booking_id).first()
    finally:
        db.close()


def _update_booking(booking_id: int, **fields) -> None:
    db = SessionLocal()
    try:
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if booking is None:
            return
        for k, v in fields.items():
            setattr(booking, k, v)
        db.commit()
    finally:
        db.close()


@activity.defn(name="check_payment_status")
async def check_payment_status(payment_id: int) -> str:
    """Return the current payment status (PENDING / SUCCESS / FAILED / CANCELLED)."""
    payment = svc.fetch_payment(payment_id)
    return str(payment.get("status", "PENDING"))


@activity.defn(name="confirm_seats_activity")
async def confirm_seats_activity(booking_id: int) -> None:
    svc.confirm_seats(booking_id)


@activity.defn(name="release_seats_activity")
async def release_seats_activity(booking_id: int) -> None:
    svc.release_seats(booking_id)


@activity.defn(name="redeem_voucher_activity")
async def redeem_voucher_activity(code: Optional[str]) -> None:
    if code:
        svc.redeem_voucher(code)


@activity.defn(name="send_notification_activity")
async def send_notification_activity(
    user_id: int, email: str, subject: str, body: str
) -> None:
    svc.send_notification(user_id, email, subject, body)


@activity.defn(name="finalize_booking_activity")
async def finalize_booking_activity(
    booking_id: int, status_value: str, reason: Optional[str] = None
) -> None:
    _update_booking(booking_id, status=status_value, failure_reason=reason)


ALL_ACTIVITIES = [
    check_payment_status,
    confirm_seats_activity,
    release_seats_activity,
    redeem_voucher_activity,
    send_notification_activity,
    finalize_booking_activity,
]
