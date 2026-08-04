"""Pytest fixtures. Uses SQLite in-memory for fast tests; prod uses Postgres via Alembic.

ENH-031: engine session-scoped + tabla clean entre tests. El schema se
crea UNA sola vez al inicio de la sesión; cada test hace DELETE de
todas las tablas en orden reverso de dependencias (milliseconds) en
vez de drop_all+create_all (~6s). Suite pasa de ~3min a <60s.
"""
import os
import sys
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
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.db.base import Base


# ENH-031: engine session-scoped. StaticPool + connect_args
# check_same_thread=False permiten que todas las conexiones vean la
# misma DB SQLite in-memory. Schema se crea UNA vez al inicio de la
# sesión de pytest y vive para todos los tests.
@pytest_asyncio.fixture(scope="session")
async def _engine_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        future=True,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_engine(_engine_session):
    """Limpia las tablas antes de cada test (DELETE en orden reverso de
    FKs). Mucho más rápido que drop/create del schema (~10ms vs ~6s).

    Usa el engine session-scoped para que la DB in-memory persista
    entre tests. El fixture mantiene el mismo nombre `db_engine` por
    compat con los tests existentes.
    """
    async with _engine_session.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())
    yield _engine_session


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


# Stub de providers IA para tests integration (los que usan el `client`
# o dispatchan el worker IA). El modo es per-tenant y los providers
# reales harían HTTP, por eso se stubbean a DisabledProvider.
import pytest  # noqa: E402

_AI_STUB_EXCLUDE_PREFIXES = (
    # BUG-030: test que mockea httpx directamente para verificar que
    # el body enviado a Groq no contenga el campo `metadata`. No debe
    # stubbearse el provider, si no el httpx mock nunca se llama.
    "test_bug030_groq_no_metadata",
    # B5 / SEG-06 AM-01: la suite comprueba que `_ping_byo_provider` RECHACE
    # los destinos internos. El stub de abajo lo sustituye por uno que
    # devuelve ok=True, así que con él puesto la suite mediría el stub y
    # pasaría en verde con el agujero abierto. Es justo el caso en que
    # stubbear invalida la prueba.
    "test_seg06_am01_ssrf_base_url",
)


@pytest.fixture(autouse=True)
def _stub_ai_providers(monkeypatch, request):
    modname = request.module.__name__.rsplit(".", 1)[-1]
    if modname.startswith(_AI_STUB_EXCLUDE_PREFIXES):
        yield
        return
    from app.services.ai import provider as provider_mod

    stub = provider_mod.DisabledProvider()

    async def _stub_generate(_self, prompt, *, system=None, override=None, json_mode=False):
        return await stub.generate(prompt, system=system, json_mode=json_mode)

    for name in ("gemini", "claude", "groq", "openai", "perplexity", "custom", "azure"):
        cls = type(provider_mod._PROVIDERS[name])
        monkeypatch.setattr(cls, "generate", _stub_generate)

    # US-104: el PATCH /admin/ai/provider corre _ping_byo_provider antes
    # de persistir. En tests no queremos hacer HTTP real → stub a ok.
    # Tests específicos del gate pueden monkeypatchearlo de vuelta.
    from app.api.v1.endpoints import admin_ai as admin_ai_mod

    async def _stub_ping(*args, **kwargs):
        return admin_ai_mod.TestConnectionResult(ok=True, latency_ms=1)

    monkeypatch.setattr(admin_ai_mod, "_ping_byo_provider", _stub_ping)
    yield


# ENH-034: mock de Celery .delay() para `send_notification_email`.
#
# Causa raíz del bottleneck de 38s en 9 tests (8 en test_ep003_requests
# + 1 en test_us063_password_reset): `enqueue_notification(...,
# send_email=True)` llama a `send_notification_email.delay()`, que
# en kombu/celery intenta abrir conexión TCP al broker definido en
# `BROKER_URL` / `REDIS_URL`. En CI no hay Redis levantado, así que
# el connect a `redis://localhost:6379/15` espera ~30s al socket
# timeout default antes de fallar. El try/except en notifications.py
# captura la excepción pero después de que se acumuló el retraso.
#
# Resultado: cada test que aprueba/rechaza request, crea proyecto, o
# pide password reset acumula ~38s de espera en producer Celery.
#
# Fix: monkeypatch `.delay()` con no-op. Equivale conceptualmente a
# `task_always_eager=True` pero más quirúrgico — no ejecuta la task
# de email (que sería no-op igual porque RESEND_API_KEY="" en tests).
# Aplicar autouse no afecta a tests que mockean otras tasks via su
# propio monkeypatch (US-051 mockea ai_tasks.* directamente).
@pytest.fixture(autouse=True)
def _stub_celery_email_delay(monkeypatch):
    from app.workers.tasks import notifications as notif_tasks

    monkeypatch.setattr(
        notif_tasks.send_notification_email, "delay", lambda *a, **kw: None
    )
    yield


