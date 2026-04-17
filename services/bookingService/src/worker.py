"""Temporal worker process — registers BookingWorkflow + activities."""
from __future__ import annotations

import asyncio
import logging

from temporalio.client import Client
from temporalio.worker import Worker

from .activities.bookingActivities import ALL_ACTIVITIES
from .config.database import Base, engine
from .config.settings import get_settings
from .models import bookingModel  # noqa: F401
from .workflows.bookingWorkflow import BookingWorkflow

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("booking-worker")


async def main() -> None:
    Base.metadata.create_all(bind=engine)
    settings = get_settings()
    log.info("Connecting to Temporal at %s (namespace=%s)", settings.TEMPORAL_HOST, settings.TEMPORAL_NAMESPACE)
    client = await Client.connect(settings.TEMPORAL_HOST, namespace=settings.TEMPORAL_NAMESPACE)

    worker = Worker(
        client,
        task_queue=settings.TEMPORAL_TASK_QUEUE,
        workflows=[BookingWorkflow],
        activities=ALL_ACTIVITIES,
    )
    log.info("Worker listening on task queue '%s'", settings.TEMPORAL_TASK_QUEUE)
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
