---
tipo: gestion
responsable: propietario
estado: vigente
revisado: 2026-09-11
revisar_cada: 30d
---

# FASE 0 — Bugs visibles (tabs, tabla RAID, sidebar pegado al header)

**Qué es.** Tres correcciones de UI sin diseño previo. Cierra el punto 13 y
la primera viñeta del punto 2.4 de `../REVAMP-V2-FEEDBACK.md`.
**Tamaño:** S. **Gate:** ninguno. **Epics:** EP005, EP006 (solo si cambia
comportamiento descrito; aquí no, son bugs).

**Reglas de esta fase.** Un commit por corrección (3 commits). No tocar
nada fuera de los tres archivos listados. No cambiar rutas ni datos.

## Preparación

```bash
git fetch origin main
git checkout -b claude/revamp-v2-f0-bugs origin/main
pnpm install --frozen-lockfile
python scripts/proximo_id.py        # anota los 3 IDs BUG-### libres
```

Usa los tres IDs BUG en orden: BUG-A (tabs), BUG-B (tabla RAID),
BUG-C (sidebar).

## Corrección 1 — tabs del detalle de proyecto no se marcan activos

**Archivo:** `apps/web/components/project-tabs-bar.tsx`.

**Hecho verificado.** El array `TABS` (líneas 17-107) tiene 10 pestañas.
Cada una trae `match: (pathname, projectId) => boolean`. Ocho de ellas
comparan contra `/admin/projects/` (líneas 25, 33, 51, 63, 74, 82, 89, 96,
106) y las URLs reales son `/pmo/projects/...`. Solo `overview` y `board`
funcionan. La clase de activo se aplica en las líneas 132-137 cuando
`active` es `true`.

**Pasos.**

1. Abre el archivo y lee las líneas 17-107 completas.
2. En cada `match` que contenga la cadena `\/admin\/projects\/` (o
   `/admin/projects/`), reemplázala por `\/pmo\/projects\/` (o
   `/pmo/projects/`). No cambies nada más del regex.
3. Verifica que la pestaña `areas` (líneas 53-64, label "Recursos") tenga
   `id: "areas"`. Si falta, agrégalo como primera propiedad del objeto.
4. Comprueba con grep que no queda ninguna referencia:

```bash
grep -n "admin/projects" apps/web/components/project-tabs-bar.tsx
# debe devolver vacío
```

**Criterio de aceptación (TC-F0-01).** Con el dev server levantado
(`pnpm --filter @pmoaas/web dev`), abrir un proyecto y navegar a cada uno
de los 10 tabs: Resumen, Plan, Board, RAID, Recursos, Artefactos, Minutas,
Reportes, Cambios, Lecciones. En cada uno, el tab actual se ve con fondo
oscuro (`bg-[var(--color-primary)]`) y texto claro. Ninguno se queda sin
marcar. Lo verificas a mano; no hay test automático de esto.

**Commit.**

```
fix(web): BUG-A — tabs del detalle de proyecto comparan /admin/ en vez de /pmo/
```

## Corrección 2 — tabla RAID del proyecto encima elementos

**Archivo:** `apps/web/app/(app)/pmo/projects/[id]/raid/page.tsx`.

**Hecho verificado.** La tabla de riesgos (línea 1215,
`<table className="w-full table-fixed text-[13px]">`) está dentro de una
`<section>` con `overflow-hidden` (línea 1211). El comentario de las
líneas 1212-1214 dice que el diseño es "2 líneas por fila, sin scroll
horizontal". Las celdas (ej. línea 1252, `<td className="px-3 py-2">`) no
llevan `whitespace-nowrap`. El owner reporta que con datos reales las
celdas se enciman. La decisión del owner (punto 13) es **quitar el wrap**.

**Patrón de referencia** (ya en el repo, funciona):
`apps/web/components/vista-maestra.tsx` líneas 815-819:

```tsx
<div className="relative max-h-[70vh] overflow-auto">
  <table className="w-full min-w-max border-separate border-spacing-0 text-[13px]">
```

y sus celdas usan `whitespace-nowrap` (líneas 339, 361, 374, 462, 517).

