---
tipo: archivo
responsable: propietario
estado: archivado
revisado: 2026-05-08
revisar_cada: nunca
---

# Setup de desarrollo — guía por sistema operativo

**ID:** `DOC-SETUP-DEV`

Esta guía describe cómo levantar el entorno de desarrollo **sin exigir Docker**
en máquinas Windows, porque ese fue el bloqueo histórico. Docker está soportado
y documentado, pero es opcional.

---

## 1. ¿Para qué usamos Docker en este proyecto?

Docker nos da una manera reproducible de correr **servicios de infraestructura
locales** (Postgres, Redis, y opcionalmente Ollama). El código de la app
(Next.js + FastAPI) se ejecuta nativo aunque haya Docker: el container no
aporta nada nuevo ahí, solo añade overhead.

En Railway (producción) no corremos Docker propio: los servicios de la app se
construyen con **Nixpacks** (auto-detecta Python/Node) y los plugins Postgres
y Redis son componentes gestionados por Railway. El único container custom es
el de Ollama (si decidimos hostearlo en Railway).

### ¿Entonces cuándo sí necesito Docker local?

- Si quieres **un único comando** que levante Postgres + Redis.
- Si no quieres ensuciar el SO con servicios.
- Si desarrollas en macOS/Linux donde Docker Desktop / OrbStack funcionan bien.

### ¿Cuándo NO necesitas Docker?

- Windows con problemas con Docker Desktop (WSL2 lento, VMMEM chupando RAM,
  licencia empresarial no otorgada, etc.).
- Prefieres usar **Railway dev services** (Postgres + Redis gestionados).
- Tienes Postgres y Redis nativos instalados.

---

## 2. Ruta A — Windows nativo (sin Docker)

### 2.1. Instalar prerequisitos

| Tool | Descarga | Comando verificación |
|---|---|---|
| Node 20 LTS | https://nodejs.org/en/download | `node -v` → v20.x |
| pnpm | `corepack enable && corepack prepare pnpm@latest --activate` | `pnpm -v` → 9.x |
| Python 3.12 | https://www.python.org/downloads/windows/ (activa "Add to PATH") | `py -3.12 --version` |
| PostgreSQL 16 | https://www.postgresql.org/download/windows/ (EnterpriseDB installer) | `psql --version` |
| Redis | **Memurai Developer** (free) https://www.memurai.com/get-memurai | `memurai-cli ping` → PONG |
| Ollama | https://ollama.com/download/windows | `ollama --version` |
| Git | https://git-scm.com/download/win | `git --version` |
| Java 21 (opcional) | https://adoptium.net (solo para MPXJ post-MVP) | `java --version` |

> **Alternativa a Memurai:** Redis nativo **Windows** via WSL2 si ya lo tienes
> instalado (`wsl --install` como admin). Instala Ubuntu, dentro de WSL corre
> `sudo apt install redis-server && sudo service redis-server start`. Desde
> Windows apuntas `REDIS_URL=redis://localhost:6379` y funciona.

### 2.2. Crear la base de datos

Una sola vez, desde `psql` o pgAdmin:

```sql
CREATE USER pmoaas WITH PASSWORD 'pmoaas_dev' CREATEDB;
CREATE DATABASE pmoaas_dev OWNER pmoaas;
CREATE DATABASE pmoaas_test OWNER pmoaas;
```

### 2.3. Configurar variables

Copia `.env.example` → `.env` y completa:

```env
DATABASE_URL=postgresql+asyncpg://pmoaas:pmoaas_dev@localhost:5432/pmoaas_dev
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=cambiar-en-dev
JWT_REFRESH_SECRET=cambiar-en-dev-refresh
AI_MODE=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b-instruct-q4_K_M
# GEMINI_API_KEY=   # si quieres usar el modo free cloud
# ANTHROPIC_API_KEY=   # opcional (fallback premium)
STORAGE_PATH=./data/uploads
```

### 2.4. Levantar la app

```powershell
# Raíz del repo
pnpm install

# Backend (consola 1)
cd apps\api
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
python scripts\seed_superadmin.py         # crea super admin inicial
uvicorn app.main:app --reload --port 8080

# Frontend (consola 2)
cd apps\web
pnpm dev                                   # http://localhost:3000

# Worker Celery (consola 3, opcional para IA)
cd apps\api
.venv\Scripts\Activate.ps1
celery -A app.worker worker --loglevel=info --pool=solo

# Ollama (consola 4, una sola vez descargar modelo)
ollama pull qwen2.5:7b-instruct-q4_K_M
ollama serve                               # queda corriendo en background
```

> **Nota:** `--pool=solo` en Windows es necesario porque Celery no soporta el
> prefork pool en Windows. Para producción usamos Linux (Railway) con prefork
> normal.

---

## 3. Ruta B — Railway dev services (lo más liviano)

Si no quieres instalar Postgres/Redis localmente, crea un **environment `dev`**
en tu proyecto Railway y usa los plugins directamente. Beneficios:

