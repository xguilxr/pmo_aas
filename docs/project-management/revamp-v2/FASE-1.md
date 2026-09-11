---
tipo: gestion
responsable: propietario
estado: vigente
revisado: 2026-09-11
revisar_cada: 30d
---

# FASE 1 — Navegación y header

**Qué es.** Reescribir el sidebar a los dos grupos del punto 2.2 y el header
según el punto 2.4 de `../REVAMP-V2-FEEDBACK.md`. Diagrama objetivo en
`../REVAMP-V2-PLAN.md` §1.
**Tamaño:** M. **Gate:** fase 0 mergeada. **Epic:** la navegación vive en
`docs/architecture/navigation.md` (DOC-ARCH-NAV); se actualiza en el mismo
bloque. EP013 está archivada: no se reabre, se anota en `navigation.md`.

**Reglas.** Dos commits: US-A (sidebar), US-B (header). Ninguna ruta se
borra ni se redirige en esta fase: las páginas que salen del sidebar siguen
existiendo y se enlazan desde otra página hasta que su fase las absorba.

## Preparación

```bash
git fetch origin main
git checkout -b claude/revamp-v2-f1-navegacion origin/main
pnpm install --frozen-lockfile
python scripts/proximo_id.py        # anota 2 IDs US-### libres
```

## Commit 1 — sidebar (US-A)

**Archivo:** `apps/web/components/app-shell.tsx`.

**Hechos verificados.**

- Tipos `NavItem` (líneas 24-34: `id, label, icono, href?, match?,
  children?, adminOnly?`) y `GrupoNav` (líneas 49-53: `id, titulo, items`).
- `GRUPOS_NAV` (líneas 55-160): grupo `organizacion` con `dashboard`,
  `portfolio`, `board`, `projects`, `imports`, `requests`, `resources`,
  `reports`; grupo `transversal` con `raid`, `changes`, `minutes`,
  `notifications`.
- `buildAdminNav()` (líneas 170-247): un `NavItem` `admin` ("Configuraciones",
  icono `settings`, href `/admin`) con hijos `tenant-mgmt`, `tenant-ai`,
  `orgs-mgmt`, `users`, `permissions`, `plan`, `audit`.
- El render de grupos está en las líneas ~741-786: primero `GRUPOS_NAV`,
  luego `adminVisible ? <RotuloDeGrupo titulo="Configuraciones" .../>` con
  `items={[adminNav]}`, luego `SUPERADMIN_GRUPOS`.
- Iconos disponibles (nombres ya usados en el archivo): `layout-dashboard`,
  `folders`, `grid-2x2`, `folder`, `upload`, `list-check`, `users`,
  `file-spreadsheet`, `triangle-alert`, `git-branch`, `file-text`, `bell`,
  `settings`. Para un icono nuevo, revisa que exista en
  `apps/web/public/icons/stroke/<nombre>.svg` antes de usarlo.

**Paso 1.** Reemplaza el contenido de `GRUPOS_NAV` por un solo grupo. Mantén
la sintaxis exacta de los objetos existentes (copia uno y cambia valores).

| id | label | icono | href | match |
|---|---|---|---|---|
| `dashboard` | Dashboard | `layout-dashboard` | `/dashboard` | el que ya tiene |
| `pmo` | PMO | `folders` | `/pmo` | `path === "/pmo" \|\| path.startsWith("/pmo/board") \|\| path.startsWith("/pmo/imports") \|\| path.startsWith("/pmo/programs") \|\| path.startsWith("/pmo/organizations")` |
| `resources` | Recursos | `users` | `/pmo/resources` | el que ya tiene |
| `requests` | Solicitudes | `list-check` | `/pmo/requests` | el que ya tiene |
| `reports` | Reportes | `file-spreadsheet` | `/pmo/reports` | `path.startsWith("/pmo/reports") \|\| path.startsWith("/pmo/raid") \|\| path.startsWith("/pmo/changes")` |
| `projects` | Proyectos | `folder` | `/pmo/projects` | `path.startsWith("/pmo/projects")` |

El grupo se llama `organizacion`, `titulo: "Organización"`. El orden de la
tabla es el orden del sidebar. El grupo `transversal` se borra entero.
`/pmo/minutes` y `/notifications` dejan de estar en el sidebar (la campana
del header sigue llevando a notificaciones).

