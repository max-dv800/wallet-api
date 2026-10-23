from fastapi import APIRouter

from wallet_api.core.database import SessionDb
from wallet_api.dependency import CurrentUser
from wallet_api.schemas.wallets import WalletCreate, WalletResponse
from wallet_api.services.wallets_services import create_new_wallet, get_wallet

router = APIRouter()


@router.post("/", response_model=WalletResponse)
async def wallet_create(
    user: CurrentUser,
    data: WalletCreate,
    db: SessionDb,
):

    wallet = await create_new_wallet(user, data, db)

    return wallet


@router.get("/", response_model=list[WalletResponse])
async def get_all_wallet(
    user: CurrentUser,
    db: SessionDb,
):
    all_wallet = await get_wallet(user, db)

    return all_wallet
