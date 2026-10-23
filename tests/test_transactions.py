import asyncio
import uuid
from decimal import Decimal

import pytest
from fastapi import status
from sqlalchemy import select

from wallet_api.models.transactions import Transaction
from wallet_api.models.wallets import Wallet

from .conftest import fake_wallet, login_cookie


@pytest.mark.asyncio
async def test_create_deposit(default_client):
    cookie, user_id = await login_cookie(default_client)
    wallet_id, headers = await fake_wallet(default_client, cookie, user_id)

    headers.update({"Idempotency-Key": uuid.uuid4().hex})
    payload = {"amount": 10000, "currency": "rub", "dst_wallet_id": wallet_id}

    response = await default_client.post(
        url="/api/v1/transactions/deposit", json=payload, headers=headers
    )

    assert response.status_code == 200, f"Ошибка создания транзакции: {response.text}"
    data = response.json()
    assert data.get("type") == "deposit"
    assert data.get("amount") == "10000.0000"


@pytest.mark.asyncio
async def test_create_deposit_race(default_client, test_session):
    cookie, user_id = await login_cookie(default_client)
    wallet_id, headers = await fake_wallet(default_client, cookie, user_id)
    idemp_key = uuid.uuid4()

    headers.update({"Idempotency-Key": idemp_key.hex})
    payload = {"amount": 15000, "currency": "rub", "dst_wallet_id": wallet_id}

    response = [
        default_client.post(
            url="/api/v1/transactions/deposit", json=payload, headers=headers
        )
        for _ in range(100)
    ]

    status_codes = await asyncio.gather(*response)

    assert all(status_codes)

    transactions = (
        await test_session.scalars(
            select(Transaction).where(
                Transaction.dst_wallet_id == wallet_id, Transaction.amount == 15000
            )
        )
    ).all()

    assert len(transactions) == 1
    for transaction in transactions:
        assert transaction.idempotency_key == idemp_key


@pytest.mark.asyncio
async def test_transaction_transfer(default_client, test_session):
    cookie_src, user_id_src = await login_cookie(default_client)
    src_wallet_id, headers = await fake_wallet(
        default_client, cookie_src, user_id_src, ballance=30000
    )

    cookie_dst, user_id_dst = await login_cookie(default_client)
    dst_wallet_id, _ = await fake_wallet(default_client, cookie_dst, user_id_dst)

    idemp_key = uuid.uuid4()

    payload = {
        "amount": 10000,
        "src_wallet_id": src_wallet_id,
        "dst_wallet_id": dst_wallet_id,
    }

    headers.update({"Idempotency-Key": idemp_key.hex})

    response = await default_client.post(
        url="/api/v1/transactions/transfer", json=payload, headers=headers
    )

    assert response.status_code == 200, f"Ошибка перевода: {response.text}"
    assert response.json().get("amount") == "10000.0000"

    src_wallet = await test_session.scalar(
        select(Wallet).where(Wallet.id == src_wallet_id)
    )
    assert src_wallet.balance == Decimal("20000.0000")

    dst_wallet = await test_session.scalar(
        select(Wallet).where(Wallet.id == dst_wallet_id)
    )
    assert dst_wallet.balance == Decimal("10000.0000")

    transaction = await test_session.scalar(
        select(Transaction).where(Transaction.idempotency_key == idemp_key)
    )
    assert str(transaction.src_wallet_id) == src_wallet_id
    assert str(transaction.dst_wallet_id) == dst_wallet_id
    assert transaction.amount == Decimal("10000.0000")
    assert transaction.type == "transfer"


@pytest.mark.asyncio
async def test_transaction_transfer_race(default_client, test_session):
    cookie_src, user_id_src = await login_cookie(default_client)
    src_wallet_id, headers = await fake_wallet(
        default_client, cookie_src, user_id_src, ballance=30000
    )

    cookie_dst, user_id_dst = await login_cookie(default_client)
    dst_wallet_id, _ = await fake_wallet(default_client, cookie_dst, user_id_dst)

    idemp_key = uuid.uuid4()

    payload = {
        "amount": 10000,
        "src_wallet_id": src_wallet_id,
        "dst_wallet_id": dst_wallet_id,
    }

    headers.update({"Idempotency-Key": idemp_key.hex})

    responses = [
        default_client.post(
            url="/api/v1/transactions/transfer", json=payload, headers=headers
        )
        for _ in range(100)
    ]

    await asyncio.gather(*responses)

    wallet_src = await test_session.scalar(
        select(Wallet).where(Wallet.id == src_wallet_id)
    )

    assert wallet_src.balance > 0


@pytest.mark.parametrize(
    "payload, expected_status, expected_detail",
    [
        (
            {
                "amount": 10000,
                "src_wallet_id": "6578ea2b-df47-43ec-9fa5-fd491686772c",
                "dst_wallet_id": "6578ea2b-df47-43ec-9fa5-fd491686772c",
            },
            status.HTTP_400_BAD_REQUEST,
            "Source and destination must differ",
        ),
        (
            {
                "amount": 40000,
                "src_wallet_id": "6978ea2b-df47-43ec-9fa5-fd491686772c",
                "dst_wallet_id": "6618ea2b-df47-43ec-9fa5-fd491686772c",
            },
            status.HTTP_400_BAD_REQUEST,
            "Limit transfer exceeded",
        ),
        (
            {
                "amount": 10000,
                "src_wallet_id": "6978ea2b-df47-43ec-9fa5-fd491686772c",
                "dst_wallet_id": "6618ea2b-df47-43ec-9fa5-fd491686772c",
            },
            status.HTTP_404_NOT_FOUND,
            "Wallet not found",
        ),
    ],
)
@pytest.mark.asyncio
async def test_transfer_exception(
    default_client, payload, expected_status, expected_detail
):
    cookie, user_id = await login_cookie(default_client)
    _, headers = await fake_wallet(default_client, cookie, user_id)

    headers.update({"Idempotency-Key": uuid.uuid4().hex})

    response = await default_client.post(
        url="/api/v1/transactions/transfer", json=payload, headers=headers
    )

    assert response.status_code == expected_status
    assert response.json().get("detail") == expected_detail
