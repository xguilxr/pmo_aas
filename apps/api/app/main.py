import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.errors import texto_por_defecto
from app.core.observabilidad import (
    captura_de_errores_activa,
    configurar_registro,
    iniciar_captura_de_errores,
)

# MCS OPS-01. Antes había aquí un `logging.basicConfig` con formato de texto
# plano — y solo aquí: el worker no configuraba nada. Ahora los dos llaman a lo
# mismo y el resultado es JSON por `stdout`, incluidos los registros de uvicorn
# y de los 31 sitios que usan `logging.getLogger` sin saber de structlog.
configurar_registro("api")
logger = logging.getLogger("pmoaas.api")


# MCS OPS-02. Vive en `core/observabilidad.py` porque el worker necesita lo
# mismo y no importa este módulo: su servicio arranca `celery` directo.
iniciar_captura_de_errores("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("starting api version=%s env=%s", settings.VERSION, settings.PYTHON_ENV)
    if settings.SEED_ON_STARTUP:
        try:
            from app.services.seed import run_initial_seed

            await run_initial_seed()
        except Exception as exc:
            logger.exception("seed failed: %s", exc)
    yield
    logger.info("api shutdown")


app = FastAPI(
    title="PMO-aaS API",
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # ENH-024: sin esto el browser oculta Content-Disposition al JS
    # cross-origin, y las descargas de PDF caen al fallback genérico
    # "reporte.pdf" en vez del nombre real construido por el backend.
    expose_headers=["Content-Disposition"],
)


@app.middleware("http")
async def cabeceras_de_seguridad(request: Request, call_next):
    """Cabeceras de seguridad en toda respuesta (MCS SEG-03).

    Auditoría MCS 2026-08-03: la aplicación solo tenía `CORSMiddleware`. CORS
    controla quién puede LEER la respuesta desde otro origen; no protege de
    clickjacking, ni de degradación a HTTP, ni de adivinación de tipo MIME.

    Notas de las decisiones:

    * `Strict-Transport-Security` solo fuera de desarrollo: en local se sirve
      por HTTP y esta cabecera dejaría el navegador fijado a HTTPS para
      `localhost`, que es molesto de revertir.
    * La `Content-Security-Policy` es la del **API**, no la del front. Esta
      aplicación devuelve JSON y archivos; no ejecuta scripts propios. Por eso
      puede ser restrictiva sin riesgo. `/docs` y `/redoc` (Swagger y ReDoc)
      cargan JS y CSS desde CDN, así que se excluyen — son herramientas de
      desarrollo, no superficie de producto.
    * `Cache-Control: no-store` en todo `/api/` (MCS SEG-01 · ASVS 8.2.1).
      Antes no se emitía ninguna cabecera de caché, y sin ella la norma del
      navegador es **heurística**: una respuesta sin `Cache-Control` ni
      `Expires` puede guardarse en disco. Eso deja la cartera de un inquilino
      —y su token en la URL de descarga— en el perfil del navegador después de
      cerrar sesión, y en el disco de un equipo compartido.

      `no-store` basta para los navegadores modernos, que es lo que pide el
      control. No se añaden `Pragma: no-cache` ni `Expires: 0`: son para
      intermediarios HTTP/1.0, aquí todo va por TLS a Railway, y una cabecera
      que no protege de nada es ruido que el siguiente lector tiene que
      descartar.

      Va por `setdefault`, como las demás: el endpoint que quiera otra cosa la
      declara en su propia respuesta y gana. Hoy hay **uno**, el logo del
      inquilino (`branding.serve_tenant_logo`, `private, max-age=60`), y lo
      fija su prueba.
    """
    respuesta = await call_next(request)

    respuesta.headers.setdefault("X-Content-Type-Options", "nosniff")
    respuesta.headers.setdefault("X-Frame-Options", "DENY")
    respuesta.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    respuesta.headers.setdefault(
        "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
    )

    if settings.PYTHON_ENV != "development":
        respuesta.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )

    if not request.url.path.startswith(("/docs", "/redoc", "/openapi.json")):
        respuesta.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
        )

    if request.url.path.startswith("/api/"):
        respuesta.headers.setdefault("Cache-Control", "no-store")

    return respuesta


