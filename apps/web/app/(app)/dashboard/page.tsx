"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import {
  AlertOctagon,
  BarChart3,
  Briefcase,
  CircleDollarSign,
  TrendingUp,
  Users,
} from "lucide-react";

import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Bars,
  Heatmap,
  Legend,
  PALETTE,
  Pie,
  RiskMatrix,
  TrendLines,
  Treemap,
  colorSalud,
} from "@/components/dashboard-charts";
import { KpiCard } from "@/components/kpi-card";
import { ApiError } from "@/lib/api";
import {
  getDashboardCharts,
  getDashboardKpis,
  getDashboardTops,
  type DashboardCharts as ChartsData,
  type DashboardKpis,
  type DashboardTops,
} from "@/lib/api/dashboard";
import { getCapacitySummary, type CapacitySummaryResponse } from "@/lib/api/capacity";
import {
  ListaTop,
  SemaforoConsolidado,
  TarjetaDeSalud,
  type FilaTop,
} from "@/components/tablero-ejecutivo";
import { getHealthMatrix, type HealthMatrixResponse } from "@/lib/api/analytics";
import {
  captureSnapshots,
  getHeatmap,
  getRiskMatrix,
  getTreemap,
  getTrends,
  type HeatmapResponse,
  type RiskMatrixResponse,
  type TreemapResponse,
  type TrendsResponse,
} from "@/lib/api/analytics";
import {
  listPortfolios,
  listPrograms,
  type Portfolio,
  type Program,
} from "@/lib/api/organizations";
import { useOrganizacionActiva } from "@/components/organizacion-activa";
import {
  PHASE_LABEL,
  PHASE_ORDER,
  TYPE_LABEL,
  etiquetaSalud,
  type ProjectPhase,
  type ProjectType,
} from "@/lib/api/projects";
import { getStoredUser } from "@/lib/auth-storage";
import { cn } from "@/lib/cn";
import { MarcaDeDatos, useLectura } from "@/components/ui/marca-de-datos";
import { formatearDesglose, formatearImporte, monedaUnica } from "@/lib/moneda";
import { useMonedaPreferida } from "@/lib/moneda-tenant";
import { etiquetaDeCadencia, useCadenciaDeReporte } from "@/lib/cadencia-tenant";

// ADR-023: la fase es ORDINAL —preparación → ejecución → hypercare → cerrado
// es una secuencia—, así que va con la rampa de un solo tono, no con cuatro
// colores sueltos. `cancelado` se sale de la secuencia y va al neutro, igual
// que en su insignia.
//
// US-202 — la tabla se deriva de `PHASE_ORDER` en vez de repetir las claves:
// esta y la de etiquetas se habían quedado en inglés (y una, en `support`, que
// ADR-019 renombró hace dos semanas). Una clave que ya no existe no falla —
// simplemente deja la fase sin color y con el valor crudo por nombre.
const PHASE_COLOR: Record<ProjectPhase, string> = {
  preparacion: PALETTE.scale[0],
  ejecucion: PALETTE.scale[2],
  hypercare: PALETTE.scale[3],
  cerrado: PALETTE.scale[4],
  cancelado: PALETTE.neutral,
};

function toEntries<T>(obj: Record<string, T>): [string, T][] {
  return Object.keys(obj).map((k) => [k, obj[k]]);
}

/** La fase en palabras. Devuelve el crudo si no la conoce: en un gráfico, un
 *  valor fuera del catálogo es un dato que hay que **ver** para corregirlo. */
function etiquetaFase(clave: string): string {
  return PHASE_LABEL[clave as ProjectPhase] ?? clave;
}

function colorFase(clave: string): string {
  return PHASE_COLOR[clave as ProjectPhase] ?? PALETTE.accent;
}

/** `budget_by_type` agrupa los proyectos sin tipo bajo `unspecified`, que no es
 *  uno de los cuatro del enum: la API lo sintetiza para no perder el importe. */
function etiquetaTipo(clave: string): string {
  if (clave === "unspecified") return "Sin especificar";
  return TYPE_LABEL[clave as ProjectType] ?? clave;
}

export default function DashboardPage() {
  return (
    <Suspense fallback={<DashboardSkeleton />}>
      <DashboardInner />
    </Suspense>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-10 w-48" />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24 w-full" />
        ))}
      </div>
    </div>
  );
}

