from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from wallet_api.models.users import User
from wallet_api.models.wallets import Wallet
from wallet_api.schemas.wallets import WalletCreate


async def create_new_wallet(
    user: User,
    data: WalletCreate,
    db: AsyncSession,
):
    wallet_exists = await db.scalar(
        select(Wallet).where(
            Wallet.currency == data.currency, Wallet.user_id == user.id
        )
    )
    if wallet_exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Wallet {data.currency} already exists!",
        )
    data.user_id = user.id
    wallet = Wallet(**data.model_dump())
    try:
        db.add(wallet)
        await db.commit()

    except IntegrityError as exc:
        await db.rollback()
        if "unique_currency_wallet" in str(exc.orig):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Wallet {data.currency} already exists!",
            ) from exc
        raise

    await db.refresh(wallet)
    return wallet


async def get_wallet(user: User, db: AsyncSession):
    wallets = await db.scalars(select(Wallet).where(Wallet.user_id == user.id))
    return wallets
