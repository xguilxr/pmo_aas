# Dockerfile común para api + worker.
#
# Historia:
# - US-048 (2026-04-21): agregó sidecar Tailscale al worker para hablar
#   con Ollama local vía tailnet WireGuard.
# - ENH-023 (2026-04-23, post-DEC-017): sidecar retirado. La IA pasó a
#   Groq hosteado (modo platform) y BYO cloud; el worker ya no necesita
#   tailnet. Se removieron `iptables` + instalación de Tailscale. El
#   servicio `worker` sobrescribe el CMD con un celery directo vía
#   `worker.railway.toml` (startCommand).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Dependencias runtime + WeasyPrint native libs (BUG-007).
# - curl + ca-certificates: wheels pip + health checks externos.
# - libpango/libcairo/libgdk-pixbuf/libharfbuzz/fonts-dejavu: WeasyPrint
#   carga estas libs nativas via cffi en runtime. Sin ellas, el import
#   falla con `OSError: cannot load library 'libgobject-2.0-0'` y el
#   reporte PDF devuelve 502 (ver BUG-007). La imagen slim no las incluye
#   por default; agregan ~30 MB.
# - build deps de psycopg/cffi quedan fuera; requirements.txt usa wheels.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libharfbuzz0b \
        libcairo2 \
        libgdk-pixbuf-2.0-0 \
        fonts-dejavu-core \
        shared-mime-info \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

# Default CMD sirve para el servicio `api`. El servicio `worker` lo
# sobrescribe vía `worker.railway.toml` (startCommand).
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2"]