**Paso 2.** Reescribe `buildAdminNav()` para que devuelva este árbol. El
`NavItem` raíz cambia: `id: "admin"`, `label: "Admin"`, `icono: "settings"`,
`href: "/admin"`. Sus `children`:

| id | label | href |
|---|---|---|
| `tenant-mgmt` | Branding | `/admin/tenant` |
| `users` | Usuarios | `/admin/users` |
| `orgs-mgmt` | Organizaciones y portafolios | `/admin/organizations` |
| `plan` | Plan e IA | `/admin/plan` |
| `audit` | Auditoría | `/admin/audit-logs` |

Se quitan `tenant-ai` (`/admin/ai` sigue existiendo; la fase 7 lo funde en
Plan e IA — mientras tanto se enlaza desde `/admin/plan`, ver paso 4) y
`permissions` (solo lectura, DEC-024; la página queda accesible por URL).

**Paso 3.** En el render (líneas ~757-770), el bloque de admin queda así:
el `RotuloDeGrupo` dice `"Configuraciones"` y `items` pasa a ser
`[cuentaNav, adminNav]`, donde `cuentaNav` es un `NavItem` nuevo definido
junto a `buildAdminNav`:

```ts
const CUENTA_NAV: NavItem = {
  id: "account",
  label: "Cuenta",
  icono: "users",
  href: "/account",
  match: (path) => path.startsWith("/account"),
};
```

`cuentaNav` se muestra a **todos** los usuarios autenticados, no solo a
`adminVisible`. Ajusta la condición: el bloque "Configuraciones" se pinta
siempre que `userReady && user`; dentro, `adminNav` solo si `adminVisible`.

**Paso 4.** Enlaces de reemplazo para lo que sale del sidebar (para que
nada quede huérfano hasta su fase):

1. `apps/web/app/(app)/pmo/page.tsx`, en el `<header>` de la línea ~357,
   junto a los botones existentes: dos `<Link>` con `Button variant="secondary" size="sm"`
   a `/pmo/board` ("Board") y `/pmo/imports` ("Importar proyectos"). Se
   quitan en la fase 4.
2. `apps/web/app/(app)/pmo/reports/page.tsx`, arriba del contenido: dos
   `<Link>` a `/pmo/raid` ("RAID de la organización") y `/pmo/changes`
   ("Cambios de la organización"). Se quitan en la fase 8.
3. `apps/web/app/(app)/admin/plan/page.tsx`: un `<Link>` a `/admin/ai`
   ("Configurar IA"). Se quita en la fase 7.

**Paso 5.** `docs/architecture/navigation.md`: reemplaza el diagrama del
sidebar (sección 1) por el de `../REVAMP-V2-PLAN.md` §1 y añade a la lista
de huérfanas: `/pmo/minutes` (temporal), `/admin/permissions`,
`/admin/areas` (hasta D4). Fecha `revisado: <hoy>`.

**Criterio de aceptación (TC-F1-01).** Usuario `role_type = user`: ve
"Organización" con 6 entradas en ese orden y "Configuraciones" con solo
"Cuenta". Usuario `admin`: además ve "Admin" desplegable con 5 hijos.
Superadmin: sin cambios. Cada entrada lleva a su ruta y se marca activa al
estar en ella o en sus sub-rutas (probar `/pmo/projects/<id>/raid` marca
"Proyectos"; `/pmo/raid` marca "Reportes").

**Commit.**

```
feat(web): US-A — sidebar en dos grupos: Organización y Configuraciones (refs REVAMP-V2 §2.2)
```

## Commit 2 — header (US-B)

**Archivo:** `apps/web/components/app-shell.tsx`, líneas 620-694.

**Hechos verificados.** El header hoy (de izquierda a derecha): botón menú
móvil; `<Link href={homeHref}>` con el logo del tenant (`logoSrc`, 200px)
o `brandName` en texto, más un `<span>` "PMO-aaS" (líneas 651-653);
`<SwitcherDeInquilino />` y `<SwitcherDeOrganizacion />` (líneas 663-668);
a la derecha, buscador `w-[260px]` (línea 675), campana, `UserMenu`.
`SwitcherDeOrganizacion` (`components/switcher-de-organizacion.tsx:33-79`)
es un `<Select>` sin etiqueta visible. **No existe** un asset de logo de
PMO-aaS en `apps/web/public/` (solo `icons/`); el owner debe entregarlo
(decisión D7). Mientras no exista, la marca es texto.

