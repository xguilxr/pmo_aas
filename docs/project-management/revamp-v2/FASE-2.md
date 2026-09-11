---
tipo: gestion
responsable: propietario
estado: vigente
revisado: 2026-09-11
revisar_cada: 30d
---

# FASE 2 — Filtro por organización activa en todas las páginas

**Qué es.** Que toda página de `(app)` lea y escriba solo la organización
del dropdown del header. Punto 2.3 de `../REVAMP-V2-FEEDBACK.md`.
**Tamaño:** M. **Gate:** fase 1 mergeada y decisión **D2** (qué rol ve
"todas"). **Epic:** EP002 (jerarquía) — actualizar la sección de alcance
por organización si cambia la regla.

**Reglas.** Un commit por página corregida (US-A…), más un commit final
para el script de limpieza de datos. No se toca el backend salvo que un
endpoint no acepte `organization_id` (ninguno de los detectados lo
necesita).

## Preparación

```bash
git fetch origin main
git checkout -b claude/revamp-v2-f2-filtro-org origin/main
pnpm install --frozen-lockfile
python scripts/proximo_id.py
```

## Hechos verificados

- Hook: `apps/web/components/organizacion-activa.tsx`. Devuelve
  `organizaciones`, `activa`, `efectiva`, `activaObj`, `agrega`, `elegir`,
  `cargando`, `vacio` (líneas 82-111). Atajo `useOrgFiltro()` (líneas
  241-243) devuelve `efectiva || undefined`. `RUTAS_QUE_AGREGAN` (líneas
  76-80) = `["/dashboard", "/pmo", "/admin/organizations"]`: en esas rutas
  el valor "Todas las organizaciones" es válido; en las demás `efectiva`
  cae a la primera organización.
- Páginas que **ya** filtran (no tocar): `dashboard/page.tsx` (líneas 196,
  243, 345), `pmo/page.tsx`, `pmo/board/page.tsx:82`, `pmo/imports/page.tsx:83`,
  `pmo/projects/page.tsx:114,168`, `pmo/reports/page.tsx` (3 usos),
  `pmo/requests/page.tsx:76`, `pmo/resources/page.tsx:145,146,179`.
- Páginas que **no** filtran: `pmo/raid/page.tsx`, `pmo/changes/page.tsx`,
  `pmo/minutes/page.tsx`. Las tres llaman funciones de
  `apps/web/lib/api/tenant-cross.ts` (`listTenantRisks` :59,
  `listTenantIssues` :65, `listTenantChanges` :71, `listTenantMinutes`
  :77) cuyo tipo de params ya tiene `organization_id?: string` (línea 13).
  El backend `apps/api/app/api/v1/endpoints/tenant_cross.py` ya filtra
  por `organization_id` en `/risks` (:88), `/issues` (:138),
  `/change-requests` (:190), `/meeting-minutes` (:220), `/reports` (:247).
- Recursos: `pmo/resources/page.tsx` pasa `organization_id` a
  `/api/v1/capacity/summary`, `/conflicts`, `/weekly-load`. El backend
  (`capacity.py:65-68`) lo acepta como opcional. Si el owner sigue viendo
  recursos de dos organizaciones, el problema son los **datos** (actores
  con `organization_id` equivocado), no el filtro: lo cubre el script del
  paso 3.

## Paso 1 — las tres páginas transversales (3 commits)

Para cada una de `pmo/raid/page.tsx`, `pmo/changes/page.tsx`,
`pmo/minutes/page.tsx`:

1. Importa el atajo: `import { useOrgFiltro } from "@/components/organizacion-activa";`.
2. Dentro del componente de página, antes de los `useEffect` de carga:
   `const orgFiltro = useOrgFiltro();`.
3. En cada llamada a `listTenant*`, agrega `organization_id: orgFiltro` al
   objeto de params. Si la llamada no recibe objeto, créalo.
