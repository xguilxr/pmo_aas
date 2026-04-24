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


# US-057: stub de providers IA para tests integration (los que usan el
# `client` o dispatchan el worker IA). Previo a US-057 los tests dependían
# de AI_MODE=disabled para que el cascade devolviera stubs; ahora el modo
# es per-tenant y los providers reales harían HTTP, por eso se stubbean.
#
# Los tests unitarios que ejercen `OllamaProvider.generate()` directamente
# (p. ej. test_enh011_ai_timeout.py con httpx mock) NO activan este
# stub: se excluyen por nombre de archivo.
import pytest  # noqa: E402

_AI_STUB_EXCLUDE_PREFIXES = (
    "test_enh011_ai_timeout",
    # BUG-030: test que mockea httpx directamente para verificar que
    # el body enviado a Groq no contenga el campo `metadata`. No debe
    # stubbearse el provider, si no el httpx mock nunca se llama.
    "test_bug030_groq_no_metadata",
)


@pytest.fixture(autouse=True)
def _stub_ai_providers(monkeypatch, request):
    modname = request.module.__name__.rsplit(".", 1)[-1]
    if modname.startswith(_AI_STUB_EXCLUDE_PREFIXES):
        yield
        return
    from app.services.ai import provider as provider_mod

    stub = provider_mod.DisabledProvider()

    async def _stub_generate(_self, prompt, *, system=None, override=None):
        return await stub.generate(prompt, system=system)

    for name in ("ollama", "gemini", "claude", "groq", "openai", "perplexity"):
        cls = type(provider_mod._PROVIDERS[name])
        monkeypatch.setattr(cls, "generate", _stub_generate)
    yield
