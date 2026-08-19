---
tipo: gestion
responsable: propietario
estado: vigente
revisado: 2026-08-19
revisar_cada: 30d
---

# HANDOFF.md — Estado para la próxima sesión

**Última actualización:** 2026-08-19
**Branch activa:** `claude/platform-restructure-concept-mapping-rjhzd7` (PR #593, docs puros, espera merge)
**Generado por:** /handoff

---

## 🎯 Dónde estamos parados

La planeación de la **reestructura de plataforma** está cerrada y aprobada
por el owner: árbol de conceptos, inventario de reutilización, modelo de
datos con oleadas W1–W8, navegación nueva y mockups/wireframes (canvas
«Mockups Reestructura PMO»). El bloque W1 (US-198 #588 … US-202 #592) está
en `status:ready`. Sigue pendiente de sesiones anteriores el despliegue de
migraciones `0105`–`0107` ya mergeadas.

## 📍 Dónde retomar (próximo paso accionable)

- Owner mergea PR **#593**; después, sesión nueva: **«Arranca US-198 #588
  con la guía de sesiones de reestructura-plan.md»** (branch nueva, 1 US =
  1 commit).

## ✅ Hecho en esta sesión (todo en `claude/platform-restructure-concept-mapping-rjhzd7`)

- `696ba9c` — mapa de conceptos + plan de reestructura (drafts).
- `8830e42` — Fase 0: inventario docs/schema/API/UI con veredictos.
- `12e7d84` — Fase 1: modelo de datos objetivo + migración W1–W8.
- `8a101c2` — issues US-198…202 (#588–#592) creados; bloque W1 en INBOX.
- `651eb7e` — Fase 2: mapa de navegación y especificación de vistas.
- `6438b01` / `f667946` — W1 a ready; plan final; **mapas de componentes**
  `docs/architecture/mapa-{backend,frontend}.md` + CLAUDE.md §1.
- Canvas de diseño publicado y aprobado: mockups hi-fi (dashboard
  ejecutivo, control tower, capacity, header con switchers) + wireframes de
  todas las páginas.

## 🔄 PRs abiertos o en flight

| # | Branch | Estado CI | Acción pendiente |
|---|---|---|---|
| #593 | claude/platform-restructure-concept-mapping-rjhzd7 | pending al cierre | merge (owner) |

## ⚠️ Gotchas y decisiones recientes

- **BU/Departamentos**: sin uso productivo (owner 2026-08-19) → Portafolio⊃
  Programa los reemplaza directo, sin mapeo de datos; drop en W8 con ADR.
- **No hay RLS real en Postgres** (ADR-003 nunca implementado): W3 lo
  materializa; hasta entonces el aislamiento es solo filtrado ORM.
- **Roles de agente IA ≠ RBAC de usuarios**: catálogo y permisos separados.
- Los **mapas de componentes son contrato**: si contradicen el código, gana
  el código y la sesión corrige el mapa en su mismo commit.
- Modelos por sesión: tabla en `reestructura-plan.md` (Opus 5 default).

## 📋 Lo que sigue (resumen; detalle en SPRINT.md → INBOX)

- **Bloque Reestructura-W1** (ready): US-198 → US-199 → {US-200, US-201} ·
  US-202 tras 198. Migraciones secuenciales, CI verde + merge entre USs.
- Luego oleadas W2+ según `reestructura-modelo-datos.md` §8 (cada una pasa
  por `triage` cuando toque).
- Pendientes previos: desplegar `0105`–`0107`, ventanas de compat, umbrales
  D-4, `tokens.md`, línea base D-6 (ver SPRINT.md).

## 📚 Estado de las epics docs

| Epic | Sincronizada | Notas |
|---|---|---|
| (todas) | sí | Sesión de docs puros; ningún commit cambió comportamiento. El diseño vive en drafts a propósito; EP002 se reescribe al implementar W1 (parte del cierre de esas USs). |

## 🧹 Cleanup técnico pendiente

- [ ] Mergear PR #593 (docs de planeación).
- [ ] Desplegar migraciones `0105`–`0107` (arrastrado; detalle y variables
      Railway en SPRINT.md — cierra todas las sesiones vivas).
- [ ] Heredados del debloat: exigir `tipos-python`/`commits` en main, hook
      `core.hooksPath .githooks`, confirmar Sentry.

## 🔮 Para sesiones futuras (sin issue todavía)

- Lecciones generadas periódicamente por IA (evaluar, quedó anotado en el
  mapa de conceptos).
- Export a PowerPoint de reportes (pedido del cliente de 23 proyectos; hoy
  solo PDF/XLSX).
- Escenarios what-if de capacidad, forecast y priorización avanzada (P2).
- TOTP como segundo factor primario (arrastrado).

---

## Cómo retomar

1. Lee este `HANDOFF.md` primero.
2. Luego `CLAUDE.md` + `docs/project-management/SPRINT.md`.
3. Para la reestructura: `docs/epics/drafts/reestructura-plan.md` (guía de
   sesiones) y el mapa de componentes del lado que toques — no re-explores.
4. Continúa desde el «próximo paso accionable» arriba.
