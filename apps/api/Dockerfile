# Dockerfile común para api + worker (US-NEW-048).
#
# El servicio `api` lo consume sin necesitar Tailscale (CMD = uvicorn).
# El servicio `worker` sobrescribe el CMD con start-worker.sh, que
# levanta `tailscaled` en user-space antes de ejecutar Celery — así el
# worker puede resolver `ollama-host.<tailnet>.ts.net:11434` desde
# Railway sin exposición pública (ver EP016 / DEC-011).
#
# Tailscale en user-space no requiere privilegios ni /dev/net/tun, que
# es justo lo que Railway NO da a containers. El binario de Tailscale
# se instala con el script oficial.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Dependencias runtime + Tailscale
# - curl + ca-certificates: para descargar y validar TLS
# - iptables: requerido por tailscaled aun con --tun=userspace-networking
#   (usa netfilter para algunas decisiones internas)
# - build deps de psycopg/cffi quedan fuera; requirements.txt usa wheels.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        iptables \
    && curl -fsSL https://tailscale.com/install.sh | sh \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app
RUN chmod +x /app/start-worker.sh

# Default CMD sirve para el servicio `api`. El servicio `worker` lo
# sobrescribe vía `worker.railway.toml` (startCommand).
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2"]
