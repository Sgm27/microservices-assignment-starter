from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..helpers import bookingHelpers as svc
from ..models.bookingModel import Booking
from ..validators.bookingSchemas import CreateBookingRequest, CreateBookingResponse


_ERROR_CODE_TO_STATUS = {
    "seat_conflict":      409,
    "voucher_invalid":    400,
    "downstream_voucher": 502,
    "downstream_payment": 502,
    "setup_timeout":      502,
}


def _price_of_showtime(showtime: dict) -> Decimal:
    return Decimal(str(showtime.get("base_price") or 0))


def _start_workflow_sync(workflow_input: dict) -> str:
    from ..config import temporalClient

    return asyncio.run(temporalClient.start_booking_workflow(workflow_input))


async def _wait_for_setup_async(workflow_id: str, timeout_s: int) -> dict[str, Any]:
    from ..config.temporalClient import query_setup_result_async

    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout_s
    while True:
        try:
            result = await query_setup_result_async(workflow_id)
        except Exception:
            result = {"state": "setting_up"}
        state = result.get("state")
        if state in ("awaiting_payment", "failed"):
            return result
        if loop.time() >= deadline:
            return {
                "state": "failed",
                "payment_id": None,
                "payment_url": None,
                "error_code": "setup_timeout",
                "error_message": "Workflow setup timeout",
            }
        await asyncio.sleep(0.2)


def _wait_for_setup(workflow_id: str, timeout_s: int = 15) -> dict[str, Any]:
    return asyncio.run(_wait_for_setup_async(workflow_id, timeout_s))


def create_booking(db: Session, payload: CreateBookingRequest) -> CreateBookingResponse:
    # 1. Fetch showtime (validate + compute original amount)
    try:
        showtime = svc.fetch_showtime(payload.showtime_id)
    except svc.DownstreamError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    seat_count = len(payload.seat_numbers)
    original_amount = _price_of_showtime(showtime) * seat_count

    # 2. Insert booking row (PENDING)
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

    # 3. Start Temporal workflow
    try:
        workflow_id = _start_workflow_sync({
            "booking_id": booking.id,
            "user_id": payload.user_id,
            "showtime_id": payload.showtime_id,
            "seat_numbers": list(payload.seat_numbers),
            "voucher_code": payload.voucher_code,
            "email": payload.email,
            "original_amount": str(original_amount),
        })
    except Exception as exc:
        booking.status = "FAILED"
        booking.failure_reason = f"workflow start failed: {exc}"
        db.commit()
        raise HTTPException(status_code=502, detail="Không thể khởi tạo workflow") from exc

    booking.workflow_id = workflow_id
    db.commit()

    # 4. Wait for setup activities to finish (via workflow query)
    result = _wait_for_setup(workflow_id, timeout_s=15)

    # 5. Map to HTTP
    if result.get("state") == "awaiting_payment":
        return CreateBookingResponse(
            booking_id=booking.id,
            workflow_id=booking.workflow_id,
            payment_id=int(result["payment_id"]),
            payment_url=result["payment_url"],
            status="AWAITING_PAYMENT",
            final_amount=booking.final_amount,
        )

    status_code = _ERROR_CODE_TO_STATUS.get(result.get("error_code"), 502)
    raise HTTPException(
        status_code=status_code,
        detail=result.get("error_message") or "Booking setup failed",
    )


def get_booking(db: Session, booking_id: int) -> Booking:
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if booking is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn đặt vé")
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
        raise HTTPException(
            status_code=400,
            detail=f"Không thể hủy đơn ở trạng thái {booking.status}",
        )

    try:
        svc.release_seats(booking.id)
    except svc.DownstreamError:
        pass

    booking.status = "CANCELLED"
    booking.failure_reason = "cancelled by user"
    db.commit()
    db.refresh(booking)
    return booking
