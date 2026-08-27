"use client";

/**
 * US-206 — Las piezas del tablero ejecutivo que no existían.
 *
 * El mockup «Dashboard ejecutivo» pide tres cosas que ningún componente sabía
 * pintar: una tarjeta de salud con los tres conteos juntos, las listas cortas
 * de «qué mirar primero», y el semáforo consolidado por dimensión.
 *
 * Viven aquí y no en `dashboard-charts.tsx` porque no son gráficos: son lecturas
 * de una cartera. `dashboard-charts.tsx` dibuja SVG genérico —una tarta es una
 * tarta— y estos tres saben qué significa un rojo.
 */
import Link from "next/link";

import { HEALTH_FILL, colorSalud } from "@/components/dashboard-charts";
import { etiquetaSalud } from "@/lib/api/projects";
import { cn } from "@/lib/cn";

/** El orden de siempre: lo que hay que mirar primero, primero. */
const SALUDES = ["red", "yellow", "green"] as const;

/**
 * La tarjeta de salud del mockup: los tres conteos en una, no tres tarjetas.
 *
 * Tres tarjetas separadas obligan a sumarlas mentalmente para saber si cubren
 * la cartera entera, y esa suma es justo el dato que dice si falta algo. Con el
 * total al frente y el desglose debajo, «14 · 6 · 3 de 23» se lee de un golpe.
 */
export function TarjetaDeSalud({
  conteos,
  cargando,
  href,
}: {
  conteos: Record<string, number>;
  cargando?: boolean;
  href?: string;
}) {
  const total = SALUDES.reduce((suma, s) => suma + (conteos[s] ?? 0), 0);
  const cuerpo = (
    <>
      <span className="text-[10.5px] font-semibold uppercase tracking-[0.07em] text-[var(--text-tertiary)]">
        Salud
      </span>
      {cargando ? (
        <span
          aria-hidden
          className="block h-8 w-24 animate-pulse rounded bg-[var(--color-muted)]"
        />
      ) : total > 0 ? (
        <>
          <div className="flex items-baseline gap-2 font-mono text-[26px] font-medium tabular-nums">
            {SALUDES.map((s) => (
              <span key={s} style={{ color: colorSalud(s) }} title={etiquetaSalud(s)}>
                {conteos[s] ?? 0}
              </span>
            ))}
          </div>
          {/* La barra proporcional: el desglose que un conteo no da. */}
          <div
            className="flex h-1 overflow-hidden rounded-full"
            role="img"
            aria-label={SALUDES.map(
              (s) => `${etiquetaSalud(s)}: ${conteos[s] ?? 0}`,
            ).join(", ")}
          >
            {SALUDES.map((s) => {
              const n = conteos[s] ?? 0;
              if (n === 0) return null;
              return (
                <span
                  key={s}
                  style={{
                    width: `${(n / total) * 100}%`,
                    backgroundColor: HEALTH_FILL[s],
                  }}
                />
              );
            })}
          </div>
        </>
      ) : (
        <p className="text-[11px] text-[var(--text-tertiary)]">
          Sin proyectos activos que evaluar
        </p>
      )}
    </>
  );
  // Las mismas clases que `KpiCard`: comparte fila con cinco de ellas y una
  // caja distinta en medio se lee como que esa tarjeta es de otra cosa.
  const clases = "group flex h-full flex-col gap-2 p-4 transition-colors hover:bg-[var(--color-subtle)]";
  return href ? (
    <Link href={href} className="block focus:outline-none">
      <div className={clases}>{cuerpo}</div>
    </Link>
  ) : (
    <div className={clases}>{cuerpo}</div>
  );
}

export type FilaTop = {
  /** Clave estable para React y, cuando hay `href`, destino de la fila. */
  id: string;
  titulo: string;
  /** La cifra que ordena la lista, ya formateada. */
  cifra: string;
  /** Contexto de la cifra: «3 severos», «4 proy.». Opcional. */
  detalle?: string;
  /** Tinte de la cifra. Sin él va en el color de texto normal. */
  color?: string;
  href?: string;
};

/**
 * Una de las listas «Top» del mockup.
 *
 * Existen porque un agregado dice que algo pasa y una lista dice **dónde**.
 * «7 riesgos severos» manda a alguien a buscar; «ERP Rollout Fase 2 — 3
 * severos» lo manda a un proyecto.
 *
 * Se quedan cortas a propósito (cinco). Una lista de veintitrés vuelve a ser la
 * tabla que ya existe abajo, y entonces no ordena nada.
 */
