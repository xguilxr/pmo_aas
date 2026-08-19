---
tipo: gestion
responsable: propietario
estado: borrador
revisado: 2026-08-18
revisar_cada: 30d
---

# Reestructura de plataforma — Plan de reconstrucción

> Plan de trabajo derivado de `reestructura-conceptos.md` (mapa de conceptos
> + feedback del cliente de 23 proyectos). Principio rector: **no se empieza
> de cero** — la base PMO existente es buena; se reestructura el modelo
> jerárquico (Tenant→Org→Proyecto), se puliría el diseño, se simplifica la
> navegación y se agregan las dos capas faltantes: gestión ejecutiva de
> portafolio y capacity planning.

## Estado (2026-08-19) — planeación CERRADA, lista para construir

| Fase | Estado | Entregable |
|---|---|---|
| Fase 0 — Inventario | ✅ | `reestructura-inventario.md` |
| Fase 1 — Modelo de datos | ✅ | `reestructura-modelo-datos.md` (BU/depto: reemplazo directo, sin datos que mapear) |
| Fase 2 — Navegación y diseño | ✅ **wireframes aprobados por el owner** | `reestructura-navegacion.md` + canvas «Mockups Reestructura PMO» (hi-fi de 4 vistas + wireframes de todas las páginas) |
| Fase 3+ — Construcción | ▶️ lista | Bloque Reestructura-W1: US-198 #588 … US-202 #592, todos `status:ready` |

La construcción corre en sesiones nuevas: ver «Guía de sesiones» al final.

## Norte

1. De seguimiento operativo «proyecto por proyecto» → herramienta de
   decisión de portafolio (control tower + dashboard ejecutivo).
2. De catálogo de recursos → capacity planning real (FTE, periodos,
   heatmaps).
3. Jerarquía limpia: Tenant → Organizaciones → (Portafolio ⊃ Programa) →
   Proyectos, con usuarios multi-tenant y shift de organización.
4. Diseño pulido, navegación reestructurada, pantallas aprovechadas a lo
   horizontal, vistas simplificadas.

## Fase 0 — Inventario de reutilización (siguiente sesión)

Antes de diseñar nada: mapear lo que existe contra el árbol de conceptos.
Salida: matriz `existente → destino` con veredicto por pieza:
**reutilizar** · **adaptar** · **reescribir** · **retirar**.

- [ ] **Inventario de docs**: epics EP001–EP020 + drafts vs el árbol nuevo.
      Detectar qué epic describe cada concepto hoy y qué contradice la
      jerarquía nueva (ej.: EP002 modela org/BU/depto/programa — el árbol
      nuevo no tiene BU/depto y anida Programa bajo Portafolio).
- [ ] **Inventario de schema**: tablas actuales vs conceptos (tenant, org,
      portfolio, program, project, resource, user, roles, AI). Detectar
      dónde falta `tenant_id`/RLS, qué renombra (Documentos→Artefactos), qué
      tabla nueva hace falta (membresía user-tenant, snapshots, asignación
      con FTE/periodo, roles de agente IA, plan de suscripción).
- [ ] **Inventario de API/routers**: endpoints por módulo, cuáles sobreviven
      el cambio de jerarquía.
- [ ] **Inventario de UI**: pantallas/rutas actuales vs navegación nueva;
      qué componentes (tablas, Gantt, RAID, filtros, export) se reutilizan
      en las vistas nuevas.
- [ ] Revisar drafts existentes que ya apuntan aquí:
      `portfolio-recursos-capacidad.md`, `plan-import-revamp.md`,
      `feedback-16jul-mejoras.md`, `EP020-secciones-atomicas.md`.
- Método: sub-agentes de research para el barrido (CLAUDE.md §14); la
  matriz-veredicto la decide la sesión con el owner.

## Fase 1 — Modelo de datos objetivo

Con el inventario en mano, diseñar el schema destino y el camino de
migración (sin ejecutar migraciones todavía):

- [ ] Jerarquía: tenant, organización, portafolio, programa (FK a
      portafolio), proyecto (FKs opcionales con regla de consistencia
      portafolio-programa), fases del proyecto.
- [ ] Identidad: usuario global + `user_tenant_membership` + scope de
      visibilidad + vínculo usuario↔recurso. JWT con
      `active_tenant_id`/`active_organization_id`.
- [ ] RLS por `tenant_id` en Postgres para toda tabla tenant-scoped.
- [ ] Recursos: capacidad/FTE/costo a nivel recurso; asignación con
      periodo, FTE y costo-snapshot.
- [ ] Snapshots bi-semanales (proyecto y portafolio) — base de tendencias.
- [ ] Salud: dimensiones, pesos configurables, calculada vs declarada,
      historial.
