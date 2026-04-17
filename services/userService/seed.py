"""Seed user_db with profile records that match the auth service sample users.

Run inside the service container (requires mysql-db up):

    docker compose up -d mysql-db
    docker compose run --rm --no-deps \
        -v $(pwd)/services/userService/seed.py:/app/seed.py \
        user-service python seed.py

Idempotent: will not duplicate rows if already seeded.
"""
from __future__ import annotations

from src.config.database import Base, SessionLocal, engine
from src.models.userModel import User

SEED_PROFILES = [
    {"email": "admin@example.com", "full_name": "Admin User", "phone": "+84900000001"},
    {"email": "alice@example.com", "full_name": "Alice Nguyen", "phone": "+84900000002"},
    {"email": "bob@example.com", "full_name": "Bob Tran", "phone": "+84900000003"},
]


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    created = 0
    try:
        for row in SEED_PROFILES:
            exists = session.query(User).filter_by(email=row["email"]).first()
            if exists:
                continue
            session.add(User(**row))
            created += 1
        session.commit()
    finally:
        session.close()

    print(f"[userService] seeded {created} new profiles (total sample set: {len(SEED_PROFILES)})")


if __name__ == "__main__":
    seed()
