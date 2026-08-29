---
tipo: guia
responsable: propietario
estado: vigente
revisado: 2026-08-29
revisar_cada: 180d
---

# Estrategia de Testing

**ID:** `DOC-TEST`

> **Reescrito el 2026-08-29.** La versión anterior describía una pirámide con
> Playwright, Vitest, `@axe-core/playwright`, Schemathesis, k6 y Hypothesis —
> ninguna de esas herramientas está en el repo (`apps/web/package.json` no
> tiene `playwright`, `vitest`, `@testing-library` ni `@axe-core`; su script
> `test` es literalmente `echo "no web tests yet"`). Era el plan original,
> nunca lo que se construyó. Esto describe lo que hay hoy.

## Lo que existe

**Solo hay tests de backend.** 217 archivos en `apps/api/tests/`, pytest.
**No hay tests automatizados de frontend** — ni unitarios, ni de integración,
ni E2E. Verificar una pantalla es manual (`npm run dev` + navegador) o, para
un cambio de UI, el flujo que describe el skill `run`.

No hay contract testing (Schemathesis), ni load testing (k6), ni property-based
testing (Hypothesis): ninguno se llegó a integrar. Si alguno se retoma, entra
aquí cuando exista de verdad, no antes.

## Backend: qué cubre pytest

Una suite, sin la separación formal unit/integration/E2E que sugiere una
pirámide — un test de un endpoint típicamente ejercita el servicio, el modelo
y la base (SQLite en memoria) en el mismo caso. Tres marcadores reales
(`apps/api/pyproject.toml`):

| Marcador | Qué enciende |
|---|---|
| `heavy` | Render real (WeasyPrint / python-docx) o hashing completo. Corre aparte (`api-tests-heavy`, solo en push a `main`) |
| `permissions` | Matriz role × endpoint (US-079, gate de regresión post-DEC-024) |
| `con_segundo_factor` | Enciende el MFA de administración, que la suite apaga por defecto |

No hay marcador `multi_tenant` ni `slow`: el aislamiento multi-tenant se
prueba en archivos con nombre explícito (`test_seg08_aislamiento_tenants.py`,
`test_us214_multi_tenant.py`, y otros ~13 más — ver
`docs/architecture/security-multitenant.md` §5), no por marcador.

**Criterio: `exit 0`, nunca un porcentaje de cobertura.** No hay un objetivo
de cobertura declarado ni medido — el criterio de este repo es que la suite
completa pase, según la skill `verificar`.

## CI/CD — los gates reales

Los jobs de `.github/workflows/ci.yml`, no una lista aspiracional:

| Job | Qué hace |
|---|---|
| `lint` | `ruff check` |
| `tipos-python` | `mypy --strict` con línea base heredada |
| `web-typecheck` | `tsc --noEmit` |
| `web-build` | `pnpm build` del frontend |
| `api-tests-smoke` | pytest sin `heavy`, en cada PR |
| `api-tests-heavy` | pytest con `heavy`, solo push a `main` |
| `api-migrations-postgres` | `alembic upgrade → downgrade → upgrade` contra Postgres real |
| `contexto-permanente` | Presupuesto de contexto + límites de `SPRINT.md`/`HANDOFF.md` + índice del conocimiento (DOC-06/07) |
| `contraste-wcag` | Contraste de color + literales fuera de token |
| `commits` | Conventional Commits + impacto documental (DOC-06) |
| `seguridad` | Secretos, SAST, dependencias vulnerables |
| `evaluacion-ia` | El conjunto de evaluación de `apps/api/evaluacion/` |

Sin contract testing, sin E2E, sin build de Docker como gate propio (el
`Dockerfile` se construye al desplegar, no en CI).

## Archivos

- [`test-matrix.md`](./test-matrix.md) — convención real de ID de caso.
- [`multi-tenant-isolation.md`](./multi-tenant-isolation.md) — el patrón real
  de aislamiento multi-tenant.

## Comandos

Los mismos que corre el CI; la skill `verificar` es la fuente de verdad y
tiene el detalle de entorno (Python 3.12 fijado, por qué):

```bash
cd apps/api && python -m ruff check .
cd apps/api && python -m pytest -q -n auto -m "not heavy"
cd apps/api && python -m pytest -q -m heavy      # solo lo que corre en main
pnpm --filter @pmoaas/web exec tsc --noEmit
python scripts/check_tipos.py
python scripts/check_contexto.py
python scripts/indexar.py --verificar
```

No hay `pytest -m multi_tenant`, `pnpm test:e2e` ni `k6 run`: ninguno existe.
