"use client";

/**
 * US-288 — el catálogo del inquilino, para las pantallas que lo consumen.
 *
 * Cinco pantallas necesitan los tipos de proyecto: el formulario de alta, el
 * de edición, el filtro de la lista, la vista maestra y el tablero. Sin una
 * caché serían cinco peticiones por navegación para una lista que cambia una
 * vez al mes.
 *
 * ## Por qué la caché vive en el módulo y no en un contexto
 *
 * Un proveedor obligaría a montarlo en el layout y a que cada pantalla nueva
 * se acuerde de estar dentro. Esto es una lista corta y estable: la promesa en
 * curso se comparte, y la respuesta se guarda hasta que alguien la invalide.
 *
 * `invalidarCatalogo()` la tira. Lo llama la pantalla de configuración después
 * de escribir, que es el único sitio donde el catálogo cambia. Un cambio hecho
 * en otra pestaña no se entera hasta recargar, y está bien: el precio de
 * enterarse sería sondear el servidor para algo que casi nunca cambia.
 */
import { useEffect, useState } from "react";

import {
  listarCatalogoVigente,
  type Catalogo,
  type ValorDeCatalogo,
} from "@/lib/api/catalogos";

const cache = new Map<Catalogo, ValorDeCatalogo[]>();
const enVuelo = new Map<Catalogo, Promise<ValorDeCatalogo[]>>();

export function invalidarCatalogo(catalogo?: Catalogo): void {
  if (catalogo) {
    cache.delete(catalogo);
    enVuelo.delete(catalogo);
    return;
  }
  cache.clear();
  enVuelo.clear();
}

async function traer(catalogo: Catalogo): Promise<ValorDeCatalogo[]> {
  const guardado = cache.get(catalogo);
  if (guardado) return guardado;
  const pendiente = enVuelo.get(catalogo);
  if (pendiente) return pendiente;
  const promesa = listarCatalogoVigente(catalogo)
    .then((valores) => {
      cache.set(catalogo, valores);
      return valores;
    })
    .finally(() => enVuelo.delete(catalogo));
  enVuelo.set(catalogo, promesa);
  return promesa;
}

export type EstadoDeCatalogo = {
  /** El catálogo completo, retirados incluidos: sirve para **nombrar**. */
  valores: ValorDeCatalogo[];
  /** Solo los que se pueden elegir hoy: sirve para **ofrecer**. */
  activos: ValorDeCatalogo[];
  /** `true` mientras no se sabe. No es lo mismo que «está vacío». */
  cargando: boolean;
  error: string | null;
  /** `clave → etiqueta`, para pintar el valor de una fila. */
  etiqueta: (clave: string | null | undefined) => string;
};

export function useCatalogo(catalogo: Catalogo): EstadoDeCatalogo {
  const [valores, setValores] = useState<ValorDeCatalogo[]>(
    () => cache.get(catalogo) ?? [],
  );
  const [cargando, setCargando] = useState(() => !cache.has(catalogo));
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let vigente = true;
    const guardado = cache.get(catalogo);
    if (guardado) {
      setValores(guardado);
      setCargando(false);
      return;
    }
    setCargando(true);
    traer(catalogo)
      .then((v) => {
        if (!vigente) return;
        setValores(v);
        setError(null);
      })
      .catch(() => {
        if (!vigente) return;
        setValores([]);
        setError("No se pudo cargar el catálogo.");
      })
      .finally(() => {
        if (vigente) setCargando(false);
      });
    return () => {
      vigente = false;
    };
  }, [catalogo]);

  return {
    valores,
    activos: valores.filter((v) => v.activo),
    cargando,
    error,
    // Sobre `valores` y no sobre `activos`: un proyecto con un tipo retirado
    // tiene que seguir mostrando su nombre. Y devuelve la clave cruda cuando
    // no la conoce, no un guion — el texto libre de antes de US-202 sale así, y
    // hay que verlo para poder corregirlo.
    etiqueta: (clave) => {
      if (!clave) return "—";
      return valores.find((v) => v.clave === clave)?.etiqueta ?? clave;
    },
  };
}
