from __future__ import annotations

import asyncio
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..helpers import bookingHelpers as svc
from ..models.bookingModel import Booking
from ..validators.bookingSchemas import CreateBookingRequest, CreateBookingResponse


def _price_of_showtime(showtime: dict) -> Decimal:
    return Decimal(str(showtime.get("base_price") or 0))


def _start_workflow_sync(workflow_input: dict) -> str:
    """Synchronously start the Temporal workflow from a sync handler.

    Imported lazily so tests can monkey-patch `temporalClient.start_booking_workflow`.
    """
    from ..config import temporalClient

    return asyncio.run(temporalClient.start_booking_workflow(workflow_input))


def create_booking(db: Session, payload: CreateBookingRequest) -> CreateBookingResponse:
    # 1. Fetch showtime (validate + price)
    try:
        showtime = svc.fetch_showtime(payload.showtime_id)
    except svc.DownstreamError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    seat_count = len(payload.seat_numbers)
    unit_price = _price_of_showtime(showtime)
    original_amount = unit_price * seat_count

    # 2. Persist booking PENDING
    booking = Booking(
        user_id=payload.user_id,
        showtime_id=payload.showtime_id,
        seat_numbers=list(payload.seat_numbers),
        voucher_code=payload.voucher_code,
        email=payload.email,
        original_amount=original_amount,
        discount_amount=Decimal(0),
        final_amount=original_amount,
        status="PENDING",
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    # 3. Reserve seats
    try:
        svc.reserve_seats(payload.showtime_id, payload.seat_numbers, booking.id)
    except svc.DownstreamError as exc:
        booking.status = "FAILED"
        booking.failure_reason = f"reserve_seats: {exc}"
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    # 4. Validate voucher
    discount_amount = Decimal(0)
    if payload.voucher_code:
        try:
            v = svc.validate_voucher(payload.voucher_code, original_amount)
        except svc.DownstreamError as exc:
            svc.release_seats(booking.id)
            booking.status = "FAILED"
            booking.failure_reason = f"voucher: {exc}"
            db.commit()
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        if not v.get("valid"):
            svc.release_seats(booking.id)
            booking.status = "FAILED"
            booking.failure_reason = f"voucher invalid: {v.get('message')}"
            db.commit()
            raise HTTPException(status_code=400, detail=v.get("message") or "invalid voucher")
        discount_amount = Decimal(str(v.get("discount_amount") or 0))

    final_amount = (original_amount - discount_amount).quantize(Decimal("0.01"))
    if final_amount < 0:
        final_amount = Decimal(0)

    # 5. Create payment
    try:
        payment = svc.create_payment(booking.id, final_amount)
    except svc.DownstreamError as exc:
        svc.release_seats(booking.id)
        booking.status = "FAILED"
        booking.failure_reason = f"payment: {exc}"
        db.commit()
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    booking.discount_amount = discount_amount
    booking.final_amount = final_amount
    booking.payment_id = int(payment["payment_id"])
    booking.status = "AWAITING_PAYMENT"
    db.commit()
    db.refresh(booking)

    # 6. Kick off Temporal workflow
    try:
        workflow_id = _start_workflow_sync(
            {
                "booking_id": booking.id,
                "payment_id": booking.payment_id,
                "user_id": booking.user_id,
                "email": booking.email,
                "voucher_code": booking.voucher_code,
            }
        )
        booking.workflow_id = workflow_id
        db.commit()
        db.refresh(booking)
    except Exception as exc:  # pragma: no cover — Temporal unavailable
        booking.failure_reason = f"workflow start failed: {exc}"
        db.commit()
        # Do not fail the HTTP call — the client already has a payment URL.
        # The worker will never pick this booking up; a manual retry is required.

    return CreateBookingResponse(
        booking_id=booking.id,
        workflow_id=booking.workflow_id,
        payment_id=booking.payment_id,
        payment_url=payment["payment_url"],
        status=booking.status,
        final_amount=booking.final_amount,
    )


def get_booking(db: Session, booking_id: int) -> Booking:
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if booking is None:
        raise HTTPException(status_code=404, detail="booking not found")
    return booking


def list_bookings_by_user(db: Session, user_id: int) -> list[Booking]:
    return (
        db.query(Booking)
        .filter(Booking.user_id == user_id)
        .order_by(Booking.created_at.desc())
        .all()
    )


def cancel_booking(db: Session, booking_id: int) -> Booking:
    booking = get_booking(db, booking_id)
    if booking.status in ("ACTIVE", "CANCELLED"):
        raise HTTPException(status_code=400, detail=f"cannot cancel booking in state {booking.status}")

    # Best-effort seat release (idempotent on the movieService side).
    try:
        svc.release_seats(booking.id)
    except svc.DownstreamError:
        pass  # seat already released or service down — keep cancelling booking anyway

    booking.status = "CANCELLED"
    booking.failure_reason = "cancelled by user"
    db.commit()
    db.refresh(booking)
    return booking
