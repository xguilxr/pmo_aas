---
tipo: gestion
responsable: propietario
estado: vigente
revisado: 2026-09-11
revisar_cada: 30d
---

# FASE 3 — Dashboard

**Qué es.** Aplicar el rediseño editorial al Dashboard: hero de avance,
rueda de salud con activos, KPI band de 5, distribuciones con hairlines.
Puntos 1 y 3 de `../REVAMP-V2-FEEDBACK.md`. Spec visual original:
`PMO-aaS Dashboard Redesign.dc.html` (zip del owner, 2026-09-10) y el
wireframe **W1** aprobado.
**Tamaño:** L. **Gate:** fase 2 mergeada y W1 aprobado. **Epic:** EP004 —
actualizar la sección de composición del dashboard en el mismo bloque.

**Reglas.** Cuatro commits en este orden: US-A rueda de salud, US-B hero
de avance, US-C KPI band + distribuciones, US-D limpieza. Cada commit deja
el dashboard funcionando. Todo con tokens de `globals.css`
(`python scripts/check_tokens.py` es gate de CI). Sin librerías de gráficas:
SVG inline como en `components/dashboard-charts.tsx`.

## Preparación

```bash
git fetch origin main
git checkout -b claude/revamp-v2-f3-dashboard origin/main
pnpm install --frozen-lockfile
python scripts/proximo_id.py
```

## Hechos verificados (`apps/web/app/(app)/dashboard/page.tsx`)

| Línea | Sección | Componentes | Datos |
|---|---|---|---|
| 715 | `<KpiBand className="grid-cols-2 sm:grid-cols-3 lg:grid-cols-6">` | 5 `KpiCard` + 1 `TarjetaDeSalud` | `getDashboardKpis` (:366), `getCapacitySummary` (:243) |
| 716 | `KpiCard label="Proyectos activos"` | | kpis |
| 723 | `<TarjetaDeSalud conteos=… href="/pmo/projects" />` | `tablero-ejecutivo.tsx:30` | kpis |
| 728 | `KpiCard label="Avance plan vs real"` | | kpis |
| 738 | `KpiCard label="Presupuesto"` | | kpis |
| 746 | `KpiCard label="Riesgos severos"` | | kpis |
| 754 | `KpiCard label="Sobreasignados"` | | capacity |
| 766 | `section "Qué mirar primero"` | 3 `ListaTop` (767, 773, 779) | `getDashboardTops` (:236) |
| 792 | `section "Distribuciones"` | `ChartCard` "Por salud" (`Pie`+`Legend`, 793), "Por fase" (`Bars`, 801), "Por programa" (804), "Por sponsor" (807) | `getDashboardCharts` (:380) |
| 816 | `section "Detalle de la cartera"` | "Avance promedio por fase" (`Bars`, 817), "Presupuesto por tipo" (824), "Matriz de riesgos" (`RiskMatrix`, 831) | charts, `getRiskMatrix` (:208) |
| 846 | `section "Tendencia y semáforo"` | `SemaforoConsolidado` (847); `Heatmap` solo admin (859) | `getHealthMatrix` (:246), `getHeatmap` |
| 870 | `section "Tendencias y portafolio"` — **solo `isAdminView`** | 3× `TrendMini` (función local :1028), `Treemap` (905) | `getTrends` (:227), `getTreemap` |
| 915 | `section "Historial de cortes"` — solo admin | tabla propia | |
| 1004 | `section "Vista maestra"` | link a `/pmo` | |
| 1066 | `function ChartCard({ title, children, loading })` — local, no exportado | | |

Firmas: `KpiBand({ children, className })` y
`KpiCard({ label, value, href, icon, format, tone, loading, trend, hint, moneda })`
en `apps/web/components/kpi-card.tsx:127` y `:141`.

## Commit 1 — rueda de salud con activos (US-A)

Fusiona tres piezas: `KpiCard "Proyectos activos"` (716),
`TarjetaDeSalud` (723) y `ChartCard "Por salud"` (793).

