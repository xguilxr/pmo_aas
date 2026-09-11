---
tipo: gestion
responsable: propietario
estado: vigente
revisado: 2026-09-11
revisar_cada: 30d
---

# FASE 6 — Recursos: unicidad por organización, alta/baja, % asignado, importación

**Qué es.** Recursos (actores) únicos por organización y correo, con alta y
baja desde `/pmo/resources`, el % asignado visible, y el importador de
recursos viviendo ahí con plantilla XLSX. Punto 5 de
`../REVAMP-V2-FEEDBACK.md`. Wireframe **W4**.
**Tamaño:** L. **Gate:** fase 5 mergeada, W4 aprobado, decisión **D1**.
**Epics:** EP017 (directorio). Migración → `DB-CHANGES.md`; D1 →
`DECISIONS.md`.

**Reglas.** Cinco commits. La migración va sola en el commit 1 y es la
única de la fase. La limpieza de datos (commit 5) corre **después** de la
migración y solo con la lista del script de la fase 2.

## Preparación

```bash
git fetch origin main
git checkout -b claude/revamp-v2-f6-recursos origin/main
pnpm install --frozen-lockfile
python scripts/proximo_id.py
cd apps/api && alembic heads
```

## Hechos verificados

- `Actor`: `apps/api/app/models/area.py:154`. `email` es nullable (línea
  193, `String(200)`). `__table_args__` (164-168) ya tiene
  `UniqueConstraint("tenant_id", "email", name="uq_actors_tenant_email")`.
  **Es por tenant, no por organización**: hoy un correo no puede existir en
  dos organizaciones del mismo tenant. Eso contradice el punto 5 ("si
  aparece en otra organización se vuelve a subir").
- Endpoints de actores (`apps/api/app/api/v1/endpoints/areas.py`,
  `actors_router`): `GET ""` :712, `POST ""` :771, `GET /{actor_id}` :905,
  `PATCH /{actor_id}` :926, `DELETE /{actor_id}` :1101 (204).
- `/pmo/resources/page.tsx` es solo lectura. Llama
  `/api/v1/capacity/summary`, `/conflicts`, `/weekly-load` con
  `organization_id` (líneas 145, 146, 179). El summary calcula
  `allocation_in_project_pct` sumando `allocation_pct` de participaciones
  `activa` (`capacity.py:143-147`).
- Importador: `importacion.py` con `kind = projects | resources`
  (`GET /columns` :108, `POST /preview` :142, `POST /{job_id}/confirm` :309).
  La UI vive en `components/importador.tsx` desde la fase 4 (antes
  `pmo/imports/page.tsx`). La plantilla se genera en cliente como **CSV**
  (`imports/page.tsx:124-134` original; ahora en `importador.tsx`).
- Branding XLSX: front `aplicarFuente`/`XLSX_FONT` en
  `apps/web/lib/plan-template.ts`; back `aplicar_a_workbook(wb)` en
  `apps/api/app/core/tipografia.py:41`.

## Decisión D1 (reformulada con los hechos)

| Opción | Constraint | Consecuencia |
|---|---|---|
| A. Por organización (lo que pidió el owner) | `UniqueConstraint("tenant_id", "organization_id", "email")` | La misma persona en dos organizaciones = dos actores. Requiere migración que reemplace `uq_actors_tenant_email` |
| B. Por tenant (lo que hay) | sin cambio | Una persona = un actor; asignable a proyectos de cualquier organización del tenant. Contradice el punto 5 y 2.3 |

Este runbook implementa **A**. Si el owner elige B, salta el commit 1 y
en el commit 3 valida contra el constraint existente.

## Commit 1 — migración: unicidad por organización (US-A)

1. `cd apps/api && alembic revision -m "actores_unicos_por_organizacion"`.
2. `upgrade`: `op.drop_constraint("uq_actors_tenant_email", "actors", type_="unique")`
   y `op.create_unique_constraint("uq_actors_org_email", "actors", ["tenant_id", "organization_id", "email"])`.
   Antes del `create`, un `UPDATE` que ponga `email = NULL` no aplica (los
   NULL no chocan en Postgres); si hay duplicados reales
   `(tenant, organization, email)` el `create` falla: en ese caso el
   script de la fase 2 ya los listó y se resuelven en el commit 5 **antes**
   de correr la migración en producción. Documenta ese orden en
   `DB-CHANGES.md`.
3. `downgrade`: inverso exacto.
4. Modelo `area.py:164-168`: reemplaza el `UniqueConstraint` para que
   `Base.metadata` coincida (`tests/test_doc03_er_generado.py` y
   `python scripts/generar_er.py` regeneran `er-generado.md`).
5. `alembic upgrade head && alembic downgrade -1 && alembic upgrade head`
   contra Postgres local: exit 0.
6. `docs/epics/DB-CHANGES.md`: fila de la migración. `DECISIONS.md`:
   `DEC-###` D1 con la tabla de arriba.

```
feat(db): US-A — actores únicos por (tenant, organización, correo) (mig. <rev>, DEC-###)
```

## Commit 2 — quitar y poner recursos desde /pmo/resources (US-B)

**Archivo:** `apps/web/app/(app)/pmo/resources/page.tsx`. Diseño W4.

1. Botón "Agregar recurso" en la cabecera → modal (`components/ui/modal.tsx`)
   con formulario: `full_name`, `email` (obligatorio en UI: es la clave de
   unicidad), `organization_id` (fijo = organización activa, no editable),
   `area_id`, `team_id` (selectores que ya usan los paneles de
   `components/directory/`; búscalos con
   `grep -rn "listAreas\|listTeams" apps/web/lib/api`), empresa/proveedor si
   el modelo lo tiene (revisa los campos de `Actor` 154-200 y expón los que
   W4 marque). Envía `POST /api/v1/actors` (función en `lib/api/`, búscala
   con `grep -rn "actors\`" apps/web/lib/api`).
   - Error 409 del backend (correo repetido en la organización) → banner
     "Ya existe un recurso con ese correo en esta organización".
2. En cada fila de la tabla de recursos, acción "Quitar" → confirmación →
   `DELETE /api/v1/actors/{id}`. Si el actor tiene participaciones
   `activa`, el backend debe rechazar (verifica en `areas.py:1101-1140`; si
   no valida, agrega la validación y un test).
3. Recarga la tabla tras crear o quitar.

**TC-F6-02.** Crear un recurso con correo nuevo → aparece. Crear otro con
el mismo correo en la misma organización → 409 y mensaje. Mismo correo en
otra organización → se crea. Quitar un recurso sin participaciones →
desaparece; con participaciones activas → rechazo con mensaje.

```
feat(web): US-B — alta y baja de recursos desde /pmo/resources (refs REVAMP-V2 §5)
```

## Commit 3 — % asignado visible (US-C)

1. Confirma qué devuelve `/api/v1/capacity/summary` por actor
   (`capacity.py:65-160`): busca el campo de asignación total
   (`allocation_pct`, `fte`, `saturacion`…). Si solo viene
   `allocation_in_project_pct` cuando se filtra por proyecto, agrega al
   summary un `allocation_total_pct` = suma de `allocation_pct` de todas
   las participaciones `activa` del actor (misma lógica de 143-147 sin
   filtrar por proyecto).
2. En la tabla de `/pmo/resources`, columna "% asignado" con ese valor en
   `font-mono tabular-nums`, y `tone` warning si > 100 (sobreasignado, el
   mismo umbral que usa el KPI "Sobreasignados" del dashboard).

**TC-F6-03.** Un actor con dos participaciones activas de 60% y 50% muestra
110% en ámbar.

```
feat(api,web): US-C — % asignado total por recurso en /pmo/resources
```

## Commit 4 — importador de recursos aquí, con plantilla XLSX (US-D)

1. En `/pmo/resources`, pestaña o sección "Importar recursos" que monta
   `<Importador kind="resources" />` (componente de la fase 4).
2. Plantilla: reemplaza la generación CSV de `importador.tsx` (código
   heredado de `imports/page.tsx:124-134`) por XLSX con `exceljs` (ya es
   dependencia): una hoja "Plantilla" con encabezados de `GET /columns`,
   una fila de ejemplo, y una hoja "Instrucciones" con los campos
   obligatorios. `aplicarFuente(ws)` en ambas. Nombre:
   `plantilla-recursos.xlsx` (`plantilla-proyectos.xlsx` para la otra
   clase).
3. Backend (`importacion.py`, rama `resources` del preview): la validación
   de "ya existe" usa `(tenant_id, organization_id, email)`; existentes se
   marcan "actualizar", nuevos "crear", filas sin correo "error". Lee el
   handler actual antes de tocarlo y agrega test en
   `apps/api/tests/test_<us>_import_recursos.py` con los tres casos.
4. Redirect en `next.config.js`: `/pmo/imports?kind=resources` →
   `/pmo/resources?tab=importar` (si la fase 4 dejó `/pmo/imports`
   redirigiendo a `/pmo?tab=importar`, agrega esta regla **antes**, más
   específica).

**TC-F6-04.** Descargar plantilla → `.xlsx` con fuente del sistema. Subir
un archivo con 1 nuevo, 1 existente y 1 sin correo → preview muestra
crear/actualizar/error; confirmar crea 1 y actualiza 1.

```
feat(web,api): US-D — importador de recursos en /pmo/resources con plantilla XLSX
```

## Commit 5 — limpieza de duplicados (US-E)

1. Con la salida del script de la fase 2
   (`scripts/diagnostico_actores_por_org.py`) y la regla D1, crea
   `scripts/fusionar_actores_duplicados.py --dry-run` que para cada
   `(tenant, organization, email)` con más de un actor: conserva el que
   tenga más participaciones activas (empate: el más antiguo), reasigna
   las participaciones del resto a ese y marca los demás `is_active=False`
   (no borra). Sin `--dry-run` aplica.
2. Corre `--dry-run` contra desarrollo, pega la salida en el PR. El owner
   decide si se corre en producción (skill `guard_irreversible`: es un
   `UPDATE` masivo, el owner lo corre a mano).

```
chore(scripts): US-E — fusión de actores duplicados por organización (dry-run por defecto)
```

## Verificación antes de push

```bash
pnpm --filter @pmoaas/web exec tsc --noEmit
python scripts/check_tokens.py
cd apps/api && .venv/bin/python -m ruff check . && .venv/bin/python -m pytest -q -n auto -m "not heavy"
python scripts/generar_er.py && git diff --stat docs/architecture/er-generado.md
python scripts/check_impacto_documental.py
```

## Cierre

PR `Revamp v2 — fase 6: recursos`. `cerrar-item` × 5. Feedback: 5 →
`hecho`; 2.3 nota de limpieza → cerrada. `SPRINT.md` → "7 (admin y
cuenta)". Antes: W7, W8, D4.

## Qué NO hacer

- No correr la migración en producción antes de resolver duplicados.
- No borrar actores (solo `is_active=False`).
- No tocar `project_participations` salvo reasignar `actor_id` en el
  script.
