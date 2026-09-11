---
tipo: gestion
responsable: propietario
estado: vigente
revisado: 2026-09-11
revisar_cada: 30d
---

# FASE 8 — Reportes: pestañas RAID, Cambios y Organización

**Qué es.** `/pmo/reports` gana tres pestañas: RAID (one-page HTML + tabla
agrupada + Excel de todos los proyectos filtrados), Cambios (mismo patrón)
y Organización (snapshot del Dashboard + árbol). `/pmo/raid` y
`/pmo/changes` se absorben. Punto 7 de `../REVAMP-V2-FEEDBACK.md`.
Wireframe **W5**.
**Tamaño:** L. **Gate:** fase 7 mergeada, W5 aprobado, D6 (contenido del
reporte de Cambios) cerrada en W5. **Epics:** EP020 (report builder),
EP006 (módulos). Endpoints nuevos de exportación → `api-conventions.md`
si añaden un patrón.

**Reglas.** Cuatro commits. Los exports nuevos reusan los servicios
existentes; no se escribe un segundo generador de XLSX.

## Preparación

```bash
git fetch origin main
git checkout -b claude/revamp-v2-f8-reportes origin/main
pnpm install --frozen-lockfile
python scripts/proximo_id.py
```

## Hechos verificados

- `apps/web/app/(app)/pmo/reports/page.tsx` ya tiene pestañas
  `PMO | Organizaciones | Programas | Proyectos` (`TABS` :55, render
  :113-121; secciones en :128, :245, :368, :703). Ya filtra por
  organización (`useOrgFiltro`, :37-38).
- `/pmo/raid/page.tsx` y `/pmo/changes/page.tsx` listan con
  `listTenantRisks/Issues/Changes` de `lib/api/tenant-cross.ts` (:59-71),
  que desde la fase 2 reciben `organization_id`. Backend
  `tenant_cross.py` acepta además `portfolio_id` y `program_id`.
- Export RAID por proyecto: `GET /{project_id}/raid/export`
  (`project_artifacts.py:342`) → `apps/api/app/services/raid_export.py`,
  `export_raid_xlsx(*, risks_rows, actions_rows, incidents_rows, decisions_rows) -> bytes`
  (:190-196), filas construidas por `build_risk_rows` / `build_issue_rows`
  del mismo módulo.
- Export Cambios por proyecto: `GET /{project_id}/changes/export`
  (`project_artifacts.py:459`) → `change_export.py`,
  `export_changes_xlsx(rows) -> bytes` (:132).
- Fuente corporativa en XLSX: `tipografia.aplicar_a_workbook(wb)`
  (`apps/api/app/core/tipografia.py:41`); los dos exports ya la usan.
- `ChartCard` exportado en `components/chart-card.tsx` (fase 3, commit 4).

## Commit 1 — endpoints de exportación transversal (US-A)

**Archivo:** `apps/api/app/api/v1/endpoints/tenant_cross.py`.

1. `GET /raid/export` con los mismos `Query` que `/risks` y `/issues`
   (`organization_id`, `portfolio_id`, `program_id`). Cuerpo: reusa la
   consulta de `list_tenant_risks` (:89) y `list_tenant_issues` (:139) sin
   paginar; construye filas con `build_risk_rows` / `build_issue_rows`
   añadiendo al inicio de cada fila las columnas `Proyecto (folio)` y
   `Proyecto` (nombre) — mira la firma de `build_*_rows` y agrega el
   parámetro `prefijo: list[Any]` si no lo tienen; los callers por proyecto
   pasan `[]`. Devuelve `StreamingResponse` con `XLSX_MIME` y
   `Content-Disposition: attachment; filename="raid-<organizacion-slug>-<YYYY-MM-DD>.xlsx"`
   (el slug: `slugify` que ya use el repo, `grep -rn "def slug" apps/api/app`).
2. `GET /change-requests/export` igual con `export_changes_xlsx`.
3. Tests `apps/api/tests/test_<us>_export_transversal.py`: dos proyectos
   en organizaciones distintas → el export filtrado por una trae solo sus
   filas; el archivo abre con `openpyxl` y la primera hoja tiene la columna
   "Proyecto".
4. `modelo-amenazas.md`: no hay ruta nueva sin autenticación (usa el mismo
   `Depends` que `/risks`); no hay que tocarlo. Verifica que
   `test_seg06_modelo_amenazas` siga verde.

```
feat(api): US-A — export XLSX de RAID y Cambios de todos los proyectos filtrados
```

## Commit 2 — pestaña RAID (US-B)

**Archivo:** `pmo/reports/page.tsx`. Diseño W5.

