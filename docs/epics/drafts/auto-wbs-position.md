# Draft — Auto-WBS con orden manual estable (`tasks.position`)

> **Estado:** propuesta para revisión del owner (no implementado).
> Origen: Fase 4 del análisis Sprint 35 (UIUX-ANALYSIS-Sprint35.md, follow-up #4).
> El owner pidió revisar el plan antes de implementar.

## 1. Problema

Hoy el orden del plan se deriva del **WBS** (orden natural) + `outline_level`.
- `POST /tasks/renumber-wbs` (US-172) renumera tomando el WBS natural como orden.
- No existe forma de **reordenar manualmente** una tarea (subirla/bajarla) y que
  ese orden persista independiente del WBS.
- Para planes planos o con WBS contradictorio, el orden es ambiguo.

## 2. Propuesta (recomendada)

Una columna **`position`** = orden lineal autoritativo del proyecto. El **indent**
sigue saliendo de `outline_level` (profundidad). Juntos definen el plan
jerárquico completo, y el algoritmo de renumber que ya tenemos (recorrer la
lista ordenada + profundidad → asignar WBS `1, 1.1, 1.2, 2, …`) funciona tal
cual, pero ordenando por `position` en vez de por WBS natural.

### Schema (migración 0088)
- `tasks.position INTEGER NULL` (nullable; backfill perezoso en el primer
  reorder/renumber). Index `(project_id, position)`.

### Backend
- `list_tasks`: `ORDER BY position NULLS LAST, outline_level, wbs` (fallback al
  orden actual cuando `position` es NULL).
- Nuevo endpoint **`POST /projects/{id}/tasks/reorder`** body `{ ordered_ids: [...] }`
  → asigna `position = índice` a cada id (bulk; el front manda el orden visible
  completo tras un drag). 1 commit, optimista en el front.
- `create_task`: `position = max(position)+1` (la nueva tarea va al final).
- `renumber-wbs`: cambiar el sort a `position NULLS LAST, _natural_wbs_key` para
  que respete el orden manual.

### Frontend
- Drag-to-reorder de filas con **@dnd-kit/sortable** (ya instalado).
- Al soltar: recomputar la lista de ids visibles → `reorder` endpoint + update
  optimista.

## 3. Decisiones abiertas (para el owner)

1. **Alcance del drag con jerarquía:** ¿mover sólo la fila (MVP) y que el PM
   corra "Auto-WBS" para re-derivar la jerarquía, o mover el **subárbol**
   completo (hijos incluidos)? Mover subárbol es bastante más complejo.
   → *Recomendación MVP:* mover sólo la fila; el indent se recalcula con Auto-WBS.
2. **Dónde se habilita el drag:** ¿sólo en vista plana (sin agrupar por WBS/Área),
   o también dentro de la agrupación? Reordenar dentro de grupos colapsados es
   confuso. → *Recomendación:* habilitar el reorder sólo en vista plana.
3. **`position` por proyecto (global) vs por hermanos (por nivel).** La global es
   mucho más simple y cubre el caso; la por-hermanos es la "correcta" para un
   árbol pero añade complejidad. → *Recomendación:* global.

## 4. Riesgos / costo
- Integrar @dnd-kit/sortable en la tabla grande del plan (la fila ya tiene mucho
  estado por la edición inline) — cuidado con conflictos drag vs. controles
  inline (área/estado/fechas). Mitigación: un "handle" de drag dedicado.
- Migración + backfill.
- **Esfuerzo: L** (el mayor del batch). 1 migración + 1 endpoint + refactor de la
  fila del plan para drag.

## 5. Plan de ejecución (si se aprueba)
1. `feat(api): US-### — tasks.position + /tasks/reorder + list order (migración 0088)`.
2. `feat(api): renumber-wbs respeta position`.
3. `feat(web): drag-to-reorder en el plan (handle dedicado) + optimista`.
4. Docs: EP009 + DB-CHANGES + navigation (sin ruta nueva).
