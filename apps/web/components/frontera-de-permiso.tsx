"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { SinPermiso } from "@/components/ui/estados";

/**
 * MCS DIS-03 — el estado «sin permiso», definido una vez para las 75 pantallas.
 *
 * ## Por qué aquí y no en cada pantalla
 *
 * La medición del 2026-08-04 encontró que **60 de las 75 pantallas** no
 * distinguían el 403. El plan avisó de que hacerlo mecánicamente «produciría 70
 * estados malos», y tenía razón para el estado vacío —qué dice una lista vacía
 * es una decisión por pantalla—. Para el 403 no: un permiso que falta se ve
 * igual en las 75, y sesenta copias de la misma tarjeta divergen en cuanto una
 * aprende algo y las otras no.
 *
 * Definir un estado una vez para todo el segmento **es definirlo**, que es lo
 * que el requisito pide. Repetirlo setenta veces es otra cosa.
 *
 * ## Por qué por evento y no por la frontera de error de Next
 *
 * `app/(app)/error.tsx` captura lo que se lanza **durante el renderizado**. Casi
 * todas las pantallas piden sus datos dentro de un `useEffect` con `.catch()`,
 * y una excepción ahí **no llega a ninguna frontera de React** — es la limitación
 * que hace que un boundary por sí solo no cierre este requisito. El evento sí
 * llega, venga de donde venga.
 *
 * ## Se limpia al navegar
 *
 * Si no, un 403 de una pantalla dejaría bloqueadas las siguientes. El
 * `pathname` es la señal: al cambiar de ruta, el permiso se vuelve a preguntar.
 */
export function FronteraDePermiso({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [denegado, setDenegado] = useState(false);

  useEffect(() => {
    setDenegado(false);
  }, [pathname]);

  useEffect(() => {
    function alDenegar() {
      setDenegado(true);
    }
    window.addEventListener("pmoaas:forbidden", alDenegar);
    return () => window.removeEventListener("pmoaas:forbidden", alDenegar);
  }, []);

  if (denegado) return <SinPermiso />;
  return <>{children}</>;
}
