from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import UUID, DateTime, Enum, ForeignKey, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .enums import Currency, Status, TypeTransaction
from .exchanges import ExchangeRate

if TYPE_CHECKING:
    from .wallets import Wallet


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)

    idempotency_key: Mapped[uuid.UUID | None] = mapped_column(
        UUID, index=True, nullable=False, unique=True
    )

    src_wallet_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("wallet.id", ondelete="RESTRICT"), nullable=True
    )
    dst_wallet_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("wallet.id", ondelete="RESTRICT"), nullable=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    currency: Mapped[Currency] = mapped_column(Enum(Currency), nullable=False)
    # Заполняем в случае обменных операций
    dst_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    rate: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    exchange_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID, ForeignKey("exchange.id", ondelete="SET NULL"), nullable=True, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[Status] = mapped_column(
        Enum(Status), default=Status.PENDING, nullable=False
    )
    type: Mapped[TypeTransaction] = mapped_column(
        Enum(TypeTransaction), default=TypeTransaction.TRANSFER, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
    )
    wallet_from: Mapped[Wallet | None] = relationship(
        foreign_keys=[src_wallet_id], back_populates="transaction_out", lazy="selectin"
    )
    wallet_to: Mapped[Wallet | None] = relationship(
        foreign_keys=[dst_wallet_id], back_populates="transaction_in", lazy="selectin"
    )
    exchange_rate: Mapped[ExchangeRate | None] = relationship(
        back_populates="transactions", lazy="selectin"
    )
