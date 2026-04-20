# Inventario de Componentes

**ID:** `DOC-DS-COMPONENTS`

Inventario organizado por categoría. Cada componente tiene anatomía, variantes, props clave y cuándo usarlo.

Paquete: `packages/ui/src/components/*`. Stories en Storybook: `pnpm storybook`.

---

## 1. Primitivos (base shadcn, tematizados)

### Button

**Anatomía:** icono (opcional) + label + keyboard hint (opcional).

**Variantes:** `primary`, `secondary`, `ghost`, `danger`, `link`.

**Tamaños:** `sm` (28px), `md` (36px — default), `lg` (44px — touch targets).

```tsx
<Button variant="primary" size="md" leftIcon={<Plus />}>Nuevo proyecto</Button>
```

Estados: hover, active, focus-visible, disabled, loading (spinner + label no cambia).

### Input, Textarea, Select, Combobox

- Altura `md` (36px) por default, `sm` (28px) en filtros densos.
- Borde sutil, focus ring brand.
- Errores con `--color-danger` + mensaje abajo.
- `Combobox` con autocompletar server-side (debounce 200ms).

### Switch

iOS-style: pista redondeada, thumb con sombra sutil. Animación 200ms `cubic-bezier(0.32, 0.72, 0, 1)`.

### Checkbox, Radio

Para listas y formularios largos. En toolbars preferimos switches/segmented.

### Segmented Control

Grupo de 2-5 opciones mutuamente excluyentes. Usado para filtros de estado ("En revisión / Aprobadas / Rechazadas").

### Badge

Chips con estado (`neutral`, `success`, `warning`, `danger`, `info`). Ícono opcional. Tamaño `xs` (20px) y `sm` (24px).

### Avatar

Foto, iniciales fallback sobre color derivado del nombre. Tamaños xs/sm/md/lg (20/28/36/48).

### Tooltip

Sobre cualquier elemento con `data-tooltip`. Delay 500ms. Apple-style: fondo oscuro semi-transparente con blur.

---

## 2. Layout

### AppShell

Layout root:
- Sidebar izquierdo (fijo desktop, drawer mobile).
- Header con breadcrumb + tenant switcher + avatar + Cmd+K.
- Main area con scroll propio.
- Drawer lateral derecho (contextual, condicional).

### Sidebar

- Logo tenant arriba.
- Navegación principal en árbol con dropdowns anidados (hasta 3 niveles):
  1. **Tablero** — enlace directo a `/dashboard`.
  2. **Organizaciones** (dropdown, enlace a `/admin/organizations`).
     - Solicitudes — `/admin/requests`.
     - Programas — `/admin/programs`.
     - Proyectos (sub-dropdown, enlace a `/admin/projects`).
       - Módulos de Proyectos (sub-grupo) — contiene todos los módulos: Riesgos, AIDs, Cambios, Documentos, Lecciones, Minutas, Tareas, Gantt, Minuta IA, Reporte IA. Los módulos apuntan al proyecto activo cuando la ruta es `/admin/projects/:id/...`; de lo contrario regresan al listado `/admin/projects`.
  3. **Admin** (dropdown).
     - Panel del Tenant — `/admin/supervision` (anteriormente "Supervisión").
     - Usuarios — `/admin/users`.
     - Roles — `/admin/roles`.
     - Auditoría — `/admin/audit-logs`.
     - Configuración — `/admin/settings`.
- Super admin: sección adicional sólo visible para `is_superadmin` (Visión general, Tenants, Logs platform, Health).
- Los grupos con `href` + `children` actúan como link **y** toggle: clic en el label navega, clic en el chevron (derecha) expande/colapsa.
- Auto-expand: al cargar o navegar, se expanden las ramas que contienen la ruta activa.
- Item activo con pill de fondo (no border).
- Cada nivel de anidación agrega `0.75rem` de indent al padding-left.
- Acrylic/vibrancy background.

### Breadcrumb

`PMO > Org > Programa > Proyecto > Módulo`. Cada segmento link. Chevrones `/` entre ellos. Overflow: trunca y muestra `…` (clic expande).

### Tabs

Para secciones del detalle de proyecto. Estilo macOS: underline sutil al activo, no bordes fuertes.

### Drawer (slide sheet)

Desde la derecha, 520px default (responsive). Overlay semi-transparente. Close: esc, clic en overlay, gesture arrastrar.

### Modal

Para acciones destructivas o formularios cortos. Centrado, max-width 480px. Blur heavy en overlay.

### Toast

