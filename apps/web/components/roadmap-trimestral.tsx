/**
 * US-247 — Roadmap trimestral del Portafolio.
 *
 * Una fila por proyecto, agrupada por portafolio, con una barra que va del
 * trimestre de inicio al de fin. El estado (por iniciar / en curso /
 * entregado / en espera) es del avance del proyecto, no de su salud: la
 * salud ya tiene su propia lectura en la matriz de abajo, y mezclar los dos
 * colores en la misma barra los vuelve ilegibles.
 */
import type { Project } from "@/lib/api/projects";
import type { Portfolio } from "@/lib/api/organizations";

type EstadoRoadmap = "por_iniciar" | "en_curso" | "entregado" | "en_espera";

const ESTADO_LABEL: Record<EstadoRoadmap, string> = {
  por_iniciar: "Por iniciar",
  en_curso: "En curso",
  entregado: "Entregado",
  en_espera: "En espera",
};

const ESTADO_COLOR: Record<EstadoRoadmap, string> = {
  por_iniciar: "var(--text-faint)",
  en_curso: "var(--color-accent)",
  entregado: "var(--color-success-fg)",
  en_espera: "var(--chart-neutral)",
};

function estadoDe(p: Project): EstadoRoadmap {
  if (p.phase === "cerrado") return "entregado";
  if (p.phase === "cancelado") return "en_espera";
  if (p.phase === "preparacion") return "por_iniciar";
  return "en_curso";
}

/** Trimestre (1-4) de una fecha ISO, o null si la fecha no cae en `year`. */
function trimestreEn(iso: string | null, year: number): number | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime()) || d.getUTCFullYear() !== year) return null;
  return Math.floor(d.getUTCMonth() / 3) + 1;
}

const TRIMESTRE_LABEL = ["1er trimestre", "2do trimestre", "3er trimestre", "4to trimestre"];

/** FASE-4 (revamp v2) — piso del navegador de año: "todo a partir del 26
 *  hacia adelante" (owner). Sin techo. */
const ANIO_MINIMO = 2026;

