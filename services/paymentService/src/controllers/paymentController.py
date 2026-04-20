import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..config import temporalClient as _temporal_client
from ..config.settings import get_settings

log = logging.getLogger(__name__)
from ..helpers.vnpayHelper import build_payment_url
from ..models.paymentModel import Payment
from ..validators.paymentSchemas import (
    ConfirmPaymentRequest,
    CreatePaymentRequest,
    CreatePaymentResponse,
    PaymentDetail,
)

FINAL_STATUSES = {"SUCCESS", "FAILED", "CANCELLED"}


def _to_detail(payment: Payment) -> PaymentDetail:
    return PaymentDetail.model_validate(payment)


def create_payment(db: Session, payload: CreatePaymentRequest) -> CreatePaymentResponse:
    existing = (
        db.query(Payment).filter(Payment.booking_id == payload.booking_id).first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Đơn thanh toán đã tồn tại cho đơn đặt vé này",
        )

    settings = get_settings()

    payment = Payment(
        booking_id=payload.booking_id,
        amount=payload.amount,
        status="PENDING",
        provider="vnpay",
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    url = build_payment_url(settings, payment.id)

    payment.payment_url = url
    db.add(payment)
    db.commit()
    db.refresh(payment)

    return CreatePaymentResponse(
        payment_id=payment.id,
        payment_url=url,
        status=payment.status,
    )


def get_by_id(db: Session, payment_id: int) -> PaymentDetail:
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy đơn thanh toán",
        )
    return _to_detail(payment)


def get_by_booking_id(db: Session, booking_id: int) -> PaymentDetail:
    payment = db.query(Payment).filter(Payment.booking_id == booking_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy đơn thanh toán",
        )
    return _to_detail(payment)


def confirm_payment(
    db: Session, payment_id: int, payload: ConfirmPaymentRequest
) -> PaymentDetail:
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy đơn thanh toán",
        )
    if payment.status in FINAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Đơn thanh toán đã được hoàn tất",
        )

    payment.status = "SUCCESS" if payload.success else "FAILED"
    payment.provider_txn_id = f"vnpay-{payment.id}"
    db.add(payment)
    db.commit()
    db.refresh(payment)

    try:
        _temporal_client.signal_payment_completed(payment.booking_id, payload.success)
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "Failed to signal BookingWorkflow for booking %s: %s",
            payment.booking_id,
            exc,
        )

    return _to_detail(payment)


def cancel_payment(db: Session, payment_id: int) -> PaymentDetail:
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy đơn thanh toán",
        )
    if payment.status == "SUCCESS":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Không thể huỷ payment đã hoàn tất",
        )
    if payment.status != "CANCELLED":
        payment.status = "CANCELLED"
        db.add(payment)
        db.commit()
        db.refresh(payment)
    return _to_detail(payment)
