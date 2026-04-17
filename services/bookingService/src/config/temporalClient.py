"""Thin wrappers around the Temporal client so handlers don't need to know its API.

Both functions are `async` so they can be called from FastAPI handlers. Tests patch
`start_booking_workflow` to avoid a real Temporal dependency.
"""
from __future__ import annotations

from typing import Any

from .settings import get_settings


async def get_temporal_client():
    from temporalio.client import Client

    settings = get_settings()
    return await Client.connect(settings.TEMPORAL_HOST, namespace=settings.TEMPORAL_NAMESPACE)


async def start_booking_workflow(workflow_input: dict[str, Any]) -> str:
    """Start BookingWorkflow and return the workflow_id."""
    from ..workflows.bookingWorkflow import BookingWorkflow

    settings = get_settings()
    client = await get_temporal_client()
    workflow_id = f"booking-{workflow_input['booking_id']}"
    handle = await client.start_workflow(
        BookingWorkflow.run,
        workflow_input,
        id=workflow_id,
        task_queue=settings.TEMPORAL_TASK_QUEUE,
    )
    return handle.id


async def cancel_booking_workflow(workflow_id: str) -> None:
    client = await get_temporal_client()
    handle = client.get_workflow_handle(workflow_id)
    await handle.cancel()