- [ ] Completitud de datos por proyecto (campos mínimos, checklist).
- [ ] AI: skills/tools/prompts/workflows, config BYOK, roles de agente con
      permisos propios.
- [ ] Plan de suscripción (schema sin paywall; free = 1 org, 3 proyectos
      sumados por tenant).
- Entregables: `DB-CHANGES.md` + decisiones en `DECISIONS.md`/ADR (la
  reestructura de jerarquía es irreversible → ADR), estrategia de migración
  de datos productivos por pasos compatibles.

## Fase 2 — Navegación y diseño

- [ ] Mapa de navegación nuevo: shift tenant/organización arriba; a nivel
      organización el dashboard con filtros portafolio/programa; el detalle
      de proyecto con sus 8 módulos; admin (usuarios/roles/AI/plan) por
      tenant.
- [ ] Wireframes de las vistas nuevas: vista maestra de portafolio (control
      tower), dashboard ejecutivo, capacity (heatmaps), portfolio board /
      project board.
- [ ] Rediseño visual: pulir, simplificar vistas, aprovechar el ancho
      horizontal de las pantallas existentes. Incluye reescribir
      `design-system/tokens.md` contra la paleta vigente (pendiente ya
      anotado en SPRINT).
- Entregable: mockups aprobados por el owner antes de tocar frontend.

## Fase 3+ — Construcción por bloques

Orden propuesto (P0 del cliente mapeado sobre la reestructura; cada bloque
se convierte en epic/US con `triage` cuando llegue su turno):

| Bloque | Contenido | Prioridad |
|---|---|---|
| B1 | Jerarquía nueva + RLS + membresía multi-tenant + shift de org | P0 (base de todo) |
| B2 | Recursos con capacidad/FTE + asignación con periodo y costo-snapshot | P0 |
| B3 | Vista maestra de portafolio + dashboard ejecutivo (filtros portafolio/programa) | P0 |
| B4 | Snapshot bi-semanal + salud explicable + historial | P0 |
| B5 | Importación masiva (proyectos, planes, recursos) + completitud/onboarding | P0 |
| B6 | Módulos de proyecto: renombrar Artefactos, minutas→RAID, cambios manuales, organigrama derivado | P0/P1 |
| B7 | Gantt/roadmap consolidado + milestones ejecutivos + dependencias entre proyectos | P1 |
| B8 | Heatmaps de capacidad + boards + RACI/stakeholders + alertas | P1 |
| B9 | AI: BYOK + roles de agente + reportes especializados + lecciones periódicas | P1/P2 |
| B10 | Plan de suscripción (enforcement de límites; paywall después) | P2 |
| B11 | What-if, forecast, priorización avanzada, automatización de reportes | P2 |

Reglas vigentes: 1 US = 1 commit, migraciones secuenciales (1 sesión = 1
lane), CI verde + merge antes de la siguiente US, fases A–D con `triage` y
`cerrar-item`.

## Riesgos del plan

- **Migración de jerarquía sobre datos productivos**: el paso BU/depto →
  Portafolio⊃Programa necesita mapeo dato por dato y ventana de
  compatibilidad (patrón `core/compatibilidad.py` ya existente).
- **Alcance**: el feedback del cliente es grande; el árbol de conceptos del
  owner manda y lo del cliente entra como complemento priorizado (P0→P2).
- **23 proyectos del prospecto**: la importación masiva (B5) conviene
  temprano para no capturar a mano al onboardear.

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

**Orden de arranque** (dependencias del bloque W1):
US-198 → US-199 → {US-200, US-201 en paralelo solo si no comparten
archivos} y US-202 tras US-198. Migraciones siempre secuenciales, CI verde
y merge antes de la siguiente US (CLAUDE.md §8).

**Modelo por tipo de sesión** (Claude Code):

| Sesión | Modelo | Por qué |
|---|---|---|
| US con migración/diseño (US-198, W2, RLS) | Opus 5 (o Fable 5 si está disponible en el plan) | Decisiones irreversibles y razonamiento largo |
| US de implementación estándar (US-199–202) | Opus 5 | Balance calidad/costo; effort `xhigh` (default de Claude Code) |
| US mecánica acotada (renames, docs, UI simple) | Sonnet 5 | Suficiente y más barato |
| Sub-agentes de research/inventario | Haiku 4.5 o Sonnet 5 | Trabajo mecánico (skill `delegar`) |

## Próximo paso inmediato

Abrir sesión nueva y arrancar **US-198 #588** (modelo y migración de
Portfolio) siguiendo la receta de arriba.
