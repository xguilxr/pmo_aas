# Propuestas de Agentes y Skills (para la librería)

**ID:** `DOC-AGENTS-SKILLS`

Ideas de agentes y skills específicos al desarrollo y operación de PMO-aaS. Se proponen para agregar a tu librería de Claude Code. Cada propuesta incluye nombre, problema que resuelve, trigger, descripción y ejemplo.

---

## 1. Agentes propuestos

### `pmo-schema-guardian`

**Resuelve:** Inconsistencia entre `models.py` (SQLAlchemy), `schemas.py` (Pydantic) y cliente TS (`packages/sdk`). Cuando alguien edita uno de los 3, los otros 2 quedan desincronizados.

**Cuándo usar:** PR que toca `app/models/*.py`, `app/schemas/*.py` o `alembic/versions/*.py`.

**Descripción:**
```
Agente que valida consistencia cross-capa del modelo de datos:
1. Parsea models SQLAlchemy, schemas Pydantic, OpenAPI spec.
2. Detecta drift: campo en model ausente en schema, tipo distinto, nullability divergente.
3. Sugiere parches concretos (o auto-aplica con --fix).
4. Valida migraciones alembic contra estado actual de la BD.
5. Genera nuevamente el cliente TS si el OpenAPI cambió.
```

**Tools:** Read, Grep, Bash (para `alembic current`, `openapi-typescript`), Edit.

**Trigger:** automático en pre-commit + disponible como `/pmo-schema-check`.

---

### `pmo-tenant-isolation-auditor`

**Resuelve:** Olvidarse de aplicar `tenant_id` filter o RLS en endpoints / queries / workers.

**Cuándo usar:** cualquier PR que agrega endpoint FastAPI, query SQLAlchemy, worker task, o toca el filesystem de uploads.

**Descripción:**
```
Escanea el diff buscando:
- Rutas sin Depends(get_current_tenant) o get_superadmin_user.
- Queries sin filter(tenant_id == ...) cuando el modelo es tenant-scoped.
- Paths de archivos que no incluyen {tenant_slug}.
- Redis keys sin tenant_id.
- Logs/traces sin tag tenant_id.
Reporta en forma de checklist con file:line y sugiere fix.
Sugiere agregar TC-MT-* si no existe para el flujo.
```

**Tools:** Grep, Read, WebFetch (para consultar docs internas), Edit.

**Trigger:** automático en PR opening + `/tenant-audit`.

---

### `pmo-epic-synthesizer`

**Resuelve:** Al agregar o modificar una épica, mantener coherencia con US, TC, OpenAPI, schema de BD.

**Descripción:**
```
Dado un cambio en docs/epics/EP*.md, sincroniza:
- Agrega/actualiza user stories referenciadas.
- Crea placeholders de test cases en test-matrix.
- Sugiere migraciones alembic si menciona campos nuevos.
- Actualiza glossary si aparecen términos nuevos.
Verifica que todas las US tengan al menos 1 TC y que los IDs sean únicos.
```

**Tools:** Read, Edit, Grep.

---

### `pmo-prompt-evaluator`

**Resuelve:** Cambios en prompts de IA pueden degradar calidad silenciosamente.

**Descripción:**
```
Cuando cambia docs/ai/prompts-catalog.md o app/ai/prompts/*.py:
1. Ejecuta golden dataset contra nuevo prompt con Ollama y/o Claude.
2. Compara outputs con baseline (similitud semántica + schema válido + campos completos).
3. Reporta regresiones o mejoras.
4. Sugiere nueva versión del prompt (incrementar .vN) si cambio sustancial.
```

**Tools:** Bash (pytest tests/ai), Read, Write.

---

### `pmo-design-system-enforcer`

**Resuelve:** Colores hardcodeados, spacing arbitrario, iconos mezclados, animaciones inconsistentes.

