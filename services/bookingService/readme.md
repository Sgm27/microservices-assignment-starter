# bookingService

Saga orchestrator cho luồng đặt vé. Dùng Temporal workflow để chờ xác nhận thanh toán và thực hiện compensation.

- **Port**: 5005
- **DB**: `booking_db.bookings`
- **Temporal**: namespace `default`, task queue `booking-task-queue`

## Single flow

1. `POST /bookings` — synchronous steps: reserve seats → validate voucher → create payment → persist `AWAITING_PAYMENT`
2. Start `BookingWorkflow` (Temporal) with booking_id + payment_id → returns `workflow_id` + `payment_url`
3. Workflow polls `paymentService` until SUCCESS / FAILED / timeout (5m)
4. On SUCCESS: confirm seats + redeem voucher + send notification → status `ACTIVE`
5. On FAILURE/timeout: release seats → status `CANCELLED`

## Endpoints

| Method | Path                        |
| ------ | --------------------------- |
| GET    | `/health`                   |
| POST   | `/bookings`                 |
| GET    | `/bookings/{id}`            |
| GET    | `/bookings/user/{user_id}`  |
| POST   | `/bookings/{id}/cancel`     |

## Run locally

```bash
pip install -r requirements.txt
# API
PYTHONPATH=. SQLALCHEMY_URL=sqlite:///./dev.db uvicorn src.app:app --reload --port 5005
# Worker (separate terminal, needs Temporal server)
PYTHONPATH=. python -m src.worker
```

## Tests

```bash
pytest -q
```
