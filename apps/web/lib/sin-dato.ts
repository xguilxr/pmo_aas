/**
 * MCS DAT-12 — «la ausencia de dato DEBE distinguirse visualmente del cero».
 *
 * No es una sutileza de presentación. Un proyecto **sin presupuesto cargado** y
 * uno **con presupuesto cero** son estados distintos y piden acciones
 * distintas: al primero le falta un dato, el segundo está mal planificado. Con
 * `?? 0` los dos salen «$0» y quien mira el tablero no puede diferenciarlos.
 *
 * Lo mismo con «0 riesgos abiertos»: puede ser un proyecto sano o uno al que
 * nadie le ha registrado riesgos todavía. El primero es una buena noticia; el
 * segundo, un aviso.
 *
 * El guion largo es la convención del producto para «no hay dato». Se declara
 * aquí y no se escribe suelto en cada componente porque cambiarlo —a «s/d», a
 * un icono— tiene que ser un cambio y no una campaña.
 */

/** Lo que se muestra cuando no hay dato. */
export const SIN_DATO = "—";

/**
 * Etiqueta accesible del hueco.
 *
 * El guion largo lo lee un lector de pantalla como una pausa, o no lo lee: sin
 * esto, «Presupuesto —» suena a «Presupuesto» y el hueco desaparece justo para
 * quien menos puede inferirlo del contexto visual.
 */
export const SIN_DATO_ETIQUETA = "sin dato";

/** `true` si el valor es una ausencia y no un número. */
export function esSinDato(valor: number | null | undefined): valor is null | undefined {
  return valor === null || valor === undefined || !Number.isFinite(valor);
}
