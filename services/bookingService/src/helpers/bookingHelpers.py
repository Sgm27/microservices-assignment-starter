"""HTTP helpers to call downstream services.

Kept as plain functions (synchronous httpx) so they can be reused from both the
FastAPI controller and the Temporal activities. Tests stub these using respx.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

import httpx

from ..config.settings import get_settings


class DownstreamError(Exception):
    """Raised when a downstream service returns a non-2xx response."""


def _settings():
    return get_settings()


# --- Movie service ----------------------------------------------------------


def fetch_showtime(showtime_id: int) -> dict[str, Any]:
    s = _settings()
    r = httpx.get(
        f"{s.MOVIE_SERVICE_URL}/showtimes/{showtime_id}",
        timeout=s.HTTP_TIMEOUT_SECONDS,
    )
    if r.status_code != 200:
        raise DownstreamError(f"showtime {showtime_id} not found ({r.status_code})")
    return r.json()


def reserve_seats(showtime_id: int, seat_numbers: list[str], booking_id: int) -> None:
    s = _settings()
    r = httpx.post(
        f"{s.MOVIE_SERVICE_URL}/seats/reserve",
        json={"showtime_id": showtime_id, "seat_numbers": seat_numbers, "booking_id": booking_id},
        timeout=s.HTTP_TIMEOUT_SECONDS,
    )
    if r.status_code != 200:
        raise DownstreamError(f"reserve_seats failed: {r.status_code} {r.text}")


def confirm_seats(booking_id: int) -> None:
    s = _settings()
    r = httpx.post(
        f"{s.MOVIE_SERVICE_URL}/seats/confirm",
        json={"booking_id": booking_id},
        timeout=s.HTTP_TIMEOUT_SECONDS,
    )
    if r.status_code not in (200, 404):
        raise DownstreamError(f"confirm_seats failed: {r.status_code}")


def release_seats(booking_id: int) -> None:
    s = _settings()
    r = httpx.post(
        f"{s.MOVIE_SERVICE_URL}/seats/release",
        json={"booking_id": booking_id},
        timeout=s.HTTP_TIMEOUT_SECONDS,
    )
    if r.status_code != 200:
        raise DownstreamError(f"release_seats failed: {r.status_code}")


# --- Voucher service --------------------------------------------------------


def validate_voucher(code: str, base_amount: Decimal) -> dict[str, Any]:
    s = _settings()
    r = httpx.post(
        f"{s.VOUCHER_SERVICE_URL}/vouchers/validate",
        json={"code": code, "base_amount": float(base_amount)},
        timeout=s.HTTP_TIMEOUT_SECONDS,
    )
    if r.status_code != 200:
        raise DownstreamError(f"validate_voucher failed: {r.status_code}")
    return r.json()


def redeem_voucher(code: str) -> None:
    s = _settings()
    r = httpx.post(
        f"{s.VOUCHER_SERVICE_URL}/vouchers/redeem",
        json={"code": code},
        timeout=s.HTTP_TIMEOUT_SECONDS,
    )
    if r.status_code not in (200, 404):
        raise DownstreamError(f"redeem_voucher failed: {r.status_code}")


# --- Payment service --------------------------------------------------------


def create_payment(booking_id: int, amount: Decimal) -> dict[str, Any]:
    s = _settings()
    r = httpx.post(
        f"{s.PAYMENT_SERVICE_URL}/payments/create",
        json={"booking_id": booking_id, "amount": float(amount)},
        timeout=s.HTTP_TIMEOUT_SECONDS,
    )
    if r.status_code != 201:
        raise DownstreamError(f"create_payment failed: {r.status_code} {r.text}")
    return r.json()


def fetch_payment(payment_id: int) -> dict[str, Any]:
    s = _settings()
    r = httpx.get(
        f"{s.PAYMENT_SERVICE_URL}/payments/{payment_id}",
        timeout=s.HTTP_TIMEOUT_SECONDS,
    )
    if r.status_code != 200:
        raise DownstreamError(f"fetch_payment failed: {r.status_code}")
    return r.json()


def cancel_payment(payment_id: int) -> None:
    s = _settings()
    r = httpx.post(
        f"{s.PAYMENT_SERVICE_URL}/payments/{payment_id}/cancel",
        timeout=s.HTTP_TIMEOUT_SECONDS,
    )
    if r.status_code not in (200, 404):
        raise DownstreamError(f"cancel_payment failed: {r.status_code} {r.text}")


# --- Notification service ---------------------------------------------------


def send_notification(user_id: int, email: str, subject: str, body: str) -> None:
    s = _settings()
    r = httpx.post(
        f"{s.NOTIFICATION_SERVICE_URL}/notifications/send",
        json={"user_id": user_id, "email": email, "subject": subject, "body": body},
        timeout=s.HTTP_TIMEOUT_SECONDS,
    )
    if r.status_code not in (200, 201):
        raise DownstreamError(f"send_notification failed: {r.status_code}")
