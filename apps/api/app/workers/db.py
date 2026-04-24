"""Helpers para ejecutar trabajo asíncrono dentro de tasks Celery.

Problema conocido (reportado 2026-04-21 en issue #28):

  RuntimeError: ... got Future ... attached to a different loop

Pasa porque Celery con `prefork` forkea desde el master, y el engine
async global (creado al importar `app.db.session`) tiene conexiones
asyncpg bound al loop del master — que en el worker child ya no
existe. Cuando `run_async` crea un loop nuevo por task y consulta DB
a través del engine heredado, las conexiones del pool explotan.

Solución: `run_async` crea un engine nuevo en el loop fresco, con
`NullPool` (cada query abre su propia conexión, sin reuso), lo
registra en `_task_sessionmaker_var` (ContextVar para aislamiento
entre tasks paralelas), corre el coroutine y al final hace dispose.

`db_session()` resuelve el sessionmaker así:
  - Si hay uno en el ContextVar (estamos dentro de `run_async`): ese.
  - Si no: `app.db.session.SessionLocal` (flujo FastAPI + tests).
"""
from __future__ import annotations

import asyncio
import contextvars
from collections.abc import AsyncIterator, Coroutine
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings

_task_sessionmaker_var: contextvars.ContextVar = contextvars.ContextVar(
    "pmoaas_task_sessionmaker",
)


def run_async[T](coro: Coroutine[object, object, T]) -> T:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    engine = create_async_engine(
        settings.database_url_async,
        echo=False,
        future=True,
        poolclass=NullPool,
    )
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    token = _task_sessionmaker_var.set(maker)
    try:
        return loop.run_until_complete(coro)
    finally:
        _task_sessionmaker_var.reset(token)
        try:
            loop.run_until_complete(engine.dispose())
        finally:
            loop.close()
            asyncio.set_event_loop(None)


@asynccontextmanager
async def db_session() -> AsyncIterator[AsyncSession]:
    try:
        maker = _task_sessionmaker_var.get()
    except LookupError:
        from app.db import session as _session_mod
        maker = _session_mod.SessionLocal
    async with maker() as s:
        yield s
