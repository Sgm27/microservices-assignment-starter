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
def client(monkeypatch):
    # Patch Temporal workflow start so no real server is needed.
    async def _fake_start(workflow_input: dict) -> str:
        return f"booking-{workflow_input['booking_id']}-wf"

    from src.config import temporalClient

    monkeypatch.setattr(temporalClient, "start_booking_workflow", _fake_start)

    from src.app import app
    from src.config.database import Base, engine

    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)
