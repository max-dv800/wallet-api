import pytest

from .conftest import login_cookie


@pytest.mark.asyncio
async def test_register_user(default_client):
    response = await default_client.post(
        url="/api/v1/auth/register",
        json={"email": "test_user@email.com", "password_hash": "test_passwordP12"},
    )

    assert response.status_code == 201, f"Ошибка: {response.text}"
    assert response.json().get("email") == "test_user@email.com"


@pytest.mark.asyncio
async def test_register_user_not_valid_password(default_client):
    response = await default_client.post(
        url="/api/v1/auth/register",
        json={"email": "test_user@email.com", "password_hash": "not_valid_pass"},
    )

    assert response.status_code == 422
    assert response.json().get("detail")[0]["type"] == "value_error"


@pytest.mark.asyncio
async def test_login_user(default_client, register_test_user):
    response = await default_client.post(
        url="/api/v1/auth/login",
        data={"username": "test_user@email.com", "password": "Password_32"},
        headers={"Origin": "http://localhost:8000"},
    )

    assert response.status_code == 200, f"Ошибка: {response.text}"
    assert "expires_in" in response.json()


@pytest.mark.asyncio
async def test_login_not_origin(default_client, register_test_user):
    response = await default_client.post(
        url="/api/v1/auth/login",
        data={"username": "test_user@email.com", "password": "Password_32"},
        headers={"Origin": "http://myweb:8000"},
    )

    assert response.status_code == 403, f"Ошибка: {response.text}"
    assert response.json().get("detail") == "Origin not allowed"


@pytest.mark.asyncio
async def test_me_page(default_client):
    cookie, _ = await login_cookie(default_client)
    response = await default_client.get(
        url="/api/v1/auth/me",
        headers={"Cookie": f"access_token={cookie.get('access_token')}"},
    )

    assert response.status_code == 200, f"Ошибка: {response.text}"


@pytest.mark.asyncio
async def test_refresh_token(default_client):
    cookie, _ = await login_cookie(default_client)

    headers = {
        "X-CSRF-Token": cookie.get("__Host-csrf_token"),
        "Cookie": f"refresh_token={cookie.get('refresh_token')}; __Host-csrf_token={cookie.get('__Host-csrf_token')}",
    }
    response = await default_client.post(url="/api/v1/auth/refresh", headers=headers)
    assert response.status_code == 200, (
        f"Ошибка обновления access токена: {response.text}"
    )
    assert "expires_in" in response.json()


@pytest.mark.asyncio
async def test_refresh_token_not_headers(default_client):
    cookie, _ = await login_cookie(default_client)

    response = await default_client.post(
        url="/api/v1/auth/refresh",
        headers={
            "Cookie": f"refresh_token={cookie.get('refresh_token')}; __Host-csrf_token={cookie.get('__Host-csrf_token')}"
        },
    )
    assert response.status_code == 403, (
        f"Ошибка обновления access токена: {response.text}"
    )
    assert response.json().get("detail") == "missing_token"


@pytest.mark.asyncio
async def test_logout(default_client):
    cookie, _ = await login_cookie(default_client)

    response = await default_client.post(
        url="/api/v1/auth/logout",
        headers={
            "X-CSRF-Token": cookie.get("__Host-csrf_token"),
            "Cookie": f"access_token={cookie.get('access_token')}; __Host-csrf_token={cookie.get('__Host-csrf_token')}",
        },
    )

    assert response.status_code == 204, f"Ошибка: {response.text}"
    data = default_client.cookies

    assert data.keys() not in ["access_token", "refresh_token", "__Host-csrf_token"]
