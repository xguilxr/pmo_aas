/**
 * MCS DIS-01 — la única frontera donde un color literal es inevitable.
 *
 * `<input type="color">` exige un `#rrggbb` concreto: no acepta `var(--token)`,
 * porque el valor del control es un dato que viaja al servidor, no un estilo.
 * Lo mismo vale para el marcador de posición del campo de texto que lo
 * acompaña.
 *
 * Así que el literal se queda, pero **declarado una sola vez y con nombre**,
 * que es la forma que el propio marco pide para las conversiones de unidad
 * (DAT-04, «únicamente en fronteras explícitas y nombradas»). Antes estaba
 * escrito dos veces en el mismo formulario, y dos copias del mismo valor
 * divergen: basta que alguien ajuste el selector y olvide el marcador.
 *
 * OJO con qué es este valor. **No es un token de diseño**: es el color de
 * marca que un inquilino no ha elegido todavía, y sale en los PDF que exporta.
 * No sigue el tema claro/oscuro de la aplicación ni debe hacerlo — un informe
 * impreso no tiene tema.
 */
export const COLOR_MARCA_POR_DEFECTO = "#1f2937";
