# SPRINT.md — Tarea activa

> **Regla:** este archivo es lo que se mira cada día. El epic se abre al tocarlo
> (`CLAUDE.md` §1). 1 US = 1 commit. Al terminar, mover la siguiente a IN-PROGRESS.
>
> **Histórico:** todo lo cerrado vive en `SPRINT-DONE-HISTORY.md`.
>
> **Límite:** este archivo no pasa de 250 líneas. Lo hace cumplir el CI
> (`scripts/check_contexto.py`); se carga en toda sesión y se paga en cada turno.

---

## 🔴 IN-PROGRESS

```
#575 y #576 MERGEADOS. **MCA está en N2**, su objetivo.

Branch `claude/audit-continuation-fzrtko`. Remediación post-R1 completa:
SUM-02, DES-03, DIS-02, SEG-07/AM-08, AM-09, SEG-01, D-7 y D-9. LEN-02 sigue
PARCIAL, con cifra: 152 de 159 mensajes dicen solo qué pasó.

MCS en N0: 25/126 conformes; la distancia a N1 baja de 54 a 50.
Informe: `docs/conformidad/2026-08-05-mcs-remediacion.md`. Todo en verde.

**Decisiones del owner (2026-08-05), las cuatro ejecutadas:** volver al producto ·
LEN-02 como norma · PyJWT · `support` → `hypercare`.

Producto: **ENH-202**, **D-2**, **D-8**, **AM-10** y **D-3** cerradas. Ninguna
amenaza sin control y **el glosario sin decisiones abiertas** — de D-4 falta
calibrar cinco valores, que es dato, no decisión.

**Espera al owner:** mergear el PR y correr las migraciones **0097-0099**.
```

> **¿Próximo ID libre?** `python scripts/proximo_id.py`. Se deriva de GitHub +
> `git log` + docs; ya no se almacena aquí (MCA CTX-03). Corrélo contra
> `origin/main` actualizado.

---

## 📥 INBOX / TRIAGE

> Solo lo **abierto**. Lo cerrado se archivó a `SPRINT-DONE-HISTORY.md`
> el 2026-08-03.

### Siguiente batch

**ENH-202 cerrada el 2026-08-05**, los cuatro frentes; cerró AM-12 de paso.

**D-8 cerrada el 2026-08-05** (ADR-021, migración 0099). **AM-10 cerrada**: el
bloqueo de cuenta pasó a retardo creciente, y con ella el modelo de amenazas
queda **sin ninguna amenaza sin control**.

- [x] **D-3 hecha** 2026-08-05 — US-194, ADR-020, mig **0100**. El `sed` sí
  resolvió las 259; lo caro fueron los **siete sitios donde `wbs` no era nuestro
  campo**, y uno (`plan-wbs-level` de `localStorage`) rompía **sin dar error**.
- [x] **Fase `cancelled` hecha** 2026-08-05 — US-195, ADR-022, **sin
  migración** (`phase` es `String(32)` sin `CHECK`). `ACTIVE_PHASES` ahora se
  deriva del vocabulario. `initiation`: descartada por el owner.
- [ ] **Paleta de gráficos propia** — owner 2026-08-05. Ni la de marca ni la de
  Tailwind: categórica, accesible y distinta del semáforo a propósito.
- [ ] **Cerrar las ventanas de compatibilidad** cuando el contador lo permita.
  Se cuentan por `compat.nombre_viejo`; fichas en `core/compatibilidad.py`.

### Remediación de R1 — hecha el 2026-08-05

Detalle y residuales en `docs/conformidad/2026-08-05-mcs-remediacion.md`.
**LEN-02 queda como norma, no como tanda** (owner): la convención está en
`api-conventions.md` §7 y los 152 mensajes con texto propio se arreglan al tocar
cada endpoint. Sigue PARCIAL, declarado. **Tandas C/D/E: no se abren.**

### Glosario — implementación de las decisiones

