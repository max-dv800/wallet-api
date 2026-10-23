from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import UUID, DateTime, Enum, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .enums import Currency

if TYPE_CHECKING:
    from .transactions import Transaction


class ExchangeRate(Base):
    __tablename__ = "exchange"
    __table_args__ = (
        UniqueConstraint("from_currency", "to_currency", name="unique_exchange"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    from_currency: Mapped[Currency] = mapped_column(Enum(Currency), nullable=False)
    to_currency: Mapped[Currency] = mapped_column(Enum(Currency), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
    )

    transactions: Mapped[list[Transaction]] = relationship(
        "Transaction", back_populates="exchange_rate", lazy="selectin"
    )
