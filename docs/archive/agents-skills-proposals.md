---
responsable: propietario
estado: archivado
revisado: 2026-05-08
revisar_cada: nunca
---

# Agentes y Skills — PMO-aaS

**ID:** `DOC-AGENTS-SKILLS`

Este documento tiene tres secciones:

1. Agentes y skills de tu plugin **`claudio-enterprises`** que vamos a usar
   en este proyecto.
2. Agentes y skills **específicos de PMO-aaS** que complementan el plugin
   (no son reutilizables genéricamente).
3. Cómo adoptarlos y mantenerlos.

> Las propuestas **genéricas** reutilizables (que deberían vivir en tu plugin
> para todos tus proyectos) están en
> [`agents-skills-generic-proposals.md`](./agents-skills-generic-proposals.md).

---

## 1. Desde `claudio-enterprises` — lo que vamos a usar

Estos son agentes/skills que asumimos que tu plugin ya expone, porque
aparecen típicamente en plugins enterprise y encajan directo con los flujos
de PMO-aaS. **Confírmame cuáles existen y te ajusto la tabla** — si alguno
no está, lo movemos a la sección 2 o a propuestas genéricas.

### 1.1. Agentes

| Agente | Uso en PMO-aaS | Cuándo invocarlo |
|---|---|---|
| `code-reviewer` (u equivalente) | Review PRs con criterios firmes | Antes de pedirme review manual, revisa de forma automática y me deja comentarios focalizados |
| `explorer` / `codebase-scout` | Exploración rápida del monorepo | Arranque de cada sesión para ubicar archivos nuevos |
| `planner` / `architect` | Plan detallado antes de implementar épicas grandes | Pre-EP006 (módulos), EP008 (IA), EP010 (Super Admin) |
| `documenter` / `docs-writer` | Mantener `docs/` coherente con el código | Tras cada PR que modifica BD, prompts o endpoints |
| `test-writer` | Generar tests unit/integration con patrones del repo | Cada nueva US, para arrancar con el shell de tests |
| `security-auditor` | Escaneo de OWASP top 10 + secrets | Pre-release, antes de deploy a production |

### 1.2. Skills

| Skill | Uso en PMO-aaS | Cuándo |
|---|---|---|
| `init` | Setup inicial del repo | Ya invocado al arranque del proyecto |
| `review` | Review estructurado de PRs | Antes de merge a `main` |
| `security-review` | Escaneo antes de release | Gate obligatorio pre-tag |
| `simplify` | Detectar refactors y duplicación | Tras completar un módulo grande (EP006) |
| `loop` | Monitoreo continuo de PRs / CI | Durante hot-development para auto-responder a fallos CI |
| `fewer-permission-prompts` | Optimizar DX | Cuando agregue nuevos agentes propios |

> **Acción pendiente para ti:** cuando abras la próxima sesión, corre
> `/agents` y `/help` para listar todo lo que `claudio-enterprises` expone y
> sustituye los nombres aquí por los reales.

---

## 2. Complementos específicos de PMO-aaS

Estos agentes/skills **no son reutilizables** — son específicos del dominio
PMO (multi-tenant, folios, 6 módulos de proyecto, prompts de IA, MPXJ, etc.).
Viven en `.claude/agents/` y `.claude/skills/` de este repo, no en el plugin.

### 2.1. Agentes

#### `pmo-schema-guardian`

**Resuelve:** inconsistencia entre `models.py` (SQLAlchemy), `schemas.py`
(Pydantic) y cliente TS (`packages/sdk`). Cuando alguien edita uno de los 3,
los otros 2 quedan desincronizados.

**Trigger:** PR que toca `app/models/*.py`, `app/schemas/*.py` o
`alembic/versions/*.py`; también `/pmo-schema-check`.

```
Valida consistencia cross-capa:
1. Parsea models SQLAlchemy, schemas Pydantic, OpenAPI spec.
2. Detecta drift: campo en model ausente en schema, tipo distinto,
   nullability divergente.
3. Sugiere parches concretos (o aplica con --fix).
4. Valida migraciones alembic contra estado actual de la BD.
5. Regenera cliente TS si OpenAPI cambió.
```

