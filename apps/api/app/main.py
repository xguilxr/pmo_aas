import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


@app.get("/health", tags=["meta"])
async def health():
    return {"status": "ok", "version": settings.VERSION, "env": settings.PYTHON_ENV}


app.include_router(api_router, prefix="/api/v1")
