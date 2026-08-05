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
Sin sesión activa. PR #575 MERGEADO el 2026-08-04. **PR #576 ABIERTO, CI verde,
esperando merge del owner** (branch `claude/cap01-y-recuento`).

#575 cerró: R1 completa (13/13 medidos), guard AUT-01 con trinquete de 24 casos,
glosario aprobado, ADR-018 (ARQ-03 excluido), IA-04 conforme, CON-04 mitigado.
#576 cierra CAP-01 y corrige el recuento de R1. **Con su merge, MCA alcanza N2.**

MCS sigue en N0: 22/126 conformes, **51 requisitos bloquean N1**.

Próximo paso — recorrer lo pendiente de una corrida, dejando las
confirmaciones del owner para el final. Ver HANDOFF.md.
```

> **¿Próximo ID libre?** `python scripts/proximo_id.py`. Se deriva de GitHub +
> `git log` + docs; ya no se almacena aquí (MCA CTX-03). Corrélo contra
> `origin/main` actualizado.

---

## 📥 INBOX / TRIAGE

> Solo lo **abierto**. Lo cerrado se archivó a `SPRINT-DONE-HISTORY.md`
> el 2026-08-03.

### Siguiente batch

- [ ] **ENH-202** — Helvetica en TODOS los exports y reportes. Cuatro frentes:
  XLSX de backend (openpyxl), PDFs (WeasyPrint, CSS base de `templates/pdf/**`),
  DOCX del charter y ExcelJS del frontend. El plan ya la usa vía US-193, así que
  hay de dónde copiar la convención.

### Remediación barata de R1 (sin IDs; conformidad)

- [ ] **SUM-02** — `USER` sin privilegios en `apps/api/Dockerfile`. 3 líneas.
- [ ] **DES-03** — `SELECT 1` con tiempo límite en `/health`. 10 líneas.
- [ ] **LEN-02** — los seis textos por defecto de `app/core/errors.py`.
- [ ] **DIS-02 + D-7** — retocar 5 tokens de `globals.css` y unificar las dos
  paletas de salud. **Son el mismo trabajo**: el verde que falla AA es el del
  semáforo. Enganchar después `scripts/check_contraste.py` al CI.
- [ ] **AM-09** — límite por IP en `/auth/login`. El limitador ya existe y se
  aplica en recuperación y reseteo; falta en el login.

### Glosario — implementación de las decisiones (D-3, D-8, D-9)

- [ ] **D-3** `tasks.wbs` → `wbs_code` · **D-8** `portfolio_function` · ambas
  tocan contrato: ADR + US propia, una por una.
- [ ] **D-9** validar `is_milestone ⟹ duration_days = 0`.
- [ ] **D-2** decidir el nombre de la fase de hypercare (`support` o renombrar) y
  si hacen falta `initiation` y `cancelled`.

> **Verificado el 2026-08-04:** los items que esta sección listaba como abiertos
> ya no lo estaban. US-168 #554 y ENH-115 #434 están **cerrados**, y la branch
> `claude/gantt-areas-fixes` no existe en el remoto — sus cuatro issues
> (#544-547) también están cerrados. Se quitan en vez de arrastrarlos.

### Conformidad (auditoría 2026-08-03)

> Estado por requisito en `docs/conformidad/plan.md`. **Las acciones del owner
> viven en `HANDOFF.md`**, no aquí: estaban en los dos sitios y una de las dos
> copias iba a envejecer (CTX-06). No consume IDs US/ENH/BUG.

**R1 cerrada el 2026-08-04** — los 13 NO VERIFICABLE medidos, ninguno queda sin
estado (`docs/conformidad/2026-08-04-mcs-r1.md`). Cuatro de los trece no eran
trabajo pendiente: IA-01 ya era NO APLICABLE, IA-04 y las decisiones CON-04 y
ARQ-03 (excluido con ADR-018) se cerraron el mismo día. En **PR #575**.

**Siguiente:** lo barato de R1 —SUM-02, DES-03, LEN-02 y DIS-02, que se cruza
con la decisión D-7 del glosario— antes de las Tandas C/D/E.

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
