from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from ..config.database import get_db
from ..config.settings import get_settings
from ..controllers import paymentController
from ..validators.paymentSchemas import (
    ConfirmPaymentRequest,
    CreatePaymentRequest,
    CreatePaymentResponse,
    PaymentDetail,
)

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/create", response_model=CreatePaymentResponse, status_code=201)
def create_payment(
    payload: CreatePaymentRequest, db: Session = Depends(get_db)
) -> CreatePaymentResponse:
    return paymentController.create_payment(db, payload)


@router.get("/vnpay-return")
def vnpay_return(request: dict | None = None) -> JSONResponse:
    # Skeleton: in a real implementation we'd verify vnp_SecureHash, mark
    # the payment SUCCESS/FAILED, then 303-redirect to the frontend.
    settings = get_settings()
    redirect_url = f"{settings.VNPAY_FRONTEND_RETURN_URL}?status=success"
    return JSONResponse(
        status_code=200,
        content={"redirect_url": redirect_url, "status": "success"},
    )


@router.get("/by-booking/{booking_id}", response_model=PaymentDetail)
def get_by_booking(booking_id: int, db: Session = Depends(get_db)) -> PaymentDetail:
    return paymentController.get_by_booking_id(db, booking_id)


@router.get("/mock/{payment_id}/page", response_class=HTMLResponse)
def mock_pay_page(payment_id: int) -> HTMLResponse:
    html = f"""<!doctype html>
<html>
  <head><meta charset="utf-8"><title>Mock Payment {payment_id}</title></head>
  <body>
    <h1>Mock Payment</h1>
    <p>Payment ID: {payment_id}</p>
    <form id="pay-form" method="POST" action="/payments/mock/{payment_id}/confirm">
      <button type="submit" name="success" value="true"
              onclick="return postJson(true)">Pay</button>
      <button type="submit" name="success" value="false"
              onclick="return postJson(false)">Cancel</button>
    </form>
    <script>
      async function postJson(success) {{
        await fetch('/payments/mock/{payment_id}/confirm', {{
          method: 'POST',
          headers: {{'Content-Type': 'application/json'}},
          body: JSON.stringify({{success: success}}),
        }});
        return false;
      }}
    </script>
  </body>
</html>"""
    return HTMLResponse(content=html, status_code=200)


@router.post("/mock/{payment_id}/confirm", response_model=PaymentDetail)
def mock_confirm(
    payment_id: int,
    payload: ConfirmPaymentRequest,
    db: Session = Depends(get_db),
) -> PaymentDetail:
    return paymentController.mock_confirm(db, payment_id, payload)


@router.get("/{payment_id}", response_model=PaymentDetail)
def get_payment(payment_id: int, db: Session = Depends(get_db)) -> PaymentDetail:
    return paymentController.get_by_id(db, payment_id)
