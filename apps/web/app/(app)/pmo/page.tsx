"use client";

/**
 * US-207 — Portafolio: la vista maestra (control tower).
 *
 * Artboard «Portafolio — Vista maestra» de los mockups aprobados.
 *
 * ## Qué era esta pantalla y por qué cambió
 *
 * Era una rejilla de tarjetas de organización («selecciona una para ver sus
 * programas») más cuatro paneles de analítica: heatmap de salud, treemap de
 * presupuesto, tendencias del inquilino y la matriz salud × dimensión.
 *
 * Los tres primeros se fueron al tablero ejecutivo con US-206, donde son la
 * lectura de la cartera. Aquí quedaban duplicados, y dos pantallas dibujando el
 * mismo treemap es cómo se llega a que digan números distintos.
 *
 * Las tarjetas de organización se van porque su trabajo era navegar, y navegar
 * ya no se hace aquí: la organización se elige en el header (US-205) y el
 * drill-down por portafolio y programa está en los filtros de esta tabla, donde
 * se combina con la fase y la salud.
 *
 * Lo que queda es lo que esta pantalla contesta y ninguna otra: **«¿qué pasa con
 * ESTE proyecto?» para veintitrés proyectos a la vez**, que es la pregunta de la
 * reunión de seguimiento.
 *
 * ## Lo que se conservó a propósito
 *
 * El status PMO en PDF y el reporte de salud en XLSX son entregables que alguien
 * manda por correo, y la matriz salud × dimensión con su evaluación 5+1 (US-192)
 * es la única superficie donde se declara salud sin abrir cada proyecto. Van
 * debajo de la tabla, que es su altura.
 */
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Icono } from "@/components/ui/icono";
import { Select } from "@/components/ui/select";
import { BoardDePortafolio } from "@/components/board-de-portafolio";
import { HealthDimensionMatrix } from "@/components/health-panel";
import { HealthEvaluationModal } from "@/components/health-evaluation-modal";
import { Importador } from "@/components/importador";
import { ProgramModal } from "@/components/program-modal";
import { RoadmapTrimestral } from "@/components/roadmap-trimestral";
import { VistaMaestra } from "@/components/vista-maestra";
import { MarcaDeDatos, useLectura } from "@/components/ui/marca-de-datos";
import { useOrganizacionActiva } from "@/components/organizacion-activa";
import { useMyPermissions } from "@/hooks/use-my-permissions";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/cn";
import { aplicarFuente, XLSX_FONT } from "@/lib/plan-template";
import {
  downloadPmoStatusReport,
  getHealthMatrix,
  type HealthMatrixResponse,
} from "@/lib/api/analytics";
import { getPlanVsActual, type PlanVsActualRow } from "@/lib/api/dashboard";
import {
  listPortfolios,
  listPrograms,
  type Portfolio,
  type Program,
} from "@/lib/api/organizations";
import {
  HEALTH_LABEL,
  PHASE_LABEL,
  PHASE_ORDER,
  listProjects,
  updateProject,
  type Project,
  type ProjectHealth,
} from "@/lib/api/projects";

/** La ruta agrega organizaciones, así que la columna que las distingue importa. */
const COLUMNA_ORG = ["organization"] as const;
// FASE-4 (revamp v2, US-B) — portafolio y programa siempre visibles: es el
// orden fijo de la lista, no algo que el usuario deba encender.
const COLUMNAS_JERARQUIA = ["portfolio", "program"] as const;