**Descripción:**
```
Revisa archivos .tsx del PR:
- Rechaza hex/rgb/hsl fuera de globals.css.
- Rechaza arbitrary values en Tailwind (text-[15px], p-[13px]) sin comment de excepción.
- Detecta mix de icon libraries (Lucide + Material).
- Detecta animaciones > 400ms o sin respeto a prefers-reduced-motion.
- Verifica uso de componentes de packages/ui en vez de divs crudos.
```

**Tools:** Read, Grep, Edit.

---

### `pmo-railway-deployer`

**Resuelve:** Deploy a Railway requiere configurar variables, healthchecks, volumes correctamente.

**Descripción:**
```
Valida:
- railway.toml en cada app tiene healthcheck configurado.
- Variables requeridas documentadas en docs/architecture/deployment-railway.md están todas definidas.
- Volúmenes montados.
- No hay secretos hardcoded.
- Alembic upgrade incluido en build command.
Sugiere railway.json para nuevo environment de preview.
```

**Tools:** Read, Bash (railway CLI), Grep.

---

## 2. Skills propuestas

### `pmo-seed-demo`

**Propósito:** Poblar una instancia local con datos realistas para demos, tests manuales, screenshots.

**Trigger:** `/pmo-seed-demo` o palabras "seed demo data", "llenar BD con ejemplo".

**Descripción:**
```
Crea:
- 2 tenants: "Acme Corp" y "Globex S.A." con slugs apropiados.
- 3 organizaciones por tenant.
- 2 programas por org.
- 12 proyectos distribuidos con variedad de fases y salud.
- Para cada proyecto: 5-20 riesgos, 3-10 incidencias, 2 cambios, 4 docs, 3 lecciones, 2 minutas.
- 1 Super Admin global (credenciales mostradas).
- 4 users por tenant con roles variados.
Idempotente: no duplica si ya existe.
Imprime credenciales al final con emails de bienvenida formateados.
```

---

### `pmo-generate-module`

**Propósito:** Scaffolding de un módulo nuevo siguiendo el patrón de los 6 existentes.

**Trigger:** `/pmo-generate-module <nombre>` — por ejemplo `/pmo-generate-module budgets`.

**Descripción:**
```
Dado un nombre de módulo nuevo:
1. Genera SQLAlchemy model con tenant_id, folio, soft delete.
2. Alembic migration.
3. Pydantic schemas (Create/Update/Out).
4. FastAPI router (CRUD + filtros + history).
5. Config declarativa del ModuleShell en frontend.
6. Tests stubs (unit + integration + TC-MT-*).
7. Entrada en test-matrix.
8. Actualiza glossary.
Todo siguiendo convenciones del proyecto (prefijo folio, RLS, audit_log).
```

---

### `pmo-migration-safe`

**Propósito:** Guiar creación de migraciones Alembic que no pierdan datos ni causen downtime.

**Trigger:** `/pmo-migrate <descripción>` o menciones de "alembic", "migración".

**Descripción:**
```
Crea migración alembic siguiendo reglas:
- NUNCA DROP COLUMN en un solo PR (flujo en 2 pasos).
- ALTER con default backfill si la tabla es grande (> 100k rows): usar NOT NULL con DEFAULT en PR 1 y remover default en PR 2.
- Agrega índices CONCURRENTLY si la tabla es hot.
- Tests que corren `upgrade()` y `downgrade()` sobre Postgres real (testcontainers).
- Documenta en comment del migration file el por qué.
Bloquea si detecta operación destructiva sin escape explícito.
```

---

### `pmo-release-notes`

**Propósito:** Generar changelog desde PRs merged entre releases.

**Trigger:** `/pmo-release` antes de tag.

**Descripción:**
```
Dados los commits desde último tag:
1. Clasifica: feat, fix, chore, docs, perf, refactor.
2. Agrupa por épica (detectando referencias EP-XXX en commits/PRs).
3. Genera release notes en formato Markdown:
   ## v1.2.0 — 2026-04-30
   ### ✨ Nuevas features
   - EP008: Soporte para modelo local con Ollama (#123)
   ### 🐛 Correcciones
   ...
4. Actualiza CHANGELOG.md.
5. Crea draft release en GitHub.
```