- Cero instalación de DB/Redis local.
- Los mismos managed services que producción (similaridad real).
- Dispondible desde varias máquinas sin replicar datos.

Costo estimado: **$5-10/mes** mientras desarrollas (puedes pausar cuando no).

### 3.1. Crear services en Railway

1. En Railway UI → tu proyecto → `+ New` → `PostgreSQL` (plugin).
2. Repite con `Redis`.
3. Railway CLI: `railway login && railway link`.
4. Obtén las URLs:
   ```bash
   railway variables -s postgres | grep DATABASE_URL
   railway variables -s redis | grep REDIS_URL
   ```
5. Pega en tu `.env` local. Están expuestas a internet con TLS y credenciales
   fuertes; no las publiques.

### 3.2. Correr migraciones

```powershell
cd apps\api
.venv\Scripts\Activate.ps1
alembic upgrade head
```

### 3.3. Ollama

Lo corres local igual que en Ruta A. No tiene sentido pagar Railway para
servir tu IA local durante desarrollo.

---

## 4. Ruta C — macOS / Linux con Docker

```bash
git clone git@github.com:xguilxr/pmo_aas.git && cd pmo_aas
cp .env.example .env

docker compose up -d postgres redis
# NO levantamos 'ollama' por Docker: usamos nativo (mucho más rápido)

pnpm install
cd apps/api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8080 &

cd ../web
pnpm dev
```

`docker-compose.yml` (se creará en el scaffolding inicial):

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: pmoaas
      POSTGRES_PASSWORD: pmoaas_dev
      POSTGRES_DB: pmoaas_dev
    ports: ["5432:5432"]
    volumes: ["pgdata:/var/lib/postgresql/data"]
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "pmoaas"]
      interval: 10s
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
volumes:
  pgdata:
```

---

## 5. Ollama en cada plataforma

| Plataforma | Recomendación |
|---|---|
| Windows | App nativa (`ollama.com/download/windows`). Sin GPU usable <5 tok/s con Qwen 7B; aún útil para dev. |
| macOS (Apple Silicon) | App `.dmg` nativa — usa Metal GPU. ~25-60 tok/s según chip. **Mejor opción single-dev.** |
| Linux con GPU NVIDIA | Instalador oficial + drivers CUDA. Mejor rendimiento absoluto. |
| Sin GPU y lento | Usa modelo más chico (`qwen2.5:3b-instruct-q4_K_M`) o cambia a **Gemini free tier** durante dev. |

Ver guía completa en [`ai/local-model-setup.md`](./ai/local-model-setup.md).

---

## 6. Troubleshooting común

| Síntoma | Causa probable | Solución |
|---|---|---|
| `asyncpg.exceptions.InvalidPasswordError` | Password mal en `.env` | Revisar `DATABASE_URL` |
| `psycopg2` no instala en Windows | Falta build tools | Usamos `psycopg[binary]` — no requiere compilar |
| `redis.exceptions.ConnectionError` | Redis no corriendo | `memurai-cli ping` o WSL `sudo service redis-server status` |
| `celery` crash en Windows | Pool prefork no soportado | Usar `--pool=solo` en dev (producción usa Linux) |
| Ollama CPU 100%, tokens lentos | Sin GPU | Modelo más chico o usa Gemini para dev |
| `alembic` no encuentra `alembic.ini` | Working dir incorrecto | Correr desde `apps/api/` |
| `next: command not found` | pnpm no ejecutó bin links | `pnpm install --force` |
| `ERR_RATE_LIMITED` en Gemini | Free tier (15 RPM) | Bajar concurrencia o cambiar a Ollama |

---

## 7. Scripts útiles (Makefile / pnpm scripts)

A nivel raíz del monorepo (creados durante scaffolding):

```jsonc
// package.json (fragmento)
{
  "scripts": {
    "dev": "turbo dev",
    "dev:api": "cd apps/api && uvicorn app.main:app --reload --port 8080",
    "dev:web": "cd apps/web && pnpm dev",
    "dev:worker": "cd apps/api && celery -A app.worker worker --loglevel=info",
    "db:migrate": "cd apps/api && alembic upgrade head",
    "db:reset": "cd apps/api && alembic downgrade base && alembic upgrade head",
    "seed:demo": "cd apps/api && python scripts/seed_demo.py",
    "test": "turbo test",
    "lint": "turbo lint"
  }
}
```

---

## 8. Cuándo considerar cambiar a Docker

Casos en los que Docker simplifica:

- Onboarding rápido de un nuevo dev (evita 5 instaladores).
- Tests de integración con servicios efímeros (ya usamos **testcontainers**
  en Python — eso sí que requiere Docker; correlo solo al ejecutar tests
  `pytest -m integration`).
- Paridad total con Railway (útil pre-release).

Si en algún momento decides migrar a Docker, `docker compose up -d` sigue
soportado sin cambios en el código.
