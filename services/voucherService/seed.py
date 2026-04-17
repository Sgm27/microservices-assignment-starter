"""Seed voucher_db with sample discount codes.

Run inside the service container (requires mysql-db up):

    docker compose up -d mysql-db
    docker compose run --rm --no-deps \
        -v $(pwd)/services/voucherService/seed.py:/app/seed.py \
        voucher-service python seed.py

Idempotent: matches by code; skips creating duplicates.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from src.config.database import Base, SessionLocal, engine
from src.models.voucherModel import Voucher

NOW = datetime.utcnow().replace(microsecond=0)

SEED_VOUCHERS = [
    {
        "code": "WELCOME10",
        "discount_percent": 10,
        "max_uses": 100,
        "valid_from": NOW - timedelta(days=1),
        "valid_to": NOW + timedelta(days=30),
    },
    {
        "code": "STUDENT20",
        "discount_percent": 20,
        "max_uses": 50,
        "valid_from": NOW - timedelta(days=1),
        "valid_to": NOW + timedelta(days=60),
    },
    {
        "code": "VIP30",
        "discount_percent": 30,
        "max_uses": 20,
        "valid_from": NOW - timedelta(days=1),
        "valid_to": NOW + timedelta(days=90),
    },
    {
        "code": "EXPIRED",
        "discount_percent": 50,
        "max_uses": 100,
        "valid_from": NOW - timedelta(days=60),
        "valid_to": NOW - timedelta(days=1),  # already expired (for negative-case demos)
    },
]


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    created = 0
    try:
        for row in SEED_VOUCHERS:
            exists = session.query(Voucher).filter_by(code=row["code"]).first()
            if exists:
                continue
            session.add(Voucher(**row))
            created += 1
        session.commit()
    finally:
        session.close()

    print(f"[voucherService] seeded {created} new vouchers (total sample set: {len(SEED_VOUCHERS)})")
    for row in SEED_VOUCHERS:
        print(f"    {row['code']}: {row['discount_percent']}% until {row['valid_to']}")


if __name__ == "__main__":
    seed()
