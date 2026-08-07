import { Cargando } from "@/components/ui/estados";

/**
 * MCS DIS-03 — el estado «en carga» del segmento.
 *
 * Next lo muestra mientras se resuelve la navegación a cualquier pantalla de
 * `app/(app)`. Cubre el hueco que la medición encontró en 12 pantallas: la
 * transición entre rutas, donde antes no había nada y la anterior se quedaba
 * congelada — indistinguible de una aplicación colgada.
 *
 * No sustituye a los esqueletos de dentro de cada pantalla, que cubren otra
 * cosa: la espera de *sus* datos una vez que ya se está en ella.
 */
export default function CargandoSegmento() {
  return <Cargando que="la pantalla" />;
}
