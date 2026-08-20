"use client";

/**
 * US-208 — La pestaña «Capacidad» de Recursos.
 *
 * Artboard «Recursos › Capacidad» de los mockups aprobados. Cuatro paneles que
 * contestan la misma pregunta a distintas alturas:
 *
 * 1. **Carga por persona × semana** — quién está saturado y **cuándo**.
 * 2. **Capacidad vs demanda** — si la organización entera da o no da.
 * 3. **Críticos compartidos** — quién es el cuello de botella.
 * 4. **Acciones sugeridas** — la lectura de los tres, en una frase.
 *
 * ## Por qué el heatmap es semanal y no mensual
 *
 * Ya había una matriz mensual (`monthly_utilization`, US-186) y no sirve para
 * esto. Una persona al 90 % de media en septiembre puede estar al 160 % la
 * semana del corte y al 40 % el resto: el promedio mensual esconde exactamente
 * el pico que hay que renivelar. El mockup pide semanas porque las decisiones de
 * capacidad se toman por semana («lo movemos a la s37»).
 *
 * ## La escala de color
 *
 * Cinco tramos y no un degradado continuo: un degradado obliga a comparar tonos
 * entre celdas lejanas, y lo que hay que ver de un golpe es dónde se cruza el
 * 100 %. Los tramos son fijos y no derivados de los umbrales del inquilino a
 * propósito — los umbrales configuran cuándo **avisar**, y esta escala dice
 * cuánto hay asignado, que es un hecho.
 */
import { useMemo, useState } from "react";

import { Select } from "@/components/ui/select";
import { MarcaDeDatos, useLectura } from "@/components/ui/marca-de-datos";
import { cn } from "@/lib/cn";
import type {
  CargaSemanalResponse,
  FilaDeCarga,
  SemanaDeCarga,
} from "@/lib/api/capacity";

/** Los cinco tramos del mockup: 0 · ≤50 · ≤80 · ≤100 · >100. */
const TRAMOS: { tope: number; etiqueta: string; fondo: string; texto: string }[] = [
  { tope: 0, etiqueta: "0", fondo: "var(--color-subtle)", texto: "var(--color-tertiary)" },
  { tope: 50, etiqueta: "≤50", fondo: "var(--color-success-bg)", texto: "var(--color-success-fg)" },
  { tope: 80, etiqueta: "≤80", fondo: "var(--color-info-bg)", texto: "var(--color-info-fg)" },
  { tope: 100, etiqueta: "≤100", fondo: "var(--color-warning-bg)", texto: "var(--color-warning-fg)" },
  { tope: Infinity, etiqueta: ">100", fondo: "var(--color-danger-bg)", texto: "var(--color-danger-fg)" },
];

function tramo(valor: number) {
  return TRAMOS.find((t) => valor <= t.tope) ?? TRAMOS[TRAMOS.length - 1];
}

/** Las semanas que una asignación toca, para el desglose de la celda. */
function tocaLaSemana(
  a: { start_date: string | null; end_date: string | null },
  semana: SemanaDeCarga,
): boolean {
  // Sin fechas la asignación es indefinida y cuenta en toda semana: es la misma
  // regla que aplica el servidor, y discrepar aquí haría que el desglose sumara
  // distinto de la celda que lo abrió.
  return (
    (!a.start_date || a.start_date <= semana.end) &&
    (!a.end_date || a.end_date >= semana.start)
  );
}

type Celda = { fila: FilaDeCarga; indice: number } | null;

