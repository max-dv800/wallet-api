from fastapi import APIRouter, Header

from wallet_api.core.database import SessionDb
from wallet_api.dependency import CurrentUser
from wallet_api.schemas.transactions import (
    DepositTransaction,
    TransactionResponse,
    TransactionTransfer,
)
from wallet_api.services.transactions_services import top_up_wallet, transfer_wallet

router = APIRouter()


@router.post("/deposit", response_model=TransactionResponse)
async def deposit_wallet(
    user: CurrentUser,
    data: DepositTransaction,
    db: SessionDb,
    idemp_key: str = Header(..., alias="Idempotency-Key"),
):
    new_transaction = await top_up_wallet(user, data, db, idemp_key)

    return new_transaction


@router.post("/transfer", response_model=TransactionResponse)
async def transfer_for_wallet(
    user: CurrentUser,
    data: TransactionTransfer,
    db: SessionDb,
    idemp_key: str = Header(..., alias="Idempotency-Key"),
):
    transfer = await transfer_wallet(user, data, db, idemp_key)

    return transfer
