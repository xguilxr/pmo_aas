---
tipo: gestion
responsable: propietario
estado: vigente
revisado: 2026-09-11
revisar_cada: 30d
---

# FASE 5 — Proyectos: orden de columnas y filtros multi-select

**Qué es.** La lista `/pmo/projects` con columnas portafolio → programa →
proyecto → detalle, y filtros como dropdown con checkmarks. Punto 8 de
`../REVAMP-V2-FEEDBACK.md`. Wireframe **W6** fija las columnas de detalle.
**Tamaño:** S. **Gate:** fase 4 mergeada, W6 aprobado. **Epic:** EP005.

**Reglas.** Dos commits: US-A componente de filtro, US-B la página.

## Preparación

```bash
git fetch origin main
git checkout -b claude/revamp-v2-f5-proyectos origin/main
pnpm install --frozen-lockfile
python scripts/proximo_id.py
```

## Hechos verificados (`apps/web/app/(app)/pmo/projects/page.tsx`)

- Columnas del `thead` (líneas 440-445, todas `SortableTh` de
  `components/ui/sortable-th.tsx`): Proyecto, Fase, Prioridad (derecha),
  Avance, Presupuesto (derecha), Salud (centro).
- Filtros: `Select` de programa (263-297), `Select` de prioridad mínima
  (341-353), `Chip` (botones pill) para fase/tipo/salud (310-339),
  checkbox nativo "Sólo míos" (298-306).
- La página ya filtra por organización (`useOrganizacionActiva`, líneas
  89, 114, 168) y carga programas con `listPrograms`.
- `components/ui/` no tiene multi-select. Tiene `checkbox.tsx`,
  `select.tsx`, `button.tsx`, `modal.tsx`, `badge.tsx`, `input.tsx`,
  `switch.tsx`, `sortable-th.tsx`, `skeleton.tsx`, `banner.tsx`,
  `breadcrumb.tsx`, `textarea.tsx`, `icono.tsx`, `estados.tsx`,
  `marca-de-datos.tsx`, `password-input.tsx`.
- `Project` (`lib/api/projects.ts:26`) trae `portfolio_id` y `program_id`
  pero no los nombres. `listPortfolios` y `listPrograms` están en
  `lib/api/organizations.ts` (:340, :199).

## Commit 1 — `FiltroMultiple` (US-A)

**Archivo nuevo:** `apps/web/components/ui/filtro-multiple.tsx`.

```ts
export function FiltroMultiple({
  label, opciones, seleccion, onChange, className,
}: {
  label: string;
  opciones: { value: string; label: string }[];
  seleccion: string[];
  onChange: (values: string[]) => void;
  className?: string;
})
```

1. Botón con la altura y borde del `Select` actual (`h-9`, clases de
   `select.tsx`), texto: `label` si no hay selección; `label · N` si hay.
   Chevron a la derecha (`Icono nombre="chevron-down"`; verifica que el svg
   exista en `apps/web/public/icons/stroke/`).
2. Al hacer clic abre un panel absoluto (`z-20`, `bg-[var(--color-surface)]`,
   `border border-[var(--border-default)]`, `rounded-[var(--radius-md)]`,
   `shadow-[var(--relieve-isla)]`) con una fila por opción: `Checkbox` de
   `components/ui/checkbox.tsx` + label. Marcar/desmarcar llama `onChange`
   con el arreglo nuevo. Fila superior "Todos / Ninguno".
3. Cierra con clic fuera (`useEffect` con `mousedown` en `document`) y con
   `Escape`. `role="listbox"` y `aria-multiselectable`.
4. Sin dependencias nuevas.

**TC-F5-01.** En una página de prueba (o Storybook si existiera; no
existe: prueba dentro de la página del commit 2), marcar dos opciones
muestra `label · 2` y el `onChange` recibe ambas.

```
feat(web): US-A — FiltroMultiple: dropdown con checkmarks reutilizable
```

## Commit 2 — la página (US-B)

1. **Columnas.** Reemplaza el `thead` (440-445) por, en este orden:
   Portafolio, Programa, Proyecto, y después las columnas de detalle que
   fije W6 (por defecto: Fase, Avance, Salud, PM, Fin). Cada una
   `SortableTh`. Para Portafolio y Programa necesitas nombres: carga
   `listPortfolios(orgId)` (la página ya carga `listPrograms`) y arma dos
   `Map<id, name>`. Sin portafolio → "—".
2. **Orden por defecto** igual que la fase 4: portafolio, programa, nombre
   (`localeCompare("es")`), aplicado antes de pasar las filas a la tabla.
3. **Filtros.** Sustituye los `Chip` de fase, tipo y salud (310-339) y el
   `Select` de programa (263-297) por cuatro `FiltroMultiple`: Portafolio,
   Programa, Fase, Salud. Tipo pasa a `FiltroMultiple` también si W6 lo
   mantiene. Prioridad mínima y "Sólo míos" se quedan como están.
   - Los valores se guardan en la URL como hoy (mira cómo la página
     persiste `program_id`; extiende a listas separadas por coma).
   - `listProjects` acepta arreglos en `phase`, `type`, `health`
     (`ListProjectsParams`, `lib/api/projects.ts:226-244`); `portfolio_id`
     y `program_id` son escalares: si hay más de uno seleccionado, filtra
     en cliente después de traer la lista con `limit` alto, o haz una
     llamada por valor y concatena. Elige la primera opción; anótalo en el
     PR.
4. Botón "Limpiar" si hay algún filtro activo (patrón de `pmo/page.tsx:501`).

**TC-F5-02.** Las tres primeras columnas son Portafolio, Programa,
Proyecto. Marcar dos fases en el filtro muestra solo esas. Recargar la
página conserva los filtros. Un usuario PM ve solo sus proyectos si marca
"Sólo míos".

```
feat(web): US-B — /pmo/projects: columnas portafolio·programa·proyecto y filtros multi-select (refs REVAMP-V2 §8)
```

## Verificación antes de push

```bash
pnpm --filter @pmoaas/web exec tsc --noEmit
python scripts/check_tokens.py
python scripts/check_contraste.py
```

## Cierre

PR `Revamp v2 — fase 5: proyectos`. `cerrar-item` × 2. Feedback: 8 →
`hecho`. `SPRINT.md` → "6 (recursos)". Antes: W4 aprobado y D1 decidida.

## Qué NO hacer

- No cambiar el detalle de proyecto ni sus tabs.
- No tocar la vista maestra de `/pmo` (ya ordenada en la fase 4).