function DashboardInner() {
  // BUG-092 — para lo que NO cuelga de un proyecto: gráficos de cartera y
  // filas agregadas. Un importe de proyecto trae la suya, ya resuelta.
  const monedaDeCartera = useMonedaPreferida();
  // US-213 — la tendencia se muestrea a la cadencia con la que esta PMO
  // reporta. El mockup pide bi-semanal, que es el default; si el inquilino
  // reporta cada semana o cada mes, el gráfico lo sigue sin tocar nada.
  const cadenciaDeReporte = useCadenciaDeReporte();
  const user = getStoredUser();
  const router = useRouter();
  const searchParams = useSearchParams();
  // US-205 — la organización ya no es estado de esta página: vive en el header.
  // Lo que queda en la URL son los dos niveles que **sí** son de esta vista.
  const { efectiva: orgFilter, elegir: elegirOrg } = useOrganizacionActiva();
  // US-201 — los tres niveles viven en la URL, no solo la organización: un
  // tablero filtrado que no se puede enviar por chat obliga a que el otro
  // reproduzca los clics, y ahí es donde se miran números distintos.
  const portfolioFromUrl = searchParams.get("portfolio_id") ?? "";
  const programFromUrl = searchParams.get("program_id") ?? "";

  const [kpis, setKpis] = useState<DashboardKpis | null>(null);
  // DAT-11: cuándo cambió lo que se está mostrando.
  const leido = useLectura(kpis);
  const [charts, setCharts] = useState<ChartsData | null>(null);
  const [loadingKpis, setLoadingKpis] = useState(true);
  const [loadingCharts, setLoadingCharts] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [portfolioFilter, setPortfolioFilter] = useState(portfolioFromUrl);
  const [programs, setPrograms] = useState<Program[]>([]);
  const [programFilter, setProgramFilter] = useState(programFromUrl);
  // US-154 — analíticas ricas (tendencias, matriz de riesgos, heatmap, treemap).
  const [riskMatrix, setRiskMatrix] = useState<RiskMatrixResponse | null>(null);
  const [heatmap, setHeatmap] = useState<HeatmapResponse | null>(null);
  const [treemap, setTreemap] = useState<TreemapResponse | null>(null);
  const [trends, setTrends] = useState<TrendsResponse | null>(null);
  // US-206 — las tres piezas del mockup que no venían de aquí: las listas
  // «top», la carga de recursos y el semáforo por dimensión.
  const [tops, setTops] = useState<DashboardTops | null>(null);
  const [capacidad, setCapacidad] = useState<CapacitySummaryResponse | null>(null);
  const [semaforo, setSemaforo] = useState<HealthMatrixResponse | null>(null);
  const [cargandoEjecutivo, setCargandoEjecutivo] = useState(true);
  // El heatmap/treemap/trends agregados son admin-equivalente; si la primera
  // llamada 403ea, ocultamos esas secciones (detección por capacidad).
  const [isAdminView, setIsAdminView] = useState(false);
  const [capturing, setCapturing] = useState(false);
  const [captureMsg, setCaptureMsg] = useState<string | null>(null);

  // US-201 — gana el nivel más específico. Los endpoints de analíticas toman un
  // scope único (no una cascada), así que un programa elegido manda sobre su
  // portafolio y este sobre su organización: es lo que el usuario acaba de
  // pedir, y los de arriba ya están implícitos en la jerarquía.
  const { scope: analyticsScope, id: analyticsId } = useMemo(() => {
    if (programFilter) return { scope: "program" as const, id: programFilter };
    if (portfolioFilter) return { scope: "portfolio" as const, id: portfolioFilter };
    if (orgFilter) return { scope: "organization" as const, id: orgFilter };
    return { scope: "tenant" as const, id: undefined };
  }, [orgFilter, portfolioFilter, programFilter]);

  // La cascada tal cual, para los endpoints que filtran en vez de scopear.
  const jerarquia = useMemo(
    () => ({
      organization_id: orgFilter || undefined,
      portfolio_id: portfolioFilter || undefined,
      program_id: programFilter || undefined,
    }),
    [orgFilter, portfolioFilter, programFilter],
  );

  useEffect(() => {
    let cancelled = false;
    const scopeParams = { scope: analyticsScope, id: analyticsId };

    // Matriz de riesgos: disponible para todos los roles (scoped por proyecto).
    getRiskMatrix(scopeParams)
      .then((r) => !cancelled && setRiskMatrix(r))
      .catch(() => !cancelled && setRiskMatrix(null));

    // Vistas agregadas (admin-equivalente).
    getHeatmap(jerarquia)
      .then((r) => {
        if (cancelled) return;
        setHeatmap(r);
        setIsAdminView(true);
      })
      .catch(() => {
        if (cancelled) return;
        setHeatmap(null);
        setIsAdminView(false);
      });
    getTreemap(scopeParams)
      .then((r) => !cancelled && setTreemap(r))
      .catch(() => !cancelled && setTreemap(null));
    getTrends({ ...scopeParams, weeks: 12, cadencia_dias: cadenciaDeReporte })
      .then((r) => !cancelled && setTrends(r))
      .catch(() => !cancelled && setTrends(null));

    // US-206 — las tres del tablero ejecutivo. Se cargan juntas y con un solo
    // indicador de carga: el mockup las presenta como una fila, y tres esqueletos
    // apareciendo en momentos distintos se lee como que algo va mal.
    setCargandoEjecutivo(true);
    void Promise.allSettled([
      getDashboardTops(jerarquia).then((r) => !cancelled && setTops(r)),
      // La capacidad no conoce la cascada: filtra por organización y nada más.
      // Con un portafolio elegido devuelve los recursos de toda la organización,
      // y eso es correcto —una persona sobreasignada lo está por la suma de
      // TODOS sus proyectos, no por los de una cartera—. Es la misma razón por
      // la que `/projects/{id}/resource-load` mira todos los proyectos del
      // recurso y no solo ese.
      getCapacitySummary({ window: "week", organization_id: orgFilter || undefined })
        .then((r) => !cancelled && setCapacidad(r))
        .catch(() => !cancelled && setCapacidad(null)),
      getHealthMatrix(jerarquia)
        .then((r) => !cancelled && setSemaforo(r))
        .catch(() => !cancelled && setSemaforo(null)),
    ]).finally(() => {
      if (!cancelled) setCargandoEjecutivo(false);
    });

    return () => {
      cancelled = true;
    };
  }, [analyticsScope, analyticsId, jerarquia, orgFilter, cadenciaDeReporte]);

  async function handleCapture() {
    setCapturing(true);
    setCaptureMsg(null);
    try {
      const res = await captureSnapshots();
      setCaptureMsg(`Snapshot capturado (${res.rows} filas).`);
      const refreshed = await getTrends({
        scope: analyticsScope,
        id: analyticsId,
        weeks: 12,
      });
      setTrends(refreshed);
    } catch (err) {
      setCaptureMsg(
        err instanceof ApiError ? err.message : "No se pudo capturar el snapshot",
      );
    } finally {
      setCapturing(false);
    }
  }

  // US-201 — la cascada limpia hacia abajo: cambiar de portafolio tira el
  // programa. No es cosmética — dejar el programa de otro portafolio produce una
  // consulta que cruza dos filtros que no se tocan y devuelve vacío, que se lee
  // como «no hay proyectos» y no como «el filtro no tiene sentido».
  //
  // US-205 — la organización salió de aquí: la elige el header. Lo que queda en
  // la URL son los dos niveles propios de esta vista (US-014: el filtro viaja en
  // la URL para que un tablero filtrado se pueda enviar por chat).
  function changeJerarquia(next: { portfolio?: string; program?: string }) {
    const portfolio = next.portfolio ?? portfolioFilter;
    const program =
      next.portfolio !== undefined ? "" : (next.program ?? programFilter);

    setPortfolioFilter(portfolio);
    setProgramFilter(program);

    const params = new URLSearchParams(searchParams.toString());
    for (const [clave, valor] of [
      ["portfolio_id", portfolio],
      ["program_id", program],
    ] as const) {
      if (valor) params.set(clave, valor);
      else params.delete(clave);
    }
    const qs = params.toString();
    router.replace(qs ? `/dashboard?${qs}` : "/dashboard");
  }

  /** El heatmap enlaza a una organización: cambia el contexto del header y
   *  arrastra el reset de los niveles de abajo, igual que el switcher. */
  function irAOrganizacion(id: string) {
    elegirOrg(id);
    changeJerarquia({ portfolio: "" });
  }

  // US-201 — los portafolios cuelgan de una organización, así que sin ella no
  // hay lista que pedir: el desplegable queda deshabilitado en vez de ofrecer
  // los de todas las organizaciones mezclados sin decir de quién es cada uno.
  useEffect(() => {
    let cancelled = false;
    if (!orgFilter) {
      setPortfolios([]);
      return;
    }
    listPortfolios(orgFilter, { is_active: true })
      .then((r) => {
        if (!cancelled) setPortfolios(r);
      })
      .catch(() => {
        if (!cancelled) setPortfolios([]);
      });
    return () => {
      cancelled = true;
    };
  }, [orgFilter]);

  // Los programas se piden por organización y se recortan por portafolio si hay
  // uno elegido: el endpoint acepta los dos y así el desplegable nunca ofrece un
  // programa que el filtro de arriba ya excluyó.
  useEffect(() => {
    let cancelled = false;
    if (!orgFilter) {
      setPrograms([]);
      return;
    }
    listPrograms({
      organization_id: orgFilter,
      portfolio_id: portfolioFilter || undefined,
      is_active: true,
    })
      .then((r) => {
        if (!cancelled) setPrograms(r);
      })
      .catch(() => {
        if (!cancelled) setPrograms([]);
      });
    return () => {
      cancelled = true;
    };
  }, [orgFilter, portfolioFilter]);

  // KPIs + Charts se refetchean al cambiar el filtro de organización.
  useEffect(() => {
    let cancelled = false;
    setLoadingKpis(true);
    setLoadingCharts(true);
    const filter = jerarquia;
    getDashboardKpis(filter)
      .then((r) => {
        if (!cancelled) setKpis(r);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(
            err instanceof ApiError ? err.message : "No se pudo cargar el tablero",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingKpis(false);
      });
    getDashboardCharts(filter)
      .then((r) => {
        if (!cancelled) setCharts(r);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoadingCharts(false);
      });
    return () => {
      cancelled = true;
    };
  }, [jerarquia]);

  const phasesData = useMemo(() => {
    const entries = charts ? toEntries(charts.projects_by_phase) : [];
    return entries.map(([k, v]) => ({
      label: etiquetaFase(k),
      value: Number(v) || 0,
      color: colorFase(k),
    }));
  }, [charts]);

  const progressData = useMemo(() => {
    const entries = charts ? toEntries(charts.progress_by_phase) : [];
    return entries.map(([k, v]) => ({
      label: etiquetaFase(k),
      value: Math.round(Number(v) || 0),
      color: colorFase(k),
    }));
  }, [charts]);

  const budgetData = useMemo(() => {
    const entries = charts ? toEntries(charts.budget_by_type) : [];
    return entries.map(([k, v]) => ({
      label: etiquetaTipo(k),
      value: Number(v) || 0,
      color: PALETTE.accent,
    }));
  }, [charts]);

  const healthData = useMemo(() => {
    const entries = charts ? toEntries(charts.portfolio_health) : [];
    return entries.map(([k, v]) => ({
      label: etiquetaSalud(k),
      value: Number(v) || 0,
      color: colorSalud(k),
    }));
  }, [charts]);

  // US-206 — las dos distribuciones nuevas. La clave vacía que manda la API es
  // «sin programa» / «sin sponsor», y se rotula aquí: el contrato no lleva
  // vocabulario de interfaz. El grupo es real —los proyectos que cuelgan del
  // portafolio sin coordinación (DEC-030)— y por eso se pinta en vez de
  // esconderse.
  const programData = useMemo(() => {
    const entries = charts ? toEntries(charts.projects_by_program) : [];
    return entries
      .map(([k, v]) => ({
        label: k || "Sin programa",
        value: Number(v) || 0,
        color: k ? PALETTE.accent : "var(--color-tertiary)",
      }))
      .sort((a, b) => b.value - a.value);
  }, [charts]);

  const sponsorData = useMemo(() => {
    const entries = charts ? toEntries(charts.projects_by_sponsor) : [];
    return entries
      .map(([k, v]) => ({
        label: k || "Sin sponsor",
        value: Number(v) || 0,
        color: k ? PALETTE.accent : "var(--color-tertiary)",
      }))
      .sort((a, b) => b.value - a.value);
  }, [charts]);

  // ---------------------------------------------------------------------------
  // US-206 — los pies de las seis tarjetas y las tres listas «top».
  // ---------------------------------------------------------------------------

  /** «N en preparación»: el pie que el mockup pone bajo los activos. */
  const enPreparacion = useMemo(() => {
    // `PHASE_ORDER[0]` y no `"preparacion"`: US-202 dejó el catálogo de fases
    // en un solo sitio, y un literal aquí es la copia que sobrevive a un
    // renombre. El orden del ciclo de vida empieza donde empieza un proyecto.
    const primeraFase = PHASE_ORDER[0];
    const n = charts?.projects_by_phase?.[primeraFase];
    if (!n) return undefined;
    return `${n} en ${etiquetaFase(primeraFase).toLowerCase()}`;
  }, [charts]);

  /**
   * La desviación en puntos: real − plan. `null` cuando falta cualquiera de los
   * dos, y eso NO es cero: sin plan no hay desviación que calcular, y escribir
   * «0 pts» diría que va justo (DAT-12).
   */
  const desviacionDePlan = useMemo(() => {
    if (kpis?.progress_avg == null || kpis?.plan_progress_avg == null) return null;
    return Math.round(kpis.progress_avg - kpis.plan_progress_avg);
  }, [kpis]);

  const pieDePlan = useMemo(() => {
    if (kpis?.plan_progress_avg == null) return undefined;
    const plan = `plan ${Math.round(kpis.plan_progress_avg)}%`;
    if (desviacionDePlan === null) return plan;
    const signo = desviacionDePlan > 0 ? "+" : "−";
    return `${plan} · ${signo}${Math.abs(desviacionDePlan)} pts`;
  }, [kpis, desviacionDePlan]);

  const pieDePresupuesto = useMemo(() => {
    const gastado = kpis?.budget_consumed_by_currency ?? {};
    const total = kpis?.budget_by_currency ?? {};
    const moneda = monedaUnica(total);
    // Con varias monedas no hay un consumido único, igual que no hay un total:
    // se pinta el desglose de lo presupuestado y se calla lo demás. Inventar
    // un «restante» sumando monedas distintas es el bug de BUG-092.
    if (!moneda) return formatearDesglose(total);
    const consumido = Number(gastado[moneda] ?? 0);
    const presupuestado = Number(total[moneda] ?? 0);
    if (!presupuestado && !consumido) return undefined;
    return `consumido ${formatearImporte(consumido, moneda)} · restante ${formatearImporte(presupuestado - consumido, moneda)}`;
  }, [kpis]);

  const pieDeRiesgos = useMemo(() => {
    const n = kpis?.severe_risks_unassigned ?? 0;
    if (!kpis?.severe_risks) return undefined;
    // Cero sin responsable es una buena noticia y se dice, en vez de dejar la
    // tarjeta sin pie: la ausencia de pie se lee como que el dato falta.
    return n > 0 ? `${n} sin responsable` : "todos con responsable";
  }, [kpis]);

  /**
   * Los recursos por encima de su capacidad. `over_pct` es demanda − capacidad
   * ya recortada a cero, así que «> 0» es exactamente «sobreasignado», sin
   * volver a elegir un umbral que el inquilino ya configuró.
   */
  const recursosSobrecargados = useMemo(
    () => (capacidad?.resources ?? []).filter((r) => r.over_pct > 0),
    [capacidad],
  );
  const sobreasignados = capacidad ? recursosSobrecargados.length : undefined;

  const topRiesgo = useMemo<FilaTop[]>(
    () =>
      (tops?.by_risk ?? []).map((p) => ({
        id: p.project_id,
        titulo: p.name,
        cifra: String(p.severe_risks),
        detalle: p.severe_risks === 1 ? "severo" : "severos",
        color: colorSalud(p.health),
        href: `/pmo/projects/${p.project_id}/raid`,
      })),
    [tops],
  );

  const topAtraso = useMemo<FilaTop[]>(
    () =>
      (tops?.by_delay ?? []).map((p) => ({
        id: p.project_id,
        titulo: p.name,
        // El signo menos tipográfico, no el guion: es un número negativo.
        cifra: `−${Math.abs(p.delta_pts)} pts`,
        detalle: `real ${p.progress_actual}% · plan ${p.progress_plan}%`,
        color: colorSalud(p.health),
        href: `/pmo/projects/${p.project_id}/plan`,
      })),
    [tops],
  );

  const topSobrecarga = useMemo<FilaTop[]>(
    () =>
      [...recursosSobrecargados]
        .sort((a, b) => b.over_pct - a.over_pct)
        .slice(0, 5)
        .map((r) => ({
          id: r.actor_id,
          titulo: r.discipline ? `${r.name} — ${r.discipline}` : r.name,
          cifra: `${Math.round(r.demand_pct)}%`,
          detalle: `${r.projects_count} ${r.projects_count === 1 ? "proyecto" : "proyectos"}`,
          // `CapacityColor` usa las mismas tres claves que la salud, así que
          // `colorSalud` sirve tal cual: no hay traducción que escribir.
          color: colorSalud(r.color),
          href: "/pmo/resources",
        })),
    [recursosSobrecargados],
  );

  // US-201 — el rastro de la cascada, para que la cabecera diga qué se está
  // mirando. Se nombran los dos niveles y no solo el más específico: «Programa
  // Alfa» a secas no dice de qué cartera es, y hay nombres repetidos.
  //
  // US-205 — la organización ya no entra en el rastro: la dice el header, y
  // repetirla aquí la pondría dos veces en la misma pantalla.
  const rastro = useMemo(() => {
    const partes = [
      portfolioFilter
        ? (portfolios.find((pf) => pf.id === portfolioFilter)?.name ?? "portafolio")
        : null,
      programFilter
        ? (programs.find((pg) => pg.id === programFilter)?.name ?? "programa")
        : null,
    ].filter(Boolean);
    return partes.join(" › ");
  }, [portfolioFilter, portfolios, programFilter, programs]);

  // US-207 — el enlace a la vista maestra viaja con los filtros de esta
  // pantalla. Sin ellos, quien lo sigue tiene que reponer portafolio y programa
  // a mano, y ese paso es el que hace que nadie siga el enlace dos veces.
  const rutaVistaMaestra = useMemo(() => {
    const usp = new URLSearchParams();
    if (portfolioFilter) usp.set("portfolio_id", portfolioFilter);
    if (programFilter) usp.set("program_id", programFilter);
    return usp.toString() ? `/pmo?${usp}` : "/pmo";
  }, [portfolioFilter, programFilter]);

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-[var(--color-primary)]">
            Tablero, {user?.full_name || user?.username || "usuario"}
          </h1>
          {leido && <MarcaDeDatos periodo="vivo" detalle="las tendencias vienen de la instantánea semanal (lunes)" actualizado={leido} />}
          <p className="mt-1 text-sm text-[var(--color-tertiary)]">
            KPIs, salud del portafolio y Plan vs Real.
            {rastro ? ` · Filtrando por: ${rastro}` : ""}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {/* US-205 — la organización se elige en el header. Aquí quedan los
              dos niveles propios de esta vista, y siguen deshabilitados sin
              organización: un desplegable con los portafolios de todas a la vez
              no dice de quién es cada uno, y hay clientes con un «Portafolio
              General» cada uno. */}
          <label
            htmlFor="portfolio-filter"
            className="text-xs font-medium text-[var(--color-tertiary)]"
          >
            Portafolio
          </label>
          <Select
            id="portfolio-filter"
            value={portfolioFilter}
            onChange={(e) => changeJerarquia({ portfolio: e.target.value })}
            aria-label="Filtrar por portafolio"
            className="min-w-[180px]"
            disabled={!orgFilter}
          >
            <option value="">
              {orgFilter ? "Todos los portafolios" : "Elige una organización"}
            </option>
            {/* DIS-03 — tres estados, no dos: «elige una organización» y «esta
                organización no tiene portafolios» son cosas distintas, y sin
                distinguirlas el desplegable vacío se lee como que algo falló. */}
            {orgFilter && portfolios.length === 0 ? (
              <option value="" disabled>
                (esta organización no tiene portafolios)
              </option>
            ) : null}
            {portfolios.map((pf) => (
              <option key={pf.id} value={pf.id}>
                {pf.name}
              </option>
            ))}
          </Select>
          <label
            htmlFor="program-filter"
            className="text-xs font-medium text-[var(--color-tertiary)]"
          >
            Programa
          </label>
          <Select
            id="program-filter"
            value={programFilter}
            onChange={(e) => changeJerarquia({ program: e.target.value })}
            aria-label="Filtrar por programa"
            className="min-w-[180px]"
            disabled={!orgFilter}
          >
            <option value="">
              {orgFilter ? "Todos los programas" : "Elige una organización"}
            </option>
            {/* Con portafolio elegido, la lista viene recortada a los suyos: hay
                que decir cuál de los dos vacíos es, o parece que se perdieron
                los programas de la organización. */}
            {orgFilter && programs.length === 0 ? (
              <option value="" disabled>
                {portfolioFilter
                  ? "(este portafolio no tiene programas)"
                  : "(esta organización no tiene programas)"}
              </option>
            ) : null}
            {programs.map((pg) => (
              <option key={pg.id} value={pg.id}>
                {pg.name}
              </option>
            ))}
          </Select>
          {/* «Limpiar» solo vacía lo de esta vista. La organización no se
              limpia desde aquí: se cambia en el header, que es donde vive. */}
          {portfolioFilter || programFilter ? (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => changeJerarquia({ portfolio: "" })}
            >
              Limpiar
            </Button>
          ) : null}
          {isAdminView ? (
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={handleCapture}
              disabled={capturing}
              title="Captura el snapshot de hoy para alimentar las tendencias"
            >
              {capturing ? "Capturando…" : "Capturar snapshot"}
            </Button>
          ) : null}
        </div>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}
      {captureMsg ? <Banner variant="info">{captureMsg}</Banner> : null}

      {/* US-206 · fila 1 — las seis tarjetas del mockup «Dashboard ejecutivo».
          Reemplazan a ocho que contaban ítems por módulo (solicitudes en
          revisión, riesgos abiertos, cambios, AIDs). No se perdieron: cada una
          de esas cifras vive en su pantalla del grupo Transversal, que es donde
          se actúa sobre ella. Este tablero contesta «cómo va la cartera», y
          para eso el par plan/real, lo consumido y los recursos sobreasignados
          dicen más que cuántos ítems hay abiertos en cada bandeja. */}
      <section aria-label="Indicadores" className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        <KpiCard
          label="Proyectos activos"
          value={kpis?.active_projects}
          loading={loadingKpis}
          icon={<Briefcase className="h-4 w-4" aria-hidden />}
          tone="accent"
          hint={enPreparacion}
          href="/pmo/projects?phase=preparacion&phase=ejecucion&phase=hypercare"
        />
        <TarjetaDeSalud
          conteos={charts?.portfolio_health ?? {}}
          cargando={loadingCharts}
          href="/pmo/projects"
        />
        <KpiCard
          label="Avance plan vs real"
          value={kpis?.progress_avg}
          loading={loadingKpis}
          format="percent"
          icon={<TrendingUp className="h-4 w-4" aria-hidden />}
          tone={desviacionDePlan !== null && desviacionDePlan < 0 ? "warning" : "success"}
          hint={pieDePlan}
        />
        {/* BUG-092 — con una sola moneda se pinta el importe. Con varias NO hay
            un total, así que se pinta el desglose: sumar pesos y euros para dar
            un número redondo es inventarlo. */}
        <KpiCard
          label="Presupuesto"
          value={kpis?.budget_total}
          loading={loadingKpis}
          format="currency"
          moneda={monedaUnica(kpis?.budget_by_currency ?? {}) ?? undefined}
          hint={pieDePresupuesto}
          icon={<CircleDollarSign className="h-4 w-4" aria-hidden />}
        />
        <KpiCard
          label="Riesgos severos"
          value={kpis?.severe_risks}
          loading={loadingKpis}
          icon={<AlertOctagon className="h-4 w-4" aria-hidden />}
          tone="danger"
          hint={pieDeRiesgos}
          href="/pmo/raid?kind=risks&severity_min=13"
        />
        <KpiCard
          label="Sobreasignados"
          value={sobreasignados}
          loading={cargandoEjecutivo}
          icon={<Users className="h-4 w-4" aria-hidden />}
          tone={sobreasignados ? "warning" : undefined}
          hint="recursos por encima de su capacidad"
          href="/pmo/resources"
        />
      </section>

      {/* US-206 · fila 2 — las tres listas cortas. Un agregado dice que algo
          pasa; estas dicen dónde. */}
      <section aria-label="Qué mirar primero" className="grid gap-4 lg:grid-cols-3">
        <ListaTop
          titulo="Top en riesgo"
          filas={topRiesgo}
          cargando={cargandoEjecutivo}
          vacio="Ningún proyecto acumula riesgos severos abiertos."
        />
        <ListaTop
          titulo="Top con atraso"
          filas={topAtraso}
          cargando={cargandoEjecutivo}
          vacio="Ningún proyecto con calendario va por detrás de su plan."
        />
        <ListaTop
          titulo="Top sobrecarga de recursos"
          filas={topSobrecarga}
          cargando={cargandoEjecutivo}
          vacio="Nadie está asignado por encima de su capacidad."
        />
      </section>

      {/* US-206 · fila 3 — las cuatro distribuciones del mockup. «Por salud» y
          «por fase» dicen en qué estado está la cartera; «por programa» y «por
          sponsor», quién la coordina y quién la pidió. Las dos últimas son
          nuevas: son las preguntas que un comité hace y que las otras dos no
          contestan. */}
      <section aria-label="Distribuciones" className="grid gap-4 lg:grid-cols-2 xl:grid-cols-4">
        <ChartCard title="Por salud" loading={loadingCharts}>
          <div className="flex items-center gap-4">
            <Pie data={healthData} ariaLabel="Proyectos por salud" />
            <div className="flex-1">
              <Legend data={healthData} />
            </div>
          </div>
        </ChartCard>
        <ChartCard title="Por fase" loading={loadingCharts}>
          <Bars data={phasesData} ariaLabel="Proyectos por fase" />
        </ChartCard>
        <ChartCard title="Por programa" loading={loadingCharts}>
          <Bars data={programData} ariaLabel="Proyectos por programa" />
        </ChartCard>
        <ChartCard title="Por sponsor" loading={loadingCharts}>
          <Bars data={sponsorData} ariaLabel="Proyectos por sponsor" />
        </ChartCard>
      </section>

      {/* Lo que el mockup no pinta pero sí existe: avance por fase, presupuesto
          por tipo y la matriz de riesgos. No entran en las cuatro filas porque
          no son la lectura ejecutiva, y borrarlas sería perder capacidad que
          alguien usa. Van debajo, que es su altura. */}
      <section aria-label="Detalle de la cartera" className="grid gap-4 lg:grid-cols-3">
        <ChartCard title="Avance promedio por fase" loading={loadingCharts}>
          <Bars
            data={progressData}
            ariaLabel="Avance promedio por fase"
            valueFormat={(n) => `${n}%`}
          />
        </ChartCard>
        <ChartCard title="Presupuesto por tipo" loading={loadingCharts}>
          <Bars
            data={budgetData}
            ariaLabel="Presupuesto por tipo"
            valueFormat={(n) => formatearImporte(n, monedaDeCartera)}
          />
        </ChartCard>
        <ChartCard title="Matriz de riesgos (probabilidad × impacto)">
          {riskMatrix && riskMatrix.total > 0 ? (
            <RiskMatrix cells={riskMatrix.cells} ariaLabel="Matriz de riesgos" />
          ) : (
            <p className="py-6 text-center text-sm text-[var(--color-tertiary)]">
              Sin riesgos abiertos con probabilidad e impacto definidos.
            </p>
          )}
        </ChartCard>
      </section>

      {/* US-206 · fila 4 — tendencias y el semáforo consolidado.
          El mockup pide la tendencia **bi-semanal**; hoy las instantáneas son
          semanales y por eso el rótulo dice semanas. La cadencia se cambia en
          US-213 y este gráfico no se toca: lee lo que haya. */}
      <section aria-label="Tendencia y semáforo" className="grid gap-4 lg:grid-cols-2">
        <ChartCard title="Semáforo consolidado">
          <SemaforoConsolidado
            filas={semaforo?.rows ?? []}
            cargando={cargandoEjecutivo}
            corte={
              leido
                ? `Corte de hoy · ${leido} · el color de cada dimensión es el peor que aparece en la cartera`
                : undefined
            }
          />
        </ChartCard>
        {isAdminView ? (
          <ChartCard title="Salud por organización">
            <Heatmap
              rows={heatmap?.rows ?? []}
              ariaLabel="Mapa de calor de salud por organización"
              onCellClick={(orgId) => irAOrganizacion(orgId)}
            />
          </ChartCard>
        ) : null}
      </section>

      {isAdminView ? (
        <section aria-label="Tendencias y portafolio" className="grid gap-4 lg:grid-cols-2">
          <ChartCard
            title={`Tendencias — corte ${etiquetaDeCadencia(cadenciaDeReporte)} (12 semanas)`}
          >
            {(trends?.series.length ?? 0) > 0 ? (
              <div className="grid gap-4 sm:grid-cols-3">
                <TrendMini
                  label="Avance promedio"
                  trends={trends}
                  metric="avg_progress"
                  color="var(--color-success-fg)"
                  valueFormat={(n) => `${Math.round(n)}%`}
                />
                <TrendMini
                  label="Riesgos abiertos"
                  trends={trends}
                  metric="open_risks"
                  color="var(--color-warning-fg)"
                />
                <TrendMini
                  label="Proyectos activos"
                  trends={trends}
                  metric="projects_active"
                  color={PALETTE.accent}
                />
              </div>
            ) : (
              <p className="py-6 text-center text-sm text-[var(--color-tertiary)]">
                Aún no hay historia. Usa “Capturar snapshot” para sembrar el primer
                punto; el job semanal llena el resto: se
                captura cada semana y se muestra por corte, así que bajar la
                cadencia de reporte no borra historia.
              </p>
            )}
          </ChartCard>
          <ChartCard title="Portafolio (presupuesto × salud)">
            <Treemap tree={treemap?.tree ?? []} ariaLabel="Treemap del portafolio" moneda={monedaDeCartera} />
          </ChartCard>
        </section>
      ) : null}

      {/* US-213 — el historial de cortes. Es la misma serie muestreada que el
          gráfico de arriba, en tabla: un gráfico contesta «¿va subiendo?» y una
          tabla contesta «¿cuánto era exactamente al corte del 4 de agosto?»,
          que es la pregunta cuando alguien discute un número en comité. */}
      {isAdminView && (trends?.series.length ?? 0) > 0 ? (
        <section
          aria-label="Historial de cortes"
          className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]"
        >
          <header className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border-default)] p-4">
            <h2 className="text-base font-semibold text-[var(--color-primary)]">
              Historial de cortes
            </h2>
            <p className="text-xs text-[var(--color-tertiary)]">
              Un corte {etiquetaDeCadencia(cadenciaDeReporte)} · el valor al
              cerrar el periodo, no el promedio
            </p>
          </header>
          <div className="overflow-x-auto">
            <table className="w-full min-w-max text-[13px]">
              <thead>
                <tr className="border-b border-[var(--border-default)] text-left text-[11px] uppercase tracking-wide text-[var(--color-tertiary)]">
                  <th className="px-4 py-2 font-medium">Corte</th>
                  <th className="px-4 py-2 text-right font-medium">Avance</th>
                  <th className="px-4 py-2 text-right font-medium">Activos</th>
                  <th className="px-4 py-2 text-right font-medium">Riesgos abiertos</th>
                  <th className="px-4 py-2 text-right font-medium">Δ avance</th>
                </tr>
              </thead>
              <tbody>
                {/* Del más reciente al más viejo: la pregunta empieza por el
                    último corte, no por el de hace tres meses. */}
                {[...(trends?.series ?? [])].reverse().map((punto, i, filas) => {
                  const anterior = filas[i + 1];
                  const avance = Number(punto.avg_progress ?? 0);
                  const delta =
                    anterior === undefined
                      ? null
                      : Math.round(avance - Number(anterior.avg_progress ?? 0));
                  return (
                    <tr
                      key={punto.snapshot_date}
                      className="border-b border-[var(--border-subtle)]"
                    >
                      <td className="px-4 py-2 tabular-nums">
                        {punto.snapshot_date}
                      </td>
                      <td className="px-4 py-2 text-right tabular-nums">
                        {Math.round(avance)}%
                      </td>
                      <td className="px-4 py-2 text-right tabular-nums">
                        {Math.round(Number(punto.projects_active ?? 0))}
                      </td>
                      <td className="px-4 py-2 text-right tabular-nums">
                        {Math.round(Number(punto.open_risks ?? 0))}
                      </td>
                      <td className="px-4 py-2 text-right tabular-nums">
                        {/* El corte más viejo no tiene delta: es «—» y no
                            «0», que se leería como «no se movió». */}
                        {delta === null ? (
                          <span className="text-[var(--color-tertiary)]">—</span>
                        ) : (
                          <span
                            style={{
                              color:
                                delta > 0
                                  ? "var(--color-success-fg)"
                                  : delta < 0
                                    ? "var(--color-danger-fg)"
                                    : "var(--color-tertiary)",
                            }}
                          >
                            {delta > 0 ? "+" : delta < 0 ? "−" : ""}
                            {Math.abs(delta)}
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {/* US-207 — la tabla «Plan vs Real» que vivía aquí es la vista maestra.
          Eran las mismas filas con seis columnas en vez de dieciséis, sin
          columnas configurables ni export, y con el orden roto en la mitad de
          sus cabeceras (los getters citaban campos que el contrato no tiene:
          `project_name`, `end_plan`). Se enlaza en vez de duplicarse: dos
          tablas de los mismos proyectos es cómo se llega a que digan cosas
          distintas. */}
      <section
        aria-label="Vista maestra"
        className="flex flex-wrap items-center justify-between gap-3 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-sm)]"
      >
        <div className="min-w-0">
          <h2 className="text-base font-semibold text-[var(--color-primary)]">
            Proyecto por proyecto
          </h2>
          <p className="mt-1 text-sm text-[var(--color-tertiary)]">
            Plan vs real, riesgos, presupuesto y fechas de cada proyecto, con
            columnas configurables y export a XLSX.
          </p>
        </div>
        <Link href={rutaVistaMaestra}>
          <Button type="button" variant="secondary" size="sm">
            <BarChart3 className="mr-1 h-3.5 w-3.5" aria-hidden />
            Abrir la vista maestra
          </Button>
        </Link>
      </section>
    </div>
  );
}

function TrendMini({
  label,
  trends,
  metric,
  color,
  valueFormat,
}: {
  label: string;
  trends: TrendsResponse | null;
  metric: string;
  color: string;
  valueFormat?: (n: number) => string;
}) {
  const data = (trends?.series ?? []).map((p) => ({
    x: p.snapshot_date,
    y: Number(p[metric] ?? 0),
  }));
  const last = data.length ? data[data.length - 1].y : 0;
  const prev = data.length > 1 ? data[data.length - 2].y : last;
  const delta = last - prev;
  return (
    <div className="space-y-1">
      <div className="flex items-baseline justify-between">
        <span className="text-xs font-medium uppercase tracking-wide text-[var(--color-tertiary)]">
          {label}
        </span>
        <span className="text-sm font-semibold tabular-nums text-[var(--color-primary)]">
          {valueFormat ? valueFormat(last) : last}
        </span>
      </div>
      <TrendLines data={data} ariaLabel={`Tendencia de ${label}`} color={color} valueFormat={valueFormat} />
      <p className="text-[11px] tabular-nums text-[var(--color-tertiary)]">
        {delta === 0 ? "Sin cambio" : `${delta > 0 ? "▲" : "▼"} ${valueFormat ? valueFormat(Math.abs(delta)) : Math.abs(delta)} vs. semana previa`}
      </p>
    </div>
  );
}

function ChartCard({
  title,
  children,
  loading,
}: {
  title: string;
  children: React.ReactNode;
  loading?: boolean;
}) {
  return (
    <article className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-sm)]">
      <h2 className="mb-3 text-sm font-semibold text-[var(--color-primary)]">{title}</h2>
      {loading ? <Skeleton className="h-[180px] w-full" /> : children}
    </article>
  );
}

function ProgressBar({ value, tone }: { value: number; tone?: "accent" }) {
  const pct = Math.max(0, Math.min(100, Math.round(value)));
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-[var(--color-muted)]">
        <div
          className={cn(
            "h-full rounded-full transition-[width]",
            tone === "accent" ? "bg-[var(--color-accent)]" : "bg-[var(--color-secondary)]",
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-10 text-right text-xs tabular-nums text-[var(--color-secondary)]">
        {pct}%
      </span>
    </div>
  );
}

function HealthDot({ health }: { health: string | null }) {
  // ENH-110: semáforo de salud = solo el color (círculo), sin la palabra.
  // El estado se preserva en title/aria-label para accesibilidad.
  if (!health) return <span className="text-xs text-[var(--color-tertiary)]">—</span>;
  const dotColor =
    health === "green"
      ? "bg-[var(--color-success-fg)]"
      : health === "yellow"
        ? "bg-[var(--color-warning-fg)]"
        : health === "red"
          ? "bg-[var(--color-danger-fg)]"
          : "bg-[var(--color-tertiary)]";
  const label = etiquetaSalud(health);
  return (
    <span
      title={label}
      aria-label={label}
      role="img"
      className={cn("inline-block h-2.5 w-2.5 rounded-full", dotColor)}
    />
  );
}
