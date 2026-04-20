# EP012 — Migración PostgreSQL → MySQL (Hostgator)

| Campo | Valor |
|---|---|
| **ID** | EP012 |
| **Prioridad** | POST-MVP — AL FINAL del roadmap |
| **Dependencias** | Todas las épicas completadas |
| **Módulo** | `infrastructure`, `database` |
| **Estado** | # PENDING |
| **Versión objetivo** | v2.0 |

## Objetivo de negocio

Reducir costo operativo moviendo la BD a una instancia MySQL en Hostgator (ya pagada) y el almacenamiento de archivos al sistema de archivos de Hostgator.

## ⚠️ Prerequisitos obligatorios

1. **Todo el producto debe estar estable en v1** antes de iniciar esta epic.
2. Backup completo verificado de PostgreSQL.
3. Entorno de staging MySQL configurado en Hostgator para pruebas.
4. Plan de rollback documentado y probado.

---

## Diferencias críticas PG → MySQL

| Feature PostgreSQL | Equivalente MySQL | Impacto |
|---|---|---|
| Row Level Security (RLS) | No existe | **ALTO** — reemplazar con filtros en ORM |
| `gen_random_uuid()` | `UUID()` | Bajo — cambio en Alembic |
| `citext` | `VARCHAR COLLATE utf8mb4_unicode_ci` | Bajo |
| `pg_trgm` (fuzzy search) | `FULLTEXT INDEX` o `LIKE` | **MEDIO** — cambiar queries de búsqueda |
| `GENERATED ALWAYS AS ... STORED` | Trigger o calcular en app layer | Medio |
| `timestamptz` | `DATETIME` + manejo de TZ en app | Medio |
| UUID v7 | UUID v4 (MySQL no tiene v7 nativo) | Bajo — ajustar generador |
| `jsonb` con operadores | `JSON` con funciones | Medio — verificar queries JSONB |
| `BIGSERIAL` | `BIGINT AUTO_INCREMENT` | Bajo |
| Cursor pagination con `uuid` | Igual si se usa `BINARY(16)` | Bajo |

---

## # PENDING — US-NEW-029 — Plan de migración + compatibilidad MySQL

**Como** desarrollador
**Quiero** un plan detallado y un entorno de prueba MySQL funcional
**Para** ejecutar la migración sin downtime.

**Criterios de aceptación:**
- [ ] Inventario completo de queries que usan features PG-específicas.
- [ ] Alembic configurado para MySQL (`mysql+pymysql://`).
- [ ] Reemplazar RLS con middleware de filtro `tenant_id` en todos los repos.
- [ ] Reemplazar `pg_trgm` con `FULLTEXT` o `LIKE` según volumen.
- [ ] Tests de integración verdes contra MySQL local.
- [ ] Script de migración de datos (pg_dump → MySQL import o via Python).
- [ ] Documentar: tablas con JSONB que usen operadores `@>`, `?`, etc.

---

## # PENDING — US-NEW-030 — Ejecución de migración zero-downtime

**Como** operaciones
**Quiero** migrar la BD en producción sin downtime mayor a 5 minutos
**Para** no afectar a usuarios activos.

**Estrategia propuesta:**
1. Configurar MySQL en Hostgator.
2. Correr dual-write: app escribe en PG y MySQL simultáneamente.
3. Verificar paridad de datos por 24h.
4. Flip: cambiar `DATABASE_URL` a MySQL.
5. Monitorear 1h.
6. Apagar dual-write y desactivar PG en Railway.

**Criterios de aceptación:**
- [ ] Dual-write implementado con feature flag.
- [ ] Script de verificación de paridad (row counts + checksums por tabla).
- [ ] Rollback probado: revertir `DATABASE_URL` en < 2 min.
- [ ] Migración de archivos a Hostgator storage documentada.
- [ ] Runbook completo con pasos y go/no-go criteria.

---

## Definition of Done

- [ ] App 100% funcional en MySQL.
- [ ] 0 queries que usen features PG-específicas sin equivalente.
- [ ] Tests E2E verdes contra MySQL en staging.
- [ ] Costo mensual reducido (Railway Postgres off).
- [ ] Backup automatizado en Hostgator.
