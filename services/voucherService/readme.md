# voucherService

Quản lý mã giảm giá: list / create / validate / redeem.

- **Port**: 5004
- **DB**: `voucher_db.vouchers`

## Endpoints

| Method | Path                | Description                                  |
| ------ | ------------------- | -------------------------------------------- |
| GET    | /health             | health check                                 |
| GET    | /vouchers           | list tất cả voucher                          |
| POST   | /vouchers           | tạo voucher mới (409 nếu trùng code)         |
| POST   | /vouchers/validate  | kiểm tra voucher + trả discount_amount       |
| POST   | /vouchers/redeem    | tăng used_count khi booking thành công       |

## Run locally

```bash
pip install -r requirements.txt
PYTHONPATH=. SQLALCHEMY_URL=sqlite:///./dev.db uvicorn src.app:app --reload --port 5004
```

## Tests

```bash
pip install -r requirements.txt
pytest -q
```
