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


# --- cancel_payment helper tests ---------------------------------------------


@respx.mock
def test_cancel_payment_helper_calls_endpoint():
    from src.helpers import bookingHelpers as svc

    route = respx.post(f"{PAYMENT}/payments/77/cancel").mock(
        return_value=Response(200, json={"id": 77, "status": "CANCELLED"})
    )

    svc.cancel_payment(77)
    assert route.called


@respx.mock
def test_cancel_payment_helper_tolerates_404():
    from src.helpers import bookingHelpers as svc

    respx.post(f"{PAYMENT}/payments/88/cancel").mock(
        return_value=Response(404, json={"detail": "not found"})
    )

    svc.cancel_payment(88)  # should NOT raise


# --- New activity tests ------------------------------------------------------


@respx.mock
def test_reserve_seats_activity_calls_movie_service():
    route = respx.post(f"{MOVIE}/seats/reserve").mock(
        return_value=Response(200, json={"ok": True})
    )
    _run(acts.reserve_seats_activity(booking_id=5, showtime_id=11, seat_numbers=["A1", "A2"]))
    assert route.called
    # Verify payload shape
    call = route.calls.last
    import json
    body = json.loads(call.request.content)
    assert body == {"showtime_id": 11, "seat_numbers": ["A1", "A2"], "booking_id": 5}


@respx.mock
def test_reserve_seats_activity_raises_on_conflict():
    import pytest as _pt
    from src.helpers.bookingHelpers import DownstreamError

    respx.post(f"{MOVIE}/seats/reserve").mock(
        return_value=Response(409, json={"detail": "seat taken"})
    )
    with _pt.raises(DownstreamError):
        _run(acts.reserve_seats_activity(booking_id=5, showtime_id=11, seat_numbers=["A1"]))


@respx.mock
def test_validate_voucher_activity_returns_normalised_dict():
    respx.post(f"{VOUCHER}/vouchers/validate").mock(
        return_value=Response(200, json={"valid": True, "discount_amount": 10000, "message": "ok"})
    )
    result = _run(acts.validate_voucher_activity("SUMMER", "100000"))
    assert result == {"valid": True, "discount_amount": "10000", "message": "ok"}


@respx.mock
def test_validate_voucher_activity_returns_invalid():
    respx.post(f"{VOUCHER}/vouchers/validate").mock(
        return_value=Response(200, json={"valid": False, "discount_amount": 0, "message": "expired"})
    )
    result = _run(acts.validate_voucher_activity("OLD", "50000"))
    assert result["valid"] is False
    assert result["message"] == "expired"


@respx.mock
def test_create_payment_activity_returns_id_and_url():
    respx.post(f"{PAYMENT}/payments/create").mock(
        return_value=Response(201, json={
            "payment_id": 77, "payment_url": "http://x/pay/77", "status": "PENDING",
        })
    )
    result = _run(acts.create_payment_activity(booking_id=5, amount="50000"))
    assert result == {"payment_id": 77, "payment_url": "http://x/pay/77"}


def test_persist_setup_activity_updates_booking_row(db_session):
    from decimal import Decimal

    from src.models.bookingModel import Booking

    b = Booking(
        user_id=1, showtime_id=11, seat_numbers=["A1"], email="x@y.z",
        original_amount=Decimal("100"), discount_amount=Decimal("0"),
        final_amount=Decimal("100"), status="PENDING",
    )
    db_session.add(b)
    db_session.commit()
    db_session.refresh(b)

    _run(acts.persist_setup_activity(b.id, 77, "10", "90"))

    db_session.expire_all()
    refreshed = db_session.query(Booking).filter(Booking.id == b.id).first()
    assert refreshed.payment_id == 77
    assert Decimal(str(refreshed.discount_amount)) == Decimal("10")
    assert Decimal(str(refreshed.final_amount)) == Decimal("90")
    assert refreshed.status == "AWAITING_PAYMENT"


@respx.mock
def test_cancel_payment_activity_calls_helper():
    route = respx.post(f"{PAYMENT}/payments/77/cancel").mock(
        return_value=Response(200, json={"id": 77, "status": "CANCELLED"})
    )
    _run(acts.cancel_payment_activity(77))
    assert route.called
