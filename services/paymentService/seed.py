"""Seed payment_db.

Run inside the service container (requires mysql-db up):

    docker compose up -d mysql-db
    docker compose run --rm --no-deps \
        -v $(pwd)/services/paymentService/seed.py:/app/seed.py \
        payment-service python seed.py

Payments are created dynamically by the booking workflow, so this seed only
ensures the schema exists and (optionally) inserts a historical COMPLETED
payment for demo/reporting pages.
Idempotent: matches by booking_id.
"""
from __future__ import annotations

from decimal import Decimal

from src.config.database import Base, SessionLocal, engine
from src.models.paymentModel import Payment

SEED_PAYMENTS = [
    {
        "booking_id": 9001,
        "amount": Decimal("270000"),
        "status": "COMPLETED",
        "provider": "vnpay",
        "payment_url": "https://vnpay.local/return?txn=DEMO9001",
        "provider_txn_id": "DEMO9001",
    },
]


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    created = 0
    try:
        for row in SEED_PAYMENTS:
            exists = session.query(Payment).filter_by(booking_id=row["booking_id"]).first()
            if exists:
                continue
            session.add(Payment(**row))
            created += 1
        session.commit()
    finally:
        session.close()

    print(
        f"[paymentService] schema ensured; seeded {created} new historical payments "
        f"(sample set: {len(SEED_PAYMENTS)})"
    )


if __name__ == "__main__":
    seed()
