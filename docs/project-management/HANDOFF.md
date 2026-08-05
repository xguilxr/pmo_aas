# HANDOFF.md — Estado para la próxima sesión

**Última actualización:** 2026-08-05
**Branch activa:** `claude/audit-continuation-fzrtko` — reiniciada sobre `main`; #578 y #579 mergeados
**Generado por:** `/handoff`

---

## 🎯 Dónde estamos parados

**MCA alcanzó N2**, su objetivo: 11 de 11 CONFORME. Nada pendiente en ese marco.
**MCS sigue en N0** — 30 cerrados de 126, **43 bloquean N1**, 96 abiertos.
**`MCS-CORE` llegó al repo**: al verificar contra él, tres de los seis cierres de
las Olas 0 y 1 no se sostuvieron.

Plan por olas en **`docs/conformidad/plan-remediacion.md`**; el marco, en
`docs/conformidad/marco/MCS-CORE.md`.

## 📍 Dónde retomar

**Ola 2 del plan: los mecánicos**, disparables sin supervisión, uno por commit.
Empezar por los que tienen el hueco contado: `DAT-12` (77 puntos), `DIS-03` (73
de 75 pantallas), `DIS-01` (25 literales), `DAT-04` (6 sitios).

## ✅ Hecho en esta sesión

Siete commits, uno por item, todos verificados por mutación:

| SHA | Qué |
|---|---|
| `3b6a37f` | **US-194** `tasks.wbs` → `wbs_code` (D-3, ADR-020, mig **0100**) |
| `8029acf` | **US-195** fase `cancelled` (ADR-022, sin migración) |
| `c1a30b5` | **US-196** D-4: índice de consumo + pisos de amarillo |
| `15d0a7a` | **US-197** paleta de gráficos, arco frío (ADR-023) |
| `7d021c8` | **AUT-01** cierra con evidencia observada → MCA a N2 |
| `39386c7` | **OPS-02** el worker no reportaba a Sentry |
| `8b57694` | Plan de remediación + `scripts/registro_conformidad.py` |

Detalle narrativo archivado en `SPRINT-DONE-HISTORY.md`.

## 🔄 PRs abiertos o en flight

| # | Branch | Estado CI | Acción |
|---|---|---|---|
| #578 | `claude/audit-continuation-fzrtko` | verde | ✅ **mergeado** — lo grueso |
| #579 | `claude/audit-continuation-fzrtko` | verde | ✅ **mergeado** — Ola 1 |

**Una branch sin PR abierto no tiene CI.** `main` exige nueve verificaciones.

## ⚠️ Gotchas y decisiones recientes

- **El registro envejece en las dos direcciones**, y remedir antes de construir
  es la regla que ordena el plan.
- **Medir contra la evidencia anotada, y no contra el requisito, produce
  cierres que no aguantan.** Pasó con `CFG-03`, `INT-03` y `ARQ-02`. Ahora que
  `MCS-CORE` está en el repo, se cierra leyendo el texto.
- **`enforce_admins: false` mantiene `CFG-03` e `INT-03` abiertos**, los dos N1.
  La decisión del owner sigue en pie; lo que cambió es que ahora se sabe que
  **N1 no se alcanza sin ponerlo en `true`**.
- **Las migraciones 0097-0100 no las corre Alembic aquí** (guard). Su SQL se
  ejercita contra el esquema de `Base.metadata`, **no contra tablas a mano**:
  así se coló `UPDATE lessons_learned` en 0098.
- **Una prueba que fija el literal del código fuente no puede fallar.** Pasó dos
  veces esta sesión —D-2 y OPS-02—; las dos las cazó la verificación por
  mutación, no la lectura.
- **El guard bloquea comandos que *mencionan* un patrón denegado**, aunque sea
  dentro de un texto. Se reformula, no se relaja.
- **`RATE_LIMITED` pasó de 422 a 429**, ya en `api-conventions.md`.
- La suite tarda ~2m50s con `-n auto`. Sin pruebas de frontend. Python 3.12 no
  es negociable.

## 📋 Lo que sigue

Detalle en `SPRINT.md` → INBOX y en `plan-remediacion.md`.

- **Olas 0 y 1** — cuatro cerrados: `GOB-02`, `LEN-01`, `DAT-05` y `ARQ-02`
  (este último tras promover 5 decisiones irreversibles a ADR-024..028).
  `CFG-03` e `INT-03` **siguen PARCIAL**: los cierra `enforce_admins: true`.
- **Ola 2** — 13 mecánicos, disparables sin supervisión, uno por commit.
- **Ola 3** — 8 grupos que necesitan postura del owner; aparte `SEG-04`.
- **Ola 4** — N1 → N2, se replanifica al llegar.

## 📚 Estado de las epics docs

| Epic | Sincronizada | Notas |
|---|---|---|
| EP005 | sí | Fases (`cancelled`) e índice de consumo del semáforo |
| EP009 | sí | `wbs_code` y el diagrama de transiciones |
| EP014 | sí | Tipografía de los entregables (ENH-202) |

Al día también: `DB-CHANGES.md` (0100), ADR-019 a ADR-023, glosario y su
revisión, `api-conventions.md`, `modelo-amenazas.md`, `conformidad.yaml`.
**Ninguna epic queda desactualizada.**

## 🧹 Acciones del owner

- [ ] **Poner `enforce_admins` en `true`** — decidido el 2026-08-05. Es lo
      único que queda de las Olas 0 y 1, y cierra `CFG-03` e `INT-03`, ambos N1:
      `gh api -X PUT repos/xguilxr/pmo_aas/branches/main/protection/enforce_admins`
- [ ] **Correr las migraciones `0097`-`0100`.** Ninguna las corrió Alembic.
- [ ] **Confirmar Sentry en Railway:** tienen que salir **dos** líneas,
      `captura de errores activa proceso=api` y `proceso=worker`, cada una en su
      servicio. Con las dos, `OPS-02` cierra.
- [ ] Smoke de la web: plan (`wbs_code`), fase `cancelled`, y los gráficos que
      cambiaron de color (dashboard, Gantt, curva-S).
- [ ] Contrastar los umbrales de D-4 contra cartera real.

## 🔮 Para sesiones futuras (sin issue todavía)

- **`design-system/tokens.md`** describe una paleta anterior a D-7 y ADR-023.
- **Línea base** (D-6) y **DCMA 14-point**: épica propia.
- El owner tiene **cambios de diseño de producto** pendientes, a retomar cuando
  la auditoría deje de ser el frente activo.

---

## Cómo retomar

1. Lee este `HANDOFF.md` primero.
2. Luego `CLAUDE.md` + `SPRINT.md` + `docs/conformidad/plan-remediacion.md`.
3. `python scripts/registro_conformidad.py` da el estado. Arranca por la
   **Ola 2**, que es mecánica.
