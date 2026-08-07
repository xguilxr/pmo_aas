/**
 * MCS DIS-04 — «toda acción destructiva DEBE nombrar el objeto afectado y su
 * consecuencia, y ofrecer confirmación o reversión».
 *
 * Medido el 2026-08-06 sobre los 17 `window.confirm` que había:
 *
 * - **Nombra el objeto:** a medias. «¿Eliminar este riesgo?» y «¿Eliminar este
 *   ítem?» no nombran nada — quien tenga dos pestañas abiertas no sabe cuál va
 *   a borrar.
 * - **Dice la consecuencia:** **cero de 17.** Ninguna decía qué se pierde ni si
 *   se puede deshacer.
 * - **Ofrece confirmación:** sí, en su forma más pobre.
 *
 * Por eso las tres partes son **obligatorias y sin valor por defecto**, igual
 * que `errors.mensaje(que=, porque=, accion=)` en el backend: un parámetro con
 * defecto es un parámetro que nadie rellena, y el mensaje vuelve a quedarse a
 * medias sin que nada chille.
 *
 * ## Por qué `reversibilidad` es un campo y no una frase libre
 *
 * En este producto conviven los dos borrados: la mayoría marcan `deleted_at`
 * —recuperable— y hay **52 sitios en el API que borran de verdad**. Decir «no
 * se puede deshacer» sobre un borrado blando es mentir, y decir «se puede
 * recuperar» sobre uno duro es peor. Con un campo tipado hay que elegir, y el
 * texto lo escribe este módulo una sola vez.
 *
 * ## Lo que este módulo NO resuelve
 *
 * Sigue usando `window.confirm`, que es bloqueante y no se puede dar estilo.
 * Cambiarlo por un diálogo propio es trabajo de diseño y no lo pide el
 * requisito: DIS-04 exige «confirmación o reversión», no un componente
 * concreto. Lo que sí exige —nombrar y advertir— es lo que faltaba, y es lo
 * que esto obliga. Al llegar el diálogo, se cambia aquí y en ningún otro sitio.
 */

/** Qué pasa con el objeto después de la acción. */
export type Reversibilidad =
  /** Marca `deleted_at`: deja de verse y se puede recuperar. */
  | "recuperable"
  /** Se borra de la base. No hay vuelta atrás. */
  | "definitiva";

/** La frase con la que se cierra el aviso, escrita una sola vez. */
const CIERRE: Record<Reversibilidad, string> = {
  recuperable: "Se puede recuperar después.",
  definitiva: "Esta acción no se puede deshacer.",
};

export type AvisoDestructivo = {
  /**
   * El objeto, **nombrado**. No «este elemento»: el nombre que la persona ve en
   * pantalla, entre comillas angulares.
   *
   * Bien: `el riesgo «Retraso del proveedor»`
   * Mal: `este riesgo`
   */
  objeto: string;
  /**
   * Qué más se lleva por delante, o qué deja de funcionar. Es la parte que no
   * existía en ninguno de los 17 avisos anteriores.
   *
   * Si de verdad no arrastra nada, se dice: `No afecta a nada más.` Escribirlo
   * cuesta lo mismo que omitirlo y le ahorra la duda a quien lee.
   */
  consecuencia: string;
  reversibilidad: Reversibilidad;
};

/**
 * Pide confirmación para una acción destructiva. `true` = seguir adelante.
 *
 * @example
 * if (!confirmarDestructivo({
 *   objeto: `el riesgo «${riesgo.title}»`,
 *   consecuencia: "Sus acciones de mitigación se eliminan con él.",
 *   reversibilidad: "recuperable",
 * })) return;
 */
export function confirmarDestructivo({
  objeto,
  consecuencia,
  reversibilidad,
}: AvisoDestructivo): boolean {
  return window.confirm(redactarAviso({ objeto, consecuencia, reversibilidad }));
}

/**
 * El texto del aviso. Separado de `confirmarDestructivo` para poder probarlo
 * sin navegador — si solo existiera la función que abre el diálogo, comprobar
 * la redacción exigiría un entorno con `window`, y lo que no se puede probar
 * barato no se prueba.
 */
export function redactarAviso({
  objeto,
  consecuencia,
  reversibilidad,
}: AvisoDestructivo): string {
  return `¿Eliminar ${objeto}?\n\n${consecuencia} ${CIERRE[reversibilidad]}`;
}
