import os
import sys
from pathlib import Path

# Ensure project root is on sys.path so `import src.*` works.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Force test settings BEFORE importing any src module.
os.environ["SQLALCHEMY_URL"] = "sqlite:///:memory:"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture
def client():
    # Lazy imports so env vars above take effect.
    from src.app import _seed_database
    from src.app import app
    from src.config.database import Base, engine

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    _seed_database()
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)
