import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ["JWT_SECRET"] = "test-secret"
os.environ["AUTH_SERVICE_URL"] = "http://auth.test"
os.environ["USER_SERVICE_URL"] = "http://user.test"
os.environ["MOVIE_SERVICE_URL"] = "http://movie.test"
os.environ["VOUCHER_SERVICE_URL"] = "http://voucher.test"
os.environ["BOOKING_SERVICE_URL"] = "http://booking.test"
os.environ["PAYMENT_SERVICE_URL"] = "http://payment.test"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from jose import jwt  # noqa: E402


@pytest.fixture
def client():
    from src.app import app
    return TestClient(app)


@pytest.fixture
def valid_token():
    return jwt.encode(
        {"sub": "42", "user_id": 42, "email": "alice@example.com", "role": "customer"},
        "test-secret",
        algorithm="HS256",
    )
