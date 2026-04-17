# notificationService

Gửi email thông báo (mock trong test/dev) cho các sự kiện booking.

- **Port**: 5007
- **DB**: `notification_db.notifications`

## Endpoints

| Method | Path                  | Description                                  |
| ------ | --------------------- | -------------------------------------------- |
| GET    | /health               | health check                                 |
| POST   | /notifications/send   | tạo notification + gửi email (mock/real)     |
| GET    | /notifications        | list notifications (mới nhất trước)          |
| GET    | /notifications/{id}   | lấy 1 notification theo id                   |

## Run locally

```bash
pip install -r requirements.txt
PYTHONPATH=. SQLALCHEMY_URL=sqlite:///./dev.db uvicorn src.app:app --reload --port 5007
```

## Tests

```bash
pip install -r requirements.txt
pytest -q
```
