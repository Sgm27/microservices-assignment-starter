"""Helpers for building mock / VNPay payment URLs.

Kept intentionally thin — real VNPay signing lives behind PAYMENT_MOCK=False
and is wired up in a later task.
"""
from __future__ import annotations

from ..config.settings import Settings


def build_mock_payment_url(settings: Settings, payment_id: int) -> str:
    base = settings.SELF_BASE_URL.rstrip("/")
    return f"{base}/payments/mock/{payment_id}/page"


def is_mock_mode(settings: Settings) -> bool:
    # PAYMENT_MOCK wins; absent VNPAY credentials also fall back to mock.
    if settings.PAYMENT_MOCK:
        return True
    return not settings.VNPAY_TMN_CODE


def build_vnpay_payment_url(settings: Settings, payment_id: int, amount) -> str:
    """Placeholder — real implementation would sign query params with HMAC SHA512."""
    base = settings.VNPAY_PAYMENT_URL
    return f"{base}?vnp_TxnRef={payment_id}&vnp_Amount={int(float(amount) * 100)}"