1. En `apps/web/components/tablero-ejecutivo.tsx` crea y exporta
   `RuedaDeSalud({ conteos, total, href })`:
   - `conteos`: `{ green: number; yellow: number; red: number }` (mismo
     tipo que recibe `TarjetaDeSalud`, línea 30).
   - `total`: proyectos activos (el valor que hoy va al `KpiCard` de 716).
   - Render: `<Pie>` de `dashboard-charts.tsx` con `size` 52 y anillo
     grueso, `total` centrado en `font-mono tabular-nums`, y a la derecha
     una leyenda de 3 filas (punto de color + etiqueta + cifra mono). Los
     colores: `HEALTH_FILL` de `dashboard-charts.tsx:301`. Etiquetas:
     `etiquetaSalud()` que ya importa la página (línea 63).
   - El bloque completo es un `<Link href={href}>` como lo es hoy
     `TarjetaDeSalud`.
2. En `dashboard/page.tsx`: borra el `KpiCard` de 716 y el `TarjetaDeSalud`
   de 723; borra el `ChartCard "Por salud"` de 793. En su lugar, como
   primera card de la sección "Distribuciones" (792), monta
   `<RuedaDeSalud conteos={…} total={…} href="/pmo/projects" />`.
3. `KpiBand` (715) pasa a `lg:grid-cols-5`.
4. Si `TarjetaDeSalud` ya no se usa en ningún otro archivo
   (`grep -rn TarjetaDeSalud apps/web`), bórrala.

**TC-F3-01.** La rueda muestra el total de activos al centro y la leyenda
suma el mismo total. Clic lleva a `/pmo/projects`. El KPI band tiene 5
cards.

```
feat(dashboard): US-A — rueda de salud con proyectos activos al centro (refs REVAMP-V2 §3)
```

## Commit 2 — hero de avance (US-B)

Fusiona `KpiCard "Avance plan vs real"` (728) con la tendencia de avance
(el `TrendMini` de "Avance promedio" en 871, hoy solo admin).

1. Comprueba quién puede llamar `getTrends`: abre
   `apps/api/app/api/v1/endpoints/analytics.py` (o donde viva `/trends`,
   `grep -rn '"/trends"' apps/api/app/api`) y mira su `Depends`. Si exige
   admin, el hero muestra la tendencia solo cuando `isAdminView`; si no,
   para todos. Anota cuál fue en el PR.
2. En `tablero-ejecutivo.tsx` crea `HeroAvance({ real, plan, serie, corte })`:
   - `real`, `plan`: porcentajes (los del `KpiCard` de 728 y su `hint`).
   - `serie`: `{ fecha: string; valor: number }[]` — la serie que hoy
     alimenta `TrendMini` de avance (mira `TrendMini` en :1028 para el
     formato exacto y reúsalo).
   - Render en una card ancha (`col-span-2` en el band): label en
     mayúsculas pequeñas, cifra grande mono (`real%`), a la derecha
     `plan% · Δ pts` con `tone` success/danger según el signo, debajo la
     línea de tendencia (`TrendLines` de `dashboard-charts.tsx:388` o un
     polyline propio con `stroke-dasharray="1 3"` como en el spec) y una
     línea de delta "▲ N pts vs. hace 12 semanas".
3. En `dashboard/page.tsx`: borra el `KpiCard` de 728. Monta `HeroAvance`
   como primera card del band con `className="lg:col-span-2"` (el band
   queda: hero ×2 + Presupuesto + Riesgos severos + Sobreasignados = 5
   columnas).
4. En la sección admin (870), quita el `TrendMini` de avance para no
   duplicar; deja los otros dos.

**TC-F3-02.** El hero muestra real, plan, delta y la línea. Con un usuario
no admin no rompe (tendencia oculta o visible según paso 1).

```
feat(dashboard): US-B — hero de avance: % real, plan y tendencia en una pieza
```

## Commit 3 — KPI band y distribuciones al estilo editorial (US-C)

Estilo del spec (tokens ya existentes; no crear nuevos):