**Estructura objetivo** (tres zonas con `justify-between`):

```
[menú móvil] [PMO · aaS] [Organización: ▾ Select]   [—— Buscar ⌘K ——]   [logo tenant] [🔔] [avatar]
```

**Pasos.**

1. Zona izquierda (`<div className="flex min-w-0 items-center gap-2">`,
   líneas 623-669):
   - Dentro del `<Link href={homeHref}>`, deja solo el texto de marca: un
     `<span>` con `PMO · aaS` y las clases de la línea 647. Borra el bloque
     `logoSrc ? <img/> : <span/>` (líneas 637-650) y el `<span>` "PMO-aaS"
     (651-653). Guarda `logoSrc` y `brandName`: se usan en el paso 3.
   - Antes de `<SwitcherDeOrganizacion />` inserta
     `<span className="hidden lg:inline text-[13px] text-[var(--text-tertiary)]">Organización:</span>`.
     `SwitcherDeInquilino` se queda donde está, antes de la etiqueta.
2. Zona central (nueva, entre la izquierda y la derecha): mueve ahí el
   botón de buscar de las líneas 671-682 envuelto en
   `<div className="hidden sm:flex flex-1 justify-center px-4">`. Cambia
   `w-[260px]` por `w-full max-w-[560px]`.
3. Zona derecha (líneas 670-693): queda el botón de buscar móvil (683-690),
   luego el logo del tenant, luego la campana, luego `UserMenu`. El logo:

```tsx
{logoSrc ? (
  <span className="hidden md:flex h-8 max-w-[140px] items-center overflow-hidden">
    {/* eslint-disable-next-line @next/next/no-img-element */}
    <img src={logoSrc} alt={brandName} className="h-full w-auto object-contain" />
  </span>
) : null}
```

   Si no hay logo, no se pinta nada (el nombre del tenant ya está en el
   `UserMenu`).

4. Los comentarios de las líneas 655-662 (US-205, US-214) siguen siendo
   verdad; déjalos.
5. `python scripts/check_tokens.py` debe dar `exit 0`: no uses colores ni
   tamaños fuera de `globals.css`.

**Criterio de aceptación (TC-F1-02).** En desktop: a la izquierda se lee
"PMO · aaS · Organización: [dropdown]"; el buscador está centrado y ocupa
hasta 560px; a la derecha, logo del tenant (si tiene), campana y avatar.
En móvil (< 640px): marca, icono de buscar, campana, avatar; el dropdown se
oculta como hoy (`lg:block`). Cambiar de organización en el dropdown sigue
filtrando el Dashboard.

**Commit.**

```
feat(web): US-B — header: marca + Organización: dropdown, buscador centrado, logo del tenant a la derecha (refs REVAMP-V2 §2.4)
```

## Verificación antes de push

```bash
pnpm --filter @pmoaas/web exec tsc --noEmit   # exit 0
python scripts/check_tokens.py                # exit 0
python scripts/check_contexto.py              # exit 0
python scripts/check_impacto_documental.py    # avisa si falta navigation.md
```

## Cierre

1. `git push -u origin claude/revamp-v2-f1-navegacion`; PR
   `Revamp v2 — fase 1: navegación y header`.
2. Skill `cerrar-item` para US-A y US-B.
3. `../REVAMP-V2-FEEDBACK.md`: punto 2 (2.1, 2.2, 2.4) → `hecho` con
   commits. 2.3 sigue `pendiente` (fase 2).
4. `SPRINT.md`: la línea de fases avanza a "→ 2 (filtro org)".

## Qué NO hacer

- No redirigir ni borrar `/pmo/board`, `/pmo/imports`, `/pmo/raid`,
  `/pmo/changes`, `/pmo/minutes`, `/admin/ai`, `/admin/permissions`.
- No tocar `SUPERADMIN_GRUPOS`.
- No crear `/admin/hierarchy` ni `/pmo/config` (fases 7 y 4).
- No cambiar `useOrganizacionActiva` (fase 2).
