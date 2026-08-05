# HANDOFF.md — Estado para la próxima sesión

**Última actualización:** 2026-08-05
**Branch activa:** `claude/audit-continuation-fzrtko` — 10 commits, **PR abierto**
**Generado por:** `/handoff`

---

## 🎯 Dónde estamos parados

**MCA alcanzó N2**, su objetivo: 11 de 11 CONFORME. Nada pendiente en ese marco.
**MCS sigue en N0** — 31 cerrados de 126, **45 bloquean N1**, 95 abiertos.
La **Ola 1 ya está hecha**: el owner protegió `main` el 2026-08-05.

El plan de remediación está escrito y ordenado por olas:
**`docs/conformidad/plan-remediacion.md`**. Se construyó sin `MCS-CORE` —no está
en este entorno— reconstruyendo el registro desde los cuatro informes fechados.

## 📍 Dónde retomar

**Ola 0 del plan: recontar.** Medio día, sin escribir código. No se salta y no
es ceremonia: el registro está desactualizado **en las dos direcciones**.

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
| #579 | `claude/audit-continuation-fzrtko` | corriendo | Esperar verde y mergear |

**Una branch sin PR abierto no tiene CI**: solo dispara en `pull_request` y en
push a `main`. `main` exige las **nueve** verificaciones, así que #579 no se
puede integrar en rojo.

## ⚠️ Gotchas y decisiones recientes

- **El registro de conformidad envejece en las dos direcciones.** A favor:
  `ARQ-02` y `GOB-02` decían «cero ADR reales» y hay 24. A la contra: `OPS-02`
  figuraba como «lo más barato que queda» y el worker no reportaba nada.
  **Remedir antes de construir** es la regla que ordena el plan.
- **`MCS-CORE` no está en este entorno.** El plan no lo usa. Lo que falta por
  eso es el criterio de aceptación por requisito: para los mecánicos el hueco
  medido **es** la vara; para los de juicio se declara al cerrar.
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

- **Ola 0** — recontar: los que nuestro trabajo pudo cerrar + los seis nunca
  medidos (`CON-04`, `DAT-08`, `DAT-16`, `DES-04`, `DIS-05`, `DIS-06`).
- **Ola 1** — ✅ cerrada entera (`CFG-03`, `INT-03`, y `contraste-wcag` exigido).
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

- [ ] **Mergear #579** cuando el CI cierre en verde.
- [x] ~~Proteger `main`~~ — hecho el 2026-08-05. `CFG-03` e `INT-03` cierran.
- [x] ~~Añadir `contraste-wcag` a las exigidas~~ — hecho el 2026-08-05. Son
      nueve; la **Ola 1 queda cerrada entera**.
- [x] ~~Decidir `enforce_admins`~~ — **se queda en `false`** (owner,
      2026-08-05). Residual aceptado y escrito: con un solo desarrollador, la
      salida de emergencia vale más que el trinquete. Se revisa si entra alguien
      más al repositorio.
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
3. Arranca por la **Ola 0**: `python scripts/registro_conformidad.py` da el
   estado, y la Ola 0 lo corrige contra el código de hoy.