**Tools:** Read, Grep, Bash (`alembic current`, `openapi-typescript`), Edit.

---

#### `pmo-tenant-isolation-auditor`

**Resuelve:** olvidar `tenant_id` filter / RLS en endpoints, queries, workers
o paths de filesystem.

**Trigger:** PR que agrega endpoint FastAPI, query SQLAlchemy, worker task
o toca el FS de uploads; también `/tenant-audit`.

```
Escanea diff buscando:
- Rutas sin Depends(get_current_tenant) o get_superadmin_user.
- Queries sin filter(tenant_id == ...) cuando el modelo es tenant-scoped.
- Paths de archivos sin {tenant_slug}.
- Redis keys sin tenant_id.
- Logs/traces sin tag tenant_id.
Reporta checklist file:line con fix sugerido.
Sugiere agregar TC-MT-* si no existe para el flujo.
```

**Tools:** Grep, Read, Edit.

---

#### `pmo-superadmin-guardrail` (nuevo — EP010)

**Resuelve:** evitar que rutas de `/superadmin/*` filtren a usuarios
regulares, y que acciones platform-wide se auditen con `scope=platform`.

**Trigger:** PR que toca `app/api/v1/superadmin/*` o
`app/frontend/app/superadmin/*`.

```
Para cada endpoint nuevo en /superadmin:
- Verifica Depends(get_superadmin_user) presente.
- Verifica que no tiene Depends(get_current_tenant) (no se mezcla alcance).
- Verifica que cada mutación agrega audit_log con scope=platform.
- Bloquea si expone datos cross-tenant sin filtro explícito de scope.
```

**Tools:** Read, Grep, Edit.

---

#### `pmo-ai-cascade-tester`

**Resuelve:** asegurar que la cascada Ollama → Gemini → Claude funciona
correctamente cuando se cambian providers, timeouts o prompts.

**Trigger:** cambios en `app/ai/providers/*`, `app/ai/cascade.py`,
`docs/ai/prompts-catalog.md`.

```
1. Ejecuta suite de fixtures contra cada provider con mocks.
2. Simula escenarios: Ollama down, Gemini 429, Claude sin API key.
3. Verifica que métrica `ai_cascade_fallback_total` se incrementa correcto.
4. Compara calidad (similitud semántica) entre providers para el mismo prompt.
5. Alerta si una nueva versión de prompt degrada calidad vs baseline.
```

**Tools:** Bash (pytest), Read, Edit.

---

#### `pmo-design-system-enforcer`

Ver definición previa — sin cambios. Detecta colores hardcoded, valores
arbitrarios Tailwind, mezcla de icon libs y animaciones fuera de tokens.

**Tools:** Read, Grep, Edit.

---

#### `pmo-railway-deployer`

Ver definición previa — sin cambios respecto a la v1, con 2 ajustes:
- Ahora también valida variables `GEMINI_API_KEY`, `GLITCHTIP_DSN_*` y
  `CF_ACCESS_CLIENT_ID/SECRET` (home-host Ollama).
- Ya no valida `SENTRY_*`.

**Tools:** Read, Bash (`railway CLI`), Grep.

---

#### `pmo-epic-synthesizer`

Ver definición previa — sin cambios. Mantiene coherencia épicas ↔ US ↔ TC ↔
glossary ↔ migrations.

**Tools:** Read, Edit, Grep.

---

#### `pmo-prompt-evaluator`

Ver definición previa — actualizado para ejecutar golden dataset también
contra **Gemini**, no solo Ollama y Claude.

**Tools:** Bash, Read, Write.

---

### 2.2. Skills

#### `pmo-seed-demo`

Sin cambios. Poblar BD con 2 tenants, orgs, programas, proyectos, riesgos,
issues, changes, docs, lessons, minutas, super admin, users — idempotente.

#### `pmo-generate-module`

