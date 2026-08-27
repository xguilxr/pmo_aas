import { cn } from "@/lib/cn";

type Props = {
  /** Nombre del archivo en `public/icons/stroke/<nombre>.svg` (Keyline, MIT). */
  nombre: string;
  /** px. 17 en navegación, 15 en botones y filas, 13–14 en chips y metadatos. */
  size?: number;
  className?: string;
};

/**
 * Icono Keyline resuelto por mask-image (tintable con currentColor, sin
 * inflar el bundle con un componente React por icono). Grid 24, stroke 2px.
 */
export function Icono({ nombre, size = 15, className }: Props) {
  const url = `url(/icons/stroke/${nombre}.svg)`;
  return (
    <span
      aria-hidden
      className={cn("inline-block shrink-0 bg-current", className)}
      style={{
        width: size,
        height: size,
        WebkitMask: `${url} center / contain no-repeat`,
        mask: `${url} center / contain no-repeat`,
      }}
    />
  );
}
