"""Temporal client helpers for paymentService — used to signal BookingWorkflow."""
from __future__ import annotations

import asyncio

from .settings import get_settings


async def get_temporal_client():
    from temporalio.client import Client

    settings = get_settings()
    return await Client.connect(
        settings.TEMPORAL_HOST,
        namespace=settings.TEMPORAL_NAMESPACE,
    )


async def signal_payment_completed_async(booking_id: int, success: bool) -> None:
    client = await get_temporal_client()
    handle = client.get_workflow_handle(f"booking-{booking_id}")
    await handle.signal("payment_completed", success)


def signal_payment_completed(booking_id: int, success: bool) -> None:
    """Sync wrapper for FastAPI handlers — tests monkey-patch this symbol."""
    asyncio.run(signal_payment_completed_async(booking_id, success))
