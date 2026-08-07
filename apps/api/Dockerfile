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
# - US-069 (2026-04-24): import MPP nativo vía MPXJ. Se agrega una etapa
#   de build (`mpxj-build`) con OpenJDK 21 + curl para bajar el jar de
#   MPXJ (pinned en `MPXJ_VERSION`) y compilar el wrapper `MpxjCli.java`.
#   En la imagen final se agrega únicamente el JRE 21 headless (~200 MB)
#   + los jars en `/opt/mpxj/`. El endpoint `/tasks/import` invoca
#   `java -cp /opt/mpxj/lib/*:/opt/mpxj/cli MpxjCli <file>` via subprocess.
#   Ver `docs/runbooks/infra/mpp-import.md` para rollback y upgrade.

# -------- Etapa 1: build del wrapper MPXJ --------
FROM eclipse-temurin:21-jdk-jammy AS mpxj-build

# Versión pinned: subirla requiere re-testar contra fixtures reales y
# actualizar el runbook. Ver `docs/runbooks/infra/mpp-import.md` §Upgrade.
ARG MPXJ_VERSION=13.7.0

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates unzip \
    && rm -rf /var/lib/apt/lists/*

# Bajar MPXJ desde GitHub releases (single-jar con dependencias embebidas
# para no arrastrar Maven al build). El asset se llama mpxj-X.Y.Z.zip y
# contiene mpxj.jar + lib/*.jar (dependencias runtime como POI + SLF4J).
WORKDIR /build
RUN curl -fsSL -o mpxj.zip \
        "https://github.com/joniles/mpxj/releases/download/v${MPXJ_VERSION}/mpxj-${MPXJ_VERSION}.zip" \
    && unzip -q mpxj.zip -d mpxj-dist \
    && mkdir -p /opt/mpxj/lib \
    && find mpxj-dist -type f -name '*.jar' -exec cp {} /opt/mpxj/lib/ \; \
    && ls /opt/mpxj/lib | head -20 \
    && rm -rf mpxj.zip mpxj-dist

# Compilar el wrapper MpxjCli.java contra los jars bajados.
COPY app/services/msproject/mpxj_cli/MpxjCli.java /build/MpxjCli.java
RUN mkdir -p /opt/mpxj/cli \
    && javac -cp "/opt/mpxj/lib/*" -d /opt/mpxj/cli /build/MpxjCli.java \
    && ls /opt/mpxj/cli \
    && chmod -R a+rX /opt/mpxj

# -------- Etapa 2: runtime API + worker --------
# python:3.12-slim está en Debian Bookworm, que NO trae openjdk-21 en los
# repos default (solo 17). En vez de añadir el repo de Temurin o pinnear
# a JRE 17, copiamos el JRE 21 headless directo desde la imagen oficial
# de Eclipse Temurin — queda en `/opt/java/openjdk` y se expone en PATH.
FROM eclipse-temurin:21-jre-jammy AS temurin-jre

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    JAVA_HOME=/opt/java/openjdk \
    PATH=/opt/java/openjdk/bin:$PATH \
    MPXJ_CLI_CP=/opt/mpxj/lib/*:/opt/mpxj/cli \
    MPP_PARSE_TIMEOUT_SECONDS=60

# Dependencias runtime + WeasyPrint native libs (BUG-007).
# - curl + ca-certificates: wheels pip + health checks externos.
# - fonts-urw-base35 (ENH-202): trae Nimbus Sans, el clon de Helvetica.
#   Sin él, el `font-family: Helvetica` de las plantillas PDF no existía en
#   la imagen y fontconfig caía a DejaVu Sans — los informes salían con una
#   fuente que nadie había elegido. Medido con WeasyPrint 68.1: con solo
#   DejaVu, `fc-match Helvetica` devuelve DejaVuSans; con este paquete, el
#   PDF incrusta NimbusSans. Añade ~11 MB.
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
        fonts-urw-base35 \
        shared-mime-info \
        # MCS INF-03 — `pg_dump` para la copia de seguridad diaria del worker.
        # Sin esto la tarea falla el primer día con «no está en el contenedor»,
        # y una copia que nunca corrió se descubre el día del incidente.
        postgresql-client \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# JRE 21 headless para MPXJ (US-069). Agrega ~180 MB vs baseline.
COPY --from=temurin-jre /opt/java/openjdk /opt/java/openjdk

# Jars de MPXJ + wrapper MpxjCli compilado desde la etapa de build.
COPY --from=mpxj-build /opt/mpxj /opt/mpxj

# MCS SUM-02: el proceso no corre como root.
#
# `python:3.12-slim` deja `root` por defecto y ahí se quedaba: cualquier fallo
# que permitiera ejecutar código dentro del contenedor lo hacía con UID 0, y con
# él la capacidad de escribir sobre el propio código desplegado.
#
# Lo que hubo que cuidar, en orden de probabilidad de romperse:
#
# - **El `CMD` corre `alembic upgrade head`.** Solo lee `alembic/versions/` y
#   escribe en Postgres, no en el sistema de archivos. No necesita privilegios.
# - **MPXJ y el JRE.** Los jars se copian desde `mpxj-build`, que ahora les da
#   lectura explícita (`chmod a+rX`) en vez de confiar en el umask del build;
#   hacerlo allí y no aquí evita duplicar ~40 MB en una capa nueva. El JRE de
#   Temurin ya viene con permisos de lectura para todos — esa imagen está
#   pensada para correr sin privilegios.
# - **`HOME` explícito.** Docker no deriva `HOME` de `/etc/passwd`: sin esto
#   queda en `/` y fontconfig —que WeasyPrint carga en cada PDF— no puede
#   escribir su caché y reconstruye la lista de fuentes en cada render.
# - **El puerto.** 8000 y el `PORT` que inyecta Railway están por encima de
#   1024, así que no hace falta capacidad para puertos privilegiados.
# - **Las subidas** van a `STORAGE_PATH` (`/tmp/pmo-uploads` por defecto, S3 en
#   producción). `/tmp` es escribible por cualquier usuario.
#
# El trinquete que impide que esto se revierta en silencio vive en
# `tests/test_sum02_contenedor_sin_privilegios.py`.
RUN useradd --system --create-home --home-dir /home/appuser \
        --shell /usr/sbin/nologin appuser
ENV HOME=/home/appuser

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# El `--chown` va aquí y no en un `RUN chown -R` posterior: en overlayfs el
# segundo duplicaría el árbol entero en una capa nueva. Exige que `appuser`
# exista ya, que es por lo que el `useradd` está arriba y no junto al `USER`.
COPY --chown=appuser:appuser . /app

USER appuser

# Default CMD sirve para el servicio `api`. El servicio `worker` lo
# sobrescribe vía `worker.railway.toml` (startCommand).
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2"]
