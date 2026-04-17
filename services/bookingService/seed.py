"""Seed booking_db.

Run inside the service container (requires mysql-db up):

    docker compose up -d mysql-db
    docker compose run --rm --no-deps \
        -v $(pwd)/services/bookingService/seed.py:/app/seed.py \
        booking-service python seed.py

Real bookings are created dynamically through the Temporal workflow, so this
seed only ensures the schema exists and (optionally) inserts one historical
CONFIRMED booking with id 9001 (aligned with the paymentService and
notificationService seeds) for demo/history pages.
Idempotent: keyed on booking id.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from src.config.database import Base, SessionLocal, engine
from src.models.bookingModel import Booking

SEED_BOOKINGS = [
    {
        "id": 9001,
        "user_id": 2,
        "showtime_id": 1,
        "seat_numbers": ["A1", "A2"],
        "voucher_code": None,
        "email": "alice@example.com",
        "original_amount": Decimal("240000"),
        "discount_amount": Decimal("0"),
        "final_amount": Decimal("240000"),
        "payment_id": 1,
        "workflow_id": "demo-workflow-9001",
        "status": "CONFIRMED",
        "created_at": datetime.utcnow() - timedelta(days=1),
        "updated_at": datetime.utcnow() - timedelta(days=1),
    },
]


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    created = 0
    try:
        for row in SEED_BOOKINGS:
            exists = session.query(Booking).filter_by(id=row["id"]).first()
            if exists:
                continue
            session.add(Booking(**row))
            created += 1
        session.commit()
    finally:
        session.close()

    print(
        f"[bookingService] schema ensured; seeded {created} new historical bookings "
        f"(sample set: {len(SEED_BOOKINGS)})"
    )


if __name__ == "__main__":
    seed()