export function CapacidadSemanal({
  datos,
  cargando,
  semanas,
  onSemanas,
}: {
  datos: CargaSemanalResponse | null;
  cargando?: boolean;
  semanas: number;
  onSemanas: (n: number) => void;
}) {
  const [area, setArea] = useState("");
  const [celda, setCelda] = useState<Celda>(null);
  // DAT-11 — el periodo lo elige este panel, no la pantalla: por eso la marca
  // vive aquí y dice cuántas semanas cubre. `ventana` es lo más cerca que el
  // vocabulario cerrado tiene de «las próximas N semanas»; el detalle lo
  // precisa, y sin él «ventana móvil» se leería como que mira hacia atrás.
  const leido = useLectura(datos);

  const areas = useMemo(() => {
    const set = new Set<string>();
    for (const f of datos?.rows ?? []) if (f.area) set.add(f.area);
    return [...set].sort();
  }, [datos]);

  const filas = useMemo(() => {
    const todas = datos?.rows ?? [];
    return area ? todas.filter((f) => f.area === area) : todas;
  }, [datos, area]);

  if (cargando) {
    return (
      <div className="space-y-2" aria-hidden>
        {Array.from({ length: 8 }).map((_, i) => (
          <span
            key={i}
            className="block h-8 animate-pulse rounded bg-[var(--color-muted)]"
          />
        ))}
      </div>
    );
  }

  // DIS-03 — sin asignaciones con FTE no hay heatmap que pintar, y decirlo con
  // el camino a arreglarlo es más útil que una rejilla vacía.
  if (!datos || datos.rows.length === 0) {
    return (
      <div className="rounded-[var(--radius-xl)] border border-dashed border-[var(--border-default)] p-10 text-center text-sm text-[var(--color-tertiary)]">
        Ningún recurso tiene asignaciones activas en las próximas {semanas}{" "}
        semanas. La carga se calcula del <strong>% FTE</strong> de las
        participaciones: cárgalo en el directorio de cada proyecto y aparece aquí.
      </div>
    );
  }

  const sem = datos.weeks;

  return (
    <div className="space-y-4">
      {leido && (
        <MarcaDeDatos
          periodo="ventana"
          detalle={`próximas ${semanas} semanas, desde el lunes de esta`}
          actualizado={leido}
        />
      )}

      <div className="flex flex-wrap items-center gap-2">
        <Select
          aria-label="Filtrar por área"
          value={area}
          onChange={(e) => setArea(e.target.value)}
          className="h-9 min-w-[150px]"
        >
          <option value="">Todas las áreas</option>
          {areas.map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </Select>
        <Select
          aria-label="Periodo del heatmap"
          value={String(semanas)}
          onChange={(e) => onSemanas(Number(e.target.value))}
          className="h-9"
        >
          {[8, 12, 16, 26].map((n) => (
            <option key={n} value={n}>
              {n} semanas
            </option>
          ))}
        </Select>
        <span className="ml-auto flex items-center gap-1.5 text-[11px] text-[var(--color-tertiary)]">
          % FTE asignado:
          {TRAMOS.map((t) => (
            <span
              key={t.etiqueta}
              className="rounded px-1.5 py-0.5 font-medium"
              style={{ backgroundColor: t.fondo, color: t.texto }}
            >
              {t.etiqueta}
            </span>
          ))}
        </span>
      </div>

      <section
        aria-label="Carga por persona y semana"
        className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]"
      >
        <div className="max-h-[60vh] overflow-auto">
          <table className="w-full min-w-max border-separate border-spacing-0 text-[12px]">
            <thead>
              <tr>
                {/* Igual que en la vista maestra: el nombre pegado a la
                    izquierda o al hacer scroll uno pierde de quién es la fila. */}
                <th className="sticky left-0 top-0 z-20 border-b border-[var(--border-default)] bg-[var(--color-surface)] px-3 py-2 text-left text-[11px] font-medium uppercase tracking-wide text-[var(--color-tertiary)]">
                  Recurso
                </th>
                {sem.map((s) => (
                  <th
                    key={s.label}
                    title={`${s.start} a ${s.end}`}
                    className="sticky top-0 z-10 border-b border-[var(--border-default)] bg-[var(--color-surface)] px-2 py-2 text-center text-[11px] font-medium text-[var(--color-tertiary)]"
                  >
                    {s.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filas.map((f) => (
                <tr key={`${f.kind}-${f.id}`} className="group">
                  <th
                    scope="row"
                    className="sticky left-0 z-10 max-w-[240px] border-b border-[var(--border-subtle)] bg-[var(--color-surface)] px-3 py-1.5 text-left font-normal group-hover:bg-[var(--color-subtle)]"
                  >
                    <span className="block truncate text-[var(--color-primary)]">
                      {f.name}
                      {f.kind === "team" ? (
                        <span className="ml-1 text-[var(--color-tertiary)]">
                          ({f.members})
                        </span>
                      ) : null}
                    </span>
                    <span className="block truncate text-[10px] text-[var(--color-tertiary)]">
                      {f.kind === "team"
                        ? "promedio del equipo"
                        : [f.discipline, `cap. ${Math.round(f.capacity_pct)}%`]
                            .filter(Boolean)
                            .join(" · ")}
                    </span>
                  </th>
                  {f.per_week.map((v, i) => {
                    const t = tramo(v);
                    const activa =
                      celda?.fila.id === f.id && celda?.indice === i;
                    return (
                      <td
                        key={i}
                        className="border-b border-[var(--border-subtle)] px-0.5 py-0.5"
                      >
                        <button
                          type="button"
                          // Las filas de equipo no tienen desglose: su valor es
                          // un promedio, y «los proyectos del promedio» no es
                          // una lista que signifique nada.
                          disabled={f.kind === "team"}
                          onClick={() => setCelda(activa ? null : { fila: f, indice: i })}
                          style={{ backgroundColor: t.fondo, color: t.texto }}
                          className={cn(
                            "block w-full rounded px-2 py-1 text-center tabular-nums",
                            f.kind === "actor" && "hover:ring-1 hover:ring-[var(--border-strong)]",
                            activa && "ring-2 ring-[var(--color-accent)]",
                          )}
                          title={
                            f.kind === "actor"
                              ? `${f.name} · ${sem[i]?.label}: ${Math.round(v)}% — clic para ver los proyectos`
                              : `${f.name} · ${sem[i]?.label}: ${Math.round(v)}% (promedio)`
                          }
                        >
                          {Math.round(v)}
                        </button>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="border-t border-[var(--border-default)] px-3 py-2 text-[11px] text-[var(--color-tertiary)]">
          Clic en una celda: los proyectos que componen esa carga. Las filas de
          equipo promedian a sus miembros. La demanda de cada persona cuenta{" "}
          <strong>todos</strong> sus proyectos, no solo los de la organización
          activa: quien está saturado lo está por la suma de todo.
          {datos.unquantified_resources > 0 ? (
            <>
              {" "}
              <strong>{datos.unquantified_resources}</strong>{" "}
              {datos.unquantified_resources === 1 ? "recurso está" : "recursos están"}{" "}
              asignado sin % FTE capturado y no{" "}
              {datos.unquantified_resources === 1 ? "aparece" : "aparecen"} aquí:
              una fila en cero se leería como «libre», y lo que pasa es que no se
              sabe. Captura el % en el directorio del proyecto.
            </>
          ) : null}
        </p>
      </section>

      {celda ? (
        <section
          aria-label="Desglose de la carga"
          className="rounded-[var(--radius-xl)] border border-[var(--color-accent)] bg-[var(--color-surface)] p-4 shadow-[var(--shadow-sm)]"
        >
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h3 className="text-sm font-semibold text-[var(--color-primary)]">
              {celda.fila.name} · {sem[celda.indice]?.label}
              <span className="ml-2 font-normal text-[var(--color-tertiary)]">
                {Math.round(celda.fila.per_week[celda.indice] ?? 0)}% asignado de{" "}
                {Math.round(celda.fila.capacity_pct)}% de capacidad
              </span>
            </h3>
            <button
              type="button"
              onClick={() => setCelda(null)}
              className="text-[11px] text-[var(--color-tertiary)] underline hover:text-[var(--color-accent)]"
            >
              Cerrar
            </button>
          </div>
          <ul className="mt-2 divide-y divide-[var(--border-subtle)]">
            {celda.fila.assignments
              .filter((a) => sem[celda.indice] && tocaLaSemana(a, sem[celda.indice]))
              .map((a) => (
                <li
                  key={`${a.project_id}-${a.start_date ?? ""}`}
                  className="flex items-center justify-between gap-3 py-1.5 text-[13px]"
                >
                  <span className="min-w-0 flex-1 truncate">
                    {a.project_name}
                    <span className="ml-1.5 text-[11px] text-[var(--color-tertiary)]">
                      {a.project_folio}
                    </span>
                    {a.is_critical ? (
                      <span className="ml-1.5 text-[11px] text-[var(--color-danger-fg)]">
                        crítico
                      </span>
                    ) : null}
                  </span>
                  <span className="shrink-0 tabular-nums">
                    {/* Sin FTE capturado no se pinta un cero: la participación
                        existe y no se sabe cuánto pesa, que no es lo mismo. */}
                    {a.allocation_pct === null
                      ? "sin % capturado"
                      : `${Math.round(a.allocation_pct)}%`}
                  </span>
                </li>
              ))}
          </ul>
        </section>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-3">
        <section
          aria-label="Capacidad vs demanda"
          className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--shadow-sm)]"
        >
          <h3 className="text-xs font-medium uppercase tracking-wide text-[var(--color-tertiary)]">
            Capacidad vs demanda (FTE)
          </h3>
          <ul className="mt-2 space-y-2">
            {datos.capacity_vs_demand.map((m) => {
              const excede = m.demand_fte > m.capacity_fte;
              // La barra se escala contra el mayor de los dos, no contra la
              // demanda: si se escalara contra la demanda, un mes con exceso y
              // otro sin él dibujarían la misma barra llena.
              const tope = Math.max(m.demand_fte, m.capacity_fte, 1);
              return (
                <li key={m.label}>
                  <div className="flex items-baseline justify-between text-[12px]">
                    <span className="text-[var(--color-primary)]">{m.label}</span>
                    <span
                      className="tabular-nums"
                      style={{
                        color: excede
                          ? "var(--color-danger-fg)"
                          : "var(--color-tertiary)",
                      }}
                    >
                      {m.demand_fte.toFixed(1)} / {m.capacity_fte.toFixed(1)}
                    </span>
                  </div>
                  <div className="relative mt-1 h-2 rounded-full bg-[var(--color-subtle)]">
                    <span
                      className="absolute inset-y-0 left-0 rounded-full"
                      style={{
                        width: `${(m.demand_fte / tope) * 100}%`,
                        backgroundColor: excede
                          ? "var(--color-danger-fg)"
                          : "var(--color-success-fg)",
                      }}
                    />
                    {/* La línea de capacidad: sin ella la barra no dice nada. */}
                    <span
                      aria-hidden
                      className="absolute inset-y-[-2px] w-0.5 bg-[var(--color-primary)]"
                      style={{ left: `${(m.capacity_fte / tope) * 100}%` }}
                    />
                  </div>
                </li>
              );
            })}
          </ul>
          <p className="mt-2 text-[11px] text-[var(--color-tertiary)]">
            Barra = demanda asignada · línea = capacidad de los recursos activos.
          </p>
        </section>

        <section
          aria-label="Recursos críticos compartidos"
          className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--shadow-sm)]"
        >
          <h3 className="text-xs font-medium uppercase tracking-wide text-[var(--color-tertiary)]">
            Recursos críticos compartidos
          </h3>
          {datos.shared_critical.length === 0 ? (
            <p className="mt-3 text-xs text-[var(--color-tertiary)]">
              Nadie está en más de un proyecto a la vez: no hay cuello de botella
              compartido.
            </p>
          ) : (
            <ul className="mt-2 divide-y divide-[var(--border-subtle)]">
              {datos.shared_critical.map((c) => (
                <li key={c.actor_id} className="py-1.5 text-[13px]">
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="min-w-0 flex-1 truncate text-[var(--color-primary)]">
                      {c.name}
                    </span>
                    <span className="shrink-0 tabular-nums text-[11px] text-[var(--color-tertiary)]">
                      {c.projects_count} proy. · pico {Math.round(c.peak_pct)}%
                    </span>
                  </div>
                  <p
                    className="truncate text-[11px] text-[var(--color-tertiary)]"
                    title={c.projects.join(" · ")}
                  >
                    {c.projects.join(" · ")}
                  </p>
                </li>
              ))}
            </ul>
          )}
          <p className="mt-2 text-[11px] text-[var(--color-tertiary)]">
            «Compartido» es medido, no declarado: estar en dos o más proyectos a
            la vez lo es, con marca o sin ella.
          </p>
        </section>

        <section
          aria-label="Acciones sugeridas"
          className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--shadow-sm)]"
        >
          <h3 className="text-xs font-medium uppercase tracking-wide text-[var(--color-tertiary)]">
            Acciones sugeridas
          </h3>
          {datos.suggested.length === 0 ? (
            <p className="mt-3 text-xs text-[var(--color-tertiary)]">
              Nadie pasa de su capacidad en el horizonte. No hay nada que
              renivelar.
            </p>
          ) : (
            <ul className="mt-2 space-y-2 text-[13px] text-[var(--color-primary)]">
              {datos.suggested.map((s) => (
                <li key={s} className="flex gap-2">
                  <span aria-hidden className="text-[var(--color-tertiary)]">
                    ·
                  </span>
                  <span>{s}</span>
                </li>
              ))}
            </ul>
          )}
          {/* El propio mockup marca los escenarios como «próximamente». Se dice
              aquí para que quien lo conoce sepa que no falta: no está hecho. */}
          <p className="mt-3 border-t border-[var(--border-subtle)] pt-2 text-[11px] text-[var(--color-tertiary)]">
            Escenarios what-if (mover una asignación y ver el efecto): pendiente.
          </p>
        </section>
      </div>
    </div>
  );
}
