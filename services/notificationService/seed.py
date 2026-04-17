"""Seed notification_db.

Run inside the service container (requires mysql-db up):

    docker compose up -d mysql-db
    docker compose run --rm --no-deps \
        -v $(pwd)/services/notificationService/seed.py:/app/seed.py \
        notification-service python seed.py

Notifications are created dynamically by the booking workflow, so this seed
only ensures the schema exists and (optionally) inserts one historical
SENT record so admin/history pages have something to show.
Idempotent: matches by (user_id, subject).
"""
from __future__ import annotations

from datetime import datetime, timedelta

from src.config.database import Base, SessionLocal, engine
from src.models.notificationModel import Notification

SEED_NOTIFICATIONS = [
    {
        "user_id": 2,
        "email": "alice@example.com",
        "subject": "Booking #9001 confirmed",
        "body": "Hi Alice, your booking #9001 for Oppenheimer (Hall-1, seats A1, A2) is confirmed.",
        "status": "SENT",
        "sent_at": datetime.utcnow() - timedelta(days=1),
    },
]


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    created = 0
    try:
        for row in SEED_NOTIFICATIONS:
            exists = (
                session.query(Notification)
                .filter_by(user_id=row["user_id"], subject=row["subject"])
                .first()
            )
            if exists:
                continue
            session.add(Notification(**row))
            created += 1
        session.commit()
    finally:
        session.close()

    print(
        f"[notificationService] schema ensured; seeded {created} new notifications "
        f"(sample set: {len(SEED_NOTIFICATIONS)})"
    )


if __name__ == "__main__":
    seed()
