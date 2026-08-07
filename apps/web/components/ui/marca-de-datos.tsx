"use client";

import { useEffect, useState } from "react";

import { cn } from "@/lib/cn";
import { desdeHace, PERIODOS, type Periodo } from "@/lib/frescura";

/**
 * MCS DAT-11 — la marca que acompaña a los números de una superficie.
 *
 * ## Por qué las dos propiedades son obligatorias y sin valor por defecto
 *
 * Es la misma lección de `lib/confirmar.ts` (DIS-04): **un parámetro con
 * defecto es un parámetro que nadie rellena**. Si `periodo` tuviera un valor
 * por omisión, todas las pantallas heredarían el mismo y la declaración diría
 * lo que dijera la primera persona que la escribió, no lo que cada superficie
 * mide.
 *
 * `actualizado` obliga a lo mismo por el otro lado: quien pone la marca tiene
 * que haber apuntado cuándo leyó. No hay forma de rellenarlo «por si acaso».
 *
 * ## Qué NO es
 *
 * No es un aviso de guardado. Ocho de los nueve «actualizado» que la auditoría
 * encontró eran eso —«Perfil actualizado.»— y por eso el requisito estaba en
 * cero pese a que la palabra aparecía por todas partes.
 */
export type MarcaProps = {
  /** Qué periodo cubren los números de esta superficie. Sin valor por defecto. */
  periodo: Periodo;
  /** Cuándo se leyeron los datos. Sin valor por defecto. */
  actualizado: Date;
  /**
   * Lo que el vocabulario cerrado no puede saber: los días de la ventana, la
   * fecha de la instantánea. Va junto a la etiqueta.
   */
  detalle?: string;
  className?: string;
};

export function MarcaDeDatos({ periodo, actualizado, detalle, className }: MarcaProps) {
  const ficha = PERIODOS[periodo];

  // Se recalcula cada minuto para que «hace un momento» no se quede fijo en
  // una pantalla que alguien deja abierta. Es justo el caso que hace falta
  // cubrir: la marca importa cuando los datos han envejecido, y eso ocurre
  // sin que nadie vuelva a renderizar.
  const [ahora, setAhora] = useState<Date | null>(null);
  useEffect(() => {
    setAhora(new Date());
    const id = setInterval(() => setAhora(new Date()), 60_000);
    return () => clearInterval(id);
  }, []);

  return (
    <p
      className={cn(
        "flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-[var(--text-tertiary)]",
        className,
      )}
      data-marca-de-datos={periodo}
    >
      <span title={ficha.explicacion} className="font-medium">
        {ficha.etiqueta}
        {detalle ? ` · ${detalle}` : ""}
      </span>
      <span aria-hidden="true">·</span>
      {/* `suppressHydrationWarning` + estado nulo en el primer render: la hora
          del servidor y la del navegador no coinciden, y sin esto Next avisa
          de desajuste en cada carga. */}
      <time dateTime={actualizado.toISOString()} suppressHydrationWarning>
        Leído {ahora ? desdeHace(actualizado, ahora) : "ahora"}
      </time>
    </p>
  );
}

/**
 * Cuándo cambió por última vez el dato que esta pantalla está mostrando.
 *
 * Se ata al estado que se pinta y no a la llamada que lo trajo, y no es un
 * atajo: es más exacto. Marcar en el `.finally()` de la petición registra
 * cuándo respondió el servidor aunque la respuesta no cambiara nada; esto
 * registra cuándo cambió lo que el usuario tiene delante, y se actualiza solo
 * cuando la pantalla refresca por un filtro.
 *
 * Devuelve `null` mientras no hay datos, para que la marca no aparezca sobre
 * un esqueleto de carga anunciando la frescura de nada.
 */
export function useLectura(datos: unknown): Date | null {
  const [leido, setLeido] = useState<Date | null>(null);
  useEffect(() => {
    if (datos !== null && datos !== undefined) setLeido(new Date());
  }, [datos]);
  return leido;
}
