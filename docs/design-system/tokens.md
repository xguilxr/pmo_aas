# Design Tokens

**ID:** `DOC-DS-TOKENS`

Tokens expuestos vía `@theme` en Tailwind v4 y como CSS variables. Toda la UI debe consumir estos tokens — **nunca hardcodear colores o tamaños**.

---

## Colores

### Brand

```css
@theme {
  --color-brand-50:  oklch(97% 0.02 240);
  --color-brand-100: oklch(93% 0.04 240);
  --color-brand-200: oklch(86% 0.08 240);
  --color-brand-300: oklch(77% 0.13 240);
  --color-brand-400: oklch(68% 0.17 240);
  --color-brand-500: oklch(60% 0.18 240);  /* primario */
  --color-brand-600: oklch(52% 0.17 240);
  --color-brand-700: oklch(44% 0.14 240);
  --color-brand-800: oklch(36% 0.10 240);
  --color-brand-900: oklch(28% 0.06 240);
}
```

Azul sobrio estilo macOS — evitamos saturación alta. Usamos **oklch** para controlar luminosidad lineal.

### Semánticos

| Token | Light | Dark | Uso |
|---|---|---|---|
| `--color-success` | oklch(67% 0.16 155) | oklch(72% 0.18 155) | Salud verde, check |
| `--color-warning` | oklch(78% 0.16 85) | oklch(82% 0.17 85) | Salud amarilla, advertencias |
| `--color-danger` | oklch(60% 0.21 25) | oklch(68% 0.22 25) | Salud roja, errores, delete |
| `--color-info` | oklch(65% 0.12 230) | oklch(72% 0.14 230) | Notificaciones informativas |
| `--color-neutral` | oklch(60% 0.02 260) | oklch(65% 0.02 260) | Badges neutrales |

### Health status (específicos de dominio)

```css
--color-health-green:  var(--color-success);
--color-health-yellow: var(--color-warning);
--color-health-red:    var(--color-danger);
```

### Superficies (light mode)

```css
--bg-base:     oklch(99% 0.002 260);    /* app background */
--bg-elevated: oklch(100% 0 0 / 0.72);  /* cards, sidebars con backdrop blur */
--bg-overlay:  oklch(100% 0 0 / 0.88);  /* modals, popovers */
--bg-hover:    oklch(96% 0.005 260);
--bg-active:   oklch(94% 0.008 260);
```

### Superficies (dark mode)

```css
--bg-base:     oklch(12% 0.01 260);
--bg-elevated: oklch(17% 0.01 260 / 0.75);
--bg-overlay:  oklch(20% 0.01 260 / 0.9);
--bg-hover:    oklch(20% 0.01 260);
--bg-active:   oklch(24% 0.015 260);
```

### Texto

```css
--text-primary:   oklch(22% 0.01 260);   /* titulares, body */
--text-secondary: oklch(45% 0.01 260);   /* subtítulos, placeholders */
--text-tertiary:  oklch(60% 0.01 260);   /* timestamps, meta */
--text-inverse:   oklch(98% 0 0);        /* sobre brand-500+ */

/* dark */
--text-primary:   oklch(96% 0.005 260);
--text-secondary: oklch(75% 0.01 260);
--text-tertiary:  oklch(58% 0.01 260);
```

### Bordes

```css
--border-subtle:  oklch(90% 0.005 260 / 0.8);   /* separadores */
--border-default: oklch(80% 0.01 260 / 0.9);
--border-strong:  oklch(60% 0.015 260);         /* focus, seleccionado */
```

---

## Tipografía

Stack:
```css
--font-sans: "InterVariable", "SF Pro Text", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
--font-display: "SF Pro Display", "InterVariable", -apple-system, sans-serif;
--font-mono: "Geist Mono", "SF Mono", ui-monospace, monospace;
```

Escala modular (ratio 1.125 menor, 1.25 mayor):

| Token | Tamaño | Line-height | Uso |
|---|---|---|---|
| `--text-xs` | 11px | 14px | Timestamps, meta |
| `--text-sm` | 13px | 18px | Tablas densas, helper |
| `--text-base` | 15px | 22px | Body por default |
| `--text-md` | 17px | 24px | Body medium |
| `--text-lg` | 20px | 28px | Subtítulos de sección |
| `--text-xl` | 24px | 32px | Títulos de página |
| `--text-2xl` | 30px | 36px | Hero en landing |
| `--text-3xl` | 38px | 44px | Display |

