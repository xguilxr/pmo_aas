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
      <span className="text-xs font-medium uppercase tracking-wide text-[var(--color-tertiary)]">
        Salud
      </span>
      {cargando ? (
        <span
          aria-hidden
          className="block h-8 w-24 animate-pulse rounded bg-[var(--color-muted)]"
        />
      ) : (
        <>
          <div className="flex items-baseline gap-2">
            {SALUDES.map((s) => (
              <span
                key={s}
                className="text-2xl font-semibold tabular-nums"
                style={{ color: colorSalud(s) }}
                title={etiquetaSalud(s)}
              >
                {conteos[s] ?? 0}
              </span>
            ))}
          </div>
          {/* La barra proporcional: el desglose que un conteo no da. Sin
              proyectos no se pinta —una barra vacía se lee como «todo verde»—. */}
          {total > 0 ? (
            <div
              className="mt-2 flex h-1.5 overflow-hidden rounded-full"
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
          ) : null}
          <p className="text-[11px] text-[var(--color-tertiary)]">
            {total > 0
              ? `${SALUDES.map((s) => etiquetaSalud(s).toLowerCase()).join(" · ")} — de ${total}`
              : "Sin proyectos activos que evaluar"}
          </p>
        </>
      )}
    </>
  );
  // Las mismas clases que `KpiCard`: comparte fila con cinco de ellas y una
  // caja distinta en medio se lee como que esa tarjeta es de otra cosa.
  const clases =
    "group flex h-full flex-col gap-1 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-sm)] transition-colors";
  return href ? (
    <Link
      href={href}
      className={cn(
        clases,
        "hover:border-[var(--border-strong)] hover:bg-[var(--color-subtle)]",
      )}
    >
      {cuerpo}
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
    <div className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--shadow-sm)]">
      <h3 className="text-xs font-medium uppercase tracking-wide text-[var(--color-tertiary)]">
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
        <p className="mt-3 text-xs text-[var(--color-tertiary)]">{vacio}</p>
      ) : (
        <ul className="mt-2 divide-y divide-[var(--border-subtle)]">
          {filas.map((f) => {
            const contenido = (
              <>
                <span className="min-w-0 flex-1 truncate" title={f.titulo}>
                  {f.titulo}
                </span>
                <span className="shrink-0 whitespace-nowrap text-right">
                  <span
                    className="font-semibold tabular-nums"
                    style={f.color ? { color: f.color } : undefined}
                  >
                    {f.cifra}
                  </span>
                  {f.detalle ? (
                    <span className="ml-1.5 text-[11px] text-[var(--color-tertiary)]">
                      {f.detalle}
                    </span>
                  ) : null}
                </span>
              </>
            );
            return (
              <li key={f.id} className="text-[13px] text-[var(--color-primary)]">
                {f.href ? (
                  <Link
                    href={f.href}
                    className="flex items-center gap-2 py-1.5 hover:text-[var(--color-accent-fg)]"
                  >
                    {contenido}
                  </Link>
                ) : (
                  <span className="flex items-center gap-2 py-1.5">{contenido}</span>
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
      <ul className="space-y-1.5">
        {DIMENSIONES.map((d) => {
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
              className="flex items-center gap-3 rounded-[var(--radius-md)] border border-[var(--border-subtle)] px-3 py-2"
            >
              <span
                aria-hidden
                className="h-2.5 w-2.5 shrink-0 rounded-full"
                style={{
                  backgroundColor: evaluados > 0 ? HEALTH_FILL[peor] : "var(--color-muted)",
                }}
              />
              <span className="min-w-0 flex-1 truncate text-[13px] font-medium text-[var(--color-primary)]">
                {d.etiqueta}
              </span>
              {evaluados === 0 ? (
                <span className="text-[11px] text-[var(--color-tertiary)]">
                  sin evaluar
                </span>
              ) : (
                <span className="shrink-0 whitespace-nowrap text-[11px] tabular-nums text-[var(--color-tertiary)]">
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
        <p className="mt-2.5 text-[11px] text-[var(--color-tertiary)]">{corte}</p>
      ) : null}
    </div>
  );
}