export default function PortafolioVistaMaestra() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { efectiva: orgFilter, agrega } = useOrganizacionActiva();
  const { canCreate, canUpdate, loading: permsLoading } = useMyPermissions();

  // US-201 — los filtros viven en la URL: una vista maestra filtrada que no se
  // puede enviar por chat obliga al otro a reproducir los clics, y ahí es donde
  // se acaban mirando números distintos.
  const [portfolioFilter, setPortfolioFilter] = useState(
    searchParams.get("portfolio_id") ?? "",
  );
  const [programFilter, setProgramFilter] = useState(
    searchParams.get("program_id") ?? "",
  );
  const [phaseFilter, setPhaseFilter] = useState(searchParams.get("phase") ?? "");
  const [healthFilter, setHealthFilter] = useState(searchParams.get("health") ?? "");

  // FASE-4 (revamp v2, US-C) — Board e Importar viven aquí como pestañas.
  const tab = (searchParams.get("tab") ?? "portafolio") as
    | "portafolio"
    | "board"
    | "importar";

  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [programs, setPrograms] = useState<Program[]>([]);

  const [filas, setFilas] = useState<PlanVsActualRow[]>([]);
  const leido = useLectura(filas);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [proyectosRoadmap, setProyectosRoadmap] = useState<Project[]>([]);
  // FASE-4 (revamp v2) — año del roadmap trimestral. Piso 2026 (owner: "todo
  // a partir del 26 hacia adelante"), sin techo.
  const [anioRoadmap, setAnioRoadmap] = useState(() => Math.max(2026, new Date().getFullYear()));
  const [healthMatrix, setHealthMatrix] = useState<HealthMatrixResponse | null>(null);
  const [evalTarget, setEvalTarget] = useState<{ id: string; name: string } | null>(null);
  const [healthReportBusy, setHealthReportBusy] = useState(false);
  const [reportError, setReportError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [showProgramModal, setShowProgramModal] = useState(false);
  // Detección por capacidad: los entregables agregados son admin-equivalente.
  // Si la matriz 403ea, la sección no se pinta en vez de mostrar un error que
  // la persona no puede resolver.
  const [esVistaAdmin, setEsVistaAdmin] = useState(false);

  const jerarquia = useMemo(
    () => ({
      organization_id: orgFilter || undefined,
      portfolio_id: portfolioFilter || undefined,
      program_id: programFilter || undefined,
    }),
    [orgFilter, portfolioFilter, programFilter],
  );

  /** Escribe los filtros en la URL sin recargar. Cada nivel limpia los de abajo. */
  const cambiarFiltro = useCallback(
    (cambio: { portfolio?: string; program?: string; phase?: string; health?: string }) => {
      const usp = new URLSearchParams(searchParams.toString());
      const set = (clave: string, valor: string) => {
        if (valor) usp.set(clave, valor);
        else usp.delete(clave);
      };
      if (cambio.portfolio !== undefined) {
        setPortfolioFilter(cambio.portfolio);
        set("portfolio_id", cambio.portfolio);
        // Cambiar de portafolio invalida el programa: uno de otra cartera
        // devolvería vacío y se leería como «no hay proyectos».
        setProgramFilter("");
        usp.delete("program_id");
      }
      if (cambio.program !== undefined) {
        setProgramFilter(cambio.program);
        set("program_id", cambio.program);
      }
      if (cambio.phase !== undefined) {
        setPhaseFilter(cambio.phase);
        set("phase", cambio.phase);
      }
      if (cambio.health !== undefined) {
        setHealthFilter(cambio.health);
        set("health", cambio.health);
      }
      router.replace(usp.toString() ? `/pmo?${usp}` : "/pmo", { scroll: false });
    },
    [router, searchParams],
  );

  const cambiarTab = useCallback(
    (siguiente: "portafolio" | "board" | "importar") => {
      const usp = new URLSearchParams(searchParams.toString());
      if (siguiente === "portafolio") usp.delete("tab");
      else usp.set("tab", siguiente);
      router.replace(usp.toString() ? `/pmo?${usp}` : "/pmo", { scroll: false });
    },
    [router, searchParams],
  );

  // Los portafolios de la organización activa; los programas, recortados al
  // portafolio elegido si hay uno.
  useEffect(() => {
    if (!orgFilter) {
      setPortfolios([]);
      setPrograms([]);
      return;
    }
    let cancelado = false;
    void Promise.allSettled([
      listPortfolios(orgFilter, { is_active: true }).then(
        (r) => !cancelado && setPortfolios(r),
      ),
      listPrograms({
        organization_id: orgFilter,
        portfolio_id: portfolioFilter || undefined,
        is_active: true,
      }).then((r) => !cancelado && setPrograms(r)),
    ]);
    return () => {
      cancelado = true;
    };
  }, [orgFilter, portfolioFilter]);

  const cargarFilas = useCallback(() => {
    setCargando(true);
    setError(null);
    return getPlanVsActual({ ...jerarquia, phase: phaseFilter || undefined })
      .then((r) => setFilas(r))
      .catch((e) => {
        setFilas([]);
        setError(
          e instanceof ApiError
            ? e.message
            : "No se pudo cargar la vista maestra. Reintenta en un momento.",
        );
      })
      .finally(() => setCargando(false));
  }, [jerarquia, phaseFilter]);

  useEffect(() => {
    void cargarFilas();
  }, [cargarFilas]);

  // US-247 — el roadmap trimestral necesita start_date/end_date, que
  // plan-vs-actual no expone (esa vista es de avance, no de calendario).
  useEffect(() => {
    if (!orgFilter) {
      setProyectosRoadmap([]);
      return;
    }
    let cancelado = false;
    listProjects({
      ...jerarquia,
      phase: phaseFilter ? (phaseFilter as import("@/lib/api/projects").ProjectPhase) : undefined,
      health: healthFilter ? [healthFilter as ProjectHealth] : undefined,
      limit: 200,
    })
      .then((r) => !cancelado && setProyectosRoadmap(r))
      .catch(() => !cancelado && setProyectosRoadmap([]));
    return () => {
      cancelado = true;
    };
  }, [jerarquia, phaseFilter, healthFilter, orgFilter]);

  useEffect(() => {
    let cancelado = false;
    getHealthMatrix(jerarquia)
      .then((r) => {
        if (cancelado) return;
        setHealthMatrix(r);
        setEsVistaAdmin(true);
      })
      .catch(() => {
        if (cancelado) return;
        setHealthMatrix(null);
        setEsVistaAdmin(false);
      });
    return () => {
      cancelado = true;
    };
  }, [jerarquia]);

  // La salud se filtra en el cliente y no en el servidor a propósito: el
  // endpoint no tiene el parámetro, la tabla ya está entera en memoria, y una
  // ida al servidor por cambiar un desplegable de tres opciones se nota.
  const visibles = useMemo(() => {
    const base = healthFilter ? filas.filter((f) => f.health === healthFilter) : filas;
    // FASE-4 (revamp v2, US-B) — orden fijo portafolio → programa → nombre;
    // "￿" manda los "sin portafolio"/"sin programa" al final.
    return [...base].sort(
      (a, b) =>
        (a.portfolio_name ?? "￿").localeCompare(b.portfolio_name ?? "￿", "es") ||
        (a.program_name ?? "￿").localeCompare(b.program_name ?? "￿", "es") ||
        a.name.localeCompare(b.name, "es"),
    );
  }, [filas, healthFilter]);

  const puedeEditar = !permsLoading && canUpdate("projects");

  /** Edición inline: actualiza y recarga. El mockup la pide en salud y prioridad. */
  const guardar = useCallback(
    async (projectId: string, cuerpo: Parameters<typeof updateProject>[1]) => {
      try {
        await updateProject(projectId, cuerpo);
        await cargarFilas();
        // La matriz de abajo también cambia: declarar salud es justo lo que
        // mueve su fila, y dejarla vieja hace que la pantalla se contradiga.
        getHealthMatrix(jerarquia)
          .then((r) => setHealthMatrix(r))
          .catch(() => {});
      } catch (e) {
        setError(
          e instanceof ApiError
            ? e.message
            : "No se pudo guardar el cambio. Reintenta.",
        );
      }
    },
    [cargarFilas, jerarquia],
  );

  async function handleDownloadReport() {
    if (downloading) return;
    setDownloading(true);
    setReportError(null);
    try {
      await downloadPmoStatusReport();
    } catch {
      setReportError("No se pudo generar el status PMO. Reintenta en un momento.");
    } finally {
      setDownloading(false);
    }
  }

  async function downloadHealthReport() {
    if (healthReportBusy || !healthMatrix) return;
    setHealthReportBusy(true);
    setReportError(null);
    try {
      const [{ getPortfolioHealthEvaluations }, ExcelJS] = await Promise.all([
        import("@/lib/api/analytics"),
        import("exceljs").then((m) => m.default),
      ]);
      const evals = await getPortfolioHealthEvaluations().catch(() => ({ rows: [] }));
      const nameById = new Map(
        healthMatrix.rows.map((r) => [r.project_id, `${r.folio} · ${r.name}`]),
      );
      const wb = new ExcelJS.Workbook();
      wb.creator = "PMO aaS";
      const RAG = (v: string | null | undefined) =>
        v === "green" ? "Verde" : v === "yellow" ? "Amarillo" : v === "red" ? "Rojo" : "—";
      const ws = wb.addWorksheet("Salud del portafolio");
      ws.columns = [
        { header: "Proyecto", key: "p", width: 44 },
        { header: "Organización", key: "o", width: 22 },
        { header: "Salud", key: "h", width: 10 },
        { header: "Fuente", key: "src", width: 12 },
        { header: "Cronograma", key: "schedule", width: 12 },
        { header: "Presupuesto", key: "budget", width: 12 },
        { header: "Riesgos", key: "risks", width: 12 },
        { header: "Decisiones", key: "decisions", width: 12 },
        { header: "Recursos", key: "resources", width: 12 },
      ];
      ws.getRow(1).font = { name: XLSX_FONT, bold: true };
      for (const r of healthMatrix.rows) {
        ws.addRow({
          p: `${r.folio} · ${r.name}`,
          o: r.organization_name ?? "",
          h: RAG(r.health_status),
          src: r.health_source === "manual" ? "PM" : "Auto",
          schedule: RAG(r.dims["schedule"]),
          budget: RAG(r.dims["budget"]),
          risks: RAG(r.dims["risks"]),
          decisions: RAG(r.dims["decisions"]),
          resources: RAG(r.dims["resources"]),
        });
      }
      const wh = wb.addWorksheet("Historial de evaluaciones");
      wh.columns = [
        { header: "Proyecto", key: "p", width: 44 },
        { header: "Fecha", key: "d", width: 12 },
        { header: "Global", key: "g", width: 10 },
        { header: "Cronograma", key: "schedule", width: 12 },
        { header: "Presupuesto", key: "budget", width: 12 },
        { header: "Riesgos", key: "risks", width: 12 },
        { header: "Decisiones", key: "decisions", width: 12 },
        { header: "Recursos", key: "resources", width: 12 },
        { header: "Nota", key: "n", width: 60 },
      ];
      wh.getRow(1).font = { name: XLSX_FONT, bold: true };
      for (const e of evals.rows) {
        wh.addRow({
          p: nameById.get(e.project_id) ?? e.project_id,
          d: e.evaluated_at,
          g: RAG(e.overall),
          schedule: RAG(e.schedule),
          budget: RAG(e.budget),
          risks: RAG(e.risks),
          decisions: RAG(e.decisions),
          resources: RAG(e.resources),
          n: e.note ?? "",
        });
      }
      // ENH-202: las filas de datos no llevan `font` propia y saldrían en
      // Calibri; el barrido las deja en Helvetica como las cabeceras.
      aplicarFuente(ws);
      aplicarFuente(wh);
      const buf = await wb.xlsx.writeBuffer();
      const url = URL.createObjectURL(
        new Blob([buf], {
          type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }),
      );
      const a = document.createElement("a");
      a.href = url;
      a.download = "reporte-salud-portafolio.xlsx";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {
      setReportError("No se pudo generar el reporte de salud. Reintenta.");
    } finally {
      setHealthReportBusy(false);
    }
  }

  const hayFiltro = Boolean(portfolioFilter || programFilter || phaseFilter || healthFilter);

  return (
    <div className="space-y-5 p-4">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
            Portafolio — vista maestra
          </h1>
          {leido && <MarcaDeDatos periodo="vivo" actualizado={leido} />}
          <p className="mt-1 text-[13px] text-[var(--text-tertiary)]">
            Una fila por proyecto, con el estado que se revisa en seguimiento. La
            gestión (alta, edición, archivado) vive en{" "}
            <Link
              href="/admin/organizations"
              className="text-[var(--color-accent)] hover:underline"
            >
              Admin → Organizaciones
            </Link>
            .
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {esVistaAdmin ? (
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={handleDownloadReport}
              loading={downloading}
            >
              <Icono nombre="download" size={14} />
              Status PMO (PDF)
            </Button>
          ) : null}
          {canCreate("programs") ? (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowProgramModal(true)}
              disabled={permsLoading}
            >
              <Icono nombre="plus" size={14} />
              Nuevo programa
            </Button>
          ) : null}
          {canCreate("projects") ? (
            <Link href="/pmo/projects/new">
              <Button variant="primary" size="sm">
                <Icono nombre="plus" size={14} />
                Nuevo proyecto
              </Button>
            </Link>
          ) : null}
        </div>
      </header>

      {/* FASE-4 (revamp v2, US-C) — Board e Importar como pestañas de /pmo,
          patrón de `project-tabs-bar.tsx` (mismas clases de activo). */}
      <div
        role="tablist"
        aria-label="Secciones de PMO"
        className="flex flex-wrap items-center gap-5 border-b border-[var(--border-default)] shadow-[var(--linea-surco)]"
      >
        {(
          [
            { v: "portafolio", label: "Portafolio" },
            { v: "board", label: "Board" },
            { v: "importar", label: "Importar proyectos" },
          ] as const
        ).map((t) => {
          const activo = tab === t.v;
          return (
            <button
              key={t.v}
              type="button"
              role="tab"
              aria-selected={activo}
              onClick={() => cambiarTab(t.v)}
              className={cn(
                "-mb-px flex h-9 items-center gap-1.5 border-b-2 text-[13px] transition-colors",
                activo
                  ? "border-[var(--color-accent)] font-semibold text-[var(--text-primary)]"
                  : "border-transparent text-[var(--text-tertiary)] hover:text-[var(--text-primary)]",
              )}
            >
              {t.label}
            </button>
          );
        })}
      </div>

      <ProgramModal
        open={showProgramModal}
        onClose={() => setShowProgramModal(false)}
        onSaved={() => {
          setShowProgramModal(false);
          void cargarFilas();
        }}
      />

      {error ? <Banner variant="danger">{error}</Banner> : null}
      {reportError ? <Banner variant="danger">{reportError}</Banner> : null}

      {tab === "board" ? <BoardDePortafolio /> : null}
      {tab === "importar" ? <Importador kind="projects" /> : null}

      {tab === "portafolio" ? (
        <>
      {/* Los cuatro filtros del mockup. La organización no está: se elige en el
          header (US-205) y aquí sería el mismo control dos veces. */}
      <section
        aria-label="Filtros"
        className="flex flex-wrap items-center gap-2 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-3 shadow-[var(--relieve-isla)]"
      >
        <Select
          aria-label="Filtrar por portafolio"
          value={portfolioFilter}
          onChange={(e) => cambiarFiltro({ portfolio: e.target.value })}
          className="h-9 min-w-[170px]"
          disabled={!orgFilter}
        >
          <option value="">
            {orgFilter ? "Todos los portafolios" : "Elige una organización"}
          </option>
          {/* DIS-03 — «elige una organización» y «esta organización no tiene
              portafolios» son cosas distintas, y sin distinguirlas el
              desplegable vacío se lee como que algo falló al cargar. */}
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
        <Select
          aria-label="Filtrar por programa"
          value={programFilter}
          onChange={(e) => cambiarFiltro({ program: e.target.value })}
          className="h-9 min-w-[170px]"
          disabled={!orgFilter}
        >
          <option value="">
            {orgFilter ? "Todos los programas" : "Elige una organización"}
          </option>
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
        <Select
          aria-label="Filtrar por fase"
          value={phaseFilter}
          onChange={(e) => cambiarFiltro({ phase: e.target.value })}
          className="h-9"
        >
          <option value="">Todas las fases</option>
          {PHASE_ORDER.map((k) => (
            <option key={k} value={k}>
              {PHASE_LABEL[k]}
            </option>
          ))}
        </Select>
        <Select
          aria-label="Filtrar por salud"
          value={healthFilter}
          onChange={(e) => cambiarFiltro({ health: e.target.value })}
          className="h-9"
        >
          <option value="">Todas las saludes</option>
          {(Object.keys(HEALTH_LABEL) as ProjectHealth[]).map((k) => (
            <option key={k} value={k}>
              {HEALTH_LABEL[k]}
            </option>
          ))}
        </Select>
        {hayFiltro ? (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() =>
              cambiarFiltro({ portfolio: "", program: "", phase: "", health: "" })
            }
          >
            Limpiar
          </Button>
        ) : null}
      </section>

      {orgFilter ? (
        <section
          aria-label="Roadmap trimestral"
          className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--relieve-isla)]"
        >
          <RoadmapTrimestral
            proyectos={proyectosRoadmap}
            portafolios={portfolios}
            year={anioRoadmap}
            onYearChange={setAnioRoadmap}
          />
        </section>
      ) : null}

      <VistaMaestra
        filas={visibles}
        cargando={cargando}
        puedeEditar={puedeEditar}
        // La columna de organización solo distingue algo cuando el header
        // agrega; con una elegida repetiría el mismo valor en cada fila.
        siempreVisibles={agrega ? [...COLUMNAS_JERARQUIA, ...COLUMNA_ORG] : COLUMNAS_JERARQUIA}
        onSalud={(id, salud) => void guardar(id, { health_status: salud })}
        onPrioridad={(id, prioridad) => void guardar(id, { priority: prioridad })}
        onDesglose={(id, nombre) => setEvalTarget({ id, name: nombre })}
      />

      {esVistaAdmin ? (
        <section
          aria-label="Salud por dimensión"
          className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--relieve-isla)]"
        >
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-sm font-semibold text-[var(--text-primary)]">
              Salud por dimensión (proyectos activos)
            </h2>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={downloadHealthReport}
              disabled={!healthMatrix}
              loading={healthReportBusy}
            >
              <Icono nombre="download" size={14} />
              Reporte de salud (XLSX)
            </Button>
          </div>
          <HealthDimensionMatrix
            rows={healthMatrix?.rows ?? []}
            onRowClick={(pid) => router.push(`/pmo/projects/${pid}`)}
            onEvaluate={(pid, name) => setEvalTarget({ id: pid, name })}
          />
        </section>
      ) : null}

      {evalTarget ? (
        <HealthEvaluationModal
          projectId={evalTarget.id}
          projectName={evalTarget.name}
          open
          onClose={() => setEvalTarget(null)}
          onSaved={() => {
            void cargarFilas();
            getHealthMatrix(jerarquia)
              .then((r) => setHealthMatrix(r))
              .catch(() => {});
          }}
        />
      ) : null}
        </>
      ) : null}
    </div>
  );
}
