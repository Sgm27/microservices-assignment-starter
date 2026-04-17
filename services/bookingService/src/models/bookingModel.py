from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from ..config.database import Base


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    showtime_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    seat_numbers: Mapped[list] = mapped_column(JSON, nullable=False)
    voucher_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)

    original_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    final_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    payment_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    workflow_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    status: Mapped[str] = mapped_column(String(24), nullable=False, default="PENDING")
    failure_reason: Mapped[str | None] = mapped_column(String(512), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
