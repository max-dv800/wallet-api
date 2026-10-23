from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from wallet_api.core.config import settings
from wallet_api.models.enums import Status, TypeTransaction
from wallet_api.models.transactions import Transaction
from wallet_api.models.users import User
from wallet_api.models.wallets import Wallet
from wallet_api.schemas.transactions import (
    MSK,
    DepositTransaction,
    TransactionResponse,
    TransactionTransfer,
)
from wallet_api.utils.cache import cache


async def top_up_wallet(
    user: User, data: DepositTransaction, db: AsyncSession, idempotency_key: str
):

    redis_idempt_key = f"idempotency_key:{idempotency_key}"

    create_redis_key = await cache.set(
        redis_idempt_key, "pending", ex=settings.PENDING_TTL, nx=True
    )

    if not create_redis_key:
        cache_result = await cache.get(redis_idempt_key)
        if cache_result == "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Request in progress"
            )
        return TransactionResponse.model_validate(cache_result)

    exists = await db.scalar(
        select(Transaction).where(Transaction.idempotency_key == idempotency_key)
    )
    if exists:
        return exists

    try:
        if data.amount > settings.MAX_SINGLE_DEPOSIT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Single limit has been exceeded",
            )

        wallet_exists = await db.scalar(
            select(Wallet).where(Wallet.id == data.dst_wallet_id).with_for_update()
        )
        if not wallet_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found"
            )

        if wallet_exists.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Wallet does not belong to user",
            )

        if wallet_exists.currency != data.currency:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Currency mismatch"
            )

        date_limit = datetime.now(timezone(MSK)) - timedelta(days=1)

        sum_amount = await db.scalar(
            select(func.coalesce(func.sum(Transaction.amount), Decimal(0))).where(
                Transaction.dst_wallet_id == data.dst_wallet_id,
                Transaction.type == TypeTransaction.DEPOSIT,
                Transaction.created_at >= date_limit,
            )
        ) or Decimal(0)

        if (sum_amount + data.amount) > settings.MAX_DAILY_DEPOSIT:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Dayli deposit limit exceeded",
            )

        deposit_tr = Transaction(
            dst_wallet_id=data.dst_wallet_id,
            amount=data.amount,
            currency=wallet_exists.currency,
            type=TypeTransaction.DEPOSIT,
            status=Status.COMPLETED,
            idempotency_key=idempotency_key,
            user_id=user.id,
        )
        db.add(deposit_tr)
        wallet_exists.balance += data.amount

        try:
            await db.commit()

        except IntegrityError:
            await db.rollback()
            exists = await db.scalar(
                select(Transaction).where(
                    Transaction.idempotency_key == idempotency_key
                )
            )
            if exists:
                transaction = TransactionResponse.model_validate(exists)
                await cache.set(
                    redis_idempt_key,
                    transaction.model_dump(),
                    ex=settings.COMPLETED_TTL,
                )
                return transaction

            raise

        await db.refresh(deposit_tr)
        transaction = TransactionResponse.model_validate(deposit_tr)
        await cache.set(
            redis_idempt_key, transaction.model_dump(), ex=settings.COMPLETED_TTL
        )
        return transaction

    except Exception:
        await cache.delete(redis_idempt_key)
        raise


async def transfer_wallet(
    user: User, data: TransactionTransfer, db: AsyncSession, idempotency_key: str
):
    redis_idempt_key = f"idempotency_key:{idempotency_key}"

    create_redis_key = await cache.set(
        redis_idempt_key, "pending", ex=settings.PENDING_TTL, nx=True
    )

    if not create_redis_key:
        cache_result = await cache.get(redis_idempt_key)
        if cache_result == "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Request in progress"
            )
        return TransactionResponse.model_validate(cache_result)

    exists = await db.scalar(
        select(Transaction).where(Transaction.idempotency_key == idempotency_key)
    )
    if exists:
        transaction = TransactionResponse.model_validate(exists)
        await cache.set(
            redis_idempt_key, transaction.model_dump(), ex=settings.COMPLETED_TTL
        )
        return transaction
    try:
        if data.src_wallet_id == data.dst_wallet_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Source and destination must differ",
            )

        if data.amount > settings.MAX_TRANSFER_AMOUNT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Limit transfer exceeded",
            )

        if not data.src_wallet_id or not data.dst_wallet_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Wallet is not specified",
            )

        wallets_id = [data.src_wallet_id, data.dst_wallet_id]
        wallets = (
            await db.scalars(
                select(Wallet)
                .where(Wallet.id.in_(wallets_id))
                .order_by(Wallet.id)
                .with_for_update()
            )
        ).all()

        wallets_by_id = {w.id: w for w in wallets}
        wallet_src = wallets_by_id.get(data.src_wallet_id)
        wallet_dst = wallets_by_id.get(data.dst_wallet_id)

        if not wallet_src or not wallet_dst:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found"
            )

        if wallet_src.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Wallet does not belong to user",
            )

        if wallet_src.currency != wallet_dst.currency:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Currency mismatch",
            )
        if wallet_src.balance < data.amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient funds"
            )

        transfer = Transaction(
            src_wallet_id=wallet_src.id,
            dst_wallet_id=wallet_dst.id,
            amount=data.amount,
            currency=wallet_src.currency,
            type=TypeTransaction.TRANSFER,
            status=Status.COMPLETED,
            idempotency_key=idempotency_key,
            user_id=user.id,
        )

        db.add(transfer)
        wallet_src.balance -= data.amount
        wallet_dst.balance += data.amount

        try:
            await db.commit()

        except IntegrityError:
            await db.rollback()
            exists = await db.scalar(
                select(Transaction).where(
                    Transaction.idempotency_key == idempotency_key
                )
            )
            if exists:
                transaction = TransactionResponse.model_validate(exists)
                await cache.set(
                    redis_idempt_key,
                    transaction.model_dump(),
                    ex=settings.COMPLETED_TTL,
                )
                return transaction
            raise

        await db.refresh(transfer)
        transaction = TransactionResponse.model_validate(transfer)
        await cache.set(
            redis_idempt_key, transaction.model_dump(), ex=settings.COMPLETED_TTL
        )
        return transaction

    except Exception:
        await cache.delete(redis_idempt_key)
        raise