1. Agrega `raid` a `TABS` (:55) con label "RAID". Sección nueva con tres
   bloques en orden:
   - **Filtros**: portafolio y programa (`Select` como en `pmo/page.tsx:428-487`);
     la organización viene del header.
   - **One-page** (`components/reports/raid-one-page.tsx`): cabecera con
     organización, filtros y fecha; KPI band de 4 (riesgos abiertos,
     severos, issues abiertos, decisiones pendientes) con `KpiCard`; la
     `RiskMatrix` (`dashboard-charts.tsx:448`) alimentada por
     `getRiskMatrix` con los mismos filtros; top 5 riesgos por severidad
     (`ListaTop`). Estilos de impresión: `@media print` que oculte sidebar
     y header (agrega la clase `print:hidden` a `<aside>` y `<header>` en
     `app-shell.tsx`) y botón "Imprimir / guardar PDF" →
     `window.print()`.
   - **Tabla agrupada**: cuatro grupos (Riesgos, Acciones, Issues,
     Decisiones) con la tabla de `pmo/raid/page.tsx` extraída a
     `components/raid-tabla-transversal.tsx`. Columnas: Proyecto, Folio,
     Título, Responsable, Estado, Severidad/Prioridad, Fecha. Sin wrap,
     scroll horizontal (patrón de la fase 0).
   - **Botón "Descargar Excel"**: `GET /api/v1/tenant/raid/export?…` con
     los filtros actuales; nombre de archivo del header
     `Content-Disposition` (patrón de `raid/page.tsx:526-531`).
2. Redirect `next.config.js`: `/pmo/raid` → `/pmo/reports?tab=raid`;
   `/pmo/raid/:type/:raidId` se queda (es el detalle de un ítem; enlázalo
   desde la tabla).
3. Borra `pmo/raid/page.tsx`. Quita el `<Link>` temporal de la fase 1.

**TC-F8-02.** Con filtros de portafolio, el one-page, la tabla y el Excel
muestran los mismos conteos. `/pmo/raid` redirige. Imprimir muestra solo
el reporte.

```
feat(web): US-B — /pmo/reports pestaña RAID: one-page, tabla agrupada y Excel (refs REVAMP-V2 §7)
```

## Commit 3 — pestaña Cambios (US-C)

Mismo patrón que RAID con lo que D6/W5 hayan fijado. Mínimo: KPI band
(pendientes de aprobación, aprobados en el periodo, implementados,
rechazados), tabla con Proyecto, Folio, Título, Tipo
(`scope|time|cost|resource`), Estado, Solicitado por, Fecha; botón Excel →
`GET /api/v1/tenant/change-requests/export`. Redirect `/pmo/changes` →
`/pmo/reports?tab=cambios`; borra `pmo/changes/page.tsx`.

```
feat(web): US-C — /pmo/reports pestaña Cambios: one-page, tabla y Excel
```

## Commit 4 — pestaña Organización (US-D)

1. Renombra la pestaña existente "Organizaciones" (sección :245) a
   "Organización" si su contenido es de una sola organización; si lista
   varias, crea la pestaña nueva y deja la vieja solo para `agrega`.
2. Contenido: **snapshot** del Dashboard = `HeroAvance` + `RuedaDeSalud`
   + KPI band (los componentes de la fase 3, alimentados por
   `getDashboardKpis`/`getDashboardCharts` con `organization_id`) y debajo
   el **árbol** portafolio → programa → proyecto (`listPortfolios`,
   `listPrograms`, `listProjects`) con líneas de jerarquía (borde
   izquierdo `border-l border-[var(--border-subtle)]` + sangría por
   nivel), cada proyecto con su punto de salud y % avance.
3. Botón "Imprimir / guardar PDF" como en RAID. Los PDF existentes de
   organización (`organizations.py:1584`, `POST /{org_id}/reports/status`)
   se enlazan desde aquí; no se reescriben.

**TC-F8-04.** Los KPIs del snapshot coinciden con `/dashboard` para la
misma organización; el árbol muestra todos los proyectos activos
agrupados.

```
feat(web): US-D — /pmo/reports pestaña Organización: snapshot y árbol de portafolios
```

## Verificación antes de push

```bash
pnpm --filter @pmoaas/web exec tsc --noEmit
python scripts/check_tokens.py
python scripts/check_contraste.py
cd apps/api && .venv/bin/python -m ruff check . && .venv/bin/python -m pytest -q -n auto -m "not heavy"
python scripts/check_impacto_documental.py
```

## Cierre

PR `Revamp v2 — fase 8: reportes`. `cerrar-item` × 4. Feedback: 7 →
`hecho`. `navigation.md`: `/pmo/raid`, `/pmo/changes` redirigidas;
`/pmo/minutes` sigue huérfana (decisión del owner si se borra).
`SPRINT.md` → "9 (code review)".

## Qué NO hacer

- No duplicar la lógica de `raid_export.py`/`change_export.py`.
- No tocar `/pmo/projects/[id]/reports` (report builder por proyecto).
- No borrar `/pmo/minutes` sin OK del owner.
