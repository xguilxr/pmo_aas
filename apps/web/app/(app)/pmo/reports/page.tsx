"use client";

/**
 * ENH-120 — Rediseño tenant-wide de Reportes.
 *
 * Tabs: PMO | Organizaciones | Programas | Proyectos.
 * - PMO (US-144): cascarón con generación + historial.
 * - Organizaciones (US-145): cascarón + filtro org.
 * - Programas (US-146): cascarón + filtros org+programa.
 * - Proyectos (ENH-120): listado actual + 4 fixes (folio, tipo, período,
 *   filtra drafts, link al detail, label "Builder").
 */
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import {
  TenantCrossFilters,
  type TenantCrossFilterValue,
} from "@/components/tenant-cross-filters";
import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Icono } from "@/components/ui/icono";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/cn";
import { downloadPortfolioStatusReport } from "@/lib/api/analytics";
import {
  listPortfolios,
  listPrograms,
  type Portfolio,
  type Program,
} from "@/lib/api/organizations";
import {
  useOrgFiltro,
  useOrganizacionActiva,
} from "@/components/organizacion-activa";
import {
  exportBuilderPdf,
  listBuilderTemplates,
  type ReportBuilderTemplate,
} from "@/lib/api/report-builder";
import { listTenantReports, type TenantReport } from "@/lib/api/tenant-cross";

type TenantReportsTab =
  | "pmo"
  | "organization"
  // US-209 — el nivel que ADR-037 metió entre la organización y el programa.
  | "portfolio"
  | "program"
  | "projects";

const TABS: Array<{ v: TenantReportsTab; label: string; icono: string }> = [
  { v: "pmo", label: "PMO", icono: "layout-dashboard" },
  { v: "organization", label: "Organizaciones", icono: "building" },
  { v: "portfolio", label: "Portafolios", icono: "folders" },
  { v: "program", label: "Programas", icono: "route" },
  { v: "projects", label: "Proyectos", icono: "file-text" },
];

export default function TenantReportsPage() {
  const search = useSearchParams();
  const tabParam = search?.get("tab") as TenantReportsTab | null;
  const activeTab: TenantReportsTab = useMemo(
    () => (TABS.find((t) => t.v === tabParam) ? (tabParam as TenantReportsTab) : "pmo"),
    [tabParam],
  );

  return (
    <div className="space-y-5">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
          Reportes
        </h1>
        <p className="text-[13px] text-[var(--text-tertiary)]">
          Reportes a nivel PMO, organización, portafolio, programa y proyecto —
          los cinco niveles de la jerarquía.
        </p>
      </header>

      {/* Bandeja con pestañas de nivel — filete inferior 2px en la activa,
          mismo patrón que /pmo/requests y el RAID de proyecto. */}
      <div
        role="tablist"
        aria-label="Niveles de reportes"
        className="flex flex-wrap items-center gap-5 border-b border-[var(--border-default)] shadow-[var(--linea-surco)]"
      >
        {TABS.map((opt) => {
          const active = activeTab === opt.v;
          const href = opt.v === "pmo" ? "/pmo/reports" : `/pmo/reports?tab=${opt.v}`;
          return (
            <Link
              key={opt.v}
              href={href}
              role="tab"
              aria-selected={active}
              className={cn(
                "-mb-px flex h-9 items-center gap-1.5 border-b-2 text-[13px] transition-colors",
                active
                  ? "border-[var(--text-primary)] font-semibold text-[var(--text-primary)]"
                  : "border-transparent text-[var(--text-tertiary)] hover:text-[var(--text-primary)]",
              )}
            >
              <Icono nombre={opt.icono} size={14} />
              {opt.label}
            </Link>
          );
        })}
      </div>

      {activeTab === "pmo" ? (
        <PmoScopePlaceholder />
      ) : activeTab === "organization" ? (
        <OrgScopePlaceholder />
      ) : activeTab === "portfolio" ? (
        <ReportesDePortafolio />
      ) : activeTab === "program" ? (
        <ProgramScopePlaceholder />
      ) : (
        <ProjectsReportsView />
      )}
    </div>
  );
}

