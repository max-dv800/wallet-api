import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi import status
from sqlalchemy import select

from wallet_api.models.transactions import Transaction

from .conftest import fake_wallet, login_cookie


@patch(
    "wallet_api.services.exchanges_services.get_cache_all",
    return_value={
        "rub:usd": "0.01232658",
        "rub:eur": "0.01097256",
        "usd:eur": "0.89015476",
    },
)
@pytest.mark.asyncio
async def test_exchange_transaction(
    mock_get_cache_all, default_client, test_session, exchange_rate
):
    cookie_src, user_id_src = await login_cookie(default_client)

    _, headers = await fake_wallet(
        default_client, cookie_src, user_id_src, ballance=30000
    )

    await fake_wallet(
        default_client, cookie=cookie_src, user_id=user_id_src, currency="usd"
    )

    payload = {"amount": 10000, "from_currency": "rub", "to_currency": "usd"}

    headers.update({"Idempotency-Key": uuid.uuid4().hex})

    response = await default_client.post(
        url="/api/v1/transactions/exchange", json=payload, headers=headers
    )

    assert response.status_code == 200, f"Ошибка транзакции: {response.text}"

    transaction = await test_session.scalar(
        select(Transaction).where(Transaction.user_id == user_id_src)
    )
    assert transaction.type == "exchange"
    assert transaction.dst_amount == Decimal(response.json().get("dst_amount"))
    mock_get_cache_all.assert_called_once()


@pytest.mark.parametrize(
    "payload, expected_status, expected_detail",
    [
        (
            {"amount": 10000, "from_currency": "rub", "to_currency": "rub"},
            status.HTTP_400_BAD_REQUEST,
            "Source and destination must differ",
        ),
        (
            {"amount": 100000, "from_currency": "rub", "to_currency": "usd"},
            status.HTTP_400_BAD_REQUEST,
            "Limit transfer exceeded",
        ),
        (
            {"amount": 6000, "from_currency": "usd", "to_currency": "rub"},
            status.HTTP_400_BAD_REQUEST,
            "Limit transfer exceeded",
        ),
    ],
)
async def test_exchanges_exceptions(
    default_client, payload, expected_status, expected_detail
):
    cookie_src, user_id_src = await login_cookie(default_client)

    _, headers = await fake_wallet(
        default_client, cookie_src, user_id_src, ballance=30000
    )

    await fake_wallet(
        default_client, cookie=cookie_src, user_id=user_id_src, currency="usd"
    )

    headers.update({"Idempotency-Key": uuid.uuid4().hex})

    response = await default_client.post(
        url="/api/v1/transactions/exchange", json=payload, headers=headers
    )

    assert response.status_code == expected_status
    assert response.json().get("detail") == expected_detail
