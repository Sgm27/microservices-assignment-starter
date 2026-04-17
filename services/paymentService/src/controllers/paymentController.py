from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..config.settings import get_settings
from ..helpers.vnpayHelper import (
    build_mock_payment_url,
    build_vnpay_payment_url,
    is_mock_mode,
)
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
            detail="payment already exists for this booking",
        )

    settings = get_settings()
    mock = is_mock_mode(settings)

    payment = Payment(
        booking_id=payload.booking_id,
        amount=payload.amount,
        status="PENDING",
        provider="mock" if mock else "vnpay",
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    if mock:
        url = build_mock_payment_url(settings, payment.id)
    else:
        url = build_vnpay_payment_url(settings, payment.id, payload.amount)

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
            detail="payment not found",
        )
    return _to_detail(payment)


def get_by_booking_id(db: Session, booking_id: int) -> PaymentDetail:
    payment = db.query(Payment).filter(Payment.booking_id == booking_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="payment not found",
        )
    return _to_detail(payment)


def mock_confirm(
    db: Session, payment_id: int, payload: ConfirmPaymentRequest
) -> PaymentDetail:
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="payment not found",
        )
    if payment.status in FINAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="payment is already finalized",
        )

    payment.status = "SUCCESS" if payload.success else "FAILED"
    payment.provider_txn_id = f"mock-{payment.id}"
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return _to_detail(payment)
