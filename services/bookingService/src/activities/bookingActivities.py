"""Temporal activities for BookingWorkflow.

Each activity is a thin wrapper around `helpers.bookingHelpers`. Some also
update the local `bookings` table (persist_setup, finalize_booking) so the
HTTP API reflects workflow progress.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from temporalio import activity

from ..config.database import SessionLocal
from ..helpers import bookingHelpers as svc
from ..models.bookingModel import Booking


def _update_booking(booking_id: int, **fields) -> None:
    db = SessionLocal()
    try:
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if booking is None:
            return
        for k, v in fields.items():
            setattr(booking, k, v)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# --- Setup activities --------------------------------------------------------


@activity.defn(name="reserve_seats_activity")
async def reserve_seats_activity(
    booking_id: int, showtime_id: int, seat_numbers: list[str]
) -> None:
    svc.reserve_seats(showtime_id, seat_numbers, booking_id)


@activity.defn(name="validate_voucher_activity")
async def validate_voucher_activity(code: str, base_amount: str) -> dict:
    result = svc.validate_voucher(code, Decimal(base_amount))
    raw_discount = result.get("discount_amount")
    return {
        "valid": bool(result.get("valid")),
        "discount_amount": str(raw_discount) if raw_discount is not None else "0",
        "message": result.get("message") or "",
    }


@activity.defn(name="create_payment_activity")
async def create_payment_activity(booking_id: int, amount: str) -> dict:
    result = svc.create_payment(booking_id, Decimal(amount))
    return {
        "payment_id": int(result["payment_id"]),
        "payment_url": str(result["payment_url"]),
    }


@activity.defn(name="persist_setup_activity")
async def persist_setup_activity(
    booking_id: int, payment_id: int, discount_amount: str, final_amount: str
) -> None:
    _update_booking(
        booking_id,
        payment_id=payment_id,
        discount_amount=Decimal(discount_amount),
        final_amount=Decimal(final_amount),
        status="AWAITING_PAYMENT",
    )


# --- Compensation / completion activities ------------------------------------


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


@activity.defn(name="cancel_payment_activity")
async def cancel_payment_activity(payment_id: int) -> None:
    svc.cancel_payment(payment_id)


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
    reserve_seats_activity,
    validate_voucher_activity,
    create_payment_activity,
    persist_setup_activity,
    confirm_seats_activity,
    release_seats_activity,
    redeem_voucher_activity,
    cancel_payment_activity,
    send_notification_activity,
    finalize_booking_activity,
]
