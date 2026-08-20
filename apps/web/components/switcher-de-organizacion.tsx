"use client";

/**
 * US-205 — El switcher de organización del header.
 *
 * Sigue el artboard «Header — contexto tenant/org» de los mockups aprobados:
 * las organizaciones del inquilino con su nombre, y «Todas las organizaciones»
 * marcada como lo que es —solo válida donde la vista agrega—.
 *
 * ## Un `<select>` y no un menú a medida
 *
 * El mockup dibuja un desplegable con iniciales y conteos por fila. Un `<select>`
 * nativo no pinta eso, y aun así es lo correcto aquí: es el control que ya se
 * usaba en las siete pantallas que este componente reemplaza, hereda foco,
 * teclado y lector de pantalla sin escribirlos, y no tiene el bug de «se abre
 * detrás del contenido» que arrastra todo menú flotante propio. El conteo por
 * fila se pierde; el que importa —cuál está activa— se ve en el propio control.
 *
 * Si más adelante hace falta la ficha rica del mockup, el sitio es este
 * componente y nada más: las pantallas leen del contexto, no de él.
 *
 * ## Por qué «Todas» solo aparece a veces
 *
 * `reestructura-navegacion.md` §1: «Todas» está disponible **únicamente** en las
 * vistas que agregan. Ofrecerla en una pantalla que opera dentro de una
 * organización deja al usuario elegir un estado que esa pantalla no sabe
 * representar — y el resultado no es un error, es una lista que mezcla
 * organizaciones sin decirlo.
 */
import { Select } from "@/components/ui/select";
import { useOrganizacionActiva } from "@/components/organizacion-activa";

export function SwitcherDeOrganizacion() {
  const { organizaciones, efectiva, agrega, elegir, cargando, vacio } =
    useOrganizacionActiva();

  // DIS-03 — un inquilino recién creado no tiene organizaciones. Se dice, en vez
  // de pintar un desplegable vacío que se lee como algo que falló al cargar.
  if (vacio) {
    return (
      <span className="hidden whitespace-nowrap rounded-[var(--radius-md)] border border-dashed border-[var(--border-default)] px-2.5 py-1 text-[12px] text-[var(--text-tertiary)] lg:inline-block">
        Sin organizaciones
      </span>
    );
  }

  if (cargando) {
    return (
      <span
        aria-hidden
        className="hidden h-[30px] w-[170px] animate-pulse rounded-[var(--radius-md)] bg-[var(--color-muted)] lg:inline-block"
      />
    );
  }

  return (
    <Select
      aria-label="Organización activa"
      title="Organización activa"
      value={efectiva}
      onChange={(e) => elegir(e.target.value)}
      className="hidden h-[30px] max-w-[220px] border-[var(--border-default)] bg-[var(--color-surface)] py-0 text-[13px] lg:block"
    >
      {/* Con una sola organización el «todas» sobra: agrega una cosa. */}
      {agrega && organizaciones.length > 1 ? (
        <option value="">Todas las organizaciones</option>
      ) : null}
      {organizaciones.map((o) => (
        <option key={o.id} value={o.id}>
          {o.name}
        </option>
      ))}
    </Select>
  );
}
