---
tipo: referencia
responsable: propietario
estado: vigente
revisado: 2026-08-19
revisar_cada: 90d
---

# Mapa de componentes — Frontend (`apps/web`)

> Para sesiones de desarrollo: qué existe y dónde, sin re-explorar. Derivado
> del inventario Fase 0 (2026-08-19). Se abre **bajo demanda** al tocar
> frontend. Actualizar la fila afectada en el mismo commit que la cambie.

## Stack

Next.js 15.5 App Router (rutas por carpeta en `app/`, grupo `(app)`
autenticado), React 19, todo `"use client"` (sin RSC de datos). Tailwind v4
con tokens CSS en `app/globals.css` (fuente de verdad; espejo de gráficos en
`apps/api/app/core/paleta.py`). Iconos lucide-react. Sin librería de charts
ni tablas: SVG y HTML propios. Export XLSX con exceljs en cliente; PDF en
backend. `@dnd-kit` solo en report builder. Fetch al API vía `lib/api/*.ts`.

## Tokens (globals.css) — los que se usan al escribir UI

DM Sans (`--font-sans`) · canvas `#F4F6FA` · surface blanca · chrome sidebar
`#182e4e` (texto `#C9D4EE`, activo `rgba(255,255,255,0.14)`) · acento
`#2A4DA0` · semáforo: ok `#007A4C`, warn `#9F5900`, danger `#BD3528` ·
gráficos categóricos (ADR-023, orden fijo): `#294c9f #008a9b #7c34a7
#ca62a1`; ordinal azul `#c4d1ec→#203d81`; neutral `#6F695A` · hairlines
`#E8E3D7` · radio tarjetas `--radius-xl: 10px`. CI vigila contraste
(`check_contraste.py`) y literales fuera de tokens (`check_tokens.py`).
`docs/design-system/tokens.md` está desactualizado — no usarlo como fuente.

## Rutas (grupo `(app)`)

| Ruta | Qué es |
|---|---|
| `/dashboard` | Tablero ejecutivo en 4 filas (US-206): 6 tarjetas · 3 listas «top» · 4 distribuciones · tendencia por corte + semáforo consolidado + historial de cortes (US-213). Cascada portafolio → programa en la URL (US-201); la organización viene del header (US-205). **No** se fusiona con `/pmo`: el mockup los mantiene separados, y desde US-207 enlaza allí en vez de repetir su tabla |
| `/pmo` | **Vista maestra** (US-207): tabla de ancho completo con **las 16 columnas** del mockup —«Compl.» con su checklist entró en US-210; «Próx. hito» y «Reporte», en US-211—, header y primera columna fijos, columnas configurables (`localStorage`), XLSX de lo visible, 4 filtros en la URL, edición inline de salud y prioridad. Debajo: matriz salud × dimensión + status PDF + reporte de salud XLSX. El treemap/heatmap/trends se fueron al tablero con US-206 |
| `/pmo/board` | **Portfolio Board** (US-219): proyectos por estatus de reporte en cuatro columnas de urgencia, con las decisiones pendientes como marcador. No se arrastra: el estatus es derivado |
| `/pmo/projects` (+`/new`, `[id]/edit`) | Lista maestra + alta/edición (`project-form.tsx`) |
| `/pmo/projects/[id]` + tabs | Detalle: `plan|tasks|gantt`, `raid`, `areas` (tab «Recursos»), `documents` (tab «Artefactos»), `minutes|ai-minutes`, `reports|builder|tweak`, `changes`, `lessons`, `charter`, `ai-context` |
| `/pmo/organizations/[id]` (+`/reports`) | Panel org (KPIs «Portafolios» y «Programas» desde US-201) |
| `/pmo/programs/[id]` (+`/reports`) | Panel programa |
| `/pmo/raid`, `/changes`, `/minutes` | Vistas cross con `TenantCrossFilters` |
| `/pmo/reports` | Cinco pestañas por nivel: PMO · Organizaciones · **Portafolios** (US-209) · Programas · Proyectos |
| `/pmo/resources` | Dos pestañas (US-208): **Catálogo** (las cuatro secciones de US-183: personas/roles/áreas/conflictos, con su ventana de tiempo) y **Capacidad** (heatmap persona×semana en % FTE, capacidad vs demanda, críticos compartidos, sugerencias) |
| `/pmo/requests` (+`/new`, `[id]`) | Solicitudes (`request-form.tsx` pide «Área que solicita» y «Equipo o sub-área»: texto libre, las palabras del solicitante — no la jerarquía) |
| `/admin/*` | tenant, ai, users, permissions, audit-logs, organizations (`org-hierarchy-section.tsx`: **Portafolio ⊃ Programa** desde US-200), areas |
| `/superadmin/*` | Pantallas de plataforma (listado en `navigation.md` §3.5) |
| `/login`, `/reset`, `/forgot-password`, `/approve/[token]`, `/notifications`, `/account` | auth y transversales |