Pesos: 400 (regular), 500 (medium para UI), 600 (semibold para títulos), 700 (bold, rara vez).

**Letter-spacing**: ligero `-0.01em` en títulos, `0` en body, `+0.02em` en all-caps labels.

---

## Spacing

Sistema base 4px. Tokens:

```
0   2   4   6   8   12  16  20  24  32  40  48  64  80  96  128
```

Equivalencias Tailwind: `spacing-0` a `spacing-32`. Para UI densa usamos `2` y `3` (8/12px) por default.

---

## Radios

```css
--radius-xs: 4px;   /* chips, pills pequeños */
--radius-sm: 6px;   /* inputs, botones */
--radius-md: 10px;  /* cards */
--radius-lg: 14px;  /* modals, drawers */
--radius-xl: 20px;  /* hero cards */
--radius-full: 9999px;
```

Apple usa squircles (radio continuo). Activamos con `border-radius: var(--radius-md)` + `border-curve: continuous` (prop experimental). En Safari/iOS se ve nativo.

---

## Sombras (minimalistas)

Apple **prefiere capas con blur** a sombras pesadas. Mantenemos:

```css
--shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.04), 0 1px 1px rgba(0, 0, 0, 0.03);
--shadow-md: 0 4px 12px rgba(0, 0, 0, 0.06), 0 2px 4px rgba(0, 0, 0, 0.04);
--shadow-lg: 0 12px 32px rgba(0, 0, 0, 0.10), 0 4px 8px rgba(0, 0, 0, 0.05);
--shadow-xl: 0 24px 48px rgba(0, 0, 0, 0.14);
```

Dark mode: sombras casi invisibles — separamos con cambio de luminosidad de fondo.

---

## Blur / vibrancy

```css
--blur-sm: blur(10px);
--blur-md: blur(20px);
--blur-lg: blur(40px) saturate(1.4);
```

Aplicar sobre fondos semi-transparentes (`/0.75`) para lograr efecto cristal de macOS.

---

## Z-index scale

```css
--z-base: 0;
--z-dropdown: 40;
--z-sticky: 50;
--z-drawer: 60;
--z-modal: 70;
--z-popover: 80;
--z-toast: 90;
--z-cmdk: 100;
```

---

## Focus ring

```css
.focus-ring {
  outline: none;
  box-shadow:
    0 0 0 2px var(--bg-base),
    0 0 0 4px var(--color-brand-500);
}
```

Visible siempre en keyboard navigation. Oculto en `:focus:not(:focus-visible)`.

---

## Tailwind config (fragmento)

```ts
// apps/web/tailwind.config.ts
import type { Config } from "tailwindcss";

export default {
  content: ["./src/**/*.{ts,tsx,mdx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-sans)"],
        display: ["var(--font-display)"],
        mono: ["var(--font-mono)"],
      },
      colors: {
        brand: {
          50: "var(--color-brand-50)", /* ... */ 900: "var(--color-brand-900)",
        },
        surface: {
          base: "var(--bg-base)",
          elevated: "var(--bg-elevated)",
          overlay: "var(--bg-overlay)",
        },
        // semánticos
        success: "var(--color-success)",
        warning: "var(--color-warning)",
        danger: "var(--color-danger)",
        info: "var(--color-info)",
      },
      borderRadius: {
        xs: "var(--radius-xs)",
        sm: "var(--radius-sm)",
        md: "var(--radius-md)",
        lg: "var(--radius-lg)",
        xl: "var(--radius-xl)",
      },
    },
  },
} satisfies Config;
```

---

## Linting de tokens

ESLint rule custom en `packages/config/eslint/no-hardcoded-colors.js` rechaza:

- Colores en hex/rgb/hsl (excepto en `globals.css` del tema).
- Font sizes literales (`text-[15px]`).
- Espaciado arbitrario en classes (`p-[13px]`).

Los overrides requieren `/* eslint-disable-next-line no-hardcoded-color */` con justificación.