Esquina inferior derecha. Max 3 simultáneos. Auto-dismiss 5s (errores 10s). Variantes: success, warning, error, info.

---

## 3. Datos

### DataTable

Tabla con:
- Header sticky.
- Orden por columna (flechas arriba/abajo).
- Selección (checkbox por fila + header).
- Paginación o infinite scroll.
- Modo denso/cómodo (toggle en toolbar).
- Row hover revela acciones (ícono-only, no visibles siempre).
- Column visibility configurable (menú en esquina).

Usa **@tanstack/react-table** debajo.

### DataCard

Para mobile o cards-view de listados. Agrupa campos clave + acciones.

### EmptyState

Ilustración + título + descripción + 1 CTA. Centrado vertical en el container.

### Skeleton

Placeholder animado para loading. Evitar shimmer rápido — pulso suave 2s.

### KPI Card

Número grande + label + tendencia opcional (↑/↓ %) + sparkline opcional. Clickeable con hover sutil.

---

## 4. Formularios

### Form (con react-hook-form + zod)

Envuelve campos, maneja estado, errores, submit.

### Field

Label + input + helper/error text. Manejo a11y con `<label for>` y `aria-describedby`.

### DatePicker, DateRangePicker

Calendario popover. Keyboard navegable. Respeta locale del tenant. Librería: **react-day-picker**.

### FileUpload

Dropzone + preview + progress. Multi-file. Drag&drop visual feedback. Validación MIME/size inline.

### MoneyInput

Con formato `$1,234.56`, prefix configurable por moneda del tenant.

### TagInput

Para tags de lecciones: input + chips.

---

## 5. Navegación

### CommandPalette (Cmd+K)

- Librería `cmdk`.
- Secciones: Go to, Actions, Search results.
- Iconos + shortcuts a la derecha.
- Preview de resultado al focar (como Raycast).

### ContextMenu

Click derecho sobre tablas/elementos. Acciones relevantes.

### Pagination

Números de página + botones prev/next + jump-to. En tablas densas, "Page X of Y" compacto.

---

## 6. Específicos del dominio

### PhaseBadge

Badge con color por fase: planning (azul claro), execution (verde), support (amarillo), closed (gris).

### HealthIndicator

Punto de color (8px) + texto opcional. Animación pulse si red.

### SeverityMatrix (5×5)

Grid 5×5 de celdas coloreadas (verde/amarillo/rojo según P×I). Hover muestra count de riesgos. Click filtra listado.

### ProjectTree

Árbol jerárquico Org → Programa → Proyecto. Expandible. Usado en sidebar y selectors.

### GanttChart

Wrapper sobre **frappe-gantt**. Props: tasks, dependencies, zoom level, onTaskClick. Responsive a tema.

### MoneyDisplay

Formatea con moneda del tenant. Variantes: `compact` ($1.2K), `full` ($1,234.56).

### DiffView

Muestra cambios antes/después (útil en audit log detail).

### StatusTimeline

Línea vertical con eventos (cambios de fase, aprobaciones). Usado en detail de solicitudes y cambios.

### RichTextEditor

Para reportes y comentarios largos. Librería: **Tiptap** (ProseMirror). Toolbar mínima. Soporta mentions `@user`.

### AIBadge

Identifica contenido generado por IA: icono sparkle + tooltip con modelo usado. Distingue claramente lo humano de lo AI-generated.

### CopyableText

Span con hover que revela botón copy. Util para folios, IDs.

### FolioBadge

Mono-font pill con folio: `PRJ-2026-001`. Copyable.

---

## 7. Patrones compuestos

### ModuleShell

Compuesto: Header (title + counter + "+ New") → Filters bar → DataTable → Pagination.

Recibe config declarativa por módulo y renderiza todo. Usado por los 6 módulos de proyecto.

### RecordDrawer

Drawer con secciones Info / Historial / Comentarios. Abrir desde DataTable row click.

### ImportWizard

3 pasos: Upload → Preview → Confirm. Usado para importación MS Project.

---

## Anti-patrones (NO hacer)

- ❌ Texto en negrita como única forma de jerarquía (usar tamaño + peso).
- ❌ Más de 3 colores primarios en una vista.
- ❌ Badges con todos los colores encendidos al mismo tiempo (visual ruido).
- ❌ Modales anidados.
- ❌ Tooltips sobre elementos interactivos visibles (son distractores).
- ❌ Animaciones mayores a 400ms en UI (solo hero landings).
- ❌ Sombras duras `0 4px 8px rgba(0,0,0,0.5)`.
- ❌ Iconos de distintas familias mezclados (Lucide + Material + Emoji).