# ENH-030: mock de renderers pesados (weasyprint + python-docx) por
# default en todo el suite. El 82% del tiempo del suite lo tomaban
# tests que generaban PDF/DOCX real (~38s cada uno). Los tests que sí
# necesitan ejercer el render real se marcan con `@pytest.mark.heavy`
# (ver pyproject.toml) y corren en el job `api-tests-heavy` del CI.
#
# Exclusiones: tests cuyo propósito es probar directamente el renderer
# (test_us037_pdf_renderer) ya llevan `pytestmark = pytest.mark.heavy`,
# entonces este stub no se aplica — respetamos la semántica del marker.
_HEAVY_RENDER_EXCLUDE_PREFIXES = (
    "test_us037_pdf_renderer",
)

_PDF_STUB_BYTES = b"%PDF-1.4\nmock-render\n%%EOF\n"
_DOCX_STUB_BYTES = b"PK\x03\x04mock-docx-zip"


@pytest.fixture(autouse=True)
def _stub_heavy_renderers(monkeypatch, request):
    modname = request.module.__name__.rsplit(".", 1)[-1]
    if modname.startswith(_HEAVY_RENDER_EXCLUDE_PREFIXES):
        yield
        return
    # Tests con marker @pytest.mark.heavy quieren el render real.
    if request.node.get_closest_marker("heavy") is not None:
        yield
        return

    def _stub_render_pdf(template_name, context):
        return _PDF_STUB_BYTES

    def _stub_html_to_pdf(html_content):
        return _PDF_STUB_BYTES

    def _stub_render_charter_docx(charter, project, logos=None):
        return _DOCX_STUB_BYTES

    # Parchamos los símbolos que tocan WeasyPrint, y también la función
    # interna síncrona del charter que hace el python-docx real
    # (_render_charter_docx). Esto evita tocar el envoltorio async
    # `generate_charter_docx` que contiene la lógica de Document +
    # storage, que sí queremos ejercitar.
    #
    # `render_html` y `html_to_text` NO se stubean: son Jinja2 puro y
    # regex, no cargan librerías nativas, y los tests que dependen de su
    # salida real deben seguir viéndola.
    import app.services.charter_generator as charter_mod
    import app.services.pdf_renderer as pdf_mod

    monkeypatch.setattr(
        charter_mod, "_render_charter_docx", _stub_render_charter_docx
    )

    stubs = {
        "render_pdf": _stub_render_pdf,
        "html_to_pdf": _stub_html_to_pdf,
    }
    originals = {name: getattr(pdf_mod, name) for name in stubs}
    for name, stub in stubs.items():
        monkeypatch.setattr(pdf_mod, name, stub)

    # `from app.services.pdf_renderer import render_pdf` cachea el símbolo
    # en el módulo importador, así que parchar solo `pdf_mod` no alcanza
    # para los que ya importaron.
    #
    # Barremos `sys.modules` en vez de mantener una lista a mano. La lista
    # anterior nombraba tres endpoints y se había quedado corta: los
    # renderers los importan seis módulos, y `html_to_pdf` no se stubeaba
    # en ninguno. Resultado: 4 tests ejercían WeasyPrint real y fallaban
    # en cualquier máquina sin las librerías nativas GTK/Pango (auditoría
    # MCA 2026-08-03, FLU-01). Una lista escrita a mano vuelve a quedarse
    # corta con el próximo endpoint que importe un renderer; el barrido no.
    #
    # Los que importen DESPUÉS de este punto ya reciben el stub, porque
    # `pdf_mod` queda parchado arriba.
    for mod_name, module in list(sys.modules.items()):
        if module is None or module is pdf_mod or not mod_name.startswith("app."):
            continue
        for name, stub in stubs.items():
            if getattr(module, name, None) is originals[name]:
                monkeypatch.setattr(module, name, stub)
    yield
