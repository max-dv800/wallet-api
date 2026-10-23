from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker

from wallet_api.core.config import settings

async_engine = create_async_engine(settings.db_url, echo=True)
AssyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False,
)

engine = create_engine(
    url=settings.db_url_sync,
    max_overflow=10,
    pool_pre_ping=True,
    pool_size=20,
    pool_recycle=1800,
)
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


async def db_session():
    async with AssyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback()


def sync_session():
    with SessionLocal() as session:
        try:
            yield session
        finally:
            session.rollback()


SyncSessionDb = Annotated[Session, Depends(sync_session)]
SessionDb = Annotated[AsyncSession, Depends(db_session)]
