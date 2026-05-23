<!--
PR template del repo. Replica el DoD de CLAUDE.md §13 + §7 Paso 7.
Si una casilla no aplica, ponle `N/A — <razón en 1 línea>` después
del checkbox, no la borres en silencio.
-->

## Resumen

<!-- 1-3 bullets de qué hace este PR y por qué -->

## Issue / referencias

<!-- - Cierra US-XXX / BUG-XXX / ENH-XXX
     - Epic: EP0XX
     - DEC / ADR relacionado (si aplica) -->

## Definition of Done (CLAUDE.md §13)

Marca cada capa que tocó este PR (o `N/A — razón`). Si el bullet
aplica pero no se hizo, el PR no está listo para merge.

- [ ] **Backend** — endpoint / Pydantic / lógica
- [ ] **Worker** — task Celery / job async
- [ ] **DB** — migración Alembic + `docs/epics/DB-CHANGES.md`
- [ ] **UX** — página o flow nuevo **con link entrante** (sidebar / tab / botón). Si hay `page.tsx` nuevo, `docs/architecture/navigation.md` actualizado.
- [ ] **UI** — componente nuevo o variante; tokens design-system
- [ ] **Docs** — epic actualizado · ADR / DEC si hay decisión arquitectónica
- [ ] **Tests** — al menos unit o integración (idealmente ambos en endpoints nuevos)
- [ ] **Multi-tenant** — query filtra por `tenant_id`; tests `TC-MT-*` siguen verdes
- [ ] **Verificación manual** — pasos ejecutados (listar abajo)

## Cómo verificar

<!-- Pasos para que el reviewer reproduzca el happy path:
1. ...
2. ...
3. ...
-->

## Archivos tocados

<!-- Lista corta (o referencia a `git diff --stat`). Sirve para
saber qué capas se modificaron sin abrir el diff completo. -->

## Riesgos / efectos colaterales

<!-- Cualquier cosa que el reviewer deba mirar con cuidado:
- ¿Es migración no reversible?
- ¿Cambia comportamiento de un endpoint existente?
- ¿Toca código compartido entre tenants?
- ¿Requiere variable de entorno nueva en Railway? (listarla) -->

## Follow-ups detectados

<!-- Si durante el fix encontré otros issues, los listo aquí para
que el owner decida si abrir nuevos tickets. No los arreglo en este PR
salvo que sean triviales y relacionados. -->
