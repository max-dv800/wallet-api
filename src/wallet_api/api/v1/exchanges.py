from fastapi import APIRouter, Header

from wallet_api.core.database import SessionDb
from wallet_api.dependency import CurrentUser
from wallet_api.schemas.transactions import TransactionExchange, TransactionResponse
from wallet_api.services.exchanges_services import transaction_exchange

router = APIRouter()


@router.post("/exchange", response_model=TransactionResponse)
async def create_exchange(
    data: TransactionExchange,
    user: CurrentUser,
    db: SessionDb,
    idemp_key: str = Header(..., alias="Idempotency-Key"),
):

    exchange = await transaction_exchange(data, user, db, idemp_key)

    return exchange
