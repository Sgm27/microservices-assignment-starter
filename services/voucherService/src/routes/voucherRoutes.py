from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..config.database import get_db
from ..controllers import voucherController
from ..validators.voucherSchemas import (
    VoucherCreateRequest,
    VoucherRedeemRequest,
    VoucherRedeemResponse,
    VoucherResponse,
    VoucherValidateRequest,
    VoucherValidateResponse,
)

router = APIRouter(prefix="/vouchers", tags=["vouchers"])


@router.get("", response_model=List[VoucherResponse])
def list_vouchers(db: Session = Depends(get_db)) -> List[VoucherResponse]:
    return voucherController.list_vouchers(db)


@router.post("", response_model=VoucherResponse, status_code=201)
def create_voucher(
    payload: VoucherCreateRequest, db: Session = Depends(get_db)
) -> VoucherResponse:
    return voucherController.create_voucher(db, payload)


@router.post("/validate", response_model=VoucherValidateResponse)
def validate_voucher(
    payload: VoucherValidateRequest, db: Session = Depends(get_db)
) -> VoucherValidateResponse:
    return voucherController.validate_voucher(db, payload)


@router.post("/redeem", response_model=VoucherRedeemResponse)
def redeem_voucher(
    payload: VoucherRedeemRequest, db: Session = Depends(get_db)
) -> VoucherRedeemResponse:
    return voucherController.redeem_voucher(db, payload)