export function ListaTop({
  titulo,
  filas,
  cargando,
  vacio,
}: {
  titulo: string;
  filas: FilaTop[];
  cargando?: boolean;
  /** Qué decir cuando no hay nada. En estas listas «nada» es una buena noticia
   *  —ningún proyecto atrasado— y hay que decirlo así, no como un hueco. */
  vacio: string;
}) {
  return (
    <div className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] px-4 py-3.5 shadow-[var(--relieve-isla)]">
      <h3 className="text-[10.5px] font-semibold uppercase tracking-[0.07em] text-[var(--text-tertiary)]">
        {titulo}
      </h3>
      {cargando ? (
        <div className="mt-2 space-y-2" aria-hidden>
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="block h-5 animate-pulse rounded bg-[var(--color-muted)]"
            />
          ))}
        </div>
      ) : filas.length === 0 ? (
        <p className="mt-3 text-xs text-[var(--text-tertiary)]">{vacio}</p>
      ) : (
        <ul className="mt-2.5">
          {filas.map((f, i) => {
            const esUltimo = i === filas.length - 1;
            const contenido = (
              <>
                <span className="min-w-0 flex-1 truncate" title={f.titulo}>
                  {f.titulo}
                </span>
                <span className="shrink-0 whitespace-nowrap text-right">
                  <span
                    className="font-mono text-[12.5px] font-medium tabular-nums"
                    style={f.color ? { color: f.color } : undefined}
                  >
                    {f.cifra}
                  </span>
                  {f.detalle ? (
                    <span className="ml-1.5 text-[11px] text-[var(--text-faint)]">
                      {f.detalle}
                    </span>
                  ) : null}
                </span>
              </>
            );
            return (
              <li
                key={f.id}
                className={cn(
                  "text-[13px] text-[var(--text-primary)]",
                  !esUltimo && "border-b border-[var(--border-subtle)] shadow-[var(--linea-surco)]",
                )}
              >
                {f.href ? (
                  <Link
                    href={f.href}
                    className="flex items-center gap-2.5 py-1.5 hover:text-[var(--color-accent-fg)]"
                  >
                    {contenido}
                  </Link>
                ) : (
                  <span className="flex items-center gap-2.5 py-1.5">{contenido}</span>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

/** Las cinco dimensiones del semáforo 5+1, en el orden del mockup. */
const DIMENSIONES: { clave: string; etiqueta: string }[] = [
  { clave: "schedule", etiqueta: "Cronograma" },
  { clave: "budget", etiqueta: "Presupuesto" },
  { clave: "risks", etiqueta: "Riesgos" },
  { clave: "resources", etiqueta: "Recursos" },
  { clave: "decisions", etiqueta: "Decisiones" },
];

/**
 * El semáforo consolidado del mockup: una luz por dimensión, para la cartera.
 *
 * ## La regla de consolidación, y por qué esta
 *
 * Una dimensión de la cartera se pinta del **peor color que aparezca** en ella:
 * roja si algún proyecto la tiene roja, amarilla si alguno la tiene amarilla,
 * verde si todos lo están.
 *
 * Es la única regla que contesta la pregunta que un semáforo consolidado hace
 * —«¿hay algo mal en esta dimensión?»—. Un promedio de colores diría «amarillo»
 * de una cartera con veintidós proyectos verdes y uno rojo, y eso no es un
 * resumen: es esconder el rojo detrás de la mayoría. Y un umbral («rojo si más
 * del 20 % está rojo») elige un número arbitrario que nadie va a poder
 * defender delante del proyecto que quedó fuera.
 *
 * Lo que evita que la regla vuelva todo rojo con veintitrés proyectos es el
 * conteo al lado: la luz dice que hay fuego y el número dice cuánto. Sin el
 * conteo esta pantalla sería inútil, y por eso no es opcional.
 */
export function SemaforoConsolidado({
  filas,
  cargando,
  corte,
}: {
  filas: { dims: Record<string, string | null> }[];
  cargando?: boolean;
  /** Pie del mockup: de qué corte son estos colores. */
  corte?: string;
}) {
  if (cargando) {
    return (
      <div className="space-y-2" aria-hidden>
        {DIMENSIONES.map((d) => (
          <span
            key={d.clave}
            className="block h-8 animate-pulse rounded bg-[var(--color-muted)]"
          />
        ))}
      </div>
    );
  }
  if (filas.length === 0) {
    return (
      <p className="py-6 text-center text-sm text-[var(--color-tertiary)]">
        Sin proyectos activos: no hay semáforo que consolidar. En cuanto haya uno
        con salud evaluada, sus cinco dimensiones aparecen aquí.
      </p>
    );
  }

  return (
    <div>
      <ul className="flex flex-col">
        {DIMENSIONES.map((d, i) => {
          const conteos = { red: 0, yellow: 0, green: 0 };
          for (const fila of filas) {
            const c = fila.dims?.[d.clave];
            if (c === "red" || c === "yellow" || c === "green") conteos[c] += 1;
          }
          const evaluados = conteos.red + conteos.yellow + conteos.green;
          const peor =
            conteos.red > 0 ? "red" : conteos.yellow > 0 ? "yellow" : "green";
          return (
            <li
              key={d.clave}
              className={cn(
                "flex h-7.5 items-center gap-2.5 text-[12.5px]",
                i > 0 && "border-t border-[var(--border-subtle)] shadow-[var(--linea-surco-arriba)]",
              )}
            >
              <span
                aria-hidden
                className="h-2 w-2 shrink-0 rounded-full"
                style={{
                  backgroundColor: evaluados > 0 ? HEALTH_FILL[peor] : "var(--color-muted)",
                }}
              />
              <span className="min-w-0 flex-1 truncate font-medium text-[var(--text-primary)]">
                {d.etiqueta}
              </span>
              {evaluados === 0 ? (
                <span className="text-[11px] text-[var(--text-faint)]">
                  sin evaluar
                </span>
              ) : (
                <span className="shrink-0 whitespace-nowrap font-mono text-[11px] text-[var(--text-tertiary)]">
                  <span style={{ color: colorSalud(peor) }} className="font-semibold">
                    {etiquetaSalud(peor)}
                  </span>
                  {conteos.red > 0 ? ` · ${conteos.red} en rojo` : ""}
                  {conteos.yellow > 0 ? ` · ${conteos.yellow} en ámbar` : ""}
                  {` · de ${evaluados}`}
                </span>
              )}
            </li>
          );
        })}
      </ul>
      {corte ? (
        <p className="mt-2.5 text-[11px] text-[var(--text-faint)]">{corte}</p>
      ) : null}
    </div>
  );
}