| Elemento | Antes | Después |
|---|---|---|
| Label de KPI | como esté en `KpiCard` | `text-[10px] font-semibold uppercase tracking-[.06em] text-[var(--text-tertiary)]`, centrado |
| Cifra | | `font-mono text-[17px] font-medium tabular-nums` |
| Sparkline | no hay | polyline 46×10, `stroke-dasharray="1 2.5"`, `opacity-70`, punto final `r=1.3`; color: `--color-accent` neutro, `--color-danger-fg` riesgos, `--color-warning-fg` sobreasignados |
| Nota | `hint` | `text-[9.5px] text-[var(--text-tertiary)]` |
| Barras de distribución | `Bars` actual | barras de 8px, `rounded-t-full`, cifra encima en mono 8.5px, etiqueta debajo separada por hairline `border-t border-[var(--border-subtle)]` |
| Card | `ChartCard` | `border border-[var(--border-default)] rounded-[var(--radius-xl)] bg-[var(--color-surface)] shadow-[var(--relieve-isla)]` (sin cambio) |

1. `kpi-card.tsx`: agrega prop opcional `serie?: number[]`. Si viene, pinta
   el sparkline bajo la cifra. Aplica las clases de la tabla al label, la
   cifra y el hint. No cambies la firma existente (compatibilidad con otros
   usos: `grep -rn "<KpiCard" apps/web`).
2. `dashboard-charts.tsx`, `Bars` (líneas 87-198): agrega prop
   `variant?: "default" | "fino"`. Con `fino` aplica el estilo de la tabla.
   Los cuatro `Bars` del dashboard pasan a `variant="fino"`; los demás usos
   no cambian.
3. Por fase usa `--chart-ord-1..5` (ordinal); por programa y sponsor usan
   `--color-accent` y `--text-faint` para "sin programa"/"sin sponsor".
   Salud nunca colorea series (ADR-023).
4. Sección "Qué mirar primero" (766): `ListaTop` pasa a filas con punto de
   salud a la izquierda, nombre truncado, cifra mono a la derecha,
   separadas por hairline. Título en mayúsculas pequeñas.

**TC-F3-03.** `python scripts/check_tokens.py` exit 0.
`python scripts/check_contraste.py` exit 0. Visualmente coincide con W1 en
KPI band, distribuciones y tops.

```
feat(dashboard): US-C — KPI band y distribuciones con la gramática editorial de W1
```

## Commit 4 — limpieza (US-D)

1. Mueve `ChartCard` (page.tsx:1066) a `components/chart-card.tsx` y
   expórtalo; el dashboard lo importa. Solo si otra fase lo va a reusar
   (la 8 sí). Si no, déjalo.
2. Borra código muerto que dejaron los commits 1-3 (`tsc` con
   `noUnusedLocals` lo señala; si no está activo, revisa a mano los
   imports de la página).
3. `docs/epics/EP004-dashboard.md`: actualiza la lista de piezas del
   dashboard (band de 5 con hero y rueda; distribuciones; tops; matriz;
   semáforo). Sub-agente Haiku (skill `delegar`).

```
refactor(dashboard): US-D — ChartCard a components y limpieza tras el rediseño
docs(epics): EP004 — composición del dashboard tras el revamp v2
```

## Verificación antes de push

```bash
pnpm --filter @pmoaas/web exec tsc --noEmit
python scripts/check_tokens.py
python scripts/check_contraste.py
python scripts/check_impacto_documental.py     # debe ver EP004 tocada
```

## Cierre

PR `Revamp v2 — fase 3: dashboard`. `cerrar-item` × 4. Feedback: puntos 1 y
3 → `hecho`. `SPRINT.md` → "4 (PMO)". Antes de la 4: W2 y W3 aprobados,
D3 decidida.

## Qué NO hacer

- No tocar el roadmap (vive en `/pmo`, punto 3 lo confirma).
- No tocar `RiskMatrix` (US-245, ya hecho).
- No crear tokens nuevos en `globals.css`.
- No mover la sección admin (870+) salvo quitar el `TrendMini` duplicado.
