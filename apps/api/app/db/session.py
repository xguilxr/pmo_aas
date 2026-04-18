from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

_url = settings.database_url_async
_engine_kwargs: dict = {"echo": False, "future": True}
if _url.startswith("postgresql"):
    _engine_kwargs.update(pool_pre_ping=True, pool_size=10, max_overflow=10)

_engine = create_async_engine(_url, **_engine_kwargs)

SessionLocal = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_engine():
    return _engine
