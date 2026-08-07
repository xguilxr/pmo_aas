"use client";

import { useEffect } from "react";

import { ErrorDeCarga, SinPermiso } from "@/components/ui/estados";

/**
 * MCS DIS-03 — el estado de error y el de «sin permiso», para todo el segmento.
 *
 * Next llama a este componente cuando algo lanza dentro de `app/(app)`. Es la
 * respuesta del propio framework a «toda pantalla DEBE definir sus estados»:
 * definirlo una vez para el segmento **es definirlo**; hacerlo setenta veces es
 * repetirlo, y sesenta copias de la misma tarjeta divergen en cuanto una
 * aprende a ofrecer «reintentar».
 *
 * La medición decía que 60 de las 75 pantallas no distinguían el 403. Este
 * archivo lo distingue para las 75.
 *
 * **El 401 no llega aquí**: `apiFetch` lo intercepta para renovar la sesión, y
 * si no puede, `RequireAuth` manda a iniciar sesión. Confundir 401 con 403 es
 * el fallo que manda a alguien a autenticarse otra vez estando ya autenticado.
 *
 * Una pantalla que quiera un texto propio puede seguir capturando el error ella
 * misma; esto es el suelo, no el techo.
 */
export default function ErrorDelSegmento({
  error,
  reset,
}: {
  error: Error & { digest?: string; status?: number };
  reset: () => void;
}) {
  useEffect(() => {
    // Va a la consola y de ahí a la captura de errores (OPS-02). Sin esto, un
    // fallo que el usuario ve queda solo en su pantalla.
    console.error("[app] error no capturado por la pantalla:", error);
  }, [error]);

  // `ApiError` lleva `status`; un error cualquiera, no. Se mira la propiedad y
  // no el mensaje: el texto cambia con el idioma y con el proveedor.
  if (error.status === 403) {
    return <SinPermiso />;
  }

  return (
    <ErrorDeCarga
      titulo="No se pudo cargar esta pantalla"
      detalle={
        error.status === 0
          ? "No hubo respuesta del servidor. Puede ser la conexión."
          : error.message || "Ocurrió un error inesperado."
      }
      reintentar={reset}
    />
  );
}
