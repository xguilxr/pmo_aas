import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings

logging.basicConfig(level=settings.LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("pmoaas.api")


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
