import pytest

from .conftest import login_cookie


@pytest.mark.asyncio
async def test_create_wallet(default_client):
    cookie, user_id = await login_cookie(default_client)

    payload = {
        "currency": "rub",
        "balance": 0,
        "user_id": user_id,
    }
    headers = {
        "X-CSRF-Token": cookie.get("__Host-csrf_token"),
        "Cookie": f"access_token={cookie.get('access_token')}; __Host-csrf_token={cookie.get('__Host-csrf_token')}",
    }

    response = await default_client.post(
        url="/api/v1/wallets/", json=payload, headers=headers
    )

    assert response.status_code == 200, f"Ошибка создания кошелька: {response.text}"
    assert response.json().get("currency") == "rub"


@pytest.mark.asyncio
async def test_get_wallets_user(default_client):
    cookie, _ = await login_cookie(default_client)

    response = await default_client.get(
        url="/api/v1/wallets/",
        headers={"Cookie": f"access_token={cookie.get('access_token')}"},
    )

    assert response.status_code == 200, (
        f"Ошибка получения списка кошельков: {response.text}"
    )
    assert response.json() == []