**Pasos.**

1. En la línea 1211, cambia `overflow-hidden` por `overflow-x-auto` en la
   `<section>`. No quites el resto de clases.
2. En la línea 1215, cambia `w-full table-fixed text-[13px]` por
   `w-full min-w-max text-[13px]`.
3. Busca todos los `<td` y `<th` de esa tabla (desde la línea 1215 hasta el
   `</table>` que la cierra) y agrega `whitespace-nowrap` a su
   `className`. Si una celda contiene texto largo (descripción, título),
   agrégale además `max-w-[32ch] truncate` y un `title={valor}` para que el
   texto completo se vea al pasar el mouse.
4. Actualiza el comentario de las líneas 1212-1214 para que diga que la
   tabla hace scroll horizontal (una línea, en español).
5. Repite los pasos 1-4 para la tabla de la sección de issues/acciones/
   decisiones (`IssuesSection`, después de la línea 1386). Localízala con
   `grep -n "<table" apps/web/app/\(app\)/pmo/projects/\[id\]/raid/page.tsx`.
6. No toques la matriz P×I de la línea 1033: ya tiene `overflow-x-auto`
   y no es tabla de datos.

**Criterio de aceptación (TC-F0-02).** En un proyecto con 5 o más riesgos
con título largo (más de 40 caracteres), la tabla RAID muestra una fila
por riesgo, ninguna celda se encima con otra, y aparece scroll horizontal
si la pantalla es angosta. Igual para la tabla de issues.

**Commit.**

```
fix(web): BUG-B — tablas RAID del proyecto sin wrap, con scroll horizontal
```

## Corrección 3 — sidebar arranca debajo de la línea del header

**Archivo:** `apps/web/components/app-shell.tsx`.

**Hecho verificado.** En las líneas 715-729 hay un
`<div className="flex h-12 items-center px-2 ...">` dentro del `<aside>`.
Solo contiene el botón "Cerrar menú" con clase `lg:hidden`. En desktop
(`lg`) queda un espacio vacío de 48px encima del primer rótulo del sidebar.
El botón de colapsar ya vive al pie (US-246).

**Pasos.**

1. Agrega `lg:hidden` a la clase del `<div>` de la línea 715, de modo que
   el bloque completo desaparezca en desktop y siga en móvil:

```tsx
"flex h-12 items-center px-2 lg:hidden",
```

2. No borres el `div`: en móvil el botón X sigue haciendo falta.
3. Comprueba que el primer `RotuloDeGrupo` ("Organización") queda a la
   altura del borde inferior del header, sin hueco.

**Criterio de aceptación (TC-F0-03).** En desktop, el rótulo "Organización"
del sidebar empieza inmediatamente debajo de la línea que separa el header.
En móvil (ancho < 1024px), al abrir el menú sigue apareciendo el botón X.

**Commit.**

```
fix(web): BUG-C — sidebar arranca pegado al header en desktop
```

## Verificación antes de push

```bash
pnpm --filter @pmoaas/web exec tsc --noEmit   # exit 0
python scripts/check_tokens.py                # exit 0
python scripts/check_contexto.py              # exit 0
```

Si alguno no da `exit 0`, es tuyo: corrígelo antes de seguir.

## Cierre

1. `git push -u origin claude/revamp-v2-f0-bugs`.
2. Abre PR contra `main` con título `Revamp v2 — fase 0: bugs visibles`.
   En el cuerpo lista los tres TC y cómo los verificaste.
3. Skill `cerrar-item` por cada BUG (comment con evidencia).
4. En `../REVAMP-V2-FEEDBACK.md`, punto 13: estado `hecho` + los tres
   commits. En el punto 2.4, tacha la primera viñeta (sidebar pegado).
5. No toques `SPRINT.md` salvo para mover la fase 0 a hecha en la línea
   "Ejecutar `REVAMP-V2-PLAN.md`".

## Qué NO hacer

- No cambiar el diseño de la tabla RAID más allá de wrap/scroll.
- No renombrar tabs ni cambiar sus `href`.
- No tocar `GRUPOS_NAV` ni el header (eso es fase 1).
