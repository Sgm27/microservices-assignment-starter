# paymentService

Tạo VNPay payment URL, nhận kết quả thanh toán.

- **Port**: 5006
- **DB**: `payment_db.payments`

## Endpoints

| Method | Path                                   | Description                              |
| ------ | -------------------------------------- | ---------------------------------------- |
| GET    | /health                                | health check                             |
| POST   | /payments/create                       | tạo payment + trả payment_url            |
| GET    | /payments/{id}                         | xem payment theo id                      |
| GET    | /payments/by-booking/{booking_id}      | xem payment theo booking_id              |
| POST   | /payments/{id}/confirm                 | đánh dấu SUCCESS / FAILED                |
| GET    | /payments/{id}/checkout                | HTML trang cổng thanh toán VNPay         |
| GET    | /payments/vnpay-return                 | VNPay IPN / return                       |

## Run locally

```bash
pip install -r requirements.txt
PYTHONPATH=. SQLALCHEMY_URL=sqlite:///./dev.db uvicorn src.app:app --reload --port 5006
```

## Tests

```bash
pip install -r requirements.txt
pytest -q
```
