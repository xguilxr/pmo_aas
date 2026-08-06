---
responsable: propietario
estado: vigente
revisado: 2026-05-08
revisar_cada: 90d
---

# Motion — Movimiento y transiciones

**ID:** `DOC-DS-MOTION`

El movimiento comunica. No decora.

---

## Principios

1. **Siempre con propósito.** Cada transición dice *de dónde vienes / adónde vas*.
2. **Corta, nunca lenta.** 120-280ms para UI; 400ms máximo para overlays.
3. **Easing natural.** Reglas Apple: salida rápida, entrada desacelerada.
4. **Respeta `prefers-reduced-motion`.** Cambiamos transiciones por crossfade de 80ms.

---

## Curvas (easing)

```ts
// packages/ui/src/tokens/motion.ts
export const easing = {
  standard: "cubic-bezier(0.32, 0.72, 0, 1)",   // in+out — la de Apple
  decelerate: "cubic-bezier(0, 0, 0.2, 1)",     // entrada
  accelerate: "cubic-bezier(0.4, 0, 1, 1)",     // salida
  linear: "linear",
};

export const duration = {
  instant: 80,
  fast: 140,
  base: 220,
  slow: 320,
  xslow: 480,   // overlays grandes
};
```

---

## Patrones

### Fade in / out

```tsx
<motion.div
  initial={{ opacity: 0 }}
  animate={{ opacity: 1 }}
  exit={{ opacity: 0 }}
  transition={{ duration: 0.22, ease: "easeOut" }}
/>
```

Uso: toasts, badges que aparecen, tooltips.

### Slide drawer (desde la derecha)

```tsx
<motion.div
  initial={{ x: "100%" }}
  animate={{ x: 0 }}
  exit={{ x: "100%" }}
  transition={{ duration: 0.28, ease: [0.32, 0.72, 0, 1] }}
  drag="x"
  dragConstraints={{ left: 0 }}
  onDragEnd={(_, info) => info.offset.x > 120 && close()}
/>
```

Uso: drawer de detalle de módulos.

### Modal scale + fade

```tsx
initial={{ opacity: 0, scale: 0.96 }}
animate={{ opacity: 1, scale: 1 }}
exit={{ opacity: 0, scale: 0.98 }}
transition={{ duration: 0.2, ease: "easeOut" }}
```

### Collapse (acordeón)

Altura animada con `height: "auto"` (Framer motion `layout` o `AnimatePresence`).
Duración 260ms, `ease: "easeInOut"`.

### Números que suben (KPI)

```tsx
<AnimatedNumber from={0} to={kpi.value} duration={600} ease="easeOut" />
```

No animar en cada re-render — sólo primer mount o cuando cambia significativamente.

### Sparkle (AI-generated)

Badge con ícono que rota lento + partículas ocasionales. Librería: **lottie-react** o custom SVG con `<animate>`.

### Lista → drill-down

Al clickear un row que abre detalle a pantalla completa: `layoutId` de Framer Motion para "morph" del card al título. Opcional — sólo en flujos hero.

### Page transitions

```tsx
<AnimatePresence mode="wait">
  <motion.div
    key={pathname}
    initial={{ opacity: 0, y: 8 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0, y: -8 }}
    transition={{ duration: 0.2 }}
  />
</AnimatePresence>
```

---

## Micro-interacciones

| Elemento | Interacción |
|---|---|
| Button | `scale: 0.98` al press + sombra reduce (duration 120) |
| Checkbox | Tick dibujado con stroke-dashoffset (220ms) |
| Switch | Thumb slide + color interpolado |
| Loading button | Label se comprime, spinner aparece centrado |
| Toast | Slide from bottom-right + tiny bounce |
| Drawer close | Si arrastraste <30%, vuelve suave. Si ≥30%, completa el cierre. |
| Row hover (table) | Background alpha 0.04 en 120ms |
| Focus ring | Aparece con fade 100ms (no scale) |
| Tab change | Underline slide entre posiciones (280ms) |

---

## Reduced motion

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 80ms !important;
    transition-duration: 80ms !important;
    animation-iteration-count: 1 !important;
  }
  /* Deshabilitamos layout morphs y translates grandes */
}
```

En Framer Motion usar:
```tsx
const shouldReduceMotion = useReducedMotion();
transition={{ duration: shouldReduceMotion ? 0.08 : 0.22 }}
```

---

## Performance

- `will-change` solo en elementos realmente animados — quitar tras terminar.
- Animar **transform** y **opacity** preferentemente (compositor GPU).
- Evitar animar `top/left/width/height` (reflow costoso).
- Para listas largas: `layout` sólo en items visibles.
- Medir con DevTools Performance; objetivo 60fps siempre, 120fps cuando el display lo soporte.

---

## Ejemplos en código

### AnimatedNumber

```tsx
import { useMotionValue, useTransform, animate } from "framer-motion";

export function AnimatedNumber({ value, duration = 0.6 }: { value: number; duration?: number }) {
  const mv = useMotionValue(0);
  const rounded = useTransform(mv, Math.round);
  useEffect(() => {
    const controls = animate(mv, value, { duration, ease: [0, 0, 0.2, 1] });
    return controls.stop;
  }, [value]);
  return <motion.span>{rounded}</motion.span>;
}
```

### PageTransition

```tsx
// apps/web/src/components/PageTransition.tsx
"use client";
import { AnimatePresence, motion } from "framer-motion";
import { usePathname } from "next/navigation";

export function PageTransition({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={pathname}
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -4 }}
        transition={{ duration: 0.22, ease: [0.32, 0.72, 0, 1] }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}
```
