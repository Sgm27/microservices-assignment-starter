# authService

Cấp JWT cho user, hỗ trợ register/login/verify.

- **Port**: 5001
- **DB**: `auth_db.auth_users`

## Endpoints

| Method | Path             | Description                                |
| ------ | ---------------- | ------------------------------------------ |
| GET    | /health          | health check                                |
| POST   | /auth/register   | tạo user mới + trả JWT                      |
| POST   | /auth/login      | xác thực + trả JWT                          |
| POST   | /auth/verify     | verify JWT, trả claims (dùng bởi gateway)   |

## Run locally

```bash
pip install -r requirements.txt
PYTHONPATH=. SQLALCHEMY_URL=sqlite:///./dev.db uvicorn src.app:app --reload --port 5001
```

## Tests

```bash
pip install -r requirements.txt
pytest -q
```
