# Estrategia de Testing

**ID:** `DOC-TEST`

## Pirámide

```
        ┌───────────┐
        │   E2E     │  Playwright, flujos core + visuales
        │  ~40 TC   │
        └───────────┘
       ┌─────────────┐
       │ Integration │  pytest + testcontainers (Postgres real)
       │   ~120 TC   │
       └─────────────┘
     ┌─────────────────┐
     │      Unit       │  Vitest (web) + pytest (api)
     │    ~250 TC      │
     └─────────────────┘
```

## Cobertura objetivo

| Capa | Tool | Objetivo |
|---|---|---|
| Unit backend | pytest + pytest-asyncio + hypothesis | ≥ 80% líneas |
| Unit frontend | Vitest + React Testing Library | ≥ 60% líneas |
| Integration | pytest + testcontainers | 100% endpoints críticos |
| Contract | Schemathesis | ✅ en cada PR |
| E2E | Playwright | ≥ 40 flujos (ver test-matrix) |
| Accessibility | `@axe-core/playwright` | 0 violaciones críticas |
| Load | k6 | release pre-flight |
| Security | `bandit` (py), `eslint-plugin-security` (ts), `trivy` (docker) | 0 high/critical |

## Convenciones

- **ID único global**: `TC-001` a `TC-999`. Los de multi-tenant usan prefijo `TC-MT-*`.
- Un TC puede tener múltiples variantes (happy/error/edge); describirlas en el mismo test con `@pytest.mark.parametrize` o `describe.each`.
- Cada PR que toca una US debe actualizar los TC asociados.
- Tests **no flaky**: si un test falla aleatoriamente, se quarantina y se arregla en máx 48h.
- **Fixtures compartidas** en `tests/fixtures/`:
  - `fixture_tenant_a`, `fixture_tenant_b` (para TC-MT-*)
  - `fixture_superadmin`, `fixture_admin`, `fixture_pm`, `fixture_viewer`
  - `fixture_project_full` (proyecto + módulos poblados)

## CI/CD gates

Un PR merges solo si:

1. ✅ Lint (ruff, biome) pasa.
2. ✅ Type checks pasan (mypy, tsc).
3. ✅ Unit tests ≥ 80% backend / 60% frontend.
4. ✅ Integration tests 100% passing.
5. ✅ **Todos los TC-MT-* pasan** (no negociable).
6. ✅ Contract tests sin regresiones OpenAPI.
7. ✅ E2E smoke suite pasa.
8. ✅ Build de Docker de los 3 servicios ok.

## Archivos

- [`test-matrix.md`](./test-matrix.md) — Matriz de trazabilidad Épica↔US↔TC con estados.
- [`multi-tenant-isolation.md`](./multi-tenant-isolation.md) — Detalle de TC-MT-* (bloqueantes).
- `e2e-plan.md` (futuro) — flujos E2E prioritarios.

## Comandos rápidos

```bash
# Backend
cd apps/api && pytest -q                      # todos
pytest -m "not slow"                          # rápidos
pytest tests/integration/test_projects.py -v  # archivo

# Frontend
cd apps/web && pnpm test                      # unit
pnpm test -- --coverage
pnpm test:e2e                                 # Playwright

# Multi-tenant suite (CI-gate)
pytest -m multi_tenant -v

# Contract
schemathesis run http://localhost:8080/openapi.json

# Load (pre-release)
k6 run scripts/k6/dashboard-kpis.js
```

## Flaky-quarantine

Tests flakys se mueven a `tests/_quarantine/` con `@pytest.mark.flaky` y se les abre ticket con SLA 48 h. Pueden bloquear CI si llevan > 5 días sin arreglar.
