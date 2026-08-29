---
tipo: gestion
responsable: propietario
estado: borrador
revisado: 2026-08-29
revisar_cada: 30d
---

# Reestructura de plataforma — lo que queda del plan de reconstrucción

> Plan derivado de `reestructura-conceptos.md`. **Reescrito el 2026-08-29**:
> las Fases 0-3 y los bloques B1-B8 se ejecutaron en su totalidad entre
> 2026-08-19 y 2026-08-27 y se retiraron de este documento — su detalle
> histórico vive en `docs/archive/epics/drafts-ejecutados/` y en las epics
> que absorbieron cada pieza. Lo que sigue aquí es **solo lo que no se ha
> construido**.

## Qué ya se ejecutó, y dónde quedó

| Fase / bloque | Qué era | Dónde vive hoy |
|---|---|---|
| Fase 0-2 (inventario, modelo de datos, navegación) | Planeación previa a construir | `docs/archive/epics/drafts-ejecutados/reestructura-{inventario,navegacion}.md` |
| B1 — Jerarquía + membresía + shift de org | Portafolio⊃Programa, `user_tenant_membership`, header de organización | `EP002-org-hierarchy.md`, ADR-037/038, US-198-205, US-214 |
| B2 — Recursos con capacidad/FTE | Tarifa congelada, asignación con periodo | `EP017-project-directory.md`, US-215 |
| B3 — Vista maestra + dashboard ejecutivo | `/pmo`, `/dashboard` | US-206, US-207 |
| B4 — Snapshot + salud + historial | Cortes periódicos, semáforo 5+1 | US-213, `services/project_health.py` |
| B5 — Importación masiva | Proyectos y recursos por organización | US-216 |
| B6 — Artefactos, minutas→RAID, cambios, organigrama | Renombres y flujos de módulo | `EP018-documents-artifacts.md`, `EP019-changes-approval.md` |
| B7 — Dependencias entre proyectos | Dependencias FS/SS/FF/SF cruzando proyectos | US-218 |
| B8 — Heatmaps, boards, RACI, alertas | `/pmo/resources`, `/pmo/board`, RACI | US-208, US-217, US-219 |

**Una pieza de B1 quedó fuera**: RLS de Postgres. No se ejecutó con el resto
—es la única de la fila marcada P0 que sigue abierta— y ya tiene sus propios
issues (#599-#601, ver `SPRINT.md`). No se repite aquí para no duplicar el
punto de seguimiento.

## Lo que sigue sin construir

| Bloque | Contenido | Estado real (2026-08-29) |
|---|---|---|
| B9 | IA: BYOK + roles de agente + reportes especializados | BYOK ya existía. El resto es `EP021-catalogo-de-ia.md`: US-224 (catálogo de plantillas) entregada; quedan US-223 (contexto), US-225 (roles de agente) y US-226 (herramientas de lectura) |
| B10 | Plan de suscripción con enforcement de límites | US-221 entregó el plan de solo lectura (`enforced: false`, la pantalla lo dice a propósito). El enforcement real —bloquear al llegar al tope— no se ha construido |
| B11 | What-if, forecast, priorización avanzada, automatización de reportes | Sin empezar. Sin US ni diseño |

## Riesgos que siguen vigentes

- **Alcance de B11**: what-if/forecast es la pieza más grande y menos
  definida que queda; necesita su propia sesión de diseño antes de un
  `triage`, no es directamente accionable como está descrito aquí.
- **B10 sin enforcement**: mientras el plan siga sin hacerse cumplir, un
  tenant puede pasarse de su tope sin que nada lo note más que la pantalla.
  No es un defecto — es la decisión declarada de US-221— pero es el motivo
  por el que B10 sigue en esta lista.

## Guía de sesiones de desarrollo (eficiencia de contexto)

Objetivo: que ninguna sesión re-explore lo que la planeación ya destiló.

**Receta por sesión (1 sesión = 1 US):**

1. Carga estándar de `CLAUDE.md` §1 (HANDOFF, SPRINT, índice de epics,
   LESSONS) — nada más por default.
2. Abrir el issue de la US (tiene AC, TC y archivos a tocar) y **solo** los
   docs que nombra:
   - Backend → `docs/architecture/mapa-backend.md` (tablas, routers,
     scoping, services — sin re-leer modelos completos).
   - Frontend → `docs/architecture/mapa-frontend.md` (rutas, componentes
     reutilizables, tokens) + el mockup/wireframe de la pantalla en el
     canvas «Mockups Reestructura PMO».
   - Diseño de la oleada → la sección relevante de
     `reestructura-modelo-datos.md` (no el archivo entero).
3. Leer solo las secciones de código que la US toca (mapa → archivo →
   sección); sub-agentes únicamente para research amplio (skill `delegar`).
4. Cerrar con `cerrar-item` + actualizar la fila del mapa si el componente
   cambió (mismo commit) + `handoff` al terminar la sesión.

**Los mapas son contrato**: si un mapa contradice el código, gana el código
y la sesión corrige el mapa en su commit. Así el costo de exploración se
paga una vez.

**Modelo por tipo de sesión** (Claude Code) — sigue aplicando a B9-B11:

| Sesión | Modelo | Por qué |
|---|---|---|
| US con migración/diseño (RLS, B11) | Opus 5 | Decisiones irreversibles y razonamiento largo |
| US de implementación estándar | Opus 5 | Balance calidad/costo; effort `xhigh` (default de Claude Code) |
| US mecánica acotada (renames, docs, UI simple) | Sonnet 5 | Suficiente y más barato |
| Sub-agentes de research/inventario | Haiku 4.5 o Sonnet 5 | Trabajo mecánico (skill `delegar`) |
