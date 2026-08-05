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
Sin US activa. La sesión del 2026-08-05 cerró su branch; el owner mergea.

REMEDIACIÓN POR OLAS — plan en `docs/conformidad/plan-remediacion.md`.
Olas 0 y 1 cerradas. **Lo siguiente es la Ola 2**, mecánica y disparable sola.

MCA: N2, su objetivo, 11/11. Nada pendiente.
MCS: N0 · 29 cerrados de 126 · **44 bloquean N1** · 97 abiertos.
**`MCS-CORE` ya está en el repo** (`docs/conformidad/marco/`).
```

> **¿Próximo ID libre?** `python scripts/proximo_id.py`. Se deriva de GitHub +
> `git log` + docs; ya no se almacena aquí (MCA CTX-03). Corrélo contra
> `origin/main` actualizado.

---

## 📥 INBOX / TRIAGE

### 🌊 Las olas — orden de ejecución

El plan completo, con el registro de los 97 abiertos y la evidencia por
requisito, está en **`docs/conformidad/plan-remediacion.md`**. El estado se
recalcula con `python scripts/registro_conformidad.py` (no se almacena: CTX-03).

- [x] **Ola 0 — hecha el 2026-08-05.** De **45 a 41** bloqueantes de N1 sin
  escribir una línea de producto: `ARQ-02`, `GOB-02`, `LEN-01` y `DAT-05`
  estaban cerrados y el registro no se había enterado. `DAT-06` trajo la
  sorpresa que justifica la ola: parecía un `sed` y esconde un **cambio de
  contrato**. `DAT-08` y `DAT-16` **no se pudieron medir** — sin `MCS-CORE` no
  se sabe qué preguntarles. Informe: `docs/conformidad/2026-08-05-ola0-recuento.md`.
- [x] **Ola 1 — hecha el 2026-08-05.** El owner protegió `main`: 8
  verificaciones exigidas en `strict`, sin force-push ni borrado. `CFG-03` e
  `INT-03` cierran; **la distancia a N1 baja de 47 a 45**. `contraste-wcag`
  entró a las exigidas —son nueve— y `enforce_admins` **se queda en `false`**
  por decisión del owner, con el residual escrito.
- [ ] **Ola 2 — 13 mecánicos, se pueden disparar solos**, uno por commit con
  prueba y verificación por mutación: `DAT-12` (77 puntos), `DIS-03` (73 de 75
  pantallas), `DIS-01` (25 literales), `DAT-04` (6 sitios), `DAT-02`, `DAT-11`,
  `OPS-01`, `DEV-04`, `CFG-04`, `SEG-05`, `DOC-01`, `DOC-03`, `LEN-02`.
- [ ] **Ola 3 — necesita postura del owner antes de tocar código.** Alcance de
  competencia (`CON-01/03/05`), escenarios de calidad con medida (`REQ-02`),
  inventario de datos personales (`REQ-03`), fichas de indicador
  (`DAT-01/DAT-10`), almacén de secretos (`SEG-02`), estrategia de pruebas
  (`DEV-02/03` — hoy **cero** en frontend), artefacto de canalización
  (`SUM-01`), entornos y copias (`INF-02/03`, `DES-02`).
  **Aparte: `SEG-04`**, CRÍTICA — autorización verificada en el punto de acceso
  y no sobre el objeto. Es trabajo de seguridad, no una declaración.
- [ ] **Ola 4 — de N1 a N2.** Sin planificar a propósito: se replanifica al
  alcanzar N1, con el registro ya remedido. Estimación del expediente: 3-4
  semanas persona a N1, 8-12 a N2.

### Producto — abierto

- [ ] **Cerrar las ventanas de compatibilidad** cuando el contador lo permita.
  Se cuentan por `compat.nombre_viejo`; fichas en `core/compatibilidad.py`.
  Tres abiertas: `phase=support`, `portfolio_function`, `wbs`.
- [ ] **Contrastar los umbrales de D-4 contra cartera real.** Los valores de
  US-196 son razonados, no medidos; se ajustan en `settings`, sin tocar código.
- [ ] **`design-system/tokens.md`** describe una paleta anterior a D-7 y
  ADR-023. Declarado obsoleto, no corregido.
- [ ] **Línea base** (D-6), sin la cual «desviación» no tiene referente, y
  **DCMA 14-point**. Épica propia, sin abrir.

> **El glosario no tiene ninguna decisión abierta.** Las nueve ejecutadas
> (`docs/dominio/03-REVISION-GLOSARIO.md`). El modelo de amenazas tampoco tiene
> ninguna sin control.

---

## 📦 Deferred, DONE y Backlog v2.0

Viven en [`SPRINT-BACKLOG.md`](SPRINT-BACKLOG.md) — se abren al planear, no al
ejecutar. El historial narrativo sigue en `SPRINT-DONE-HISTORY.md`.

---

## Notas y cambios recientes

> Histórico narrativo en `SPRINT-DONE-HISTORY.md`.

- **2026-08-05 (auditoría + producto):** siete commits sobre
  `claude/audit-continuation-fzrtko`, más los de #577. **MCA alcanza N2** con
  AUT-01 cerrado por evidencia observada. En producto: `wbs_code`, fase
  `cancelled`, umbrales de D-4 y paleta de gráficos (ADR-020 a ADR-023).

  Lo que la medición no veía: los informes salían en DejaVu Sans desde hacía
  meses, PyJWT 2.10.1 cambiaba cinco CVE por siete, la migración 0098 escribía
  en una tabla inexistente con una prueba que fijaba el literal del código, el
  presupuesto del semáforo no miraba el tiempo, y el worker no reportaba a
  Sentry. Detalle en `SPRINT-DONE-HISTORY.md`.

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
