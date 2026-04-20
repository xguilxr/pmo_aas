# Design System — PMO Platform

**ID:** `DOC-DESIGN-STYLE`
**Audiencia:** agentes de código (Claude Code, Cursor) y devs humanos.
**Stack objetivo:** Next.js 15 + Tailwind CSS v4 + shadcn/ui + Radix.

Esta guía define el lenguaje visual de la plataforma PMO. Es la **fuente de verdad** para tokens, componentes y patrones. Cualquier UI debe compilar contra estos tokens — no inventes colores, tamaños, radios o sombras fuera de esta lista.

---

## 1. Principios de diseño

1. **Claridad sobre decoración.** La plataforma existe para que un PMO tome decisiones rápido: el diseño nunca debe competir con los datos.
2. **Neutros primero, color como señal.** Fondo y superficies en blanco/gris cálido. El color se reserva para estados (activo, en riesgo, bloqueado) y acciones primarias.
3. **Densidad legible.** Tablas densas pero con aire suficiente: line-height generoso, separadores sutiles, tipografía con tracking abierto en tamaños pequeños.
4. **Un solo nivel de énfasis por vista.** Como máximo un botón primario y un estado destacado por pantalla.
5. **Bordes antes que sombras.** La jerarquía se construye con `border` de 1px y tonos de superficie, no con drop-shadows pronunciados.
6. **Consistencia antes que creatividad.** Si un patrón ya existe en este documento, úsalo. Si necesitas uno nuevo, agrégalo aquí primero.
7. **Accesibilidad es default.** Contraste mínimo AA (4.5:1 texto normal, 3:1 texto grande / UI). Focus visible siempre.

### Tono de voz (UI copy)
- Directo, sin jerga corporativa. Evita "sinergias", "empoderar", "experiencia".
- Verbos de acción en imperativo: *Crear proyecto*, no *Creación de proyecto*.
- Etiquetas cortas (1–3 palabras). Descripciones debajo si hace falta contexto.
- Números siempre con separador de miles (`1,384`). Fechas: `11 August 2022` (día mes año, sin coma).

---

## 2. Tokens de color

### 2.1 Escala neutra (cálida, baja saturación)

Basada en `oklch` para transiciones perceptualmente uniformes. Tinte cálido ≈ hue 80, croma ≤ 0.01 (casi neutral puro).

| Token | Valor | Uso |
|---|---|---|
| `--neutral-0` | `oklch(100% 0 0)` | Fondo de tarjetas, modales, inputs |
| `--neutral-50` | `oklch(98.5% 0.003 80)` | Fondo app, fondo de tabla header |
| `--neutral-100` | `oklch(96.8% 0.004 80)` | Hover sutil, filas alternas |
| `--neutral-200` | `oklch(92.5% 0.005 80)` | Bordes de cards, dividers |
| `--neutral-300` | `oklch(87% 0.006 80)` | Bordes de inputs, outlines |
| `--neutral-400` | `oklch(70% 0.008 80)` | Iconos disabled, placeholders |
| `--neutral-500` | `oklch(55% 0.009 80)` | Texto secundario, labels de tabla |
| `--neutral-600` | `oklch(42% 0.009 80)` | Texto body |
| `--neutral-700` | `oklch(30% 0.008 80)` | Texto énfasis, iconos activos |
| `--neutral-800` | `oklch(20% 0.006 80)` | Headings, botón primario (fondo) |
| `--neutral-900` | `oklch(12% 0.004 80)` | Texto fuerte, modo oscuro superficie |
| `--neutral-950` | `oklch(7% 0.003 80)` | Dark mode background |

### 2.2 Acentos de estado (pastel, misma lightness/croma)

Todos comparten `L≈88%` (fondo) / `L≈45%` (texto) / `L≈70%` (borde) y `C≈0.08`. Cambiamos sólo el hue.

| Estado | Hue | Fondo | Borde | Texto |
|---|---|---|---|---|
| Success / Active | `155` (verde) | `oklch(94% 0.05 155)` | `oklch(82% 0.09 155)` | `oklch(42% 0.11 155)` |
| Warning / Onboarding | `85` (ámbar) | `oklch(95% 0.06 85)` | `oklch(84% 0.11 85)` | `oklch(45% 0.13 85)` |
| Danger / Inactive | `25` (rojo-rosa) | `oklch(94% 0.04 25)` | `oklch(82% 0.08 25)` | `oklch(48% 0.13 25)` |
| Info / In review | `240` (azul) | `oklch(94% 0.04 240)` | `oklch(82% 0.08 240)` | `oklch(46% 0.12 240)` |
| Neutral / Draft | — | `var(--neutral-100)` | `var(--neutral-300)` | `var(--neutral-600)` |

> No uses los acentos para superficies grandes (fondos de sección, botones primarios). Sólo para badges, dots, barras finas, iconos de estado y deltas numéricos.

### 2.3 Tokens semánticos

