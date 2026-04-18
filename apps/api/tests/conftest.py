"""Pytest fixtures. Uses SQLite in-memory for fast tests; prod uses Postgres via Alembic."""
import os
from collections.abc import AsyncIterator

import pytest_asyncio

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("SEED_ON_STARTUP", "false")
os.environ.setdefault("JWT_SECRET", "test_jwt_secret_please_change_in_prod")
os.environ.setdefault("JWT_REFRESH_SECRET", "test_refresh_secret_please_change_in_prod")
os.environ.setdefault("ALLOWED_ORIGINS", "http://testclient")
os.environ.setdefault("BCRYPT_ROUNDS", "4")

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings  # noqa: E402
from app.db.base import Base  # noqa: E402
import app.models  # noqa: E402,F401


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(settings.database_url_async, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncIterator[AsyncSession]:
    maker = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_engine) -> AsyncIterator[AsyncClient]:
    """Override the app's session factory to use the test engine."""
    from app.db import session as session_mod
    from app.main import app

    maker = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    session_mod.SessionLocal = maker

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c
