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
| `/dashboard` | KPIs+charts tenant-wide con filtro org (→ se consolida con /pmo en dashboard ejecutivo) |
| `/pmo` | Panel portafolio del tenant (treemap/trends/heatmap, matriz salud, PDF status) |
| `/pmo/projects` (+`/new`, `[id]/edit`) | Lista maestra + alta/edición (`project-form.tsx`) |
| `/pmo/projects/[id]` + tabs | Detalle: `plan|tasks|gantt`, `raid`, `areas` (recursos), `documents`, `minutes|ai-minutes`, `reports|builder|tweak`, `changes`, `lessons`, `charter`, `ai-context` |
| `/pmo/organizations/[id]` (+`/reports`) | Panel org (tiene KPIs BU/depto†) |
| `/pmo/programs/[id]` (+`/reports`) | Panel programa |
| `/pmo/raid`, `/changes`, `/minutes`, `/reports` | Vistas cross con `TenantCrossFilters` |
| `/pmo/resources` | Capacidad/saturación (tabs personas/roles/áreas/conflictos) |
| `/pmo/requests` (+`/new`, `[id]`) | Solicitudes (`request-form.tsx` tiene BU/depto†) |
| `/admin/*` | tenant, ai, users, permissions, audit-logs, organizations (BU/depto† en `org-hierarchy-section.tsx`), areas |
| `/superadmin/*` | 8 pantallas plataforma |
| `/login`, `/reset`, `/forgot-password`, `/approve/[token]`, `/notifications`, `/account` | auth y transversales |

† = muere con la reestructura (W1 / US-199–201).

## Componentes reutilizables (components/)

- **Shell/nav**: `app-shell.tsx` (sidebar TOP_NAV + OrgTreeNav + admin nav;
  header 60px sin switchers — el switcher tenant/org nuevo va aquí),
  `project-tabs-bar.tsx`, `module-shell.tsx` (lista+CRUD genérico por folio;
  ojo: `max-w-6xl` — soltar para vistas anchas), `org-tree-nav.tsx` (árbol
  org→prog→proy; se retira del sidebar en la reestructura),
  `frontera-de-permiso.tsx`.
- **Datos**: `ui/sortable-th.tsx` + `lib/hooks/use-sortable-rows.ts`,
  `inline-select-cell.tsx`, `tenant-cross-filters.tsx` (org/programa/
  proyecto → sumar portafolio). No hay tabla virtualizada ni column-pinning
  (la control tower lo necesitará).
- **Gráficos**: `dashboard-charts.tsx` — exporta `Pie, Bars, Gauge,
  TrendLines, RiskMatrix, Heatmap, Treemap, Legend, PALETTE, serieColor`
  (SVG propio). `kpi-card.tsx`.
- **Salud**: `health-panel.tsx` (`healthTone`, `HealthStatusCard`,
  `HealthDimensionMatrix` 5+1, `HealthWhyPanel`),
  `health-evaluation-modal.tsx`.
- **Plan**: `gantt-view.tsx`, `import-wizard.tsx`, `lib/plan-template.ts`
  (XLSX).
- **Boards**: `raid-kanban.tsx` (kanban DnD nativo, columnas=estados —
  base de project/portfolio boards).
- **Directory**: `directory/` (PersonPicker, ProjectAreaPicker,
  AreasAndTeamsPanel, TenantActorsPanel),
  `admin/user-scope-assignment-picker.tsx`.
- **UI base**: `ui/` (button, input, select, modal, badge, banner, skeleton,
  breadcrumb, estados Vacío/Cargando/Error/SinPermiso, marca-de-datos).
- **Forms de dominio**: `project-form.tsx`, `organization-form.tsx`,
  `request-form.tsx`, `program-modal.tsx`.

## API client (lib/)

`lib/api/*.ts` por dominio (organizations, requests, analytics, reports,
report-builder, superadmin, project-charters, …). `lib/auth-storage.ts`
guarda tenant activo (→ el contexto org activo nuevo vive aquí + JWT).
`lib/org-label.ts` (label configurable — precedente para renombrar niveles).
`lib/cn.ts` (clsx+tailwind-merge).

## Reglas al escribir UI

Tokens siempre (`var(--color-*)`), nada hardcodeado (CI). Estados
vacío/cargando/error/sin-permiso en toda vista. Vistas anchas (tablas,
heatmaps, gantt): sin `max-w-*`. Semáforo enlaza a su desglose
(`HealthWhyPanel`). Mockups aprobados de la reestructura: canvas «Mockups
Reestructura PMO» (páginas Mockups hi-fi + Wireframes).
