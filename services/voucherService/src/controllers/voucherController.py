from datetime import datetime
from typing import List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..models.voucherModel import Voucher
from ..validators.voucherSchemas import (
    VoucherCreateRequest,
    VoucherRedeemRequest,
    VoucherRedeemResponse,
    VoucherResponse,
    VoucherValidateRequest,
    VoucherValidateResponse,
)


def list_vouchers(db: Session) -> List[VoucherResponse]:
    rows = db.query(Voucher).order_by(Voucher.id).all()
    return [VoucherResponse.model_validate(v) for v in rows]


def create_voucher(db: Session, payload: VoucherCreateRequest) -> VoucherResponse:
    existing = db.query(Voucher).filter(Voucher.code == payload.code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="voucher code already exists",
        )
    voucher = Voucher(
        code=payload.code,
        discount_percent=payload.discount_percent,
        max_uses=payload.max_uses,
        used_count=0,
        valid_from=payload.valid_from,
        valid_to=payload.valid_to,
    )
    db.add(voucher)
    db.commit()
    db.refresh(voucher)
    return VoucherResponse.model_validate(voucher)


def _compute_amounts(base_amount: float, discount_percent: int) -> tuple[float, float]:
    discount_amount = round(base_amount * discount_percent / 100.0, 2)
    final_amount = round(base_amount - discount_amount, 2)
    return discount_amount, final_amount


def validate_voucher(db: Session, payload: VoucherValidateRequest) -> VoucherValidateResponse:
    voucher = db.query(Voucher).filter(Voucher.code == payload.code).first()
    if not voucher:
        return VoucherValidateResponse(
            valid=False,
            discount_amount=0.0,
            final_amount=round(payload.base_amount, 2),
            message="voucher not found",
        )

    now = datetime.utcnow()
    if now < voucher.valid_from or now > voucher.valid_to:
        return VoucherValidateResponse(
            valid=False,
            discount_amount=0.0,
            final_amount=round(payload.base_amount, 2),
            message="voucher expired or not yet valid",
        )

    if voucher.used_count >= voucher.max_uses:
        return VoucherValidateResponse(
            valid=False,
            discount_amount=0.0,
            final_amount=round(payload.base_amount, 2),
            message="voucher has reached max uses",
        )

    discount_amount, final_amount = _compute_amounts(
        payload.base_amount, voucher.discount_percent
    )
    return VoucherValidateResponse(
        valid=True,
        discount_amount=discount_amount,
        final_amount=final_amount,
        message="ok",
    )


def redeem_voucher(db: Session, payload: VoucherRedeemRequest) -> VoucherRedeemResponse:
    voucher = db.query(Voucher).filter(Voucher.code == payload.code).first()
    if not voucher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="voucher not found",
        )
    if voucher.used_count >= voucher.max_uses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="voucher has reached max uses",
        )
    voucher.used_count = voucher.used_count + 1
    db.add(voucher)
    db.commit()
    db.refresh(voucher)
    return VoucherRedeemResponse(
        code=voucher.code,
        used_count=voucher.used_count,
        max_uses=voucher.max_uses,
    )
