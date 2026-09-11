---
tipo: gestion
responsable: propietario
estado: vigente
revisado: 2026-09-11
revisar_cada: 30d
---

# FASE 4 — PMO: Gantt por año, lista ordenada, Board e Importar adentro, config de portafolios

**Qué es.** `/pmo` pasa a ser la página única de portafolio: Gantt trimestral
navegable por año, lista de proyectos ordenada, Board e importación de
proyectos como pestañas, y `/pmo/config` para portafolios y programas.
Puntos 2.2 y 4 de `../REVAMP-V2-FEEDBACK.md`. Wireframes **W2** (PMO) y
**W3** (config).
**Tamaño:** XL. **Gate:** fase 3 mergeada, W2 y W3 aprobados, decisión
**D3** (portafolio-programa base). **Epics:** EP002 (jerarquía), EP005
(proyectos). Si D3 siembra filas: `DB-CHANGES.md` + `DECISIONS.md`.

**Reglas.** Cinco commits en orden. Cada uno deja `/pmo` usable. La
migración (si D3 la pide) va en su propio commit y es la única de la fase.

## Preparación

```bash
git fetch origin main
git checkout -b claude/revamp-v2-f4-pmo origin/main
pnpm install --frozen-lockfile
python scripts/proximo_id.py
cd apps/api && alembic heads    # anota la revisión head; la migración nueva cuelga de ella
```

## Hechos verificados

- `apps/web/components/roadmap-trimestral.tsx`: el año se calcula en el
  default del parámetro, línea 49 (`year = new Date().getFullYear()`), y el
  trimestre actual en la línea 56. Solo pinta un año.
- `apps/web/app/(app)/pmo/page.tsx`: `RoadmapTrimestral` se monta en la
  línea 545 (`proyectos={proyectosRoadmap} portafolios={portfolios}`);
  `VistaMaestra` en la 549. La carga de `proyectosRoadmap` (líneas ~199-220)
  llama `listProjects` con `limit: 200`.
- `apps/web/components/vista-maestra.tsx:551`: `VistaMaestra({ filas,
  cargando, puedeEditar, siempreVisibles, onSalud, onPrioridad, onDesglose })`.
  Sin prop de orden: ordena por dentro con `useSortableRows(filas)` (línea
  581), que respeta el orden de entrada hasta que el usuario hace clic en
  una columna.
- `PlanVsActualRow` (`apps/web/lib/api/dashboard.ts:109-140`) ya trae
  `portfolio_name`, `program_id`, `program_name`.
- `/pmo/board/page.tsx`: llama `getPortfolioBoard({ organization_id })`
  (línea 82) → `GET /api/v1/dashboard/portfolio-board`.
- `/pmo/imports/page.tsx`: importador con `kind = projects | resources`
  (`apps/api/app/api/v1/endpoints/importacion.py`: `GET /columns` :108,
  `POST /preview` :142, `POST /{job_id}/confirm` :309).
- API de portafolios y programas ya completa en
  `apps/web/lib/api/organizations.ts`: `listPortfolios` :340,
  `createPortfolio` :353, `updatePortfolio` :363, `deletePortfolio` :372,
  `hardDeletePortfolio` :304; `createProgram` :252, `updateProgram` :256,
  `deleteProgram` :260, `hardDeleteProgram` :280. **No hay UI** que use
  `createPortfolio`, `updatePortfolio` ni `updateProgram`.
- `program-modal.tsx` solo crea programas.

## Commit 1 — Gantt navegable por año (US-A)

**Archivo:** `components/roadmap-trimestral.tsx` y `pmo/page.tsx`.

1. Cambia la firma: `year` deja de tener default y pasa a ser obligatorio;
   agrega `onYearChange: (y: number) => void`. Quita el cálculo de la
   línea 49.