## Componentes reutilizables (components/)

- **Shell/nav**: `app-shell.tsx` (sidebar en grupos con rótulo `GRUPOS_NAV`
  —Organización · Transversal— + admin nav, US-204; header 60px con el switcher
  de organización, US-205 — el de inquilino es US-214),
  `project-tabs-bar.tsx` (tabs «Recursos» y «Artefactos» desde US-204, rutas
  `/areas` y `/documents` sin cambio), `module-shell.tsx` (lista+CRUD genérico
  por folio), `frontera-de-permiso.tsx`.
  `org-tree-nav.tsx` **se borró en US-205**: la organización está en el header y
  el drill-down portafolio ⊃ programa vive en los filtros de cada vista.
- **Contexto de organización**: `organizacion-activa.tsx` (proveedor montado en
  `app/(app)/layout.tsx`; `activa` es lo elegido y `efectiva` lo que va a la
  consulta — ver `navigation.md` §2.0) y `switcher-de-organizacion.tsx`. Las
  pantallas leen con `useOrgFiltro()`; ninguna carga su propia lista de
  organizaciones para filtrar. Delante va `switcher-de-inquilino.tsx` (US-214),
  que se pinta solo con más de una membresía y **recarga la aplicación** al
  cambiar: cambiar de inquilino cambia organizaciones, proyectos, personas,
  marca, moneda y permisos, y re-consultar pantalla por pantalla dejaría media
  interfaz con datos del anterior. Los formularios sí conservan su `<Select>`: ahí
  la organización es un campo de lo que se crea.
- **Datos**: `ui/sortable-th.tsx` + `lib/hooks/use-sortable-rows.ts`,
  `inline-select-cell.tsx`, `tenant-cross-filters.tsx` (portafolio → programa →
  proyecto desde US-201, con la organización heredada del header desde US-205;
  cada nivel limpia los de abajo). No hay tabla virtualizada ni column-pinning
  (la control tower lo necesitará).
- **Capacidad**: `capacidad-semanal.tsx` — el heatmap persona×semana con su
  escala de cinco tramos, el desglose de celda (resuelto en cliente sobre las
  asignaciones que trae la fila) y los tres paneles de lectura.
- **Vista maestra**: `vista-maestra.tsx` — la tabla del control tower.
  Columnas declaradas como datos (`clave`/`etiqueta`/`orden`/`celda`/`texto`),
  así que el XLSX exporta exactamente las visibles. Header y primera columna
  `sticky`; la celda fija lleva fondo propio o se transparenta.
- **Cadencia**: `lib/cadencia-tenant.ts` — `useCadenciaDeReporte()` y
  `etiquetaDeCadencia()`. Llega con el branding, como la moneda.
- **Tablero ejecutivo**: `tablero-ejecutivo.tsx` — `TarjetaDeSalud` (3
  conteos + barra proporcional), `ListaTop` (las listas «qué mirar primero»),
  `SemaforoConsolidado` (5 dimensiones, cada una del peor color que aparece,
  con el conteo al lado). No están en `dashboard-charts.tsx` porque no son
  gráficos: saben qué significa un rojo.
- **Gráficos**: `dashboard-charts.tsx` — exporta `Pie, Bars, Gauge,
  TrendLines, RiskMatrix, Heatmap, Treemap, Legend, PALETTE, serieColor`
  (SVG propio). `kpi-card.tsx`.
- **Salud**: `health-panel.tsx` (`healthTone`, `HealthStatusCard`,
  `HealthDimensionMatrix` 5+1, `HealthWhyPanel`),
  `health-evaluation-modal.tsx`.
- **Plan**: `gantt-view.tsx`, `import-wizard.tsx`, `lib/plan-template.ts`
  (XLSX), `dependencias-externas.tsx` (US-218: las dependencias con otros
  proyectos, en panel y no como flechas del Gantt — una flecha necesita dos
  extremos en pantalla y el otro está en otro plan),
  `linea-base-plan.tsx` (US-212: capturar/comparar; sin línea base dice «la
  desviación es desconocida», no cero, y muestra las dos derivas — la del plan
  se puede reescribir, la real no).
