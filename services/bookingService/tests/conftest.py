import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ["SQLALCHEMY_URL"] = "sqlite:///:memory:"
os.environ["MOVIE_SERVICE_URL"] = "http://movie-service.test"
os.environ["VOUCHER_SERVICE_URL"] = "http://voucher-service.test"
os.environ["PAYMENT_SERVICE_URL"] = "http://payment-service.test"
os.environ["NOTIFICATION_SERVICE_URL"] = "http://notification-service.test"
os.environ["TEMPORAL_HOST"] = "temporal.test:7233"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture
def db_session():
    from src.config.database import Base, SessionLocal, engine

    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(monkeypatch):
    async def _fake_start(workflow_input: dict) -> str:
        return f"booking-{workflow_input['booking_id']}-wf"

    def _fake_wait_for_setup(workflow_id: str, timeout_s: int = 15) -> dict:
        # Default success — individual tests override via monkeypatch.
        return {
            "state": "awaiting_payment",
            "payment_id": 777,
            "payment_url": "http://payment-service.test/payments/777/checkout",
            "error_code": None,
            "error_message": None,
        }

    from src.config import temporalClient
    from src.controllers import bookingController

    monkeypatch.setattr(temporalClient, "start_booking_workflow", _fake_start)
    monkeypatch.setattr(bookingController, "_wait_for_setup", _fake_wait_for_setup)

    from src.app import app
    from src.config.database import Base, engine

    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)
