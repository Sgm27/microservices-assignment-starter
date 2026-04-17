"""API-level tests for POST /bookings.

Downstream HTTP calls (movie/voucher/payment) are stubbed with respx.
Temporal workflow start is patched in conftest.
"""
from __future__ import annotations

import respx
from httpx import Response

MOVIE = "http://movie-service.test"
VOUCHER = "http://voucher-service.test"
PAYMENT = "http://payment-service.test"
NOTIFY = "http://notification-service.test"


def _showtime_body(showtime_id: int = 1, base_price: float = 100000.0) -> dict:
    return {
        "id": showtime_id,
        "movie_id": 1,
        "room": "A",
        "starts_at": "2026-06-01T18:00:00",
        "base_price": base_price,
        "total_seats": 30,
    }


def _create_booking_payload(**overrides) -> dict:
    base = {
        "user_id": 1,
        "showtime_id": 1,
        "seat_numbers": ["A1", "A2"],
        "email": "test@example.com",
    }
    base.update(overrides)
    return base


@respx.mock
def test_create_booking_happy_path_no_voucher(client):
    respx.get(f"{MOVIE}/showtimes/1").mock(return_value=Response(200, json=_showtime_body()))
    respx.post(f"{MOVIE}/seats/reserve").mock(return_value=Response(200, json={"ok": True}))
    payment_route = respx.post(f"{PAYMENT}/payments/create").mock(
        return_value=Response(
            201,
            json={"payment_id": 42, "payment_url": "http://pay/mock/42", "status": "PENDING"},
        )
    )

    r = client.post("/bookings", json=_create_booking_payload())
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["booking_id"] >= 1
    assert body["payment_id"] == 42
    assert body["payment_url"] == "http://pay/mock/42"
    assert body["status"] == "AWAITING_PAYMENT"
    assert body["workflow_id"] == f"booking-{body['booking_id']}-wf"
    assert body["final_amount"] == "200000.00"  # 2 seats * 100000

    # ensure payment got the right amount
    assert payment_route.called
    sent_json = payment_route.calls.last.request.read().decode()
    assert '"amount": 200000.0' in sent_json


@respx.mock
def test_create_booking_with_valid_voucher(client):
    respx.get(f"{MOVIE}/showtimes/1").mock(return_value=Response(200, json=_showtime_body()))
    respx.post(f"{MOVIE}/seats/reserve").mock(return_value=Response(200, json={"ok": True}))
    respx.post(f"{VOUCHER}/vouchers/validate").mock(
        return_value=Response(
            200,
            json={"valid": True, "discount_amount": 20000.0, "final_amount": 180000.0},
        )
    )
    respx.post(f"{PAYMENT}/payments/create").mock(
        return_value=Response(
            201,
            json={"payment_id": 7, "payment_url": "http://pay/mock/7", "status": "PENDING"},
        )
    )

    r = client.post(
        "/bookings", json=_create_booking_payload(voucher_code="WELCOME10")
    )
    assert r.status_code == 201, r.text
    assert r.json()["final_amount"] == "180000.00"


@respx.mock
def test_create_booking_invalid_voucher_releases_seats(client):
    respx.get(f"{MOVIE}/showtimes/1").mock(return_value=Response(200, json=_showtime_body()))
    respx.post(f"{MOVIE}/seats/reserve").mock(return_value=Response(200, json={"ok": True}))
    respx.post(f"{VOUCHER}/vouchers/validate").mock(
        return_value=Response(200, json={"valid": False, "discount_amount": 0, "final_amount": 0, "message": "expired"})
    )
    release = respx.post(f"{MOVIE}/seats/release").mock(return_value=Response(200, json={"ok": True}))

    r = client.post("/bookings", json=_create_booking_payload(voucher_code="BAD"))
    assert r.status_code == 400
    assert release.called


@respx.mock
def test_create_booking_seat_conflict(client):
    respx.get(f"{MOVIE}/showtimes/1").mock(return_value=Response(200, json=_showtime_body()))
    respx.post(f"{MOVIE}/seats/reserve").mock(return_value=Response(409, json={"detail": "taken"}))

    r = client.post("/bookings", json=_create_booking_payload())
    assert r.status_code == 409


@respx.mock
def test_create_booking_showtime_not_found(client):
    respx.get(f"{MOVIE}/showtimes/1").mock(return_value=Response(404, json={"detail": "nope"}))

    r = client.post("/bookings", json=_create_booking_payload())
    assert r.status_code == 404


@respx.mock
def test_get_booking_and_list_by_user(client):
    respx.get(f"{MOVIE}/showtimes/1").mock(return_value=Response(200, json=_showtime_body()))
    respx.post(f"{MOVIE}/seats/reserve").mock(return_value=Response(200, json={"ok": True}))
    respx.post(f"{PAYMENT}/payments/create").mock(
        return_value=Response(
            201,
            json={"payment_id": 99, "payment_url": "http://pay/mock/99", "status": "PENDING"},
        )
    )

    r = client.post("/bookings", json=_create_booking_payload())
    booking_id = r.json()["booking_id"]

    g = client.get(f"/bookings/{booking_id}")
    assert g.status_code == 200
    assert g.json()["id"] == booking_id

    listing = client.get("/bookings/user/1")
    assert listing.status_code == 200
    assert any(b["id"] == booking_id for b in listing.json())


def test_get_booking_not_found(client):
    r = client.get("/bookings/9999")
    assert r.status_code == 404


@respx.mock
def test_cancel_booking_releases_seats(client):
    respx.get(f"{MOVIE}/showtimes/1").mock(return_value=Response(200, json=_showtime_body()))
    respx.post(f"{MOVIE}/seats/reserve").mock(return_value=Response(200, json={"ok": True}))
    respx.post(f"{PAYMENT}/payments/create").mock(
        return_value=Response(
            201,
            json={"payment_id": 1, "payment_url": "http://pay/mock/1", "status": "PENDING"},
        )
    )
    release = respx.post(f"{MOVIE}/seats/release").mock(return_value=Response(200, json={"ok": True}))

    r = client.post("/bookings", json=_create_booking_payload())
    booking_id = r.json()["booking_id"]

    c = client.post(f"/bookings/{booking_id}/cancel")
    assert c.status_code == 200
    assert c.json()["status"] == "CANCELLED"
    assert release.called
