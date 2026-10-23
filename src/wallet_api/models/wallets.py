from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import UUID, DateTime, Enum, ForeignKey, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .enums import Currency
from .transactions import Transaction

if TYPE_CHECKING:
    from .users import User


class Wallet(Base):
    __tablename__ = "wallet"
    __table_args__ = (
        UniqueConstraint("user_id", "currency", name="unique_currency_wallet"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user: Mapped[User] = relationship(back_populates="wallets", lazy="selectin")

    currency: Mapped[Currency] = mapped_column(Enum(Currency), default=Currency.RUB)
    balance: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    transaction_out: Mapped[list[Transaction]] = relationship(
        "Transaction",
        foreign_keys="Transaction.src_wallet_id",
        back_populates="wallet_from",
        lazy="selectin",
    )
    transaction_in: Mapped[list[Transaction]] = relationship(
        "Transaction",
        foreign_keys="Transaction.dst_wallet_id",
        back_populates="wallet_to",
        lazy="selectin",
    )
