import asyncio
import logging
import uuid
from decimal import Decimal

import aiodocker
import pytest
from aiodocker.exceptions import DockerError
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from wallet_api.core.config import settings
from wallet_api.core.database import db_session
from wallet_api.main import app
from wallet_api.models.base import Base
from wallet_api.models.exchanges import ExchangeRate
from wallet_api.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


test_engine = create_async_engine(url=settings.db_url, echo=True, poolclass=NullPool)


@pytest.fixture(scope="session")
async def test_celery_app():
    celery_app.conf.task_always_eager = True
    yield
    celery_app.conf.task_always_eager = False


@pytest.fixture(scope="session", autouse=True)
async def redis_docker():
    client = aiodocker.Docker()
    container = None

    try:
        old_container = await client.containers.get("test-redis")
        await old_container.delete(force=True)
        logger.info("Удаление старого контейнера")
    except DockerError:
        pass

    try:
        container = await client.containers.run(
            config={
                "Image": "redis:latest",
                "Cmd": [
                    "redis-server",
                ],
                "HostConfig": {
                    "PortBindings": {"6379/tcp": [{"HostPort": "6380"}]},
                },
            },
            name="test-redis",
        )
        await asyncio.sleep(1.5)
        logs = await container.log(stdout=True)
        logger.info(f"Лог контейнера: {logs}")

        yield container

    except DockerError:
        logger.exception("Ошибка запуска контейнера")
        raise

    finally:
        if container:
            try:
                await container.delete(force=True)
            except DockerError as exc:
                logger.warning(f"Ошибка удаления контейнера {exc}")

        await client.close()


@pytest.fixture(scope="function", autouse=True)
async def clear_redis_docker():
    async with Redis(host="localhost", port=6380, db=0) as redis:
        await redis.flushall()
        yield
        await redis.flushall()


@pytest.fixture(scope="session")
async def test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield
    finally:
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await test_engine.dispose()


@pytest.fixture(scope="function")
async def test_session(test_db):
    async with test_engine.connect() as conn:
        trans = await conn.begin()
        TestSessionLocal = async_sessionmaker(
            bind=conn,
            class_=AsyncSession,
            autoflush=False,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            async with TestSessionLocal() as session:
                yield session
        finally:
            await trans.rollback()


@pytest.fixture
async def default_client(test_session):
    async def override_get_db():
        yield test_session

    app.dependency_overrides[db_session] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as cl:
        yield cl

    app.dependency_overrides.clear()


async def login_cookie(client: AsyncClient):
    email = f"test-{uuid.uuid4().hex[:10]}@mail.com"

    response = await client.post(
        url="/api/v1/auth/register",
        json={"email": email, "password_hash": "test_passworD12"},
    )

    user_id = response.json().get("id")

    assert response.status_code == 201, (
        f"Ошибка регистрации пользователя: {response.text}"
    )

    response_login = await client.post(
        url="/api/v1/auth/login",
        data={"username": email, "password": "test_passworD12"},
        headers={"Origin": "http://localhost:8000"},
    )

    assert response_login.status_code == 200, f"Ошибка входа: {response_login.text}"

    cookie = client.cookies

    return cookie, user_id


async def fake_wallet(client: AsyncClient, cookie, user_id, ballance=0, currency="rub"):

    payload = {"balance": ballance, "currency": currency, "user_id": user_id}

    headers = {
        "X-CSRF-Token": cookie.get("__Host-csrf_token"),
        "Cookie": f"access_token={cookie.get('access_token')}; __Host-csrf_token={cookie.get('__Host-csrf_token')}",
    }

    response = await client.post(url="/api/v1/wallets/", json=payload, headers=headers)

    assert response.status_code == 200, f"Ошибка создания кошелька: {response.text}"

    wallet_id = response.json().get("id")

    return wallet_id, headers


@pytest.fixture
async def exchange_rate(test_session):
    exchange = ExchangeRate(
        from_currency="rub", to_currency="usd", rate=Decimal("0.01232658")
    )
    test_session.add(exchange)
    await test_session.flush()
    return exchange


@pytest.fixture
async def register_test_user(default_client):
    response = await default_client.post(
        url="/api/v1/auth/register",
        json={"email": "test_user@email.com", "password_hash": "Password_32"},
    )
    assert response.status_code == 201, (
        f"Ошибка создания нового пользователя: {response.text}"
    )
