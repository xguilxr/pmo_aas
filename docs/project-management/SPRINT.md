---
responsable: propietario
estado: vigente
revisado: 2026-08-05
revisar_cada: 30d
---

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
Sin US activa. Branch `claude/remediacion-ola-2-2kg36x` — el owner abre el PR.

REMEDIACIÓN POR OLAS — plan en `docs/conformidad/plan-remediacion.md`.
Olas 0, 1 y **2 cerradas**. Lo siguiente necesita postura del owner (Ola 3).

MCA: N2, su objetivo, 11/11. Nada pendiente.
MCS: N0 · **32 bloquean N1** (eran 41) · una sola exclusión viva (ARQ-03).
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

- [x] **Olas 0 y 1 — hechas el 2026-08-05.** De 45 a 41 sin escribir producto
  (el registro no se había enterado de cuatro cierres), y `main` protegida.
  Detalle en `plan-remediacion.md` y en los informes fechados.
- [x] **Ola 2 — hecha el 2026-08-06.** De **41 a 32** bloqueantes, once commits
  con prueba y verificación por mutación. Cierran `SEG-05`, `OPS-01`, `DEV-04`,
  `CFG-04`, `DIS-01`+`CFG-14`, `DOC-01`, `DOC-03`, `DAT-04`+`DAT-08`, `DAT-12`,
  y `DAT-05` **vuelve a cerrar** — estaba CONFORME sobre una lista escrita a
  mano y quedaba una quinta paleta, en el acta que se firma. Siguen PARCIAL
  `DAT-06` (queda `amber_max`, es contrato) y `LEN-02` (177→169, con el
  mecanismo ya puesto). **`DAT-02`, `DIS-03` y `DAT-11` se reclasifican**: no
  son mecánicos, y ahora están medidos. Detalle en `plan-remediacion.md`.
- [ ] **Ola 3 — necesita postura del owner.** Alcance de competencia
  (`CON-01/03/05`), escenarios de calidad con medida (`REQ-02`), inventario de
  datos personales (`REQ-03`), fichas de indicador (`DAT-01/10`), almacén de
  secretos (`SEG-02`), estrategia de pruebas (`DEV-02/03` — hoy **cero** en
  frontend), artefacto de canalización (`SUM-01`), entornos y copias
  (`INF-02/03`, `DES-02`). **Aparte: `SEG-04`**, CRÍTICA — autorización sobre
  el objeto y no solo sobre el punto de acceso. Se le suman de la Ola 2:
  `DAT-02` (renombres con migración), `DIS-03` y `DAT-11` (épica de producto).
- [ ] **Ola 4 — de N1 a N2.** Se replanifica al alcanzar N1.

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

- **2026-08-06 (Ola 2):** once commits. Lo que la medición no veía: el acta en
  `.docx` se firmaba con la paleta anterior a DIS-02; once citas a tokens
  inexistentes hacían que la página de documentos pintara tema claro en modo
  oscuro y que la tabla de permisos saliera sin fondo; el gate de tipos daba
  verde sin analizar nada; el worker no configuraba su registro y Celery se lo
  llevaba por delante. Cuatro hallazgos, ninguno de leer código: los cuatro
  salieron de medir contra el texto del requisito.

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