4. Agrega `orgFiltro` al array de dependencias del `useEffect` que dispara
   la carga, para que cambiar el dropdown recargue.
5. Verifica en el navegador: cambiar de organización en el header cambia
   la lista.

**Criterio de aceptación (TC-F2-01).** Con dos organizaciones que tengan
riesgos, en `/pmo/raid` la lista cambia al cambiar el dropdown y nunca
mezcla ambas. Igual en `/pmo/changes` y `/pmo/minutes`.

**Commits.**

```
fix(web): US-A — /pmo/raid filtra por organización activa (refs REVAMP-V2 §2.3)
fix(web): US-B — /pmo/changes filtra por organización activa
fix(web): US-C — /pmo/minutes filtra por organización activa
```

## Paso 2 — regla D2: quién ve "todas"

Hoy cualquier usuario con más de una organización ve la opción "Todas las
organizaciones" en las rutas de `RUTAS_QUE_AGREGAN`
(`switcher-de-organizacion.tsx:66-68`). Aplica la decisión D2 del plan
(recomendada: solo `role_type === "admin"`):

1. En `organizacion-activa.tsx`, donde se calcula `agrega`, añade la
   condición del rol. El usuario viene de `useAuth()` o del contexto que ya
   use el archivo; búscalo con `grep -n "user" apps/web/components/organizacion-activa.tsx`.
2. Si el usuario no es admin y `activa === TODAS`, `efectiva` debe caer a
   `organizaciones[0].id` (ya lo hace para rutas no agregadoras; extiende
   la misma lógica).
3. Test manual: con un usuario `role_type = user` con 2 organizaciones, el
   dropdown no muestra "Todas" en `/dashboard`.

**Commit.**

```
feat(web): US-D — solo admin del tenant ve "Todas las organizaciones" (DEC-### D2)
```

Registra D2 en `docs/epics/DECISIONS.md` con el siguiente `DEC-###` libre.

## Paso 3 — limpieza de datos (script, no migración)

**Hecho.** El owner reporta actores duplicados entre dos organizaciones
que "se juntaron". No hay que cambiar el esquema; hay que corregir filas.

1. Crea `scripts/diagnostico_actores_por_org.py` (solo lectura) que, con
   `DATABASE_URL` del entorno, liste por tenant los `actors` cuyo `email`
   aparece en más de una `organization_id`, con columnas:
   `email, actor_id, organization_id, organization.name, n_participaciones_activas`.
   Usa SQLAlchemy con los modelos de `apps/api/app/models/area.py` (`Actor`,
   línea 154) y `project_participation.py`.
2. Corre el script contra la base de desarrollo y pega la salida en el PR.
3. **No borres ni muevas filas en esta fase.** La decisión de cuál copia
   sobrevive es del owner (depende de D1, fase 6). El script deja la lista;
   la corrección se hace en la fase 6 con la regla de unicidad definida.

**Commit.**

```
chore(scripts): US-E — diagnóstico de actores duplicados entre organizaciones
```

## Verificación antes de push

```bash
pnpm --filter @pmoaas/web exec tsc --noEmit   # exit 0
python scripts/check_tokens.py                # exit 0
python scripts/check_contexto.py              # exit 0
```

## Cierre

1. Push, PR `Revamp v2 — fase 2: filtro por organización`.
2. `cerrar-item` por cada US. Punto 2.3 → `hecho` (con nota: limpieza de
   datos diferida a fase 6).
3. `SPRINT.md`: "→ 3 (dashboard)". Antes de la fase 3 hace falta el
   wireframe W1 aprobado.

## Qué NO hacer

- No cambiar `RUTAS_QUE_AGREGAN` (el Dashboard y `/pmo` sí deben poder
  agregar para el admin).
- No agregar `organization_id` a endpoints que ya lo aceptan (revisa antes
  con grep en `apps/api/app/api/v1/endpoints/`).
- No borrar datos.