```css
:root {
  --bg-app:         var(--neutral-50);
  --bg-surface:     var(--neutral-0);
  --bg-subtle:      var(--neutral-100);
  --bg-muted:       var(--neutral-200);

  --border-subtle:  var(--neutral-200);
  --border-default: var(--neutral-300);
  --border-strong:  var(--neutral-400);

  --text-primary:   var(--neutral-800);
  --text-secondary: var(--neutral-600);
  --text-tertiary:  var(--neutral-500);
  --text-disabled:  var(--neutral-400);
  --text-inverse:   var(--neutral-0);

  --accent-primary-bg:    var(--neutral-800);
  --accent-primary-fg:    var(--neutral-0);
  --accent-primary-hover: var(--neutral-900);

  --focus-ring:     oklch(55% 0.15 240);

  /* Chrome (sidebar + topbar) — NAVY #182e4e (DEC-006, fuente de verdad) */
  --chrome-bg:             #182e4e;
  --chrome-bg-translucent: color-mix(in oklab, #182e4e 92%, transparent);
  --chrome-border:         #10203a;
  --chrome-text:           #F0F3FF;
  --chrome-text-muted:     #A7B0D9;
  --chrome-hover:          #24406a;
  --chrome-active:         #10203a;

  --chrome-soft-bg:     oklch(97% 0.012 240);
  --chrome-soft-border: oklch(90% 0.018 240);
  --chrome-soft-text:   oklch(36% 0.025 240);
}
```

### 2.4 Dark mode

No negro puro: base `oklch(22%)` con tinte azulado.

---

## 3. Tipografía

**Familia única: DM Sans.** Pesos 400, 500, 600, 700. Fallback `ui-sans-serif, system-ui, sans-serif`.
**Mono:** JetBrains Mono para IDs y celdas numéricas.

### 3.1 Escala

| Nombre | Tamaño | Line-height | Weight | Letter-spacing | Uso |
|---|---|---|---|---|---|
| `display` | 32px | 1.2 | 700 | -0.02em | H1 páginas |
| `h1` | 24px | 1.25 | 700 | -0.015em | Títulos sección |
| `h2` | 20px | 1.3 | 600 | -0.01em | Títulos card |
| `h3` | 18px | 1.35 | 600 | -0.005em | Subheadings |
| `body-lg` | 16px | 1.5 | 400 | 0 | Texto formularios |
| `body` | 14px | 1.5 | 400 | 0 | **Default** |
| `body-sm` | 13px | 1.45 | 400 | 0 | Texto secundario |
| `label` | 12px | 1.35 | 500 | 0.01em | Labels |
| `caption` | 11px | 1.3 | 500 | 0.02em | Metadata |
| `kpi` | 28px | 1.1 | 700 | -0.02em | Números KPI |
| `mono-sm` | 12px | 1.4 | 500 | 0 | IDs |

### 3.2 Reglas
- Nunca `font-weight` > 700.
- `tabular-nums` en columnas numéricas.
- Alineación izquierda por defecto.
- `text-wrap: pretty` en párrafos largos.

---

## 4. Espaciado

Escala base **4px**. Usa sólo múltiplos.

| Token | px |
|---|---|
| `space-1` | 4 |
| `space-2` | 8 |
| `space-3` | 12 |
| `space-4` | 16 |
| `space-5` | 20 |
| `space-6` | 24 |
| `space-8` | 32 |
| `space-10` | 40 |
| `space-12` | 48 |
| `space-16` | 64 |

### Layout

- **Sidebar:** 240px (chrome azul translúcido), 64px colapsado.
- **Topbar:** 56px.
- **Main:** padding `24px 32px`, max 1440px en ≥1600px.
- **Grid:** 12 cols, gutter 24px.

---

## 5. Radios, bordes, sombras

| Token | Valor | Uso |
|---|---|---|
| `radius-xs` | 4px | Checkbox |
| `radius-sm` | 6px | Inputs, chips |
| `radius-md` | 8px | **Default** botones |
| `radius-lg` | 12px | Cards, modales |
| `radius-xl` | 16px | Contenedores grandes |
| `radius-full` | 9999px | Avatares, badges pill |

- Bordes: siempre `1px solid`. Nunca 2px excepto focus outline.
- Cards **NO** llevan sombra. Sombras sólo para flotantes (dropdown, popover, modal, toast).

---

## 6. Componentes base

### Button
| Variant | Uso |
|---|---|
| `primary` | Acción principal |
| `secondary` | Apoyo |
| `ghost` | Terciaria |
| `danger` | Destructiva |
| `link` | Navegación inline |

Tamaños `sm` (h-8) · `md` (h-9) · `lg` (h-10).

### Input
- Altura default 36px (`h-9`).
- Error: borde `danger-border` + texto `danger-fg`.

### Badge
- Altura fija 24px, con borde.
- Dot opcional cuando sustituye semáforo.

### Card
- Padding 20px, sin sombra, borde `subtle`.

### KPI Card
- Número primero, label debajo.
- Delta pastilla `success` / `danger`.

### Table
- Fila 56px con avatar, 48px sin.
- Header `bg-subtle` con label `12px 500`.
- `tabular-nums` en números.

### Sidebar
- Chrome azul marino sólido (`--chrome-bg = #182e4e`).
- Items `h-9`, icono 16px, gap 10px.
- Activo: fondo `chrome-active` + weight 600.
- **Sin footer con datos de usuario.** La identidad del usuario y la acción
  de cerrar sesión viven en el menú del topbar (ver abajo).

