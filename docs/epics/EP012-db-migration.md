# EP012 — Instalación productivo en Hostgator MySQL (code-compat + fresh install)

> **⚠️ EPIC CANCELADO — 2026-04-21 (ver DEC-013).**
>
> El owner subió el tier de Railway y productivo v1.0 corre íntegramente
> en Railway Postgres. Ya **no se planea** migrar la BD a MySQL
> HostGator: los blockers técnicos (JSONB, GENERATED, citext, RLS,
> ausencia de IP estática en Railway Hobby) dejan de ser relevantes, y
> el costo incremental del upgrade de Railway se cubre con las
> licencias cobradas a clientes.
>
> Este archivo se conserva como **referencia histórica** del análisis
> PG↔MySQL que se hizo; no se va a ejecutar. HostGator sigue sirviendo
> únicamente el landing estático `www.pmo-aas.com` (ver DEC-012).
>
> **Supersede:** DEC-002 y DEC-012 (la parte de "reabrir a v1.1 si los
> blockers se resuelven") quedan revocadas por DEC-013.
>
> Si en el futuro se necesita cambiar el proveedor de BD, el plan B de
> DEC-013 es Supabase/Neon (ambos Postgres, sin rework del código).

| Campo | Valor |
|---|---|
| **ID** | EP012 |
| **Prioridad** | ❌ CANCELLED (DEC-013, 2026-04-21) |
| **Dependencias** | — (ya no aplica) |
| **Módulo** | `infrastructure`, `database`, `deploy` |
| **Estado** | ❌ CANCELLED |
| **Versión objetivo** | — (no se ejecuta) |

## Objetivo de negocio

Liberar v1.0 en **Hostgator con MySQL** (infra ya pagada) sin migrar datos reales desde un productivo previo: el MVP se construye en staging y el primer release productivo es una **instalación fresca**.

### Ambientes (DEC-017 a registrar)

| Ambiente | Host | BD | Storage | Uso |
|---|---|---|---|---|
| **Local dev** | Docker | PostgreSQL | filesystem | desarrollo individual |
| **Staging** | Railway | PostgreSQL | Railway volume / S3 | QA y demos |
| **Productivo** | Hostgator | **MySQL 8** | Hostgator filesystem | release v1.0 en adelante |

- **Staging se queda en Railway Postgres** — no se migra.
- **Productivo arranca directamente en Hostgator MySQL** — no hay dual-write, no hay cut-over desde otra prod.
- Por lo tanto esta épica NO es una migración online; es **(a) volver el código dialect-agnostic** + **(b) plan de fresh install** en Hostgator.

### DEC a registrar en DECISIONS.md al cierre del bloque

- **DEC-017** — Ambientes: local (Postgres) + staging Railway (Postgres) + productivo Hostgator (MySQL). El código debe correr en ambos dialectos.
- **DEC-018** — Productivo es instalación fresca en Hostgator MySQL. No hay dual-write ni migración de datos desde staging (staging es desechable). La data del tenant productivo nace en MySQL.
- **DEC-019** — DEC-002 (migración al final del roadmap) se supersede por esta estrategia: ya no se "migra" Postgres prod a MySQL prod, simplemente productivo se despliega en MySQL de entrada.

---

## Diferencias críticas PG → MySQL (inventario técnico)

| Feature PostgreSQL usada hoy | Equivalente MySQL | Estrategia |
|---|---|---|
| Row Level Security (RLS) | No existe | Reemplazar con filtros `tenant_id` en cada repo del ORM |
| `gen_random_uuid()` default | `UUID()` / generar en app layer | Generar UUIDs en Python (uuid7 si quieres orden temporal) |
| `citext` (case-insensitive email) | `VARCHAR COLLATE utf8mb4_unicode_ci` | Cambiar tipo + collation |
| `pg_trgm` (fuzzy search) | `FULLTEXT INDEX` + `MATCH AGAINST` | Switch de queries o caer a `LIKE %x%` en volumen bajo |
| `GENERATED ALWAYS AS ... STORED` (ej. `severity`) | Calcular en Python al escribir; trigger opcional | Mover a app layer |
| `timestamptz` | `DATETIME(6)` + convertir a UTC en app | Pydantic asegura TZ consistente |
| `jsonb` con operadores `@>`, `?`, `->` | `JSON` + `JSON_CONTAINS`, `JSON_EXTRACT` | Revisar cada query uno a uno |
| `BIGSERIAL` | `BIGINT AUTO_INCREMENT` | Alembic lo resuelve |
| Cursor pagination con UUID | `BINARY(16)` si se prefiere storage compacto | Opcional, puede quedar como `CHAR(36)` |
| Secuencias (folios `PRJ-YYYY-NNN`) | Tabla `sequences` + `UPDATE ... SELECT LAST_INSERT_ID()` | Implementar un helper `next_sequence(name)` |

Este inventario lo materializa **US-NEW-029**.

---

## ⚠️ Prerequisitos obligatorios

1. MVP estable en staging (todas las épicas v1.0) con suite E2E verde.
2. Backup y export de staging verificable (para re-seed rápido en demos, no para productivo).
3. Entorno MySQL 8 en Hostgator aprovisionado y accesible.
4. Plan de rollback documentado: si productivo falla, staging continúa operando como entorno de soporte mientras se arregla prod.

---

## ❌ CANCELLED — US-NEW-029 — Compatibilidad MySQL del código (dialect-agnostic)

> Cancelada por DEC-013 (2026-04-21). El código se mantiene Postgres-only
> en Railway; no se invierte en hacerlo dialect-agnostic.

**Como** desarrollador
**Quiero** que el backend corra idéntico en PostgreSQL (staging) y en MySQL 8 (productivo)
**Para** desplegar v1.0 en Hostgator sin sorpresas.

**Criterios de aceptación:**
- [ ] Inventario completo de queries / modelos / migraciones que usan features PG-específicas (ver tabla arriba) — archivo `docs/db/pg-vs-mysql-audit.md`.
- [ ] `sqlalchemy` URL switchable por env (`DATABASE_URL=postgresql://…` o `mysql+pymysql://…`).
- [ ] Alembic: cada migración existente se revisa y se reemplaza:
  - `gen_random_uuid()` → UUIDs generados en Python (callable en la columna).
  - `citext` → `VARCHAR(255) COLLATE utf8mb4_unicode_ci` (MySQL) / `citext` (PG) con `variant()` de SQLAlchemy.
  - `timestamptz` → `DATETIME` en MySQL, `TIMESTAMP WITH TIME ZONE` en PG, unificado vía `DateTime(timezone=True)` en SA.
  - `jsonb` → `JSON` (SA resuelve con dialect).
  - `GENERATED STORED` → calcular en `__init__` del modelo o en `@validates`.
- [ ] Reemplazar **RLS** con middleware/dependency de repositorio que inyecta filtro `tenant_id = current_tenant` en cada query.
- [ ] Reemplazar **pg_trgm**:
  - Módulos con volumen bajo (tenants, users): `LIKE '%term%'`.
  - Lessons (full-text): `FULLTEXT INDEX` + `MATCH(...) AGAINST(...)`.
- [ ] Folios secuenciales (`PRJ-`, `RIS-`, etc.): crear tabla `sequences(key, year, last_num)` + helper `next_folio(kind, year)` con `SELECT ... FOR UPDATE` para concurrencia.
- [ ] Suite de tests corre en CI contra **ambos** dialectos (matriz: postgres / mysql). Failure en cualquiera bloquea merge.
- [ ] Documento `docs/db/pg-vs-mysql-audit.md` con status por item (OK / migrado / pendiente).

**Test Cases:**
- `TC-NEW-029-1` (integration) — Suite completa verde contra PostgreSQL.
- `TC-NEW-029-2` (integration) — Suite completa verde contra MySQL 8 local.
- `TC-NEW-029-3` (integration) — Aislamiento multi-tenant preservado sin RLS (el filtro en ORM hace el mismo trabajo).
- `TC-NEW-029-4` (integration) — `next_folio('PRJ', 2026)` bajo concurrencia genera secuencia sin duplicados.
- `TC-NEW-029-5` (integration) — Query fuzzy de lessons funciona en ambos dialectos.

---

## ❌ CANCELLED — US-NEW-030 — Setup Hostgator MySQL + pipeline de deploy productivo (fresh install)

> Cancelada por DEC-013 (2026-04-21). Productivo corre en Railway, no en
> HostGator MySQL. El pipeline CI/CD productivo se mantiene contra
> Railway (auto-deploy por push a `main`).

**Como** ops
**Quiero** aprovisionar Hostgator MySQL, pipeline de CI/CD productivo y runbook de instalación
**Para** desplegar v1.0 en Hostgator de manera repetible.

**Criterios de aceptación:**
- [ ] MySQL 8 en Hostgator provisionado con:
  - Charset `utf8mb4`, collation `utf8mb4_unicode_ci`.
  - Usuarios `app_rw` (read/write) y `app_ro` (read-only, para reportes).
  - Backup automatizado diario (Hostgator config).
  - Conexión TLS obligatoria.
- [ ] Storage de archivos en sistema de archivos de Hostgator bajo `/home/{cpanel_user}/pmo_aas_uploads/` con permisos correctos.
- [ ] Variables de ambiente de productivo documentadas en `docs/deploy/production.md`:
  - `DATABASE_URL=mysql+pymysql://…`
  - `UPLOAD_DIR=/home/.../pmo_aas_uploads`
  - `APP_ENV=production`
  - Keys: Resend, AI providers, etc.
- [ ] Pipeline CI/CD (GitHub Actions) con job `deploy-production`:
  - Trigger manual (workflow_dispatch) para v1.0; después por tag `v*.*.*`.
  - Ejecuta tests (matriz pg + mysql) + build de frontend.
  - Deploy vía SSH/FTP a Hostgator.
  - Ejecuta `alembic upgrade head` contra MySQL productivo post-deploy.
  - Healthcheck + rollback automático si health falla 3 veces en 60s.
- [ ] Script `scripts/prod-bootstrap.py` que en una instancia fresca:
  - Corre `alembic upgrade head`.
  - Crea el primer tenant + super admin desde un seed mínimo provisto por env.
  - Idempotente (no duplica si ya hay tenants).
- [ ] Runbook `docs/deploy/production-runbook.md` con:
  - Pasos de provisión inicial (una vez).
  - Pasos de cada release (alembic, deploy, healthcheck, rollback).
  - Criterios go / no-go por release.
  - Cómo restaurar desde backup.
- [ ] Monitoreo básico: log del app enviado a Hostgator error_log + opcionalmente GlitchTip (si ya está en EP010).
- [ ] Verificación previa al release: correr suite E2E contra productivo con tenant de prueba que se borra al final (script `scripts/prod-smoke.sh`).

**Test Cases:**
- `TC-NEW-030-1` (runbook) — Bootstrap en instancia fresca se completa en < 10 min.
- `TC-NEW-030-2` (integration) — Smoke E2E contra productivo recién instalado pasa.
- `TC-NEW-030-3` (runbook) — Rollback desde v1.0.1 → v1.0.0 recupera en < 5 min.
- `TC-NEW-030-4` (integration) — Upload de archivo → persiste en filesystem Hostgator, URL servida.

---

## Endpoints afectados

Ninguno nuevo. Esta épica es infra + code-compat.

## Cambios de schema

Ninguno estructural — los existentes se re-expresan para ser dialect-agnostic en la migración de US-NEW-029.

---

## Definition of Done

- [ ] Suite de tests verde en CI contra **ambos** dialectos.
- [ ] 0 queries o migraciones que usen features PG-específicas sin equivalente.
- [ ] Staging sigue funcionando en Railway Postgres sin cambios visibles al usuario.
- [ ] Hostgator MySQL productivo provisionado y accesible.
- [ ] Pipeline de deploy productivo ejecutable + documentado.
- [ ] Runbook de instalación, release y rollback completos.
- [ ] Smoke test automatizable contra productivo.
- [ ] DEC-017, DEC-018, DEC-019 registrados en DECISIONS.md.
