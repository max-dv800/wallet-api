import uuid
from datetime import timedelta
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from wallet_api.models.enums import Currency, TypeTransaction

MSK = timedelta(hours=3)


class BaseTransaction(BaseModel):
    amount: Decimal = Field(gt=0, decimal_places=4, max_digits=12)


class TransactionExchange(BaseTransaction):
    from_currency: Currency
    to_currency: Currency


class TransactionTransfer(BaseTransaction):
    src_wallet_id: uuid.UUID | None = Field(default=None)
    dst_wallet_id: uuid.UUID | None = Field(default=None)


class DepositTransaction(BaseTransaction):
    currency: Currency = Field(default=Currency.RUB)
    dst_wallet_id: uuid.UUID | None = Field(default=None)


class TransactionResponse(BaseTransaction):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: TypeTransaction
    exchange_id: uuid.UUID | None
    dst_amount: Decimal | None
    rate: Decimal | None
    src_wallet_id: uuid.UUID | None = Field(default=None)
    currency: Currency = Field(default=Currency.RUB)
    dst_wallet_id: uuid.UUID | None = Field(default=None)