// US-144 — Tab PMO. Generación + (placeholder) historial.
function PmoScopePlaceholder() {
  const [templates, setTemplates] = useState<ReportBuilderTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listBuilderTemplates({ level: 1 })
      .then((all) => {
        if (!cancelled) setTemplates(all);
      })
      .catch((err) => {
        if (!cancelled)
          setError(err instanceof Error ? err.message : "No se pudo cargar plantillas");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function generatePmoReport(tpl: ReportBuilderTemplate) {
    setExporting(tpl.id);
    setError(null);
    try {
      const blob = await exportBuilderPdf(tpl.id, {
        level: 1,
        window_days: 30,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `pmo-status-${tpl.code}-${new Date().toISOString().slice(0, 10)}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo generar el reporte");
    } finally {
      setExporting(null);
    }
  }

  return (
    <div className="space-y-5">
      {error ? <Banner variant="danger">{error}</Banner> : null}

      <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--relieve-isla)]">
        <div className="flex items-start gap-3">
          <Icono nombre="layout-dashboard" size={17} className="mt-0.5 text-[var(--color-accent)]" />
          <div className="flex-1">
            <h2 className="text-base font-semibold text-[var(--text-primary)]">
              Reporte Status PMO
            </h2>
            <p className="mt-0.5 text-xs text-[var(--text-tertiary)]">
              Genera el reporte de status de toda la PMO (sin filtros). El reporte
              se descarga directo como PDF.
            </p>
          </div>
        </div>

        {loading ? (
          <div className="mt-4 space-y-2">
            <Skeleton className="h-14 w-full" />
          </div>
        ) : templates.length === 0 ? (
          <p className="mt-4 text-xs italic text-[var(--text-tertiary)]">
            Sin plantillas Nivel 1 disponibles. Verifica el seed de
            `report_builder_templates`.
          </p>
        ) : (
          <ul className="mt-4 space-y-2">
            {templates.map((tpl) => (
              <li
                key={tpl.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--color-subtle)] px-3 py-2"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-[var(--text-primary)]">
                    {tpl.name}
                  </p>
                  <p className="mt-0.5 text-[11px] text-[var(--text-tertiary)]">
                    {tpl.section_codes.length} secciones · Modo {tpl.composition_mode}
                  </p>
                </div>
                <Button
                  size="sm"
                  onClick={() => generatePmoReport(tpl)}
                  loading={exporting === tpl.id}
                  disabled={exporting !== null}
                >
                  <Icono nombre="download" size={14} />
                  Descargar
                </Button>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Cascarón: historial scoped a PMO no persiste todavía. Cuando la
          estructura final del reporte esté definida (sesión owner aparte),
          aquí va una tabla con los descargados anteriormente. */}
      <section className="rounded-[var(--radius-xl)] border border-dashed border-[var(--border-default)] bg-[var(--color-subtle)] p-6 text-center">
        <p className="text-xs text-[var(--text-tertiary)]">
          <strong className="text-[var(--text-secondary)]">Historial:</strong>{" "}
          se habilitará cuando se defina la estructura final del reporte PMO
          (cascarón aprobado por owner — pendiente sesión de diseño).
        </p>
      </section>
    </div>
  );
}

// US-145 — Tab Organizaciones con filtro org + generación.
function OrgScopePlaceholder() {
  const [templates, setTemplates] = useState<ReportBuilderTemplate[]>([]);
  // US-205 — la organización la elige el header.
  const orgId = useOrgFiltro() ?? "";
  const { activaObj: orgActiva } = useOrganizacionActiva();
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listBuilderTemplates({ level: 2 })
      .then((tpls) => {
        if (!cancelled) setTemplates(tpls);
      })
      .catch((err) => {
        if (!cancelled)
          setError(err instanceof Error ? err.message : "No se pudo cargar");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function generateOrgReport(tpl: ReportBuilderTemplate) {
    if (!orgId) {
      setError("Selecciona una organización antes de generar");
      return;
    }
    setExporting(tpl.id);
    setError(null);
    try {
      const blob = await exportBuilderPdf(tpl.id, {
        level: 2,
        organization_id: orgId,
        window_days: 30,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const orgName = orgActiva?.name?.replace(/[^a-z0-9]+/gi, "-") ?? "org";
      a.download = `org-${orgName}-${tpl.code}-${new Date().toISOString().slice(0, 10)}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo generar el reporte");
    } finally {
      setExporting(null);
    }
  }

  return (
    <div className="space-y-5">
      {error ? <Banner variant="danger">{error}</Banner> : null}

      <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--relieve-isla)]">
        <div className="flex items-start gap-3">
          <Icono nombre="building" size={17} className="mt-0.5 text-[var(--color-accent)]" />
          <div className="flex-1">
            <h2 className="text-base font-semibold text-[var(--text-primary)]">
              Reporte por Organización
            </h2>
            <p className="mt-0.5 text-xs text-[var(--text-tertiary)]">
              Selecciona una organización y descarga su reporte Status.
            </p>
          </div>
        </div>

        {/* US-205 vació este contenedor al llevarse el select de organización
            al header y dejó la rejilla sin hijos. */}
        {loading ? (
          <div className="mt-4 space-y-2">
            <Skeleton className="h-14 w-full" />
          </div>
        ) : templates.length === 0 ? (
          <p className="mt-4 text-xs italic text-[var(--text-tertiary)]">
            Sin plantillas Nivel 2 disponibles.
          </p>
        ) : (
          <ul className="mt-4 space-y-2">
            {templates.map((tpl) => (
              <li
                key={tpl.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--color-subtle)] px-3 py-2"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-[var(--text-primary)]">
                    {tpl.name}
                  </p>
                  <p className="mt-0.5 text-[11px] text-[var(--text-tertiary)]">
                    {tpl.section_codes.length} secciones · Modo {tpl.composition_mode}
                  </p>
                </div>
                <Button
                  size="sm"
                  onClick={() => generateOrgReport(tpl)}
                  loading={exporting === tpl.id}
                  disabled={exporting !== null || !orgId}
                >
                  <Icono nombre="download" size={14} />
                  Descargar
                </Button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="rounded-[var(--radius-xl)] border border-dashed border-[var(--border-default)] bg-[var(--color-subtle)] p-6 text-center">
        <p className="text-xs text-[var(--text-tertiary)]">
          <strong className="text-[var(--text-secondary)]">Historial scoped a la organización:</strong>{" "}
          se habilitará cuando se persistan reportes Level=2 (cascarón pendiente
          sesión de diseño de schema).
        </p>
      </section>
    </div>
  );
}

// US-146 — Tab Programas con filtros org + programa.
/**
 * US-209 — Reportes de portafolio.
 *
 * El nivel que faltaba entero. ADR-037 metió el portafolio **entre** la
 * organización y el programa, y el reporte existía para inquilino,
 * organización, programa y proyecto: la única forma de mirar una cartera era el
 * reporte de su organización, que suma las demás.
 *
 * Dos entregables, y son distintos:
 *
 * - **Status del portafolio (PDF)** — el reporte de siempre
 *   (`scope_status.html`), agregando los proyectos de la cartera y comparando
 *   por programa, que es el nivel de abajo.
 * - **Plantillas de nivel 2** — el builder de secciones, con el scope puesto en
 *   el portafolio.
 */
function ReportesDePortafolio() {
  const orgId = useOrgFiltro() ?? "";
  const [portafolios, setPortafolios] = useState<Portfolio[]>([]);
  const [portfolioId, setPortfolioId] = useState("");
  const [plantillas, setPlantillas] = useState<ReportBuilderTemplate[]>([]);
  const [cargando, setCargando] = useState(true);
  const [cargandoPf, setCargandoPf] = useState(false);
  const [generando, setGenerando] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelado = false;
    listBuilderTemplates({ level: 2 })
      .then((tpls) => !cancelado && setPlantillas(tpls))
      .catch((err) => {
        if (!cancelado)
          setError(err instanceof Error ? err.message : "No se pudo cargar");
      })
      .finally(() => {
        if (!cancelado) setCargando(false);
      });
    return () => {
      cancelado = true;
    };
  }, []);

  useEffect(() => {
    if (!orgId) {
      setPortafolios([]);
      setPortfolioId("");
      return;
    }
    let cancelado = false;
    setCargandoPf(true);
    listPortfolios(orgId, { is_active: true })
      .then((pfs) => {
        if (cancelado) return;
        setPortafolios(pfs);
        // La elección anterior no sobrevive al cambio de organización: un
        // portafolio de otra devolvería un reporte vacío, no un error.
        setPortfolioId("");
      })
      .catch((err) => {
        if (!cancelado)
          setError(
            err instanceof Error ? err.message : "No se pudieron cargar los portafolios",
          );
      })
      .finally(() => {
        if (!cancelado) setCargandoPf(false);
      });
    return () => {
      cancelado = true;
    };
  }, [orgId]);

  const nombrePf =
    portafolios.find((p) => p.id === portfolioId)?.name?.replace(/[^a-z0-9]+/gi, "-") ??
    "portafolio";

  function descargar(blob: Blob, nombre: string) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = nombre;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function statusPdf() {
    if (!portfolioId) {
      setError("Elige un portafolio antes de generar");
      return;
    }
    setGenerando("status");
    setError(null);
    try {
      // Este helper descarga solo (el nombre lo pone él), como los otros
      // niveles. Las plantillas del builder sí devuelven Blob porque el nombre
      // lleva el código de la plantilla.
      await downloadPortfolioStatusReport(portfolioId);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "No se pudo generar el status del portafolio",
      );
    } finally {
      setGenerando(null);
    }
  }

  async function plantillaPdf(tpl: ReportBuilderTemplate) {
    if (!portfolioId) {
      setError("Elige un portafolio antes de generar");
      return;
    }
    setGenerando(tpl.id);
    setError(null);
    try {
      const blob = await exportBuilderPdf(tpl.id, {
        level: 2,
        // Los dos: el portafolio define qué se agrega y la organización, de
        // quién es el branding del PDF.
        organization_id: orgId,
        portfolio_id: portfolioId,
        window_days: 30,
      });
      descargar(
        blob,
        `portafolio-${nombrePf}-${tpl.code}-${new Date().toISOString().slice(0, 10)}.pdf`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo generar el reporte");
    } finally {
      setGenerando(null);
    }
  }

  return (
    <div className="space-y-5">
      {error ? <Banner variant="danger">{error}</Banner> : null}

      <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--relieve-isla)]">
        <div className="flex items-start gap-3">
          <Icono nombre="folders" size={17} className="mt-0.5 text-[var(--color-accent)]" />
          <div className="flex-1">
            <h2 className="text-base font-semibold text-[var(--text-primary)]">
              Reporte por Portafolio
            </h2>
            <p className="mt-0.5 text-xs text-[var(--text-tertiary)]">
              Agrega los proyectos de la cartera —los de sus programas y los que
              cuelgan directo de ella— y los compara por programa.
            </p>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <Select
            aria-label="Portafolio del reporte"
            value={portfolioId}
            onChange={(e) => setPortfolioId(e.target.value)}
            className="h-9 min-w-[220px]"
            disabled={!orgId || cargandoPf}
          >
            <option value="">
              {!orgId
                ? "Elige una organización en el header"
                : cargandoPf
                  ? "Cargando portafolios…"
                  : "Elige un portafolio"}
            </option>
            {/* DIS-03 — «elige una organización» y «esta organización no tiene
                portafolios» son cosas distintas, y un desplegable vacío sin
                distinguirlas se lee como que algo falló al cargar. */}
            {orgId && !cargandoPf && portafolios.length === 0 ? (
              <option value="" disabled>
                (esta organización no tiene portafolios)
              </option>
            ) : null}
            {portafolios.map((pf) => (
              <option key={pf.id} value={pf.id}>
                {pf.name}
              </option>
            ))}
          </Select>
          <Button
            type="button"
            variant="primary"
            size="sm"
            onClick={statusPdf}
            disabled={!portfolioId || generando !== null}
            loading={generando === "status"}
          >
            <Icono nombre="download" size={14} />
            Status del portafolio (PDF)
          </Button>
        </div>

        {cargando ? (
          <div className="mt-4 space-y-2">
            <Skeleton className="h-14 w-full" />
          </div>
        ) : plantillas.length === 0 ? (
          <p className="mt-4 text-xs italic text-[var(--text-tertiary)]">
            Sin plantillas Nivel 2 disponibles. El status de arriba no las
            necesita.
          </p>
        ) : (
          <ul className="mt-4 space-y-2">
            {plantillas.map((tpl) => (
              <li
                key={tpl.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--color-subtle)] px-3 py-2"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-[var(--text-primary)]">
                    {tpl.name}
                  </p>
                  <p className="truncate text-xs text-[var(--text-tertiary)]">
                    {tpl.code}
                  </p>
                </div>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => plantillaPdf(tpl)}
                  disabled={!portfolioId || generando !== null}
                  loading={generando === tpl.id}
                >
                  <Icono nombre="download" size={14} />
                  PDF
                </Button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}


function ProgramScopePlaceholder() {
  const [programs, setPrograms] = useState<Program[]>([]);
  const [templates, setTemplates] = useState<ReportBuilderTemplate[]>([]);
  // US-205 — la organización la elige el header.
  const orgId = useOrgFiltro() ?? "";
  const [programId, setProgramId] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [loadingPrograms, setLoadingPrograms] = useState(false);
  const [exporting, setExporting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listBuilderTemplates({ level: 2 })
      .then((tpls) => {
        if (!cancelled) setTemplates(tpls);
      })
      .catch((err) => {
        if (!cancelled)
          setError(err instanceof Error ? err.message : "No se pudo cargar");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Recarga programas cuando cambia la org.
  useEffect(() => {
    if (!orgId) {
      setPrograms([]);
      setProgramId("");
      return;
    }
    let cancelled = false;
    setLoadingPrograms(true);
    listPrograms({ organization_id: orgId })
      .then((ps) => {
        if (!cancelled) {
          setPrograms(ps);
          setProgramId("");
        }
      })
      .catch((err) => {
        if (!cancelled)
          setError(err instanceof Error ? err.message : "No se pudo cargar programas");
      })
      .finally(() => {
        if (!cancelled) setLoadingPrograms(false);
      });
    return () => {
      cancelled = true;
    };
  }, [orgId]);

  async function generateProgramReport(tpl: ReportBuilderTemplate) {
    if (!programId) {
      setError("Selecciona organización y programa antes de generar");
      return;
    }
    setExporting(tpl.id);
    setError(null);
    try {
      const blob = await exportBuilderPdf(tpl.id, {
        level: 2,
        organization_id: orgId,
        program_id: programId,
        window_days: 30,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const progName =
        programs.find((p) => p.id === programId)?.name?.replace(/[^a-z0-9]+/gi, "-") ?? "prog";
      a.download = `program-${progName}-${tpl.code}-${new Date().toISOString().slice(0, 10)}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo generar el reporte");
    } finally {
      setExporting(null);
    }
  }

  return (
    <div className="space-y-5">
      {error ? <Banner variant="danger">{error}</Banner> : null}

      <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--relieve-isla)]">
        <div className="flex items-start gap-3">
          <Icono nombre="route" size={17} className="mt-0.5 text-[var(--color-accent)]" />
          <div className="flex-1">
            <h2 className="text-base font-semibold text-[var(--text-primary)]">
              Reporte por Programa
            </h2>
            <p className="mt-0.5 text-xs text-[var(--text-tertiary)]">
              Selecciona organización y programa para descargar el reporte Status.
            </p>
          </div>
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <label className="block">
            <span className="mb-1 block text-[12px] font-medium text-[var(--text-secondary)]">
              Programa
            </span>
            <Select
              value={programId}
              onChange={(e) => setProgramId(e.target.value)}
              disabled={!orgId || loadingPrograms || programs.length === 0}
            >
              <option value="">
                {!orgId
                  ? "— Primero elige una organización —"
                  : loadingPrograms
                  ? "Cargando..."
                  : programs.length === 0
                  ? "— Sin programas —"
                  : "— Selecciona —"}
              </option>
              {programs.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </Select>
          </label>
        </div>

        {loading ? (
          <div className="mt-4 space-y-2">
            <Skeleton className="h-14 w-full" />
          </div>
        ) : templates.length === 0 ? (
          <p className="mt-4 text-xs italic text-[var(--text-tertiary)]">
            Sin plantillas Nivel 2 disponibles.
          </p>
        ) : (
          <ul className="mt-4 space-y-2">
            {templates.map((tpl) => (
              <li
                key={tpl.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--color-subtle)] px-3 py-2"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-[var(--text-primary)]">
                    {tpl.name}
                  </p>
                  <p className="mt-0.5 text-[11px] text-[var(--text-tertiary)]">
                    {tpl.section_codes.length} secciones · Modo {tpl.composition_mode}
                  </p>
                </div>
                <Button
                  size="sm"
                  onClick={() => generateProgramReport(tpl)}
                  loading={exporting === tpl.id}
                  disabled={exporting !== null || !programId}
                >
                  <Icono nombre="download" size={14} />
                  Descargar
                </Button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="rounded-[var(--radius-xl)] border border-dashed border-[var(--border-default)] bg-[var(--color-subtle)] p-6 text-center">
        <p className="text-xs text-[var(--text-tertiary)]">
          <strong className="text-[var(--text-secondary)]">Historial scoped al programa:</strong>{" "}
          se habilitará cuando se persistan reportes Level=2 con `program_id` (mismo cascarón que US-145).
        </p>
      </section>
    </div>
  );
}

// ENH-120: tab Proyectos = contenido actual + 4 fixes.
function ProjectsReportsView() {
  const [filter, setFilter] = useState<TenantCrossFilterValue>({});
  const [rows, setRows] = useState<TenantReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    listTenantReports(filter)
      .then((r) => {
        if (!cancelled) setRows(r);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "No se pudo cargar");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [filter]);

  return (
    <>
      {error ? <Banner variant="danger">{error}</Banner> : null}

      <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--relieve-isla)]">
        <TenantCrossFilters value={filter} onChange={setFilter} />
        <p className="mt-2 text-[11px] text-[var(--text-tertiary)]">
          Sólo se muestran reportes guardados (no borradores).
        </p>
      </section>

      <section className="overflow-hidden rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--relieve-isla)]">
        {loading ? (
          <div className="space-y-2 p-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        ) : rows.length === 0 ? (
          <div className="p-10 text-center text-sm text-[var(--text-tertiary)]">
            Sin reportes guardados para los filtros actuales.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full table-fixed text-[13px]">
              <thead className="border-b border-[var(--border-default)] bg-[var(--color-subtle)] text-left text-[10.5px] font-semibold uppercase tracking-[0.06em] text-[var(--text-tertiary)] shadow-[var(--linea-surco)]">
                <tr>
                  <th className="h-8.5 w-24 px-3 font-semibold">Folio</th>
                  <th className="h-8.5 px-3 font-semibold">Título</th>
                  <th className="h-8.5 w-28 px-3 font-semibold">Tipo</th>
                  <th className="h-8.5 w-28 px-3 font-semibold">Período</th>
                  <th className="h-8.5 w-28 px-3 font-semibold">Estado</th>
                  <th className="h-8.5 w-56 px-3 font-semibold">Proyecto</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr
                    key={r.id}
                    className="border-b border-[var(--border-subtle)] shadow-[var(--linea-surco)] hover:bg-[var(--color-subtle)]"
                  >
                    <td className="h-11 px-3 align-middle text-[12px] tracking-[0.01em] text-[var(--text-tertiary)]">
                      {r.folio}
                    </td>
                    <td className="h-11 px-3 align-middle">
                      {/* ENH-120: link al detail del reporte específico, no al listing del proyecto */}
                      <Link
                        href={`/pmo/projects/${r.project_id}/reports/${r.id}`}
                        className="block overflow-hidden text-ellipsis whitespace-nowrap text-[var(--text-primary)] hover:underline"
                        title={r.title}
                      >
                        {r.title}
                      </Link>
                    </td>
                    <td className="h-11 px-3 align-middle">
                      {/* ENH-120: label "Builder" para reportes de US-140 */}
                      <Badge
                        variant={r.report_type === "Builder" ? "info" : "neutral"}
                      >
                        {r.report_type ?? "—"}
                      </Badge>
                    </td>
                    <td className="h-11 px-3 align-middle text-[12.5px] text-[var(--text-secondary)]">
                      {r.period ?? "—"}
                    </td>
                    <td className="h-11 px-3 align-middle text-[12.5px] text-[var(--text-secondary)]">
                      {r.status}
                    </td>
                    <td className="h-11 px-3 align-middle">
                      <Link
                        href={`/pmo/projects/${r.project_id}`}
                        className="block overflow-hidden text-ellipsis whitespace-nowrap text-[12.5px] text-[var(--color-accent)] hover:underline"
                        title={r.project_name}
                      >
                        <span className="text-[12px] tracking-[0.01em]">{r.project_folio}</span>
                        <span className="ml-1 text-[var(--text-secondary)]">
                          — {r.project_name}
                        </span>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}
