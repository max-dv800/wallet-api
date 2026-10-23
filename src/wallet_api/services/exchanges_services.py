from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from wallet_api.core.config import settings
from wallet_api.models.enums import Currency, Status, TypeTransaction
from wallet_api.models.exchanges import ExchangeRate
from wallet_api.models.transactions import Transaction
from wallet_api.models.users import User
from wallet_api.models.wallets import Wallet
from wallet_api.schemas.transactions import TransactionExchange, TransactionResponse
from wallet_api.utils.cache import cache
from wallet_api.utils.currency_rate import get_cache_all


async def transaction_exchange(
    data: TransactionExchange, user: User, db: AsyncSession, idemp_key: str
):
    key = f"idempotency_key:{idemp_key}"
    create_redis_key = await cache.set(key, "pending", ex=settings.PENDING_TTL, nx=True)

    if not create_redis_key:
        cache_result = await cache.get(key)
        if cache_result == "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Request in progress"
            )
        return TransactionResponse.model_validate(cache_result)

    exist_transaction = await db.scalar(
        select(Transaction).where(Transaction.idempotency_key == idemp_key)
    )
    if exist_transaction:
        return exist_transaction

    try:
        if data.from_currency == Currency.RUB:
            if data.amount > settings.EXCHANGE_LIMIT_RUB:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Limit transfer exceeded",
                )
        else:
            if data.amount > settings.EXCHANGE_LIMIT_USD_EUR:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Limit transfer exceeded",
                )

        if data.from_currency == data.to_currency:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Source and destination must differ",
            )

        currency = [data.from_currency, data.to_currency]
        wallets = (
            await db.scalars(
                select(Wallet)
                .where(Wallet.user_id == user.id, Wallet.currency.in_(currency))
                .order_by(Wallet.currency)
                .with_for_update()
            )
        ).all()

        wallets_by_currency = {w.currency: w for w in wallets}
        src_wallet = wallets_by_currency.get(data.from_currency)
        dst_wallet = wallets_by_currency.get(data.to_currency)
        if not src_wallet or not dst_wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found "
            )
        if src_wallet.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Wallet does not belong to user",
            )
        if src_wallet.currency == dst_wallet.currency:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Currency match",
            )
        if src_wallet.balance < data.amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient funds"
            )

        key_for_cache = f"{src_wallet.currency}:{dst_wallet.currency}"
        rates = get_cache_all()
        rate = rates.get(key_for_cache)
        if not rate:
            raise ValueError(
                f"No rate for {src_wallet.currency} to {dst_wallet.currency}"
            )

        exchange_rate_id = await db.scalar(
            select(ExchangeRate).where(
                ExchangeRate.from_currency == src_wallet.currency,
                ExchangeRate.to_currency == dst_wallet.currency,
            )
        )
        if not exchange_rate_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Exchange rate not found"
            )

        dst_amount = data.amount * Decimal(rate)
        transaction = Transaction(
            src_wallet_id=src_wallet.id,
            dst_wallet_id=dst_wallet.id,
            amount=data.amount,
            dst_amount=dst_amount,
            currency=src_wallet.currency,
            type=TypeTransaction.EXCHANGE,
            status=Status.COMPLETED,
            idempotency_key=idemp_key,
            user_id=user.id,
            rate=rate,
            exchange_id=exchange_rate_id.id,
        )

        db.add(transaction)
        src_wallet.balance -= data.amount
        dst_wallet.balance += dst_amount

        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            exists = await db.scalar(
                select(Transaction).where(Transaction.idempotency_key == idemp_key)
            )
            if exists:
                exchange = TransactionResponse.model_validate(exists)
                await cache.set(
                    key,
                    exchange.model_dump(),
                    ex=settings.COMPLETED_TTL,
                )
                return exchange
            raise

        await db.refresh(transaction)
        exchange = TransactionResponse.model_validate(transaction)
        await cache.set(key, exchange.model_dump(), ex=settings.COMPLETED_TTL)
        return exchange

    except Exception:
        await cache.delete(key)
        raise
