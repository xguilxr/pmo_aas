/**
 * BUG-092 — la única frontera donde un importe se convierte en texto.
 *
 * ## Qué había
 *
 * `tenant.settings.currency` ofrecía MXN, USD y EUR y **el formulario que la
 * guardaba era el único sitio que la leía**. Las diez superficies que muestran
 * dinero traían `currency: "MXN"` escrito a mano, así que un inquilino en
 * dólares —el propio sembrado crea uno— veía sus importes **rotulados en
 * pesos**. El número no estaba mal; la unidad era mentira, que en un importe es
 * lo mismo.
 *
 * ## La decisión del owner (2026-08-07)
 *
 * La moneda va **sobre el proyecto**. El inquilino declara una *preferida*, que
 * es el valor inicial de los proyectos que no eligen una propia. Cada
 * superficie tiene que reflejar la que corresponde.
 *
 * ## Por qué `moneda` no tiene valor por defecto
 *
 * Misma lección que `confirmar.ts` y que `MarcaDeDatos`: **un parámetro con
 * defecto es un parámetro que nadie rellena.** Si `formatearImporte` asumiera
 * MXN cuando no le pasan nada, el bug volvería exactamente igual y en el mismo
 * sitio — la diferencia entre `currency: "MXN"` escrito a mano y un defecto
 * escondido en una función es de dónde está escrito, no de qué hace.
 *
 * El código de moneda lo trae la API, ya resuelto: el frontend nunca aplica la
 * regla «nulo significa la del inquilino», porque esa regla vive en
 * `app/dominio/moneda.py` y dos sitios decidiendo lo mismo divergen.
 */

/** Los tres códigos que el producto admite. */
export const MONEDAS = ["MXN", "USD", "EUR"] as const;
export type Moneda = (typeof MONEDAS)[number];

/**
 * El último recurso cuando ni el proyecto ni el inquilino dicen nada. Es la que
 * el producto venía aplicando de facto, así que ningún importe existente cambia
 * de rótulo. Espeja `dominio.moneda.POR_DEFECTO`, y una prueba lo comprueba.
 */
export const POR_DEFECTO = "MXN";

/** El locale con el que se agrupan los millares. No es la moneda. */
const LOCALE = "es-MX";

/**
 * Un importe con su moneda. `moneda` es obligatoria y no tiene defecto.
 *
 * `null` y `undefined` devuelven el marcador de «sin dato» (DAT-12): un
 * presupuesto no cargado no es un presupuesto de cero, y pintarlo como `$0`
 * dice que alguien decidió no gastar cuando lo que pasa es que nadie lo
 * capturó.
 */
export function formatearImporte(
  valor: number | null | undefined,
  moneda: string,
  opciones?: { decimales?: number },
): string {
  if (valor === null || valor === undefined || Number.isNaN(valor)) return "—";
  return new Intl.NumberFormat(LOCALE, {
    style: "currency",
    currency: moneda,
    maximumFractionDigits: opciones?.decimales ?? 0,
  }).format(valor);
}

/**
 * Un desglose `{moneda: importe}` como texto, para los agregados de cartera.
 *
 * **Con varias monedas no hay un total**, y esta función no lo inventa: las
 * pinta todas separadas. Sumar 1.000 MXN y 1.000 EUR para escribir «2.000» es
 * producir un número que no existe en ninguna parte, y convertir exigiría un
 * tipo de cambio con fecha y con firma — que es otro frente.
 *
 * Sin ninguna devuelve el marcador de «sin dato», que es distinto de cero por
 * el mismo motivo de siempre.
 */
export function formatearDesglose(porMoneda: Record<string, number>): string {
  const entradas = Object.entries(porMoneda ?? {});
  if (entradas.length === 0) return "—";
  return entradas
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([moneda, valor]) => formatearImporte(valor, moneda))
    .join(" · ");
}

/** ¿El desglose está en una sola moneda? Decide si se pinta uno o varios. */
export function monedaUnica(porMoneda: Record<string, number>): string | null {
  const codigos = Object.keys(porMoneda ?? {});
  return codigos.length === 1 ? codigos[0] : null;
}
