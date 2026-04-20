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


@router.get("/{payment_id}/checkout", response_class=HTMLResponse)
def payment_checkout_page(payment_id: int, db: Session = Depends(get_db)) -> HTMLResponse:
    payment = paymentController.get_by_id(db, payment_id)
    amount = f"{float(payment.amount):,.0f} VND"
    html = f"""<!doctype html>
<html lang="vi">
  <head>
    <meta charset="utf-8">
    <title>VNPay — Payment #{payment_id}</title>
    <style>
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        background: linear-gradient(135deg, #0b2d6b 0%, #1e4fb3 100%);
        min-height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 24px;
      }}
      .card {{
        background: #fff;
        border-radius: 12px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        width: 100%;
        max-width: 440px;
        overflow: hidden;
      }}
      .header {{
        background: #0b2d6b;
        color: #fff;
        padding: 16px 24px;
        font-weight: 600;
        font-size: 18px;
        letter-spacing: 0.5px;
      }}
      .body {{ padding: 24px; text-align: center; }}
      .amount-box {{
        background: #f5f7fb;
        border: 1px solid #e1e6f0;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 20px;
      }}
      .amount-label {{ color: #6b7280; font-size: 13px; }}
      .amount-value {{ color: #d32027; font-size: 24px; font-weight: 700; margin-top: 4px; }}
      .qr-wrap {{
        display: flex;
        justify-content: center;
        margin: 12px 0 8px;
      }}
      .qr-wrap img {{
        max-width: 280px;
        width: 100%;
        height: auto;
        border: 1px solid #e1e6f0;
        border-radius: 8px;
        padding: 8px;
        background: #fff;
      }}
      .hint {{ color: #6b7280; font-size: 13px; margin: 8px 0 20px; }}
      .actions {{
        display: flex;
        gap: 12px;
        margin-top: 16px;
      }}
      button {{
        flex: 1;
        padding: 12px 16px;
        border: 0;
        border-radius: 8px;
        font-size: 15px;
        font-weight: 600;
        cursor: pointer;
        transition: opacity 0.15s;
      }}
      button:hover {{ opacity: 0.9; }}
      button:disabled {{ opacity: 0.5; cursor: not-allowed; }}
      .btn-pay {{ background: #0b9e4a; color: #fff; }}
      .btn-cancel {{ background: #e5e7eb; color: #111827; }}
      .status {{
        margin-top: 16px;
        padding: 10px;
        border-radius: 8px;
        font-size: 14px;
        display: none;
      }}
      .status.ok {{ background: #ecfdf5; color: #065f46; display: block; }}
      .status.err {{ background: #fef2f2; color: #991b1b; display: block; }}
      .meta {{ color: #9ca3af; font-size: 12px; margin-top: 16px; }}
    </style>
  </head>
  <body>
    <div class="card">
      <div class="header">VNPay — Cổng thanh toán</div>
      <div class="body">
        <div class="amount-box">
          <div class="amount-label">Số tiền cần thanh toán</div>
          <div class="amount-value">{amount}</div>
        </div>
        <div class="qr-wrap">
          <img src="/static/vnpay-qr.png" alt="VNPay QR Code">
        </div>
        <div class="hint">Quét mã QR bằng ứng dụng ngân hàng để thanh toán</div>
        <div class="actions">
          <button class="btn-pay" onclick="confirmPay(true)">Đã thanh toán</button>
          <button class="btn-cancel" onclick="confirmPay(false)">Huỷ</button>
        </div>
        <div id="status" class="status"></div>
        <div class="meta">Payment ID: {payment_id} · Booking ID: {payment.booking_id}</div>
      </div>
    </div>
    <script>
      async function confirmPay(success) {{
        const buttons = document.querySelectorAll('button');
        buttons.forEach(b => b.disabled = true);
        const status = document.getElementById('status');
        try {{
          const res = await fetch('/payments/{payment_id}/confirm', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{success: success}}),
          }});
          const data = await res.json();
          if (res.ok) {{
            status.className = 'status ok';
            status.textContent = success
              ? 'Thanh toán thành công! Trạng thái: ' + data.status
              : 'Đã huỷ thanh toán. Trạng thái: ' + data.status;
          }} else {{
            status.className = 'status err';
            status.textContent = data.detail || 'Có lỗi xảy ra';
            buttons.forEach(b => b.disabled = false);
          }}
        }} catch (e) {{
          status.className = 'status err';
          status.textContent = 'Lỗi kết nối: ' + e.message;
          buttons.forEach(b => b.disabled = false);
        }}
      }}
    </script>
  </body>
</html>"""
    return HTMLResponse(content=html, status_code=200)


@router.post("/{payment_id}/confirm", response_model=PaymentDetail)
def confirm_payment(
    payment_id: int,
    payload: ConfirmPaymentRequest,
    db: Session = Depends(get_db),
) -> PaymentDetail:
    return paymentController.confirm_payment(db, payment_id, payload)


@router.post("/{payment_id}/cancel", response_model=PaymentDetail)
def cancel(payment_id: int, db: Session = Depends(get_db)):
    return paymentController.cancel_payment(db, payment_id)


@router.get("/{payment_id}", response_model=PaymentDetail)
def get_payment(payment_id: int, db: Session = Depends(get_db)) -> PaymentDetail:
    return paymentController.get_by_id(db, payment_id)
