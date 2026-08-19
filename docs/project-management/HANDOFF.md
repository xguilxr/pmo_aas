# HANDOFF.md — Estado para la próxima sesión

**Última actualización:** 2026-08-19
**Branch activa:** `claude/handoff-development-2awr5v`
**Generado por:** /handoff

---

## 🎯 Dónde estamos parados

Bloque **Reestructura-W1** terminado: la jerarquía es `organización → portafolio
⊃ programa → proyecto` (ADR-037) y el vocabulario del proyecto está en español
con el tipo como enum (ADR-038). Doce commits pusheados, **PR #594** abierto
contra `main` y esperando verificación. Nada mergeado todavía; las migraciones
`0105`–`0111` siguen sin desplegar.

## 📍 Dónde retomar

Verificar el PR **#594** (CI y recorrido de UI), cerrar los issues **#588–#592**
y desplegar. Después, **Reestructura-W2** con la «Guía de sesiones» de
`docs/epics/drafts/reestructura-plan.md`.

## ✅ Hecho en esta sesión

- **US-198** `27b6ae9` — tabla `portfolios`, `programs.portfolio_id` NOT NULL,
  regla de consistencia en `services/jerarquia.py`. Mig. 0108.
- **US-199** `c529085` — CRUD `/portfolios`; BU/departamentos fuera de la API.
  Mig. 0109 (suelta 7 columnas FK).
- **US-202** `3253338` + `0f2d167` — fases al español y `type` como enum, con
  catálogo único y 5 ventanas de compat. Mig. 0110.
- **US-200** `f3f1063` — UI de la jerarquía: acordeón, árbol de 5 niveles,
  selects anidados.
- **US-201** `3c066f6` — cascada org → portafolio → programa en el tablero, las
  vistas cross y los snapshots.
- **Limpieza** `ea5710b` `c36d208` `399fe0f` `0bdcf8c` `92c9882` `f155f40` —
  ENH-190 retirada (DEC-032, mig. 0111), vocabulario duplicado unido, 675 líneas
  huérfanas fuera, 20 documentos al día.

Detalle narrativo en `SPRINT-DONE-HISTORY.md` (ronda 2026-08-19).

## 🔄 PRs abiertos

| # | Branch | Estado CI | Acción pendiente |
|---|---|---|---|
| #594 | `claude/handoff-development-2awr5v` | recién abierto | verificar y mergear |

## ⚠️ Gotchas y decisiones

- **El job `heavy` solo corre al pushear a `main`.** US-199 rompió un test heavy
  y la suite normal no lo vio durante tres commits. Arreglado en `399fe0f`, pero
  vale la pena decidir si ese job debe correr también en los PRs.
- **El contador de compat tiene un hueco**: `GET /projects` no normaliza ni
  registra `phase`/`type`, así que no ve a quien filtra con el nombre viejo.
  Taparlo **antes** de cerrar esas ventanas.
- Las tablas `business_units`/`departments` se quedan en el esquema hasta W8, a
  propósito: un `drop` es irreversible y no se paga en la misma oleada.
- Los campos de texto `business_unit`/`department` de la solicitud **no** son la
  jerarquía y se conservan («Área que solicita», «Equipo o sub-área»).

## 📋 Lo que sigue

Detalle en `SPRINT.md` → INBOX.

- Desplegar `0105`–`0111` y verificar #594.
- Los nueve follow-ups listados en #594 (superficie de API sin pantalla, cadena
  de permisos muerta, rutas sin enlace).
- **W3** RLS de Postgres · **W8** el `drop` de BU/departamentos.

## 📚 Estado de las epics docs

| Epic | Sincronizada | Notas |
|---|---|---|
| EP002 | sí | jerarquía nueva; US-002/003/004 marcadas retiradas |
| EP003 | sí | clasificación de la solicitud y del acta |
| EP004 | sí | endpoints, US-201 y los 5 scopes de snapshot |
| EP005 | sí | vocabulario US-202 |
| EP007 | sí | US-024 marcada RETIRADA, la sustituye US-200 |
| EP010 | sí | counts del detalle de inquilino |

## 🧹 Cleanup técnico pendiente (owner)

- [ ] Verificar y mergear **#594**; cerrar **#588–#592**.
- [ ] Desplegar `0105`–`0111`; leer el registro de `0110` y `0111`.
- [ ] Decidir los nueve follow-ups de #594.
- [ ] Decidir si el job `heavy` corre en los PRs.

## 🔮 Para sesiones futuras (sin issue)

- Deduplicar la suite de tests: `_FakeRedis` ×7, `_build_xlsx` ×6 y el helper
  `_admin(...)` reimplementado en 30 archivos.
- Reescribir `design-system/tokens.md` contra la paleta vigente (D-7, ADR-023).

---

## Cómo retomar

1. Lee este `HANDOFF.md`.
2. Luego `CLAUDE.md` + `SPRINT.md` + el epic en flight.
3. Continúa desde «Dónde retomar».