### Topbar
- 56px, **mismo fondo chrome azul marino** que el sidebar; borde inferior
  `chrome-border`.
- Izquierda: botón hamburguesa (móvil) + marca.
- Derecha: **UserMenu** (avatar con iniciales + nombre truncado + chevron) que
  al abrir despliega un menú flotante con:
  - Avatar grande, nombre completo, email, chips de roles o badge
    "Super admin".
  - Acción única `Cerrar sesión` (logout API + limpieza de `localStorage` +
    redirect a `/login`).
- Dropdown se cierra con click fuera, `Esc`, o selección.
- Ancho del menú 256px, radius `lg`, shadow óptica media, animación
  `motion-enter` (200 ms ease-out, translate 4px + fade).
- Posición absoluta `right-0 top-[calc(100%+6px)]`, `z-50`.

### Tabs
- Subrayado inferior (nunca pills para nav principal).

### Dropdown / Modal / Toast
- Rounded `lg`, shadow `md`.
- Modal overlay `bg-neutral-900/40 backdrop-blur-[2px]`.

---

## 7. Patrones PMO

### Estados de proyecto
| Estado | Color |
|---|---|
| `Active` | success |
| `At risk` | warning |
| `Blocked` | danger |
| `Planning` | info |
| `On hold` | neutral |
| `Completed` | neutral outline |

### Deltas
Positivo → verde, negativo → rojo. Siempre con `↑/↓` explícito.

### Progress bars
6px de alto, relleno `neutral-800` (no verde). Color sólo si indica desviación.

---

## 8. Motion
- Default: `150ms cubic-bezier(0.2, 0, 0, 1)`.
- Aparecer: `200ms ease-out` + fade + translate 4px.
- Respeta `prefers-reduced-motion: reduce`.

---

## 9. Accesibilidad
- Contraste AA mínimo.
- Focus ring `--focus-ring` 2px, offset 2px.
- Hit-target ≥ 36×36 desktop, 44×44 touch.
- Iconos decorativos: `aria-hidden="true"`.

---

## 10. Mac-inspired accents (sutiles)

Adoptamos **inspiración**, no imitación:

1. Materiales translúcidos en sidebar, popovers y command palette.
2. Jerarquía por elevación óptica (blur + sombra difusa).
3. Radios `14–18px` en contenedores grandes.
4. Tracking negativo en titulares display.
5. Segmented control tipo "pill group" como alternativa a tabs.
6. Status dots (verde/ámbar/rojo) reinterpretados como indicadores de salud en portfolio — **nunca** como traffic-light de ventana.

### Nuevos tokens

```css
--material-thin:     oklch(100% 0 0 / 0.72);
--material-regular:  oklch(100% 0 0 / 0.85);
--material-thick:    oklch(100% 0 0 / 0.94);
--material-blur:     saturate(140%) blur(20px);

--shadow-optical-sm: 0 1px 2px oklch(0% 0 0 / 0.04),
                     0 2px 8px -2px oklch(0% 0 0 / 0.06);
--shadow-optical-md: 0 2px 4px oklch(0% 0 0 / 0.04),
                     0 8px 24px -4px oklch(0% 0 0 / 0.08),
                     0 16px 40px -8px oklch(0% 0 0 / 0.06);
--shadow-optical-lg: 0 4px 8px oklch(0% 0 0 / 0.04),
                     0 16px 48px -8px oklch(0% 0 0 / 0.10),
                     0 32px 80px -16px oklch(0% 0 0 / 0.08);

--radius-window: 14px;
--radius-modal:  16px;
--radius-sheet:  18px;
```

---

## 11. Do & Don't

✅ **Hacer**
- Colores siempre desde tokens.
- Texto secundario en `text-secondary`, no `text-tertiary` por defecto.
- Una sola acción primaria por vista.
- `tabular-nums` en columnas numéricas.

❌ **No hacer**
- Gradientes en botones, cards o fondos.
- >3 colores de acento por vista.
- Sombras en cards estáticas.
- Mezclar radios `sm` y `xl` en el mismo grupo.
- Emojis como iconos de UI.
- Mayúsculas excepto abreviaciones (ID, KPI, PMO).

---

## 12. Referencias rápidas

```
Fondo app        → bg-app          (neutral-50)
Superficie       → bg-surface      (neutral-0)
Card border      → border-subtle   (neutral-200)
Texto título     → text-primary    (neutral-800)
Texto body       → text-secondary  (neutral-600)
Texto meta       → text-tertiary   (neutral-500)
Botón primario   → bg-neutral-800 / text-inverse
Focus ring       → oklch(55% 0.15 240)

Sidebar          → chrome-bg (#182e4e)
Topbar           → chrome-bg (#182e4e)
User dropdown    → top-right del topbar
Radius input     → rounded-md (8px)
Radius card      → rounded-lg (12px)
Padding card     → p-5 (20px)
Altura input     → h-9 (36px)
Altura fila      → h-14 con avatar / h-12 sin
```
