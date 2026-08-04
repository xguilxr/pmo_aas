import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings

logging.basicConfig(level=settings.LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("pmoaas.api")


def _iniciar_captura_de_errores() -> None:
    """Notificación de errores en producción (MCS OPS-02).

    Auditoría MCS 2026-08-03: no había ninguna. Un 500 en producción quedaba en
    los registros de Railway y nadie se enteraba salvo que un usuario lo
    reportase.

    Sin `SENTRY_DSN` esto no hace nada: en local y en tests queda inerte, y se
    enciende poniendo la variable en Railway. `send_default_pii=False` porque
    este producto trata datos de proyecto de sus clientes y no hay motivo para
    exportarlos a un tercero junto con la traza.
    """
    if not settings.SENTRY_DSN:
        return
    try:
        import sentry_sdk
    except ImportError:
        logger.warning("SENTRY_DSN definido pero sentry-sdk no está instalado")
        return

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.PYTHON_ENV,
        release=settings.VERSION,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        send_default_pii=False,
    )
    logger.info("captura de errores activa env=%s", settings.PYTHON_ENV)


_iniciar_captura_de_errores()


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
            "detail": "Error interno del servidor",
            "code": "INTERNAL_SERVER_ERROR",
            "fields": {},
        },
        headers=_error_cors_headers(request),
    )


@app.get("/health", tags=["meta"])
async def health():
    return {"status": "ok", "version": settings.VERSION, "env": settings.PYTHON_ENV}


app.include_router(api_router, prefix="/api/v1")