2. En la cabecera del componente (donde está el `<h3>` "Roadmap
   trimestral, {year}") pon a la derecha del título un control de año:
   botón `‹`, el año en `font-mono`, botón `›`. Cada botón llama
   `onYearChange(year ± 1)`. Límite inferior: 2026 (el owner pide "todo a
   partir del 26 hacia adelante"); no hay límite superior.
3. En `pmo/page.tsx`, estado `const [anio, setAnio] = useState(Math.max(2026, new Date().getFullYear()))`
   y pásalo: `<RoadmapTrimestral … year={anio} onYearChange={setAnio} />`.
4. La carga de `proyectosRoadmap` no depende del año (trae todos los
   proyectos filtrados); el recorte por año ya lo hace el componente
   (`trimestreEn`). Verifica que un proyecto 2026-11 → 2027-03 aparece en
   2026 (Q4) y en 2027 (Q1) al cambiar de año.
5. El mensaje vacío ("Ningún proyecto visible tiene fecha…") debe incluir
   el año seleccionado.

**TC-F4-01.** Con proyectos en 2026 y 2027, `‹ 2026 ›` muestra los de 2026;
`›` pasa a 2027 y muestra los de 2027; `‹` desde 2026 no baja.

```
feat(pmo): US-A — roadmap trimestral navegable por año, desde 2026 (refs REVAMP-V2 §4)
```

## Commit 2 — lista ordenada portafolio → programa → nombre (US-B)

1. En `pmo/page.tsx`, donde se calcula `visibles` (línea ~218, `useMemo`
   que filtra por salud), ordena el resultado antes de devolverlo:

```ts
.sort((a, b) =>
  (a.portfolio_name ?? "￿").localeCompare(b.portfolio_name ?? "￿", "es") ||
  (a.program_name ?? "￿").localeCompare(b.program_name ?? "￿", "es") ||
  a.name.localeCompare(b.name, "es"))
```

   `￿` manda los "sin portafolio"/"sin programa" al final.
2. Pasa `siempreVisibles={["portfolio", "program"]}` (revisa en
   `vista-maestra.tsx` los ids de columna exactos con
   `grep -n '"portfolio"\|"program"' apps/web/components/vista-maestra.tsx`;
   si las columnas no existen, agrégalas al catálogo de columnas de la
   vista maestra, después de "Proyecto").
3. La columna "Organización" (`COLUMNA_ORG`, línea 72) solo se muestra
   cuando `agrega` (ya es así); no cambies eso.

**TC-F4-02.** La lista bajo el Gantt sale agrupada visualmente por
portafolio y programa sin encabezados de grupo, y los "sin portafolio" al
final.

```
feat(pmo): US-B — vista maestra ordenada por portafolio, programa y nombre
```

## Commit 3 — Board e Importar como pestañas de /pmo (US-C)

1. Extrae el cuerpo de `pmo/board/page.tsx` (todo lo que hay dentro del
   `return`, más sus hooks) a `components/board-de-portafolio.tsx`,
   exportando `BoardDePortafolio()`. `pmo/board/page.tsx` queda como
   `return <BoardDePortafolio />` temporalmente.
2. Igual con `pmo/imports/page.tsx` → `components/importador.tsx`,
   `Importador({ kind }: { kind: "projects" | "resources" })`. La página
   de imports queda `return <Importador kind="projects" />` (la clase
   `resources` se reubica en la fase 6).
3. En `pmo/page.tsx`, arriba del roadmap, una barra de pestañas con el
   patrón de `components/project-tabs-bar.tsx` (mismas clases de activo):
   `Portafolio | Board | Importar proyectos`. El tab activo se guarda en la
   URL (`?tab=board`, `?tab=importar`) con `useSearchParams` como ya hace la
   página con los filtros (`cambiarFiltro`, línea 121).
   - `Portafolio` (default): roadmap + vista maestra + salud por dimensión.
   - `Board`: `<BoardDePortafolio />`.
   - `Importar proyectos`: `<Importador kind="projects" />`.
4. Redirects en `apps/web/next.config.js`, dentro de `redirects()` (líneas
   5-94, sigue el formato de los existentes, `permanent: true`):
   - `/pmo/board` → `/pmo?tab=board`
   - `/pmo/imports` → `/pmo?tab=importar`
5. Borra `pmo/board/page.tsx` y `pmo/imports/page.tsx` (ya redirigidos).
6. Quita de `pmo/page.tsx` los dos `<Link>` temporales de la fase 1.
7. `docs/architecture/navigation.md`: `/pmo/board` y `/pmo/imports` pasan
   a "redirigidas".

**TC-F4-03.** `/pmo?tab=board` muestra el board; `/pmo/board` redirige;
`/pmo/imports` redirige; el importador de proyectos funciona igual que
antes (preview + confirm).

```
feat(pmo): US-C — Board e importación de proyectos como pestañas de /pmo
```

## Commit 4 — portafolio-programa base (US-D, solo si D3 = sembrar)

**Decisión D3.** Opción recomendada: cada organización tiene un portafolio
`code = "BASE"` y dentro un programa "General"; los proyectos sin
portafolio/programa se asignan ahí al crearse.

1. Migración Alembic (`cd apps/api && alembic revision -m "portafolio_programa_base_por_organizacion"`):
   - `upgrade`: para cada `organizations` activa sin `portfolios.code = 'BASE'`,
     inserta un `Portfolio(name="Base", code="BASE", is_active=True)` y un
     `Program(name="General", portfolio_id=<ese>, is_active=True)`. Luego
     `UPDATE projects SET portfolio_id=<base>, program_id=<general> WHERE
     organization_id=<org> AND portfolio_id IS NULL`.
   - `downgrade`: pone a NULL `portfolio_id`/`program_id` de los proyectos
     que apuntan a un `BASE` y borra esos programas y portafolios.
   - Usa `op.get_bind()` y SQL explícito, no los modelos ORM (las
     migraciones no importan modelos en este repo; mira una migración
     reciente como plantilla).
2. Backend: en la creación de proyecto
   (`apps/api/app/api/v1/endpoints/projects.py`, `POST ""`), si
   `portfolio_id` viene vacío, resolver el `BASE` de la organización. Igual
   en la aprobación de solicitud que crea el proyecto
   (`project_requests.py`).
3. Backend: en la creación de organización (`organizations.py:213`), crear
   el par base en la misma transacción.
4. Test: `apps/api/tests/test_<us>_portafolio_base.py` — crear organización
   → existe BASE/General; crear proyecto sin portafolio → cae en BASE.
5. `docs/epics/DB-CHANGES.md` (tabla de la migración) y
   `docs/epics/DECISIONS.md` (`DEC-###` D3). `EP002`: regla del base.

**TC-F4-04.** `pytest -q -n auto -m "not heavy"` exit 0. Una organización
nueva tiene BASE/General. Un proyecto creado sin portafolio aparece en el
Gantt bajo "Base".

```
feat(org): US-D — portafolio y programa base por organización (mig. <rev>, DEC-###)
```

Si D3 = "calcular sin sembrar": omite este commit y en la fase 8 el árbol
muestra "Sin portafolio" como grupo virtual (la vista maestra ya lo hace).

## Commit 5 — /pmo/config: portafolios y programas (US-E)

**Ruta nueva:** `apps/web/app/(app)/pmo/config/page.tsx`. Diseño: W3.

1. Lista de portafolios de la organización activa (`listPortfolios(orgId, { is_active: true })`),
   cada uno desplegable con sus programas (`listPrograms({ organization_id, portfolio_id })`)
   y dentro sus proyectos (`listProjects({ organization_id, program_id })`)
   — "estilo carpetas".
2. Formulario de portafolio (nuevo, `components/portfolio-form.tsx`):
   campos `name`, `code`, `description`, `owner_actor_id` (selector de
   actores: reusa `PersonPicker` de `components/directory/` si existe;
   `grep -rn "export function PersonPicker" apps/web/components`),
   `is_active`. Crea con `createPortfolio`, edita con `updatePortfolio`.
3. Programa: extiende `program-modal.tsx` para editar (`updateProgram`,
   `ProgramUpdateBody` :182) además de crear. Campos: los de
   `ProgramCreateBody` :170.
4. Mover proyecto: en cada fila de proyecto, un `Select` de programa; al
   cambiar llama `updateProject(id, { program_id, portfolio_id })` (el
   backend valida que el programa pertenezca al portafolio, US-199).
5. Borrar: `deletePortfolio`/`deleteProgram` (soft). El borrado permanente
   (`hardDelete*`) **no** va aquí: es de Admin (fase 7).
6. Botón "Configurar portafolios y programas" en la cabecera de `/pmo`
   (junto a "Nuevo programa"), visible si `canUpdate("portfolios")` o el
   permiso equivalente (`useMyPermissions`).
7. Sidebar: `/pmo/config` se marca bajo "PMO" (el `match` de la fase 1 ya
   cubre `/pmo/*` salvo projects/resources/requests/reports; verifica).

**TC-F4-05.** Crear portafolio → aparece; crear programa dentro → aparece;
mover un proyecto de programa → la vista maestra y el Gantt lo reflejan;
borrar un programa vacío → desaparece; borrar uno con proyectos → el
backend rechaza y la UI muestra el mensaje.

```
feat(pmo): US-E — /pmo/config: alta, edición y reasignación de portafolios y programas
```

## Verificación antes de push

```bash
pnpm --filter @pmoaas/web exec tsc --noEmit
python scripts/check_tokens.py
cd apps/api && .venv/bin/python -m ruff check . && .venv/bin/python -m pytest -q -n auto -m "not heavy"
python scripts/check_impacto_documental.py
```

## Cierre

PR `Revamp v2 — fase 4: PMO`. `cerrar-item` × 5. Feedback: 2.2 (PMO) y 4 →
`hecho`. `SPRINT.md` → "5 (proyectos)". Antes: W6 aprobado.

## Qué NO hacer

- No mover el importador de recursos todavía (fase 6).
- No borrar `/pmo/programs/[id]` ni `/pmo/organizations/[id]`: siguen
  siendo el detalle al que se llega desde `/pmo/config`.
- No hacer borrado permanente desde `/pmo/config`.
