"""Temporal workflow that finalises a booking after payment."""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from ..activities.bookingActivities import (
        check_payment_status,
        confirm_seats_activity,
        finalize_booking_activity,
        redeem_voucher_activity,
        release_seats_activity,
        send_notification_activity,
    )


POLL_INTERVAL_SECONDS = 5
PAYMENT_TIMEOUT_SECONDS = 300  # 5 minutes


@workflow.defn(name="BookingWorkflow")
class BookingWorkflow:
    @workflow.run
    async def run(self, input: dict[str, Any]) -> str:
        booking_id: int = int(input["booking_id"])
        payment_id: int = int(input["payment_id"])
        user_id: int = int(input["user_id"])
        email: str = str(input["email"])
        voucher_code = input.get("voucher_code")

        # 1. Poll payment status until terminal or timeout
        elapsed = 0
        final_status = "PENDING"
        while elapsed < PAYMENT_TIMEOUT_SECONDS:
            status = await workflow.execute_activity(
                check_payment_status,
                payment_id,
                start_to_close_timeout=timedelta(seconds=30),
            )
            if status in ("SUCCESS", "FAILED", "CANCELLED"):
                final_status = status
                break
            await workflow.sleep(POLL_INTERVAL_SECONDS)
            elapsed += POLL_INTERVAL_SECONDS

        # 2. SUCCESS → confirm, redeem, notify, mark ACTIVE
        if final_status == "SUCCESS":
            await workflow.execute_activity(
                confirm_seats_activity,
                booking_id,
                start_to_close_timeout=timedelta(seconds=30),
            )
            if voucher_code:
                await workflow.execute_activity(
                    redeem_voucher_activity,
                    voucher_code,
                    start_to_close_timeout=timedelta(seconds=30),
                )
            await workflow.execute_activity(
                send_notification_activity,
                args=[
                    user_id,
                    email,
                    "Booking confirmed",
                    f"Booking {booking_id} confirmed. Enjoy the show!",
                ],
                start_to_close_timeout=timedelta(seconds=30),
            )
            await workflow.execute_activity(
                finalize_booking_activity,
                args=[booking_id, "ACTIVE", None],
                start_to_close_timeout=timedelta(seconds=30),
            )
            return "ACTIVE"

        # 3. Failure / timeout → compensate
        reason = f"payment {final_status.lower()}" if final_status != "PENDING" else "payment timeout"
        await workflow.execute_activity(
            release_seats_activity,
            booking_id,
            start_to_close_timeout=timedelta(seconds=30),
        )
        await workflow.execute_activity(
            finalize_booking_activity,
            args=[booking_id, "CANCELLED", reason],
            start_to_close_timeout=timedelta(seconds=30),
        )
        return "CANCELLED"