Sin cambios. Scaffolding de módulo siguiendo patrón de los 6 existentes
(model, migration, schemas, router, ModuleShell config, tests, test-matrix,
glossary).

#### `pmo-migration-safe`

Sin cambios. Guía creación de Alembic seguras (no DROP COLUMN en un PR,
backfill con default, índices CONCURRENTLY, tests upgrade/downgrade con
testcontainers).

#### `pmo-release-notes`

Sin cambios. Changelog desde PRs merged entre tags, clasificado por épica.

#### `pmo-plan-vs-actual-explorer`

Sin cambios. Queries read-only sobre la BD para investigar desviaciones de
proyectos y explicar en lenguaje natural.

#### `pmo-ai-cost-estimator`

Ampliado: ahora también muestra costo en **Gemini** (free tier vs paid) y
en **Claude** con prompt caching, más el costo de infra home-host (amortizado).

#### `pmo-openapi-diff`

Sin cambios. Muestra cambios de API entre SHAs, clasifica breaking vs
non-breaking.

#### `pmo-superadmin-runbook` (nuevo — EP010)

**Propósito:** ejecutar runbooks de Super Admin (eliminar tenant, exportar,
toggle maintenance mode) con validaciones y logs.

**Trigger:** `/pmo-superadmin <runbook> <args>`.

```
Runbooks disponibles:
- delete-tenant <slug>      → valida, exporta, programa 24h, confirma.
- export-tenant <slug>      → ZIP firmado con SHA256.
- toggle-maintenance <on|off> → confirma, audita.
- rotate-secret <scope>     → genera nuevo, rota con zero-downtime.
```

---

## 3. Adopción y mantenimiento

### 3.1. Cómo adoptar los específicos de PMO

1. Crear archivo `.claude/agents/pmo-<nombre>.md` con el prompt del agente.
2. Crear archivo `.claude/skills/pmo-<nombre>.md` con el prompt del skill.
3. Commit como `chore(claude): add <nombre> agent`.
4. Probar con un par de invocaciones reales.
5. Iterar el prompt si genera ruido.

### 3.2. Cuándo promover uno a `claudio-enterprises`

Si un agente/skill aquí empieza a ser útil en otros proyectos (ej.
`tenant-isolation-auditor` en cualquier SaaS multi-tenant), generalízalo
y muévelo al plugin. Deja aquí un shim que lo invoque con config PMO.

### 3.3. Priorización MVP

| P | Propuesta | Por qué ahora |
|---|---|---|
| P0 | `pmo-tenant-isolation-auditor` | Seguridad crítica desde día 1 |
| P0 | `pmo-superadmin-guardrail` | Evita leaks en EP010 |
| P0 | `pmo-seed-demo` | Necesario para desarrollo diario |
| P1 | `pmo-schema-guardian` | Previene bugs cross-capa frecuentes |
| P1 | `pmo-ai-cascade-tester` | Garantiza que Gemini fallback funciona |
| P1 | `pmo-generate-module` | Acelera post-MVP |
| P2 | `pmo-prompt-evaluator` | Cuando prompts cambien frecuentemente |
| P2 | `pmo-migration-safe` | Cuando haya datos reales |
| P3 | `pmo-release-notes` | Post-MVP con releases recurrentes |
| P3 | `pmo-design-system-enforcer` | Post-MVP |
| P3 | `pmo-openapi-diff` | Cuando haya consumidores externos |
| P3 | `pmo-superadmin-runbook` | Post-MVP si creces a >10 tenants |

---

## 4. Documentación oficial

- Claude Code docs: usa el agente `claude-code-guide` (disponible en sesión)
  para cualquier duda de configuración.
- Agentes: `.claude/agents/*.md` — el frontmatter define nombre, descripción,
  tools disponibles, modelo.
- Skills: `.claude/skills/*.md` — lo mismo, pero son procedimientos de
  texto que el modelo ejecuta paso a paso.

Próximos pasos concretos están en [`construction-plan.md`](./construction-plan.md).
