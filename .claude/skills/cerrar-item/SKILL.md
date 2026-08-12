---
name: cerrar-item
description: Cierre de una US/BUG/ENH implementada — commit, push, comment de cierre con evidencia, checklist end-to-end y labels/SPRINT.md. Úsala al terminar de implementar. NO para crear issues (triage) ni cerrar la sesión (handoff).
---

# Cerrar un item — de código escrito a fix entregado

Cubre las **Fases C y D** del ciclo. La diferencia entre «fix submitted» y «fix
delivered» es el comment de cierre con la verificación ejecutada.

---

## Antes de tocar código

- **Gate `status:ready` (soft).** Idealmente el issue lo tiene antes de empezar.
  Si el owner pidió ejecutar directo, está OK saltarlo. La regla dura: **Claude
  nunca arranca sin un OK explícito del owner**, sea por label o por chat.
- **1 US/BUG/ENH = 1 commit.** Sin mezclar.
- Mover el item de INBOX → **IN-PROGRESS** en `SPRINT.md`.
- Cambiar label: `triage`/`ready` → `status:in-progress`.

---

## Pensar el slice completo antes de escribir

Ante «agrega X», «permite hacer Y», «arregla Z», preguntarse **qué capa toca**:

1. **Backend** — ¿endpoint nuevo o modificado? ¿Schema Pydantic?
2. **Worker** — ¿parte asíncrona? ¿task de Celery?
3. **DB** — ¿columna nueva, tabla nueva, migración?
4. **UX** — ¿página o flujo nuevo? **¿Desde dónde se llega?** (link en sidebar,
   tab, botón, breadcrumb). *Si la funcionalidad no es alcanzable, no existe.*
5. **UI** — ¿componente nuevo o variante? ¿Cumple tokens del design system?
6. **Docs** — epic, `navigation.md` (si hay página), ADR (si hay decisión),
   `DB-CHANGES.md` (si hay schema).

Si una capa queda sin tocar, **se explica por qué** en la línea N/A del DoD. El
default no es saltarse la capa: es justificar por qué no aplica.

### Anclas concretas — estas obligan

| Si tocás… | Obliga a |
|---|---|
| `page.tsx` nuevo en `apps/web/app/` | actualizar `docs/architecture/navigation.md` + tener al menos un `href=` o `router.push()` entrante |
| Modelo nuevo en `apps/api/app/models/` | migración Alembic + entrada en `docs/epics/DB-CHANGES.md` + ER de `docs/architecture/database.md` |
| Provider nuevo en `services/ai/byo_catalog.py` | `docs/runbooks/ai/byo-setup.md`, `docs/ai/README.md`, `EP008-ai.md` |
| Capability nueva en `core/permissions.py` | `docs/architecture/security-multitenant.md` §3 + decidir si aparece en `/admin/permissions` |
| ADR / DEC nueva | entrada en `docs/adr/README.md` o `docs/epics/DECISIONS.md`, en el mismo bloque |

### Antipatrones que esto bloquea

- ❌ Página nueva sin link entrante → huérfanas.
- ❌ Endpoint sin schema Pydantic ni tests.
- ❌ Columna nueva sin actualizar `DB-CHANGES.md` ni la epic.
- ❌ Renombrar URL sin actualizar `navigation.md` ni redirect.
- ❌ Implementar API sin pensar cómo se consume desde la UI.

---

## Commit + push

```
fix(scope): BUG-006 — desc corta (refs #42)
feat(scope): US-051 — desc corta (refs #42)
```

- **Nunca** `fix #N` / `closes #N` / `resolves #N`. El owner cierra a mano.
- Si toca schema: migración Alembic en el **mismo** commit + referencia en
  `DB-CHANGES.md`.
- **Push inmediato** tras el commit. No acumular commits locales.
- Verificación verde antes de commitear (comandos en la skill `verificar`).

---

## Comment al issue + label — no es opcional

Cada push que resuelve un issue obliga a dos acciones inmediatas:

1. **Cambiar label:** `status:in-progress` → `status:fix-committed`.
2. **Dejar comment** con esta plantilla:

```markdown
## Resuelto en commit <SHA corto>

- **Tipo:** BUG-006 (o US-051 / ENH-003)
- **Resuelve:** <qué del reporte original queda arreglado>
- **No resuelve** (si aplica): <scope fuera de este commit>

### Archivos tocados
- `apps/api/app/api/v1/endpoints/foo.py`
- `apps/web/components/bar.tsx`

### Cómo verificar
1. <pasos de smoke test>
2. <endpoint / URL / acción en UI>

### Follow-ups detectados
<si encontré algo durante el fix que abre otro issue, lo listo aquí>

### Definition of Done
- [ ] **Backend** (endpoint + Pydantic + tests)  ·  _(N/A si no aplica)_
- [ ] **Worker / job async**  ·  _(N/A si síncrono)_
- [ ] **DB** (migración Alembic + DB-CHANGES.md)  ·  _(N/A si no toca schema)_
- [ ] **UX** (¿página/flow nuevo? ¿desde dónde se llega? linkear nav)  ·  _(N/A si solo backend)_
- [ ] **UI** (componente o variante; tokens design-system)
- [ ] **Docs** (epic · `navigation.md` si hay página nueva · ADR si hay decisión)
- [ ] **Tests** (al menos unit o integración)
- [ ] **Verificación manual** (pasos de arriba ejecutados)
```

3. Mover el item en `SPRINT.md` IN-PROGRESS → DONE (solo si es el último del
   bloque; si no, esperar al cierre del bloque).
4. **Actualizar epic doc si aplica.** Si el commit cambió comportamiento descrito
   en `docs/epics/EP0XX-*.md`, editar la epic en el mismo branch. Delegable a
   sub-agente Haiku (ver skill `delegar`).
5. **No cerrar el issue.** Lo cierra el owner al verificar.

> Si hay que actualizar labels o comments en N issues a la vez (cierre de bloque
> grande), delegar a un sub-agente con la lista completa.

---

## Fase D — cierre

**El owner verifica.** Si OK, cierra el issue con `completed`. Si no, comenta,
pone `status:needs-rework`, y Claude retoma en el **mismo** issue — no se crea
uno nuevo.

**Cierre de bloque (Claude).** Cuando todos los issues del bloque están en
`fix-committed` o cerrados:

- Actualizar `SPRINT.md`: mover los items a DONE.
- Verificar que las epics afectadas estén actualizadas. Si quedaron pendientes,
  hacerlo ahora.
- Si el bloque cierra el sprint, ejecutar el cleanup completo (skill `handoff`).