**D-2, D-7 y D-9 hechas el 2026-08-05.** D-2 con ventana de compatibilidad: el
API sigue aceptando `support` y devuelve siempre `hypercare` (ADR-019, mig 0098).

**D-4 decidida en su forma: uno por dimensión** (2026-08-05), apoyada en las
cinco de US-191. Falta **calibrar los cinco valores** contra un proyecto real —
eso es dato, no decisión, y es lo único que queda del glosario.

> **Verificado el 2026-08-04:** los items que esta sección listaba como abiertos
> ya no lo estaban. US-168 #554 y ENH-115 #434 están **cerrados**, y la branch
> `claude/gantt-areas-fixes` no existe en el remoto — sus cuatro issues
> (#544-547) también están cerrados. Se quitan en vez de arrastrarlos.

### Conformidad (auditoría 2026-08-03)

> Estado por requisito en `docs/conformidad/plan.md`. **Las acciones del owner
> viven en `HANDOFF.md`**, no aquí: estaban en los dos sitios y una de las dos
> copias iba a envejecer (CTX-06). No consume IDs US/ENH/BUG.

**R1 cerrada el 2026-08-04** — los 13 NO VERIFICABLE medidos
(`docs/conformidad/2026-08-04-mcs-r1.md`). Cuatro no eran trabajo pendiente.

**Siguiente:** nada de conformidad. Se volvió al producto por decisión del owner.

---

## 📦 Deferred, DONE y Backlog v2.0

Viven en [`SPRINT-BACKLOG.md`](SPRINT-BACKLOG.md) — se abren al planear, no al
ejecutar. El historial narrativo sigue en `SPRINT-DONE-HISTORY.md`.

---

## Notas y cambios recientes

> Histórico narrativo en `SPRINT-DONE-HISTORY.md`.

- **2026-08-03 (auditoría de conformidad + remediación):** MCA y MCS auditados
  (`docs/conformidad/`: cuatro informes + plan). **PR #573**, CI verde.

  **MCA 10/11** — contexto permanente −43 %, comandos de verificación
  ejecutables, tres controles nuevos en CI. **MCS 9/126**, no alcanza N1.

  La Tanda A cerró tres de las cuatro exposiciones críticas. Los escáneres, en
  su primer día: una vulnerabilidad real de XML en el importador (archivo del
  usuario a un parser sin defensa), 10 de 23 CVE de Python cerradas —6 de
  subida de archivos, 2 de JWT— y la crítica de Next.js. **B1**: suite de
  aislamiento entre inquilinos, verificada por mutación.

  Detalle completo en `docs/conformidad/plan.md` y en el PR.

---

## Instrucción para Claude Code

Cuando arranques una sesión nueva:

1. Lee `docs/project-management/HANDOFF.md` PRIMERO.
2. Luego `CLAUDE.md` + este archivo + el epic referenciado en IN-PROGRESS.
3. Mueve la siguiente US/ENH/BUG de **INBOX** (marcada `status:ready`) a **IN-PROGRESS** antes de empezar.
4. Cambia label del issue: `status:ready` → `status:in-progress`.
5. Implementa con tests verdes + typecheck (comandos en la skill `verificar`).
6. Commit con header `<tipo>(<scope>): <ID> — <desc> (refs #<issue>)` y push.
7. Cambia label → `status:fix-committed` + comment con template CLAUDE.md §3 paso 6.
8. Mueve item a DONE en este archivo o a la tabla histórica si cierra sprint.
9. Resumen de ronda al owner siguiendo CLAUDE.md §11.
10. Al cierre de sesión: invocar `/handoff` para limpiar este archivo y dejar bridge.

**Regla sagrada:** 1 US = 1 commit. No mezclar varios IDs en el mismo commit.

**Regla post-Sprint 26 (decisión owner 2026-05-22):** desarrollo secuencial puro. 1 sesión activa, 1 lane, 1 branch. Migraciones consecutivas sin paralelización.
