"""Helpers para ejecutar trabajo asíncrono dentro de tasks Celery.

Las tasks de Celery son sync por default, pero el código de servicio
(providers IA, repositorios SQLAlchemy async, `write_audit`) está
escrito en async. Este módulo expone:

- `run_async(coro)`: corre una coroutine en un event loop nuevo y
  devuelve su resultado. Envuelve `asyncio.run` con manejo explícito
  del ciclo para evitar `DeprecationWarning` al reusar el loop dentro
  de pytest con `CELERY_TASK_ALWAYS_EAGER=true`.

- `db_session()`: context manager async que abre una sesión nueva
  contra `app.db.session.SessionLocal` **al momento de uso**. Es
  importante que no capturemos la fábrica al import, porque el
  conftest de tests la sobrescribe para usar SQLite in-memory.
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Coroutine
from contextlib import asynccontextmanager
from typing import TypeVar

T = TypeVar("T")


def run_async(coro: Coroutine[object, object, T]) -> T:
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            raise RuntimeError("run_async: event loop already running in this thread")
    except RuntimeError:
        loop = asyncio.new_event_loop()
    else:
        if loop.is_closed():
            loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
        asyncio.set_event_loop(None)


@asynccontextmanager
async def db_session() -> AsyncIterator[object]:
    from app.db import session as _session_mod

    async with _session_mod.SessionLocal() as s:
        yield s
