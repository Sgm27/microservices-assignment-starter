"""End-to-end tests for BookingWorkflow using Temporal time-skipping env.

Activities are replaced by stub async functions registered under the
production activity names. We only verify workflow orchestration — the
real activity bodies are tested separately in test_activities.py.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

import pytest
from temporalio import activity
from temporalio.client import Client
from temporalio.exceptions import ApplicationError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker


TASK_QUEUE = "booking-test-queue"

ACTIVITY_NAMES = [
    "reserve_seats_activity",
    "validate_voucher_activity",
    "create_payment_activity",
    "persist_setup_activity",
    "confirm_seats_activity",
    "release_seats_activity",
    "redeem_voucher_activity",
    "cancel_payment_activity",
    "send_notification_activity",
    "finalize_booking_activity",
]


@dataclass
class ActivitySpy:
    """Records calls and returns a fixed value (or raises)."""
    name: str
    returns: Any = None
    raises: Exception | None = None
    calls: list[tuple[tuple, dict]] = field(default_factory=list)

    def __call__(self) -> Callable[..., Awaitable[Any]]:
        @activity.defn(name=self.name)
        async def _stub(*args: Any, **kwargs: Any) -> Any:
            self.calls.append((args, kwargs))
            if self.raises is not None:
                raise self.raises
            return self.returns

        return _stub


def _build_spies(overrides: dict[str, dict] | None = None) -> dict[str, ActivitySpy]:
    """Build an ActivitySpy for every activity; overrides set returns/raises."""
    overrides = overrides or {}
    spies: dict[str, ActivitySpy] = {}
    for name in ACTIVITY_NAMES:
        cfg = overrides.get(name, {})
        spies[name] = ActivitySpy(
            name=name,
            returns=cfg.get("returns"),
            raises=cfg.get("raises"),
        )
    return spies


def _activities_from_spies(spies: dict[str, ActivitySpy]) -> list:
    return [spy() for spy in spies.values()]


def _default_workflow_input(voucher_code: str | None = None) -> dict:
    return {
        "booking_id": 1,
        "user_id": 100,
        "showtime_id": 11,
        "seat_numbers": ["A1"],
        "voucher_code": voucher_code,
        "email": "test@example.com",
        "original_amount": "100000",
    }


async def _run_workflow(
    env: WorkflowEnvironment,
    spies: dict[str, ActivitySpy],
    wf_input: dict,
    *,
    signal_success: bool | None = None,
    time_skip_seconds: int = 0,
) -> tuple[str, dict]:
    """Run BookingWorkflow to completion, return (result, final_query)."""
    from src.workflows.bookingWorkflow import BookingWorkflow

    client: Client = env.client
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[BookingWorkflow],
        activities=_activities_from_spies(spies),
    )

    async with worker:
        handle = await client.start_workflow(
            BookingWorkflow.run,
            wf_input,
            id=f"booking-test-{uuid.uuid4()}",
            task_queue=TASK_QUEUE,
        )

        if signal_success is not None:
            # wait until workflow reaches awaiting_payment, then signal
            for _ in range(60):
                state = (await handle.query("get_setup_result"))["state"]
                if state == "awaiting_payment":
                    break
                if state == "failed":
                    break
                await env.sleep(1)
            await handle.signal("payment_completed", signal_success)
        elif time_skip_seconds > 0:
            # reach awaiting_payment first, then skip past the timeout
            for _ in range(60):
                state = (await handle.query("get_setup_result"))["state"]
                if state in ("awaiting_payment", "failed"):
                    break
                await env.sleep(1)
            await env.sleep(time_skip_seconds)

        result = await handle.result()
        final_state = await handle.query("get_setup_result")
        return result, final_state


@pytest.fixture
async def env():
    env = await WorkflowEnvironment.start_time_skipping()
    try:
        yield env
    finally:
        await env.shutdown()


@pytest.mark.asyncio
async def test_happy_path_signal_success(env):
    spies = _build_spies({
        "create_payment_activity": {
            "returns": {"payment_id": 77, "payment_url": "http://x/77"},
        },
    })

    result, final = await _run_workflow(
        env, spies, _default_workflow_input(), signal_success=True,
    )

    assert result == "ACTIVE"
    assert final["state"] == "awaiting_payment"
    assert final["payment_url"] == "http://x/77"
    assert len(spies["confirm_seats_activity"].calls) == 1
    assert len(spies["send_notification_activity"].calls) == 1
    assert len(spies["finalize_booking_activity"].calls) == 1
    # no compensation
    assert len(spies["release_seats_activity"].calls) == 0
    assert len(spies["cancel_payment_activity"].calls) == 0


@pytest.mark.asyncio
async def test_signal_failure_triggers_compensation(env):
    spies = _build_spies({
        "create_payment_activity": {
            "returns": {"payment_id": 77, "payment_url": "http://x/77"},
        },
    })

    result, _ = await _run_workflow(
        env, spies, _default_workflow_input(), signal_success=False,
    )

    assert result == "CANCELLED"
    assert len(spies["release_seats_activity"].calls) == 1
    assert len(spies["cancel_payment_activity"].calls) == 1


@pytest.mark.asyncio
async def test_payment_timeout_triggers_compensation(env):
    spies = _build_spies({
        "create_payment_activity": {
            "returns": {"payment_id": 77, "payment_url": "http://x/77"},
        },
    })

    result, _ = await _run_workflow(
        env, spies, _default_workflow_input(), time_skip_seconds=310,
    )

    assert result == "CANCELLED"
    assert len(spies["release_seats_activity"].calls) == 1
    assert len(spies["cancel_payment_activity"].calls) == 1


@pytest.mark.asyncio
async def test_seat_conflict_no_compensation(env):
    spies = _build_spies({
        "reserve_seats_activity": {
            "raises": ApplicationError("seat conflict", non_retryable=True),
        },
    })

    result, final = await _run_workflow(env, spies, _default_workflow_input())

    assert result == "FAILED_SETUP"
    assert final["state"] == "failed"
    assert final["error_code"] == "seat_conflict"
    assert len(spies["release_seats_activity"].calls) == 0


@pytest.mark.asyncio
async def test_voucher_invalid_releases_seats(env):
    spies = _build_spies({
        "validate_voucher_activity": {
            "returns": {"valid": False, "discount_amount": "0", "message": "expired"},
        },
    })

    result, final = await _run_workflow(
        env, spies, _default_workflow_input(voucher_code="BAD"),
    )

    assert result == "FAILED_SETUP"
    assert final["error_code"] == "voucher_invalid"
    assert len(spies["release_seats_activity"].calls) == 1


@pytest.mark.asyncio
async def test_payment_downstream_error_releases_seats(env):
    spies = _build_spies({
        "create_payment_activity": {
            "raises": ApplicationError("payment service down", non_retryable=True),
        },
    })

    result, final = await _run_workflow(env, spies, _default_workflow_input())

    assert result == "FAILED_SETUP"
    assert final["error_code"] == "downstream_payment"
    assert len(spies["release_seats_activity"].calls) == 1
