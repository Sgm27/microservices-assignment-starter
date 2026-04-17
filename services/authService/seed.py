"""Seed auth_db with sample users.

Run inside the service container (requires mysql-db up):

    docker compose up -d mysql-db
    docker compose run --rm --no-deps \
        -v $(pwd)/services/authService/seed.py:/app/seed.py \
        auth-service python seed.py

Idempotent: will not duplicate rows if already seeded.
"""
from __future__ import annotations

from passlib.context import CryptContext

from src.config.database import Base, SessionLocal, engine
from src.models.authUserModel import AuthUser

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SEED_USERS = [
    {"email": "admin@example.com", "password": "admin123", "role": "admin"},
    {"email": "alice@example.com", "password": "password123", "role": "customer"},
    {"email": "bob@example.com", "password": "password123", "role": "customer"},
]


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    created = 0
    try:
        for row in SEED_USERS:
            exists = session.query(AuthUser).filter_by(email=row["email"]).first()
            if exists:
                continue
            session.add(
                AuthUser(
                    email=row["email"],
                    password_hash=pwd_context.hash(row["password"]),
                    role=row["role"],
                )
            )
            created += 1
        session.commit()
    finally:
        session.close()

    print(f"[authService] seeded {created} new users (total sample set: {len(SEED_USERS)})")
    print("  login credentials:")
    for row in SEED_USERS:
        print(f"    {row['email']} / {row['password']} ({row['role']})")


if __name__ == "__main__":
    seed()