export function RoadmapTrimestral({
  proyectos,
  portafolios,
  year,
  onYearChange,
}: {
  proyectos: Project[];
  portafolios: Portfolio[];
  year: number;
  onYearChange: (y: number) => void;
}) {
  const trimestreActual =
    new Date().getFullYear() === year ? Math.floor(new Date().getMonth() / 3) + 1 : null;

  const nombrePortafolio = new Map(portafolios.map((p) => [p.id, p.name]));

  const conRango = proyectos
    .map((p) => {
      if (!p.start_date || !p.end_date) return null;
      const inicio = new Date(p.start_date);
      const fin = new Date(p.end_date);
      if (Number.isNaN(inicio.getTime()) || Number.isNaN(fin.getTime())) return null;
      // El proyecto puede empezar antes o terminar después del año mostrado;
      // se recorta a los bordes del roadmap en vez de desaparecer.
      const inicioAño = inicio.getUTCFullYear() < year ? 1 : trimestreEn(p.start_date, year);
      const finAño = fin.getUTCFullYear() > year ? 4 : trimestreEn(p.end_date, year);
      if (
        inicio.getUTCFullYear() > year ||
        fin.getUTCFullYear() < year ||
        inicioAño === null ||
        finAño === null
      )
        return null;
      return { proyecto: p, q1: inicioAño, q2: Math.max(inicioAño, finAño) };
    })
    .filter((x): x is { proyecto: Project; q1: number; q2: number } => x !== null);

  const porPortafolio = new Map<string, typeof conRango>();
  for (const fila of conRango) {
    const clave = fila.proyecto.portfolio_id ?? "sin-portafolio";
    if (!porPortafolio.has(clave)) porPortafolio.set(clave, []);
    porPortafolio.get(clave)!.push(fila);
  }

  // FASE-4 — navegador de año a la derecha del título. Piso 2026, sin techo.
  const controlAnio = (
    <div className="flex items-center gap-1.5">
      <button
        type="button"
        onClick={() => onYearChange(year - 1)}
        disabled={year <= ANIO_MINIMO}
        aria-label="Año anterior"
        className="flex h-6 w-6 items-center justify-center rounded-[var(--radius-sm)] border border-[var(--border-default)] text-[var(--text-secondary)] disabled:opacity-40"
      >
        ‹
      </button>
      <span className="font-mono text-[13px] font-semibold text-[var(--text-primary)]">
        {year}
      </span>
      <button
        type="button"
        onClick={() => onYearChange(year + 1)}
        aria-label="Año siguiente"
        className="flex h-6 w-6 items-center justify-center rounded-[var(--radius-sm)] border border-[var(--border-default)] text-[var(--text-secondary)]"
      >
        ›
      </button>
    </div>
  );

  if (conRango.length === 0) {
    return (
      <div>
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-sm font-semibold text-[var(--text-primary)]">
            Roadmap trimestral, {year}
          </h3>
          {controlAnio}
        </div>
        <p className="text-[12px] text-[var(--text-tertiary)]">
          Ningún proyecto visible tiene fecha de inicio y fin en {year} para el roadmap.
        </p>
      </div>
    );
  }

  return (
    <div role="img" aria-label={`Roadmap trimestral ${year}`}>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2.5">
          <h3 className="text-sm font-semibold text-[var(--text-primary)]">
            Roadmap trimestral, {year}
          </h3>
          {controlAnio}
        </div>
        <div className="flex flex-wrap gap-3.5 text-[10.5px] text-[var(--text-secondary)]">
          {(Object.keys(ESTADO_LABEL) as EstadoRoadmap[]).map((e) => (
            <span key={e} className="flex items-center gap-1.5">
              <span
                className="inline-block h-[9px] w-[9px] rounded-[3px]"
                style={{ background: ESTADO_COLOR[e] }}
              />
              {ESTADO_LABEL[e]}
            </span>
          ))}
        </div>
      </div>

      <div
        className="grid border-b border-[var(--border-default)] pb-1.5"
        style={{ gridTemplateColumns: "200px repeat(4,1fr)" }}
      >
        <span />
        {TRIMESTRE_LABEL.map((label, i) => {
          const q = i + 1;
          const esActual = q === trimestreActual;
          return (
            <span
              key={label}
              className={
                esActual
                  ? "border-l border-dashed border-[var(--color-accent)] text-center text-[10px] font-bold uppercase tracking-wide text-[var(--color-accent)]"
                  : "text-center text-[10px] font-semibold uppercase tracking-wide text-[var(--text-tertiary)]"
              }
            >
              {label}
              {esActual ? " · hoy" : ""}
            </span>
          );
        })}
      </div>

      {[...porPortafolio.entries()].map(([portfolioId, filas]) => (
        <div key={portfolioId}>
          <div
            className="grid items-center bg-[var(--color-bg-subtle)]"
            style={{ gridTemplateColumns: "200px repeat(4,1fr)", height: 20 }}
          >
            <span className="truncate pl-0.5 text-[10px] font-semibold uppercase tracking-wide text-[var(--text-tertiary)] [grid-column:1/-1]">
              {nombrePortafolio.get(portfolioId) ?? "Sin portafolio"}
            </span>
          </div>
          {filas.map(({ proyecto, q1, q2 }) => {
            const estado = estadoDe(proyecto);
            const color = ESTADO_COLOR[estado];
            const vacia = estado === "en_espera";
            return (
              <div
                key={proyecto.id}
                className="grid items-center border-b border-[var(--border-subtle)]"
                style={{ gridTemplateColumns: "200px repeat(4,1fr)", height: 28 }}
              >
                <span className="truncate pr-1.5 text-[11px] text-[var(--text-secondary)]">
                  {proyecto.folio} — {proyecto.name}
                </span>
                <div
                  className="flex h-4 items-center justify-center rounded-full text-[9px] font-semibold text-white"
                  style={{
                    gridColumn: `${q1 + 1}/${q2 + 2}`,
                    background: vacia ? "var(--color-bg-muted)" : color,
                    border: vacia ? "1px solid var(--border-default)" : undefined,
                    color: vacia ? "transparent" : undefined,
                  }}
                >
                  {estado === "en_curso" ? `${proyecto.progress}%` : estado === "entregado" ? "✓" : ""}
                </div>
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}