def _error_cors_headers(request: Request) -> dict[str, str]:
    """BUG-079: réplica de los headers CORS para respuestas de error.

    Las excepciones NO manejadas las atrapa `ServerErrorMiddleware` (la capa
    más externa, por ENCIMA de `CORSMiddleware`), así que su 500 no vuelve a
    pasar por CORS y sale SIN `Access-Control-Allow-Origin`. El browser lo
    bloquea y el front muestra "No se pudo conectar con el servidor" en vez
    del error real, ocultando el bug. Reinyectamos los headers a mano,
    espejando la config de `CORSMiddleware` (allow_credentials + origen
    permitido).
    """
    origin = request.headers.get("origin")
    if not origin:
        return {}
    allowed = settings.cors_origins
    if "*" in allowed or origin in allowed:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Vary": "Origin",
        }
    return {}


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """BUG-079: devuelve un 500 con envelope consistente (igual shape que
    AppError) y CON headers CORS, para que el cliente lea el error real en
    lugar de un falso "no se pudo conectar". El traceback se sigue logueando
    (y ServerErrorMiddleware lo re-lanza para uvicorn/Railway).
    """
    logger.exception(
        "unhandled exception on %s %s", request.method, request.url.path
    )
    return JSONResponse(
        status_code=500,
        content={
            # LEN-02: el texto sale del catálogo de `core.errors` y no de un
            # literal aquí. Era la única copia del mensaje que vivía fuera del
            # catálogo, y por eso la única que se iba a quedar atrás.
            "detail": texto_por_defecto("INTERNAL_SERVER_ERROR"),
            "code": "INTERNAL_SERVER_ERROR",
            "fields": {},
        },
        headers=_error_cors_headers(request),
    )


HEALTH_DB_TIMEOUT_SECONDS = 3.0
"""Tiempo máximo que `/health` espera a la base antes de darla por caída.

Muy por debajo del `healthcheckTimeout = 60` de `railway.toml`: la
comprobación tiene que **responder** «mal» dentro de la ventana de Railway, no
agotarla. Una que se cuelga es indistinguible de una que nunca contestó, y
Railway trata las dos igual — pero colgarse deja además la conexión ocupada.
"""


async def _base_de_datos_responde() -> bool:
    """`SELECT 1` acotado en el tiempo. `False` si no contesta o falla.

    Se resuelve `SessionLocal` en el momento de la llamada y no al importar:
    `tests/conftest.py` sustituye ese atributo del módulo para apuntar al motor
    de pruebas, y un `from ... import SessionLocal` congelaría el original.
    """
    from app.db import session as db_session

    try:
        async with asyncio.timeout(HEALTH_DB_TIMEOUT_SECONDS):
            async with db_session.SessionLocal() as sesion:
                await sesion.execute(text("SELECT 1"))
        return True
    except Exception:
        # A propósito se atrapa todo: un fallo de resolución de nombre, un
        # motor mal configurado y un tiempo agotado significan lo mismo para
        # quien decide si promover el despliegue.
        logger.warning("health: la base de datos no respondió", exc_info=True)
        return False


@app.get("/health", tags=["meta"])
async def health():
    """Salud del servicio (MCS DES-03).

    Hasta la auditoría R1 devolvía una constante: atrapaba «el proceso no
    arrancó» y ningún otro caso. Una API desplegada contra una base inalcanzable
    respondía `ok` y Railway promovía el despliegue —el `healthcheckPath` de
    `railway.toml` condicionaba la aceptación a una comprobación que no
    comprobaba nada—.

    **No dice por qué falló.** La ruta es pública (`test_permission_matrix.py`),
    así que el detalle del error se queda en los registros: quien opera lo ve,
    internet no.
    """
    cuerpo = {
        "status": "ok",
        "version": settings.VERSION,
        "env": settings.PYTHON_ENV,
        "checks": {
            "database": "ok",
            # MCS OPS-02 — que la captura de errores esté encendida es
            # comprobable desde fuera, no leyendo registros de arranque.
            # `degraded` y no `unreachable`: sin captura el servicio funciona,
            # lo que se pierde es enterarse cuando deje de hacerlo.
            "error_capture": "ok" if captura_de_errores_activa() else "disabled",
        },
    }
    if not await _base_de_datos_responde():
        cuerpo["status"] = "degraded"
        cuerpo["checks"]["database"] = "unreachable"
        return JSONResponse(status_code=503, content=cuerpo)
    return cuerpo


app.include_router(api_router, prefix="/api/v1")
