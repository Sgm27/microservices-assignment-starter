"""API-level tests for /bookings endpoints.

The controller calls fetch_showtime (stubbed via respx), then starts a
Temporal workflow and polls its setup-result query. Tests monkey-patch
`_wait_for_setup` to simulate workflow outcomes without running Temporal.
"""
from __future__ import annotations

import respx
from httpx import Response

MOVIE = "http://movie-service.test"


def _showtime_body(showtime_id: int = 1, base_price: float = 100000.0) -> dict:
    return {
        "id": showtime_id,
        "movie_id": 1,
        "room": "A",
        "starts_at": "2026-06-01T18:00:00",
        "base_price": base_price,
        "total_seats": 30,
    }


def _payload(**overrides) -> dict:
    base = {
        "user_id": 1,
        "showtime_id": 1,
        "seat_numbers": ["A1", "A2"],
        "email": "test@example.com",
    }
    base.update(overrides)
    return base


def _override_setup(monkeypatch, result: dict) -> None:
    """Replace the conftest default setup result for a single test."""
    from src.controllers import bookingController

    def _fake(workflow_id: str, timeout_s: int = 15) -> dict:
        return result

    monkeypatch.setattr(bookingController, "_wait_for_setup", _fake)


# ----------------------------- Happy path -----------------------------


@respx.mock
def test_create_booking_happy_path(client):
    respx.get(f"{MOVIE}/showtimes/1").mock(
        return_value=Response(200, json=_showtime_body())
    )

    r = client.post("/bookings", json=_payload())
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["booking_id"] >= 1
    assert body["payment_id"] == 777
    assert body["payment_url"].endswith("/payments/777/checkout")
    assert body["status"] == "AWAITING_PAYMENT"
    assert body["workflow_id"] == f"booking-{body['booking_id']}-wf"


# --------------------- Setup error mapping ----------------------------


@respx.mock
def test_create_booking_seat_conflict_returns_409(client, monkeypatch):
    respx.get(f"{MOVIE}/showtimes/1").mock(
        return_value=Response(200, json=_showtime_body())
    )
    _override_setup(monkeypatch, {
        "state": "failed",
        "payment_id": None,
        "payment_url": None,
        "error_code": "seat_conflict",
        "error_message": "Ghế A1 đã được đặt",
    })

    r = client.post("/bookings", json=_payload())
    assert r.status_code == 409
    assert "A1" in r.json()["detail"]


@respx.mock
def test_create_booking_voucher_invalid_returns_400(client, monkeypatch):
    respx.get(f"{MOVIE}/showtimes/1").mock(
        return_value=Response(200, json=_showtime_body())
    )
    _override_setup(monkeypatch, {
        "state": "failed",
        "payment_id": None,
        "payment_url": None,
        "error_code": "voucher_invalid",
        "error_message": "Mã giảm giá không hợp lệ",
    })

    r = client.post("/bookings", json=_payload(voucher_code="BAD"))
    assert r.status_code == 400


@respx.mock
def test_create_booking_voucher_downstream_returns_502(client, monkeypatch):
    respx.get(f"{MOVIE}/showtimes/1").mock(
        return_value=Response(200, json=_showtime_body())
    )
    _override_setup(monkeypatch, {
        "state": "failed",
        "payment_id": None,
        "payment_url": None,
        "error_code": "downstream_voucher",
        "error_message": "voucher-service 500",
    })

    r = client.post("/bookings", json=_payload(voucher_code="X"))
    assert r.status_code == 502


@respx.mock
def test_create_booking_payment_downstream_returns_502(client, monkeypatch):
    respx.get(f"{MOVIE}/showtimes/1").mock(
        return_value=Response(200, json=_showtime_body())
    )
    _override_setup(monkeypatch, {
        "state": "failed",
        "payment_id": None,
        "payment_url": None,
        "error_code": "downstream_payment",
        "error_message": "payment 503",
    })

    r = client.post("/bookings", json=_payload())
    assert r.status_code == 502


@respx.mock
def test_create_booking_setup_timeout_returns_502(client, monkeypatch):
    respx.get(f"{MOVIE}/showtimes/1").mock(
        return_value=Response(200, json=_showtime_body())
    )
    _override_setup(monkeypatch, {
        "state": "failed",
        "payment_id": None,
        "payment_url": None,
        "error_code": "setup_timeout",
        "error_message": "Workflow setup timeout",
    })

    r = client.post("/bookings", json=_payload())
    assert r.status_code == 502


@respx.mock
def test_create_booking_showtime_not_found_returns_404(client):
    respx.get(f"{MOVIE}/showtimes/99").mock(
        return_value=Response(404, json={"detail": "nope"})
    )

    r = client.post("/bookings", json=_payload(showtime_id=99))
    assert r.status_code == 404


# --------------------- Read endpoints / cancel ------------------------


@respx.mock
def test_get_booking_and_list_by_user(client):
    respx.get(f"{MOVIE}/showtimes/1").mock(
        return_value=Response(200, json=_showtime_body())
    )

    r = client.post("/bookings", json=_payload())
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
    respx.get(f"{MOVIE}/showtimes/1").mock(
        return_value=Response(200, json=_showtime_body())
    )
    release = respx.post(f"{MOVIE}/seats/release").mock(
        return_value=Response(200, json={"ok": True})
    )

    r = client.post("/bookings", json=_payload())
    booking_id = r.json()["booking_id"]

    c = client.post(f"/bookings/{booking_id}/cancel")
    assert c.status_code == 200
    assert c.json()["status"] == "CANCELLED"
    assert release.called
