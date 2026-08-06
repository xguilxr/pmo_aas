---
tipo: referencia
responsable: propietario
estado: vigente
revisado: 2026-05-08
revisar_cada: 90d
---

# Design System — PMO-aaS

**ID:** `DOC-DS`

## Principios (inspirados en Apple / HIG)

1. **Claridad.** Jerarquía visual antes que decoración. La tipografía hace el peso, no los bordes.
2. **Deferencia.** La UI cede protagonismo al contenido. Superficies neutras, color sólo para significado.
3. **Profundidad con materiales.** Blur/vibrancy suave para separar capas (sidebar, modals, drawers), sin sombras pesadas.
4. **Movimiento con propósito.** Cada transición comunica: dónde vienes, adónde vas, qué cambió. Easing natural (cubic-bezier 0.32, 0.72, 0, 1).
5. **Consistencia cross-plataforma.** Funciona perfecto en Mac Safari, iPad Safari, Chrome desktop.
6. **Accesibilidad nativa.** WCAG AA en contraste, focus rings visibles, reduced-motion respetado.

---

## Estructura de archivos

| Archivo | Contenido |
|---|---|
| [`tokens.md`](./tokens.md) | Colores, tipografía, radios, spacing, sombras |
| [`components.md`](./components.md) | Inventario de componentes con anatomía |
| [`motion.md`](./motion.md) | Curvas, duraciones, patrones |

---

## Librería base

- **shadcn/ui** — copiamos componentes, no dependemos del paquete. Adaptamos a nuestros tokens.
- **Radix UI** (base headless de shadcn) — accesibilidad probada.
- **Tailwind CSS v4** — sistema de tokens con `@theme`.
- **Framer Motion** — animaciones complejas.
- **lucide-react** + **@phosphor-icons/react** — set principal.
- **Geist Mono / Geist Sans** o **Inter var** + **SF Pro (fallback via CDN)** — tipografía.

---

## Patrones clave

### 1. Superficies y jerarquía

Tres niveles de elevación, todas con blur sutil (backdrop-filter) en vez de sombras duras:

```css
.surface-app      { background: var(--bg-base); }
.surface-elevated { background: var(--bg-elevated); backdrop-filter: blur(20px); }
.surface-overlay  { background: var(--bg-overlay);  backdrop-filter: blur(40px) saturate(1.4); }
```

### 2. Transiciones de página

Next.js App Router + Framer Motion `<AnimatePresence>`. Transición default: `slide + fade` en 240 ms con easing Apple.

### 3. Drawers y sheets (no modals)

Para detalle de módulos (riesgo, incidencia, doc): **drawer desde la derecha**, 520px de ancho, empuja contenido detrás con `translate-x` ligero. Cerrar con gesture (arrastrar hacia la derecha en trackpad/touch) o tecla `Esc`.

### 4. Sidebar translúcido

Como el Finder: lista vertical con acrylic/vibrancy. Items con icono + label, estado activo con pill de fondo sutil (no un border). Los grupos se organizan en dropdowns anidados (Tablero · Organizaciones · Admin) con toggle por chevron y auto-expand según la ruta activa. Ver `components.md § Sidebar` para el mapa completo.

### 5. Controles táctiles estilo iOS/macOS

- **Switches** en vez de checkboxes para toggles booleanos.
- **Segmented control** para tabs pequeñas (estados de módulo).
- **Stepper numérico** con `+/-` y arrastre horizontal.

### 6. Empty states ilustrados

Cada vista sin datos muestra: ilustración limpia (outline), título corto, 1 CTA.
Librería: **unDraw** con override de color al primario.

### 7. Gráficos

- Sin grid pesada. Ejes con líneas finas (1px, 20% opacidad).
- Colores del design system únicamente (evitar paletas full chroma).
- Tooltips flotantes con blur background.

---

## Densidad de información

Dos modos:

| Modo | Cuándo | Detalle |
|---|---|---|
| `comfortable` (default) | Lectura, dashboard | Más aire, 44px row height |
| `compact` | Tablas admin, listados largos | 32px row height, tipografía 13px |

Toggle en `user.preferences.density`.

---

## Dark mode

Obligatorio desde día 1. Siguiendo HIG macOS Sonoma/Sequoia:

- **Fondos fríos** (no #000 puro), matiz ligero hacia azul.
- **Elevaciones** con luminosidad creciente (no sombras).
- **Color accent** mantiene consistencia (mismo tono en ambos modos).

Activación: `media (prefers-color-scheme: dark)` + override manual en `user.preferences.theme`.

---

## Iconografía

- **Lucide** como base (geométricos, 2px stroke).
- **Phosphor duotone** para hero illustrations en empty states.
- Evitar emoji en UI (dejar a los usuarios).

---

## Ejemplos de referencia

- **macOS Finder**: sidebar, navegación, Quick Look.
- **Linear**: transitions entre views, command bar (`Cmd+K`).
- **Notion**: drag&drop de bloques (para editor de reportes).
- **Things (Cultured Code)**: check animations, progress subtle.
- **Raycast**: command palette con preview.

---

## `Cmd+K` command palette (requerido)

Accesible desde cualquier pantalla. Integra:

- Navegación rápida: `Ir a proyecto…`, `Ir a módulo…`.
- Acciones: `Crear solicitud`, `Nuevo riesgo`, `Generar minuta con IA`.
- Búsqueda global: proyectos, documentos, minutas (server-side, debounced).
- Atajos: `?` muestra lista de keybindings.

Librería: **cmdk** + nuestro design system.

---

## Responsive

| Breakpoint | Tailwind | Target |
|---|---|---|
| Mobile | < 640 | iPhone Safari |
| Tablet | 640-1024 | iPad Safari |
| Desktop | ≥ 1024 | Mac Safari/Chrome |
| Wide | ≥ 1440 | Monitores externos |

**Mobile**: sidebar se colapsa a bottom nav con 5 items max. Drawers ocupan 100% del viewport.

---

## Accesibilidad

- Focus ring visible (2px, accent color) siempre.
- Soporte completo de teclado: Tab, Shift+Tab, flechas en listas.
- `prefers-reduced-motion` deshabilita animaciones no esenciales.
- Contraste AA en todo texto (mínimo 4.5:1).
- Screen-reader friendly: headings correctos, aria-labels en iconos solos.
- Tests con `@axe-core/playwright` gating CI.
