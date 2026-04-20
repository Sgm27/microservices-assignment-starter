"""BookingWorkflow — saga orchestrator per CLAUDE.md.

Setup activities: reserve_seats → validate_voucher → create_payment → persist_setup.
Then waits for `payment_completed` signal (timeout 5 min), then either confirms
or compensates (release_seats + cancel_payment).
"""
from __future__ import annotations

import asyncio
from datetime import timedelta
from decimal import Decimal
from typing import Any, Optional

from temporalio import workflow
from temporalio.exceptions import ActivityError

with workflow.unsafe.imports_passed_through():
    from ..activities.bookingActivities import (
        cancel_payment_activity,
        confirm_seats_activity,
        create_payment_activity,
        finalize_booking_activity,
        persist_setup_activity,
        redeem_voucher_activity,
        release_seats_activity,
        reserve_seats_activity,
        send_notification_activity,
        validate_voucher_activity,
    )


PAYMENT_TIMEOUT_SECONDS = 300  # 5 minutes
ACTIVITY_TIMEOUT = timedelta(seconds=30)


@workflow.defn(name="BookingWorkflow")
class BookingWorkflow:
    def __init__(self) -> None:
        self._state: str = "setting_up"
        self._payment_id: Optional[int] = None
        self._payment_url: Optional[str] = None
        self._error_code: Optional[str] = None
        self._error_message: Optional[str] = None
        self._payment_result: Optional[bool] = None

    @workflow.signal
    def payment_completed(self, success: bool) -> None:
        self._payment_result = bool(success)

    @workflow.query
    def get_setup_result(self) -> dict[str, Any]:
        return {
            "state": self._state,
            "payment_id": self._payment_id,
            "payment_url": self._payment_url,
            "error_code": self._error_code,
            "error_message": self._error_message,
        }

    def _fail(self, code: str, message: str) -> None:
        self._state = "failed"
        self._error_code = code
        self._error_message = message

    @workflow.run
    async def run(self, input: dict[str, Any]) -> str:
        booking_id: int = int(input["booking_id"])
        user_id: int = int(input["user_id"])
        showtime_id: int = int(input["showtime_id"])
        seat_numbers: list[str] = list(input["seat_numbers"])
        voucher_code: Optional[str] = input.get("voucher_code")
        email: str = str(input["email"])
        original_amount = Decimal(str(input["original_amount"]))

        # --- 1. Reserve seats -------------------------------------------------
        try:
            await workflow.execute_activity(
                reserve_seats_activity,
                args=[booking_id, showtime_id, seat_numbers],
                start_to_close_timeout=ACTIVITY_TIMEOUT,
            )
        except ActivityError as exc:
            cause = str(exc.cause) if exc.cause else str(exc)
            self._fail("seat_conflict", cause)
            await workflow.execute_activity(
                finalize_booking_activity,
                args=[booking_id, "FAILED", f"reserve_seats: {cause}"],
                start_to_close_timeout=ACTIVITY_TIMEOUT,
            )
            return "FAILED_SETUP"

        # --- 2. Validate voucher (optional) -----------------------------------
        discount = Decimal(0)
        if voucher_code:
            try:
                v = await workflow.execute_activity(
                    validate_voucher_activity,
                    args=[voucher_code, str(original_amount)],
                    start_to_close_timeout=ACTIVITY_TIMEOUT,
                )
            except ActivityError as exc:
                cause = str(exc.cause) if exc.cause else str(exc)
                await workflow.execute_activity(
                    release_seats_activity,
                    booking_id,
                    start_to_close_timeout=ACTIVITY_TIMEOUT,
                )
                self._fail("downstream_voucher", cause)
                await workflow.execute_activity(
                    finalize_booking_activity,
                    args=[booking_id, "FAILED", f"voucher: {cause}"],
                    start_to_close_timeout=ACTIVITY_TIMEOUT,
                )
                return "FAILED_SETUP"

            if not v["valid"]:
                msg = v.get("message") or "Mã giảm giá không hợp lệ"
                await workflow.execute_activity(
                    release_seats_activity,
                    booking_id,
                    start_to_close_timeout=ACTIVITY_TIMEOUT,
                )
                self._fail("voucher_invalid", msg)
                await workflow.execute_activity(
                    finalize_booking_activity,
                    args=[booking_id, "FAILED", f"voucher invalid: {msg}"],
                    start_to_close_timeout=ACTIVITY_TIMEOUT,
                )
                return "FAILED_SETUP"

            discount = Decimal(v["discount_amount"])

        final_amount = original_amount - discount
        if final_amount < 0:
            final_amount = Decimal(0)

        # --- 3. Create payment -----------------------------------------------
        try:
            pay = await workflow.execute_activity(
                create_payment_activity,
                args=[booking_id, str(final_amount)],
                start_to_close_timeout=ACTIVITY_TIMEOUT,
            )
        except ActivityError as exc:
            cause = str(exc.cause) if exc.cause else str(exc)
            await workflow.execute_activity(
                release_seats_activity,
                booking_id,
                start_to_close_timeout=ACTIVITY_TIMEOUT,
            )
            self._fail("downstream_payment", cause)
            await workflow.execute_activity(
                finalize_booking_activity,
                args=[booking_id, "FAILED", f"payment: {cause}"],
                start_to_close_timeout=ACTIVITY_TIMEOUT,
            )
            return "FAILED_SETUP"

        self._payment_id = int(pay["payment_id"])
        self._payment_url = str(pay["payment_url"])

        # --- 4. Persist setup on booking row ---------------------------------
        await workflow.execute_activity(
            persist_setup_activity,
            args=[booking_id, self._payment_id, str(discount), str(final_amount)],
            start_to_close_timeout=ACTIVITY_TIMEOUT,
        )
        self._state = "awaiting_payment"

        # --- 5. Wait for payment_completed signal or timeout -----------------
        try:
            await workflow.wait_condition(
                lambda: self._payment_result is not None,
                timeout=timedelta(seconds=PAYMENT_TIMEOUT_SECONDS),
            )
        except asyncio.TimeoutError:
            self._payment_result = False
            reason = "payment timeout"
        else:
            reason = None if self._payment_result else "payment failed"

        # --- 6a. Success path ------------------------------------------------
        if self._payment_result:
            await workflow.execute_activity(
                confirm_seats_activity,
                booking_id,
                start_to_close_timeout=ACTIVITY_TIMEOUT,
            )
            if voucher_code:
                await workflow.execute_activity(
                    redeem_voucher_activity,
                    voucher_code,
                    start_to_close_timeout=ACTIVITY_TIMEOUT,
                )
            await workflow.execute_activity(
                send_notification_activity,
                args=[
                    user_id,
                    email,
                    "Xác nhận đặt vé",
                    f"Đơn đặt vé {booking_id} đã được xác nhận. Chúc bạn xem phim vui vẻ!",
                ],
                start_to_close_timeout=ACTIVITY_TIMEOUT,
            )
            await workflow.execute_activity(
                finalize_booking_activity,
                args=[booking_id, "ACTIVE", None],
                start_to_close_timeout=ACTIVITY_TIMEOUT,
            )
            return "ACTIVE"

        # --- 6b. Compensation path (signal False or timeout) -----------------
        await workflow.execute_activity(
            release_seats_activity,
            booking_id,
            start_to_close_timeout=ACTIVITY_TIMEOUT,
        )
        await workflow.execute_activity(
            cancel_payment_activity,
            self._payment_id,
            start_to_close_timeout=ACTIVITY_TIMEOUT,
        )
        await workflow.execute_activity(
            finalize_booking_activity,
            args=[booking_id, "CANCELLED", reason],
            start_to_close_timeout=ACTIVITY_TIMEOUT,
        )
        return "CANCELLED"
