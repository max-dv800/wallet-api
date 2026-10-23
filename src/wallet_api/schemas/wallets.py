import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from wallet_api.models.enums import Currency


class BaseWallet(BaseModel):
    currency: Currency = Field(default=Currency.RUB)
    balance: Decimal = Field(default=Decimal(0))


class WalletCreate(BaseWallet):
    user_id: uuid.UUID


class WalletResponse(BaseWallet):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