---

### `pmo-plan-vs-actual-explorer`

**Propósito:** Permitir hacer queries en BD rápidamente para investigar desviaciones.

**Trigger:** "¿por qué el proyecto X está en rojo?", "muestra plan vs real de …".

**Descripción:**
```
Usa un ReadOnlyDB MCP (o conexión directa con rol read-only) para:
1. Query project por folio o nombre.
2. Calcular desviaciones (fecha, presupuesto, avance).
3. Listar top riesgos y AIDs críticas.
4. Explicar en lenguaje natural qué está impactando.
5. Sugerir acciones (con prefijo "Sugerencia:" para que humano evalúe).
Nunca escribe. Solo lectura.
```

---

### `pmo-ai-cost-estimator`

**Propósito:** Estimar costo mensual de IA según tamaño de tenant.

**Trigger:** `/pmo-ai-cost <num_projects> <meetings_per_month>`.

**Descripción:**
```
Dado número de proyectos y minutas/reportes/mes esperados, calcula:
- Tokens estimados con Ollama (y tiempo GPU).
- Costo con Claude (con prompt caching).
- Comparativa visual.
- Recomendación de modo según volumen y sensibilidad.
```

---

### `pmo-openapi-diff`

**Propósito:** Mostrar cambios en el API entre dos SHAs/branches para avisar consumers.

**Trigger:** `/pmo-api-diff <base>` en PR.

**Descripción:**
```
Compara OpenAPI spec de base vs HEAD:
- Endpoints agregados / removidos / renombrados.
- Parámetros cambios.
- Schemas cambios (campos agregados/removidos, tipos).
- Clasifica breaking vs non-breaking.
- Genera comentario estructurado en el PR con lista.
```

---

## 3. Agentes ya existentes que usamos mucho

Confirmación de cuáles de los actuales son más valiosos en este proyecto:

- **Explore** — fundamental para onboarding/exploración rápida.
- **Plan** — para definir estrategia de features grandes.
- **Agent general-purpose** — tareas multi-step.
- **claude-code-guide** — dudas sobre config de Claude Code.

---

## 4. Skills de Claude Code que queremos habilitar/explorar

De las ya disponibles:

- **simplify** — revisión de changes para reuso/calidad.
- **review** — review de PRs.
- **security-review** — obligatorio antes de cada release.
- **init** — ya usado para setup inicial.
- **fewer-permission-prompts** — para optimizar DX del equipo.
- **loop** — para monitoreo continuo de PRs / deploys.

---

## 5. Cómo agregar estas propuestas a tu librería

1. Crear archivo `.claude/agents/pmo-schema-guardian.md` (o nombre respectivo) con el prompt y tools.
2. Crear `.claude/skills/pmo-seed-demo.md` para skills.
3. Probar cada uno con un par de invocaciones.
4. Iterar: si produce ruido, refinar el prompt.
5. Compartir con equipo vía el repo.

Documentación oficial de Claude Code sobre agents/skills: su CLI `/help` o `/agents` lista los disponibles; doc en `claude-code-guide` vía este sistema.

---

## Priorización sugerida

| Priority | Propuesta | Por qué ahora |
|---|---|---|
| P0 | `pmo-tenant-isolation-auditor` | Seguridad crítica, aplica desde día 1 |
| P0 | `pmo-seed-demo` | Necesario para desarrollo diario |
| P1 | `pmo-schema-guardian` | Previene bugs comunes de cross-capa |
| P1 | `pmo-generate-module` | Acelera desarrollo de módulos post-MVP |
| P2 | `pmo-prompt-evaluator` | Útil cuando IA se vuelva crítica |
| P2 | `pmo-migration-safe` | Cuando tengamos BD con datos reales |
| P3 | `pmo-release-notes` | Post-MVP, cuando haya releases frecuentes |
| P3 | `pmo-design-system-enforcer` | Post-MVP |
| P3 | `pmo-openapi-diff` | Cuando tengamos consumers externos |