- **Directorio del proyecto**: `directory/DirectoryView.tsx` (US-217: columna
  RACI ordenada por rango y franja que nombra a la A; US-215: columna de costo
  con la tarifa congelada, botón «Congelar tarifa» donde falta y el hueco
  nombrado — «sin tarifa» y «sin fechas o % FTE» llevan a acciones distintas),
  `directory/TenantActorsPanel.tsx` (US-215: tarifa **y su unidad de tiempo**,
  que la API tenía desde US-182 sin ninguna pantalla que la llenara).
- **Boards**: `raid-kanban.tsx` (kanban DnD nativo, columnas=estados —
  genérico: lo usan RAID y el Project Board),
  `app/(app)/pmo/board/page.tsx` (Portfolio Board por estatus de reporte, US-219
  — **no** se arrastra: el estatus es derivado y el recálculo lo devolvería a su
  sitio), `app/(app)/pmo/projects/[id]/board/page.tsx` (Project Board, US-219 —
  aquí **sí**, porque `tasks.status` lo declara una persona; el corte de la
  cadencia es una marca en la tarjeta, no una columna).
- **IA**: `app/(app)/admin/ai/page.tsx` (proveedor BYOK) + `consumo-de-ia.tsx`
  (US-222: trabajos y tokens por mes, reparto por modelo, fallidos junto al
  total; **sin cifra en pesos**, y la pantalla dice por qué). El resto del
  artboard de IA —skills, tools, prompts, workflows, roles de agente— está en
  `EP021-catalogo-de-ia.md` con las preguntas que lo bloquean.
- **Plan**: `app/(app)/admin/plan/page.tsx` (US-221: tier, topes y consumo; la
  pantalla **dice** que no se hace cumplir —si no, «3/1» con barra roja se lee
  como un bloqueo y genera una llamada de soporte por algo que no pasa—, y sin
  tope no dibuja barra).
- **Importación masiva**: `app/(app)/pmo/imports/page.tsx` (US-216: subir →
  validar → confirmar, con el reporte de tres estados por fila y la plantilla
  generada desde las columnas que declara el backend; la organización de destino
  viene del header, no de un selector propio).
- **Directory**: `directory/` (PersonPicker, ProjectAreaPicker,
  AreasAndTeamsPanel, TenantActorsPanel),
  `admin/user-scope-assignment-picker.tsx`.
- **UI base**: `ui/` (button, input, select, modal, badge, banner, skeleton,
  breadcrumb, estados Vacío/Cargando/Error/SinPermiso, marca-de-datos).
- **Forms de dominio**: `project-form.tsx`, `organization-form.tsx`,
  `request-form.tsx`, `program-modal.tsx`.

## API client (lib/)

`lib/api/*.ts` por dominio (organizations, requests, analytics, reports,
report-builder, superadmin, project-charters, …). **Vocabulario del proyecto**
(US-202 / ADR-038): `lib/api/projects.ts` declara `ProjectPhase`
(`preparacion|ejecucion|hypercare|cerrado|cancelado`), `ProjectType`
(`transformacion|operacion|innovacion|bau`), `PHASE_LABEL`, `PHASE_ORDER` y
`TYPE_LABEL`; `lib/api/modules.ts`, `LESSON_PHASE_*` (la fase `cerrado` se dice
«Cierre» en una lección). Los dos tipos están atados al backend por
`apps/api/tests/test_us202_vocabulario.py`, que lee este archivo: renombrar en un
lado y no en el otro deja el formulario mandando un valor que la API rechaza.
`lib/auth-storage.ts`
guarda tenant activo (→ el contexto org activo nuevo vive aquí + JWT).
`lib/cn.ts` (clsx+tailwind-merge).

## Reglas al escribir UI

Tokens siempre (`var(--color-*)`), nada hardcodeado (CI). Estados
vacío/cargando/error/sin-permiso en toda vista. Vistas anchas (tablas,
heatmaps, gantt): sin `max-w-*`. Semáforo enlaza a su desglose
(`HealthWhyPanel`). Mockups aprobados de la reestructura: canvas «Mockups
Reestructura PMO» (páginas Mockups hi-fi + Wireframes).
