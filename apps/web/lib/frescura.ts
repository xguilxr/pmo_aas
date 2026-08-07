/**
 * MCS DAT-11 — el periodo de un número y cuándo se leyó.
 *
 * > «Todo número presentado DEBE indicar su periodo y su marca de
 * > actualización.»
 *
 * ## Qué se midió
 *
 * La auditoría R1 lo dijo con una frase: «hay exactamente una marca de
 * actualización en todo el producto». Nueve archivos mencionaban «actualizado»
 * y **ocho eran avisos de guardado** —«Perfil actualizado.»—, que no son marcas
 * de frescura sino confirmaciones. La única real acompañaba a un texto, no a un
 * número.
 *
 * Y el problema no era estético: el producto **tiene instantáneas**, así que
 * cuando alguien lee «12 proyectos activos» la pregunta de si eso es de ahora,
 * del corte de anoche o de la semana pasada no es retórica.
 *
 * ## El vocabulario, cerrado a propósito
 *
 * Declarar el periodo por superficie con texto libre habría producido treinta
 * frases distintas para cuatro situaciones. Son cuatro, y elegir es una
 * decisión de producto por pantalla — pero de un menú, no de la nada.
 */

/** Los cuatro periodos que el producto sabe declarar. */
export type Periodo = "vivo" | "acumulado" | "ventana" | "corte";

type Ficha = {
  /** Lo que lee quien mira. */
  etiqueta: string;
  /** Qué significa exactamente, para el `title` del elemento. */
  explicacion: string;
};

export const PERIODOS: Record<Periodo, Ficha> = {
  vivo: {
    etiqueta: "Estado actual",
    explicacion:
      "Se calcula al pedir la pantalla, sobre los datos de este momento. No viene de una instantánea.",
  },
  acumulado: {
    etiqueta: "Acumulado",
    explicacion:
      "Cuenta todo lo registrado desde el inicio, sin recortar por fecha.",
  },
  ventana: {
    etiqueta: "Ventana móvil",
    explicacion:
      "Cubre solo los últimos días indicados; lo anterior no entra en el número.",
  },
  corte: {
    etiqueta: "Al corte",
    explicacion:
      "Viene de una instantánea guardada. No refleja lo que haya cambiado después.",
  },
};

/**
 * El instante en que esta pantalla obtuvo sus datos.
 *
 * Lo lleva el frontend y no la API a propósito: meter un sobre
 * `{datos, periodo, actualizado}` en cada respuesta sería romper el contrato de
 * todos los puntos de acceso a la vez. Lo que el usuario necesita saber —«esto
 * es de hace un minuto» o «esto lleva ahí desde ayer»— se contesta igual desde
 * aquí, y sin migrar la API entera.
 *
 * **Lo que esta marca NO dice** es cuándo se calculó el dato en el servidor.
 * Para los números `vivo` coinciden. Para los de `corte`, la fecha de la
 * instantánea la trae la propia respuesta y va en `detalle`.
 */
export function marcarLectura(): Date {
  return new Date();
}

/**
 * «hace 2 min», «hace 3 h», o la hora si ya pasó de un día.
 *
 * Relativo mientras es útil y absoluto cuando deja de serlo: «hace 19 h» obliga
 * a hacer la resta mentalmente, y a esa distancia lo que importa es qué día.
 */
export function desdeHace(instante: Date, ahora: Date = new Date()): string {
  const segundos = Math.max(0, Math.floor((ahora.getTime() - instante.getTime()) / 1000));
  if (segundos < 60) return "hace un momento";
  const minutos = Math.floor(segundos / 60);
  if (minutos < 60) return `hace ${minutos} min`;
  const horas = Math.floor(minutos / 60);
  if (horas < 24) return `hace ${horas} h`;
  return instante.toLocaleString("es-MX", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}
