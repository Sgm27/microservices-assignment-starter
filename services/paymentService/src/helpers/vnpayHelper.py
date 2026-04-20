"""Helpers for building VNPay payment URLs."""
from __future__ import annotations

from ..config.settings import Settings


def build_payment_url(settings: Settings, payment_id: int) -> str:
    base = settings.SELF_BASE_URL.rstrip("/")
    return f"{base}/payments/{payment_id}/checkout"
