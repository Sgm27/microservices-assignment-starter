"""Tests for Temporal activity functions — runs them as plain async coroutines."""
from __future__ import annotations

import asyncio

import respx
from httpx import Response

from src.activities import bookingActivities as acts

MOVIE = "http://movie-service.test"
VOUCHER = "http://voucher-service.test"
PAYMENT = "http://payment-service.test"
NOTIFY = "http://notification-service.test"


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro) if False else asyncio.run(coro)


@respx.mock
def test_check_payment_status_returns_remote_status():
    respx.get(f"{PAYMENT}/payments/42").mock(
        return_value=Response(200, json={"id": 42, "status": "SUCCESS"})
    )
    assert _run(acts.check_payment_status(42)) == "SUCCESS"


@respx.mock
def test_confirm_and_release_seats_call_movie_service():
    confirm = respx.post(f"{MOVIE}/seats/confirm").mock(return_value=Response(200, json={"ok": True}))
    release = respx.post(f"{MOVIE}/seats/release").mock(return_value=Response(200, json={"ok": True}))

    _run(acts.confirm_seats_activity(7))
    _run(acts.release_seats_activity(7))

    assert confirm.called
    assert release.called


@respx.mock
def test_redeem_voucher_noop_when_none_and_calls_when_set():
    redeem = respx.post(f"{VOUCHER}/vouchers/redeem").mock(return_value=Response(200, json={"ok": True}))
    _run(acts.redeem_voucher_activity(None))
    assert not redeem.called
    _run(acts.redeem_voucher_activity("WELCOME10"))
    assert redeem.called


@respx.mock
def test_send_notification_posts_payload():
    send = respx.post(f"{NOTIFY}/notifications/send").mock(
        return_value=Response(201, json={"id": 1, "status": "SENT"})
    )
    _run(acts.send_notification_activity(1, "a@b.c", "sub", "body"))
    assert send.called
