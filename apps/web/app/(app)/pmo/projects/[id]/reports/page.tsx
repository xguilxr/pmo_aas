"use client";

import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState, type FormEvent } from "react";
import {
  ArrowLeft,
  CalendarClock,
  Download,
  Eye,
  FileText,
  LayoutGrid,
  Mail,
  Pencil,
  Plus,
  Send,
  Sparkles,
  Trash2,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api";
import { getStoredUser } from "@/lib/auth-storage";
import { draftReport, sendReport } from "@/lib/api/ai";
import { useAIJobPolling } from "@/lib/hooks/use-ai-job-polling";
import {
  PERIOD_LABEL,
  SECTION_LABELS,
  type AIReportTemplate,
  aiGenerateReport,
  createAIReportTemplate,
  deleteAIReportTemplate,
  deleteReportHistory,
  listAIReportTemplates,
  createReport,
  deleteReport,
  downloadReportHistory,
  generateAvanceReport,
  generateSeguimientoReport,
  getReport,
  listReports,
  listReportHistory,
  previewAvanceTemplate,
  previewReportHistory,
  previewReportHtml,
  previewSeguimientoTemplate,
  regenerateBuilderPdf,
  updateReport,
  type Report,
  type ReportHistoryItem,
  type ReportPeriod,
} from "@/lib/api/reports";
import {
  CADENCE_LABEL,
  REPORT_TYPE_LABEL,
  createScheduledReport,
  deleteScheduledReport,
  listScheduledReports,
  runScheduledReportNow,
  updateScheduledReport,
  type ScheduledReport,
  type ScheduledReportCadence,
  type ScheduledReportType,
} from "@/lib/api/scheduled-reports";
import { type Area, listAreasByProject } from "@/lib/api/areas";
import {
  listBuilderTemplates,
  type ReportBuilderTemplate,
} from "@/lib/api/report-builder";
import { cn } from "@/lib/cn";

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("es-MX", {
      year: "numeric",
      month: "short",
      day: "2-digit",
    });
  } catch {
    return iso;
  }
}

function StatusBadge({ status }: { status: Report["status"] }) {
  return status === "sent" ? (
    <Badge variant="success">Enviado</Badge>
  ) : (
    <Badge variant="neutral">Borrador</Badge>
  );
}

function GeneratorBadge({ generator }: { generator: Report["generator"] }) {
  if (generator === "avance") return <Badge variant="info">Avance</Badge>;
  if (generator === "seguimiento")
    return <Badge variant="info">Seguimiento</Badge>;
  if (generator === "builder")
    return <Badge variant="accent">Builder</Badge>;
  return null;
}

// ENH-055: toggle de vistas con hash en URL.
// US-141: añade "builder" para listar reportes generados desde el
// Report Builder (`generator='builder'`) con acción "Regenerar PDF".
type ReportsView = "catalog" | "history" | "builder" | "create";

function parseViewHash(): ReportsView {
  if (typeof window === "undefined") return "catalog";
  const h = (window.location.hash || "").replace(/^#/, "").toLowerCase();
  if (h === "history" || h === "create" || h === "builder") return h;
  return "catalog";
}

function ReportsInner() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const searchParams = useSearchParams();
  const editingId = searchParams.get("report");

  const [rows, setRows] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  // ENH-055: vista activa persistida en `location.hash`.
  const [view, setView] = useState<ReportsView>("catalog");

  useEffect(() => {
    setView(parseViewHash());
    function onHash() {
      setView(parseViewHash());
    }
    if (typeof window !== "undefined") {
      window.addEventListener("hashchange", onHash);
      return () => window.removeEventListener("hashchange", onHash);
    }
  }, []);

  function setViewAndHash(v: ReportsView) {
    setView(v);
    if (typeof window !== "undefined") {
      const newHash = v === "catalog" ? "" : `#${v}`;
      const url = `${window.location.pathname}${window.location.search}${newHash}`;
      window.history.replaceState(null, "", url);
    }
  }

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      setRows(await listReports(id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar reportes");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!editingId) void refresh();
  }, [id, editingId]);

  function openReport(rid: string) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("report", rid);
    router.replace(`/pmo/projects/${id}/reports?${params.toString()}`);
  }
  function closeEditor() {
    const params = new URLSearchParams(searchParams.toString());
    params.delete("report");
    const qs = params.toString();
    router.replace(
      qs ? `/pmo/projects/${id}/reports?${qs}` : `/pmo/projects/${id}/reports`,
    );
  }

  if (editingId) {
    return (
      <ReportEditor
        reportId={editingId}
        projectId={id}
        onBack={closeEditor}
        onDeleted={() => {
          closeEditor();
          void refresh();
        }}
      />
    );
  }

  return (
    <div className="mx-auto max-w-5xl space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <nav className="text-[11px] text-[var(--text-tertiary)]">
            <Link href="/pmo/projects" className="hover:underline">
              Proyectos
            </Link>
            <span className="mx-1">/</span>
            <Link href={`/pmo/projects/${id}`} className="hover:underline">
              Detalle
            </Link>
            <span className="mx-1">/</span>
            <span>Reportes</span>
          </nav>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
            Reportes
          </h1>
          <p className="mt-1 text-[13px] text-[var(--text-tertiary)]">
            Reportes de estado manuales o asistidos con IA. Enviables por
            email con PDF opcional.
          </p>
        </div>
        {/* US-109 (rework): CTA principal hacia el panel de creación con
            tweaker IA. El destino `/reports/tweak` (sin query) muestra el
            panel inicial con los 2 modos: "Generar nuevo reporte" vs
            "Generar con base en plantilla".
            US-135 (Sprint 30): segundo CTA hacia el Report Builder canvas
            (EP020). Chip "Nuevo" para señalar funcionalidad reciente. */}
        <div className="flex items-center gap-2">
          <Link href={`/pmo/projects/${id}/reports/builder`}>
            <Button variant="secondary">
              <LayoutGrid className="h-4 w-4" aria-hidden />
              Report Builder
              <Badge className="ml-1 bg-violet-100 text-[10px] text-violet-700">
                Nuevo
              </Badge>
            </Button>
          </Link>
          <Link href={`/pmo/projects/${id}/reports/tweak`}>
            <Button>
              <Sparkles className="h-4 w-4" aria-hidden /> Crear reporte (IA + plantilla)
            </Button>
          </Link>
        </div>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      {/* ENH-055: toggle 3 vistas Catálogo / Historial / Creación con
          persistencia en hash. */}
      <div
        role="radiogroup"
        aria-label="Vista de reportes"
        className="inline-flex rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-surface)] p-0.5"
      >
        {(
          [
            { v: "catalog" as const, label: "Catálogo" },
            { v: "history" as const, label: "Historial" },
            { v: "builder" as const, label: "Builder" },
            { v: "create" as const, label: "Creación" },
          ]
        ).map((opt) => {
          const active = view === opt.v;
          return (
            <button
              key={opt.v}
              type="button"
              role="radio"
              aria-checked={active}
              onClick={() => setViewAndHash(opt.v)}
              className={cn(
                "rounded-[var(--radius-sm)] px-4 py-1.5 text-xs font-medium transition-colors",
                active
                  ? "bg-[var(--color-primary)] text-[var(--color-inverse)]"
                  : "text-[var(--text-secondary)] hover:bg-[var(--color-subtle)]",
              )}
            >
              {opt.label}
            </button>
          );
        })}
      </div>

      {view === "history" ? (
        <ReportHistoryView projectId={id} />
      ) : view === "builder" ? (
        <ReportBuilderView projectId={id} />
      ) : view === "create" ? (
        <ReportCreateAIView projectId={id} />
      ) : (
        <>
          <ReportCatalogView projectId={id} />
          <ScheduledReportsSection projectId={id} />
        </>
      )}

      <CreateReportModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        projectId={id}
        onCreated={(r) => {
          setCreateOpen(false);
          openReport(r);
        }}
      />
    </div>
  );
}

function ScheduledReportsSection({ projectId }: { projectId: string }) {
  const [rows, setRows] = useState<ScheduledReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<ScheduledReport | null>(null);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      setRows(await listScheduledReports(projectId));
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Error al cargar programaciones",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, [projectId]);

  async function toggleEnabled(row: ScheduledReport) {
    try {
      await updateScheduledReport(row.id, { enabled: !row.enabled });
      await refresh();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Error al actualizar",
      );
    }
  }

  async function remove(row: ScheduledReport) {
    if (!window.confirm("¿Eliminar esta programación?")) return;
    try {
      await deleteScheduledReport(row.id);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al eliminar");
    }
  }

  // BUG-036: dispara el envío inmediato sin esperar la cadencia.
  // Útil para que el owner valide end-to-end (PDF + email) antes de
  // confiar en el beat scheduler.
  async function sendNow(row: ScheduledReport) {
    if (
      !window.confirm(
        `Enviar el reporte ahora a ${row.recipients.length} destinatario(s)?`,
      )
    ) {
      return;
    }
    try {
      const r = await runScheduledReportNow(row.id);
      window.alert(r.note);
      // Refresh para que `last_run_at` se actualice una vez procesado.
      setTimeout(() => void refresh(), 5_000);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Error al encolar el envío",
      );
    }
  }

  return (
    <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]">
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border-subtle)] px-4 py-3">
        <div className="flex items-center gap-2">
          <CalendarClock
            className="h-4 w-4 text-[var(--color-tertiary)]"
            aria-hidden
          />
          <h2 className="text-sm font-semibold text-[var(--color-primary)]">
            Envíos automáticos programados
          </h2>
        </div>
        <Button
          size="sm"
          onClick={() => {
            setEditing(null);
            setFormOpen(true);
          }}
        >
          <Plus className="h-4 w-4" aria-hidden /> Nueva programación
        </Button>
      </header>
      {error ? (
        <div className="px-4 pt-3">
          <Banner variant="danger">{error}</Banner>
        </div>
      ) : null}
      {loading ? (
        <div className="space-y-2 p-4">
          {Array.from({ length: 2 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      ) : rows.length === 0 ? (
        <div className="px-4 py-6 text-center text-sm text-[var(--color-tertiary)]">
          Sin programaciones aún. Crea una para enviar Reportes de Avance o
          Seguimiento a los involucrados en una cadencia fija.
        </div>
      ) : (
        <ul className="divide-y divide-[var(--border-subtle)]">
          {rows.map((r) => (
            <li
              key={r.id}
              className="flex items-center gap-3 px-4 py-3 hover:bg-[var(--color-subtle)]"
            >
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <span className="font-medium text-[var(--color-primary)]">
                    {REPORT_TYPE_LABEL[r.report_type]}
                  </span>
                  <Badge variant="neutral">{CADENCE_LABEL[r.cadence]}</Badge>
                  {r.enabled ? (
                    <Badge variant="success">Activa</Badge>
                  ) : (
                    <Badge variant="neutral">Pausada</Badge>
                  )}
                </div>
                <div className="mt-0.5 flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-[var(--color-tertiary)]">
                  <span className="inline-flex items-center gap-1">
                    <Mail className="h-3 w-3" aria-hidden />
                    {r.recipients.length} destinatarios
                  </span>
                  <span>Próximo: {fmtDate(r.next_run_at)}</span>
                  <span>Último envío: {fmtDate(r.last_run_at)}</span>
                  {r.last_error ? (
                    <span className="text-[var(--color-danger-fg)]">
                      {r.last_error}
                    </span>
                  ) : null}
                </div>
              </div>
              <div className="flex items-center gap-1">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => sendNow(r)}
                  aria-label="Enviar ahora"
                  title="Enviar ahora (sin esperar la cadencia)"
                >
                  Enviar ahora
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => toggleEnabled(r)}
                  aria-label={r.enabled ? "Pausar" : "Reactivar"}
                  title={r.enabled ? "Pausar" : "Reactivar"}
                >
                  {r.enabled ? "Pausar" : "Activar"}
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setEditing(r);
                    setFormOpen(true);
                  }}
                  aria-label="Editar"
                  title="Editar"
                >
                  <Pencil className="h-4 w-4" aria-hidden />
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => remove(r)}
                  aria-label="Eliminar"
                  title="Eliminar"
                >
                  <Trash2 className="h-4 w-4" aria-hidden />
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
      <ScheduledReportForm
        open={formOpen}
        projectId={projectId}
        existing={editing}
        onClose={() => setFormOpen(false)}
        onSaved={() => {
          setFormOpen(false);
          void refresh();
        }}
      />
    </section>
  );
}

function ScheduledReportForm({
  open,
  projectId,
  existing,
  onClose,
  onSaved,
}: {
  open: boolean;
  projectId: string;
  existing: ScheduledReport | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [reportType, setReportType] = useState<ScheduledReportType>("avance");
  const [cadence, setCadence] = useState<ScheduledReportCadence>("weekly");
  const [recipients, setRecipients] = useState("");
  const [enabled, setEnabled] = useState(true);
  // ENH-046: campos opcionales según cadencia.
  const [dayOfWeek, setDayOfWeek] = useState<number>(0); // 0 = Lunes
  const [hourOfDay, setHourOfDay] = useState<number>(9); // 09:00 default
  // ENH-056: día del mes para cadence=monthly.
  const [dayOfMonth, setDayOfMonth] = useState<number>(1);
  const [runAtDate, setRunAtDate] = useState<string>(""); // YYYY-MM-DD
  const [runAtTime, setRunAtTime] = useState<string>("09:00"); // HH:MM
  // ENH-114: plantilla del builder cuando report_type='custom'.
  const [builderTemplateId, setBuilderTemplateId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    if (existing) {
      setReportType(existing.report_type);
      setCadence(existing.cadence);
      setRecipients(existing.recipients.join(", "));
      setEnabled(existing.enabled);
      setDayOfWeek(existing.day_of_week ?? 0);
      setHourOfDay(existing.hour_of_day ?? 9);
      setDayOfMonth(existing.day_of_month ?? 1);
      setBuilderTemplateId(existing.report_builder_template_id ?? null);
      if (existing.run_at) {
        const d = new Date(existing.run_at);
        setRunAtDate(d.toISOString().slice(0, 10));
        setRunAtTime(
          `${String(d.getUTCHours()).padStart(2, "0")}:${String(d.getUTCMinutes()).padStart(2, "0")}`,
        );
      } else {
        setRunAtDate("");
        setRunAtTime("09:00");
      }
    } else {
      setReportType("avance");
      setCadence("weekly");
      setRecipients("");
      setEnabled(true);
      setDayOfWeek(0);
      setHourOfDay(9);
      setDayOfMonth(1);
      setRunAtDate("");
      setRunAtTime("09:00");
      setBuilderTemplateId(null);
    }
    setError(null);
  }, [open, existing]);

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      const list = recipients
        .split(/[,\s]+/)
        .map((s) => s.trim())
        .filter(Boolean);
      if (list.length === 0) {
        setError("Agrega al menos un destinatario");
        setSaving(false);
        return;
      }
      for (const r of list) {
        if (!emailRe.test(r)) {
          setError(`Email inválido: ${r}`);
          setSaving(false);
          return;
        }
      }
      // ENH-046 / ENH-056: armar payload con los campos condicionales.
      const cadenceFields: {
        day_of_week?: number | null;
        hour_of_day?: number | null;
        day_of_month?: number | null;
        run_at?: string | null;
      } = {};
      if (cadence === "weekly") {
        cadenceFields.day_of_week = dayOfWeek;
        cadenceFields.hour_of_day = hourOfDay;
      } else if (cadence === "daily") {
        cadenceFields.hour_of_day = hourOfDay;
      } else if (cadence === "monthly") {
        cadenceFields.day_of_month = dayOfMonth;
        cadenceFields.hour_of_day = hourOfDay;
      } else if (cadence === "once") {
        if (!runAtDate) {
          setError("Selecciona la fecha de ejecución");
          setSaving(false);
          return;
        }
        // Combinar fecha local + hora local → ISO. Backend asume UTC si naive,
        // así que convertimos explicitamente con `new Date(...)` que toma la
        // tz local del browser y serializa a UTC con toISOString().
        const iso = new Date(`${runAtDate}T${runAtTime}:00`).toISOString();
        cadenceFields.run_at = iso;
      }

      // ENH-114: validar selección de plantilla del builder.
      if (reportType === "custom" && !builderTemplateId) {
        setError("Selecciona la plantilla del builder a programar");
        setSaving(false);
        return;
      }
      const builderField =
        reportType === "custom"
          ? { report_builder_template_id: builderTemplateId }
          : {};
      if (existing) {
        await updateScheduledReport(existing.id, {
          report_type: reportType,
          cadence,
          recipients: list,
          enabled,
          ...cadenceFields,
          ...builderField,
        });
      } else {
        await createScheduledReport(projectId, {
          report_type: reportType,
          cadence,
          recipients: list,
          enabled,
          ...cadenceFields,
          ...builderField,
        });
      }
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al guardar");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={existing ? "Editar programación" : "Nueva programación"}
    >
      <form onSubmit={submit} className="space-y-3">
        <div>
          <label
            htmlFor="sched-type"
            className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
          >
            Tipo de reporte
          </label>
          <Select
            id="sched-type"
            value={reportType}
            onChange={(e) =>
              setReportType(e.target.value as ScheduledReportType)
            }
          >
            <option value="avance">Reporte de Avance</option>
            <option value="seguimiento">Reporte de Seguimiento</option>
            <option value="custom">Plantilla del Builder</option>
          </Select>
        </div>
        {/* ENH-114: cuando es 'custom', el usuario debe elegir una
            plantilla del Report Builder (US-131 backend ya lo acepta). */}
        {reportType === "custom" && (
          <BuilderTemplatePicker
            projectId={projectId}
            value={builderTemplateId}
            onChange={setBuilderTemplateId}
          />
        )}
        <div>
          <label
            htmlFor="sched-cadence"
            className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
          >
            Cadencia
          </label>
          <Select
            id="sched-cadence"
            value={cadence}
            onChange={(e) =>
              setCadence(e.target.value as ScheduledReportCadence)
            }
          >
            <option value="daily">Diario</option>
            <option value="weekly">Semanal</option>
            <option value="monthly">Mensual</option>
            <option value="once">Una vez (fecha específica)</option>
          </Select>
        </div>

        {cadence === "weekly" ? (
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label
                htmlFor="sched-dow"
                className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
              >
                Día de la semana
              </label>
              <Select
                id="sched-dow"
                value={String(dayOfWeek)}
                onChange={(e) => setDayOfWeek(Number(e.target.value))}
              >
                <option value="0">Lunes</option>
                <option value="1">Martes</option>
                <option value="2">Miércoles</option>
                <option value="3">Jueves</option>
                <option value="4">Viernes</option>
                <option value="5">Sábado</option>
                <option value="6">Domingo</option>
              </Select>
            </div>
            <div>
              <label
                htmlFor="sched-hod"
                className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
              >
                Hora (24h)
              </label>
              <Select
                id="sched-hod"
                value={String(hourOfDay)}
                onChange={(e) => setHourOfDay(Number(e.target.value))}
              >
                {Array.from({ length: 24 }, (_, h) => (
                  <option key={h} value={h}>{`${String(h).padStart(2, "0")}:00`}</option>
                ))}
              </Select>
            </div>
          </div>
        ) : null}

        {cadence === "daily" ? (
          <div>
            <label
              htmlFor="sched-hod-d"
              className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
            >
              Hora (24h)
            </label>
            <Select
              id="sched-hod-d"
              value={String(hourOfDay)}
              onChange={(e) => setHourOfDay(Number(e.target.value))}
            >
              {Array.from({ length: 24 }, (_, h) => (
                <option key={h} value={h}>{`${String(h).padStart(2, "0")}:00`}</option>
              ))}
            </Select>
          </div>
        ) : null}

        {cadence === "monthly" ? (
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label
                htmlFor="sched-dom"
                className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
              >
                Día del mes (1-31)
              </label>
              <Select
                id="sched-dom"
                value={String(dayOfMonth)}
                onChange={(e) => setDayOfMonth(Number(e.target.value))}
              >
                {Array.from({ length: 31 }, (_, i) => i + 1).map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </Select>
              <p className="mt-1 text-[11px] text-[var(--color-tertiary)]">
                Si el mes seleccionado no tiene ese día, se enviará el último día del mes.
              </p>
            </div>
            <div>
              <label
                htmlFor="sched-hod-m"
                className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
              >
                Hora (24h)
              </label>
              <Select
                id="sched-hod-m"
                value={String(hourOfDay)}
                onChange={(e) => setHourOfDay(Number(e.target.value))}
              >
                {Array.from({ length: 24 }, (_, h) => (
                  <option key={h} value={h}>{`${String(h).padStart(2, "0")}:00`}</option>
                ))}
              </Select>
            </div>
          </div>
        ) : null}

        {cadence === "once" ? (
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label
                htmlFor="sched-runat-date"
                className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
              >
                Fecha
              </label>
              <Input
                id="sched-runat-date"
                type="date"
                value={runAtDate}
                onChange={(e) => setRunAtDate(e.target.value)}
              />
            </div>
            <div>
              <label
                htmlFor="sched-runat-time"
                className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
              >
                Hora
              </label>
              <Input
                id="sched-runat-time"
                type="time"
                step={3600}
                value={runAtTime}
                onChange={(e) => setRunAtTime(e.target.value)}
              />
            </div>
          </div>
        ) : null}

        <div>
          <label
            htmlFor="sched-recipients"
            className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
          >
            Destinatarios (emails separados por coma)
          </label>
          <Input
            id="sched-recipients"
            value={recipients}
            onChange={(e) => setRecipients(e.target.value)}
            placeholder="pm@empresa.com, sponsor@empresa.com"
          />
        </div>
        <div className="flex items-center gap-2">
          <input
            id="sched-enabled"
            type="checkbox"
            checked={enabled}
            onChange={(e) => setEnabled(e.target.checked)}
          />
          <label
            htmlFor="sched-enabled"
            className="text-sm text-[var(--color-secondary)]"
          >
            Activa
          </label>
        </div>
        {error ? <Banner variant="danger">{error}</Banner> : null}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" loading={saving}>
            {existing ? "Guardar" : "Crear"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function CreateReportModal({
  open,
  onClose,
  projectId,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  projectId: string;
  onCreated: (reportId: string) => void;
}) {
  const [period, setPeriod] = useState<ReportPeriod>("weekly");
  const [title, setTitle] = useState("");
  const [recipients, setRecipients] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      const list = recipients
        .split(/[,\s]+/)
        .map((s) => s.trim())
        .filter(Boolean);
      for (const r of list) {
        if (!emailRe.test(r)) {
          setError(`Email inválido: ${r}`);
          setSaving(false);
          return;
        }
      }
      const created = await createReport(projectId, {
        title: title.trim() || undefined,
        period,
        recipients: list,
      });
      setTitle("");
      setRecipients("");
      setPeriod("weekly");
      onCreated(created.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al crear reporte");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Nuevo reporte">
      <form onSubmit={submit} className="space-y-3">
        <div>
          <label
            htmlFor="rep-title"
            className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
          >
            Título (opcional)
          </label>
          <Input
            id="rep-title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Se autogenera si lo dejas vacío"
          />
        </div>
        <div>
          <label
            htmlFor="rep-period"
            className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
          >
            Periodo
          </label>
          <Select
            id="rep-period"
            value={period}
            onChange={(e) => setPeriod(e.target.value as ReportPeriod)}
          >
            <option value="daily">Diario</option>
            <option value="weekly">Semanal</option>
            <option value="monthly">Mensual</option>
          </Select>
        </div>
        <div>
          <label
            htmlFor="rep-recipients"
            className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
          >
            Destinatarios (emails separados por coma)
          </label>
          <Input
            id="rep-recipients"
            value={recipients}
            onChange={(e) => setRecipients(e.target.value)}
            placeholder="pm@empresa.com, sponsor@empresa.com"
          />
        </div>
        {error ? <Banner variant="danger">{error}</Banner> : null}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" loading={saving}>
            Crear y abrir editor
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function GenerateWithAIButton({
  projectId,
  onCreated,
}: {
  projectId: string;
  onCreated: (reportId: string) => void;
}) {
  const [dispatching, setDispatching] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const polling = useAIJobPolling({
    jobId,
    enabled: !!jobId,
    onSuccess: (job) => {
      const payload = (job.output ?? null) as { report_id?: string } | null;
      if (payload?.report_id) {
        onCreated(payload.report_id);
      } else {
        setError("El worker no devolvió report_id");
      }
      setJobId(null);
    },
    onError: (job) => {
      setError(job.error || "La generación falló");
      setJobId(null);
    },
  });

  async function generate() {
    setDispatching(true);
    setError(null);
    try {
      const r = await draftReport(projectId, {});
      setJobId(r.job_id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al generar con IA");
    } finally {
      setDispatching(false);
    }
  }

  const working = dispatching || polling.isPolling;

  return (
    <div className="flex flex-col items-end gap-1">
      <Button
        type="button"
        variant="secondary"
        onClick={generate}
        loading={working}
      >
        <Sparkles className="h-4 w-4" aria-hidden /> Generar con IA
      </Button>
      {polling.isPolling ? (
        <span className="text-[11px] text-[var(--text-tertiary)]">
          {polling.status === "queued" ? "En cola..." : "Generando..."}
        </span>
      ) : null}
      {error ? (
        <span className="text-[11px] text-[var(--color-danger-fg)]">{error}</span>
      ) : null}
      {polling.error ? (
        <span className="text-[11px] text-[var(--color-danger-fg)]">{polling.error}</span>
      ) : null}
    </div>
  );
}

function GenerateAvanceButton({
  projectId,
  onDone,
}: {
  projectId: string;
  onDone: () => void;
}) {
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function generate() {
    setWorking(true);
    setError(null);
    try {
      await generateAvanceReport(projectId);
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al generar reporte");
    } finally {
      setWorking(false);
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <Button
        type="button"
        variant="secondary"
        onClick={generate}
        loading={working}
      >
        <Download className="h-4 w-4" aria-hidden /> Reporte de Avance (PDF)
      </Button>
      {error ? (
        <span className="text-[11px] text-[var(--color-danger-fg)]">{error}</span>
      ) : null}
    </div>
  );
}

function GenerateSeguimientoButton({
  projectId,
  onDone,
}: {
  projectId: string;
  onDone: () => void;
}) {
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function generate() {
    setWorking(true);
    setError(null);
    try {
      await generateSeguimientoReport(projectId);
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al generar reporte");
    } finally {
      setWorking(false);
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <Button
        type="button"
        variant="secondary"
        onClick={generate}
        loading={working}
      >
        <Download className="h-4 w-4" aria-hidden /> Reporte de Seguimiento (PDF)
      </Button>
      {error ? (
        <span className="text-[11px] text-[var(--color-danger-fg)]">{error}</span>
      ) : null}
    </div>
  );
}

function ReportEditor({
  reportId,
  projectId,
  onBack,
  onDeleted,
}: {
  reportId: string;
  projectId: string;
  onBack: () => void;
  onDeleted: () => void;
}) {
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [sendSubject, setSendSubject] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getReport(reportId)
      .then((r) => {
        if (cancelled) return;
        setReport(r);
      })
      .catch((err) => {
        if (!cancelled)
          setError(
            err instanceof ApiError ? err.message : "Error al cargar reporte",
          );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [reportId]);

  const readOnly = report?.status === "sent";

  const sectionKeys = useMemo(
    () =>
      Object.keys(report?.sections ?? {}).length > 0
        ? Object.keys(report!.sections)
        : Object.keys(SECTION_LABELS),
    [report],
  );

  async function save() {
    if (!report || readOnly) return;
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const updated = await updateReport(report.id, {
        title: report.title,
        period: report.period ?? undefined,
        recipients: report.recipients,
        sections: report.sections,
      });
      setReport(updated);
      setNotice("Reporte guardado.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al guardar");
    } finally {
      setSaving(false);
    }
  }

  async function send() {
    if (!report) return;
    setSending(true);
    setError(null);
    setNotice(null);
    try {
      await sendReport(report.id, {
        recipients: report.recipients,
        subject: sendSubject || report.title,
        include_pdf: false,
      });
      setReport({ ...report, status: "sent", sent_at: new Date().toISOString() });
      setNotice("Reporte enviado.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al enviar");
    } finally {
      setSending(false);
    }
  }

  async function remove() {
    if (!report) return;
    try {
      await deleteReport(report.id);
      onDeleted();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al eliminar");
    }
  }

  if (loading || !report) {
    return (
      <div className="mx-auto max-w-5xl space-y-3">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div className="min-w-0">
          <button
            type="button"
            onClick={onBack}
            className="inline-flex items-center gap-1 text-[11px] text-[var(--text-tertiary)] hover:underline"
          >
            <ArrowLeft className="h-3 w-3" aria-hidden /> Volver al listado
          </button>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <input
              value={report.title}
              onChange={(e) =>
                setReport({ ...report, title: e.target.value })
              }
              disabled={readOnly}
              className={cn(
                "min-w-0 flex-1 border-0 bg-transparent text-2xl font-semibold tracking-tight text-[var(--text-primary)] outline-none focus:outline-none disabled:cursor-not-allowed",
              )}
            />
            <StatusBadge status={report.status} />
            {report.generated_by_ai ? <Badge variant="info">IA</Badge> : null}
          </div>
        </div>
        <div className="flex gap-2">
          {!readOnly ? (
            <>
              <Button variant="ghost" onClick={() => setConfirmDelete(true)}>
                <Trash2 className="h-4 w-4" aria-hidden /> Eliminar
              </Button>
              <Button variant="secondary" loading={saving} onClick={save}>
                Guardar
              </Button>
              <Button loading={sending} onClick={send}>
                <Send className="h-4 w-4" aria-hidden /> Enviar
              </Button>
            </>
          ) : null}
        </div>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}
      {notice ? <Banner variant="success">{notice}</Banner> : null}

      <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-sm)]">
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]">
              Periodo
            </label>
            <Select
              value={report.period ?? ""}
              onChange={(e) =>
                setReport({
                  ...report,
                  period: (e.target.value || null) as ReportPeriod | null,
                })
              }
              disabled={readOnly}
            >
              <option value="">Sin periodo</option>
              <option value="daily">Diario</option>
              <option value="weekly">Semanal</option>
              <option value="monthly">Mensual</option>
            </Select>
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]">
              Destinatarios (emails separados por coma)
            </label>
            <Input
              value={report.recipients.join(", ")}
              onChange={(e) =>
                setReport({
                  ...report,
                  recipients: e.target.value
                    .split(/[,\s]+/)
                    .map((s) => s.trim())
                    .filter(Boolean),
                })
              }
              disabled={readOnly}
            />
          </div>
          <div className="sm:col-span-2">
            <label className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]">
              Asunto al enviar (opcional)
            </label>
            <Input
              value={sendSubject}
              onChange={(e) => setSendSubject(e.target.value)}
              placeholder={report.title}
              disabled={readOnly}
            />
          </div>
        </div>
      </section>

      <section className="space-y-3">
        {sectionKeys.map((k) => (
          <div
            key={k}
            className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--shadow-sm)]"
          >
            <h3 className="mb-2 text-sm font-semibold text-[var(--color-primary)]">
              {SECTION_LABELS[k] ?? k}
            </h3>
            <Textarea
              rows={5}
              value={report.sections[k] ?? ""}
              onChange={(e) =>
                setReport({
                  ...report,
                  sections: { ...report.sections, [k]: e.target.value },
                })
              }
              disabled={readOnly}
              placeholder="Escribe aquí…"
            />
          </div>
        ))}
      </section>

      <Modal
        open={confirmDelete}
        onClose={() => setConfirmDelete(false)}
        title="Eliminar reporte"
      >
        <p className="text-sm text-[var(--color-secondary)]">
          ¿Seguro? El reporte y sus secciones se borrarán permanentemente.
        </p>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="ghost" onClick={() => setConfirmDelete(false)}>
            Cancelar
          </Button>
          <Button variant="danger" onClick={remove}>
            Eliminar
          </Button>
        </div>
      </Modal>
    </div>
  );
}

export default function ReportsPage() {
  return (
    <Suspense
      fallback={
        <div className="p-8">
          <Skeleton className="h-10 w-48" />
        </div>
      }
    >
      <ReportsInner />
    </Suspense>
  );
}

// ENH-055 fase 2 — vista Catálogo: solo templates (Avance + Seguimiento)
// con Visualizar/Descargar. Las generaciones se persisten automáticamente
// en Historial (backend US-092). El catálogo NO crece con cada descarga;
// solo se expande cuando se agregan templates nuevos (futuro: IA-creados).
type CatalogTemplate = {
  id: "avance" | "seguimiento";
  title: string;
  description: string;
};

const CATALOG_TEMPLATES: CatalogTemplate[] = [
  {
    id: "avance",
    title: "Reporte de Avance",
    description:
      "Estado del proyecto a una fecha de corte: KPIs, hitos, RAID y avance de tareas.",
  },
  {
    id: "seguimiento",
    title: "Reporte de Seguimiento",
    description:
      "Actividades por responsable en un período de tiempo (1 día, 1 semana, 1 mes).",
  },
];

// ENH-063: opciones canónicas de período. El default 7 = 1 semana.
const PERIOD_OPTIONS = [
  { value: 1, label: "1 día" },
  { value: 7, label: "1 semana" },
  { value: 14, label: "2 semanas" },
  { value: 30, label: "1 mes" },
  { value: 90, label: "3 meses" },
] as const;

function ReportCatalogView({ projectId }: { projectId: string }) {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  // ENH-063: período seleccionado por template card. Cada card mantiene
  // su propio valor (default 7 días = 1 semana).
  const [periodByTemplate, setPeriodByTemplate] = useState<
    Record<string, number>
  >({ avance: 7, seguimiento: 7 });

  async function run(
    template: CatalogTemplate,
    action: "preview" | "download",
  ) {
    const key = `${template.id}-${action}`;
    setBusy(key);
    setError(null);
    const periodDays = periodByTemplate[template.id] ?? 7;
    try {
      if (template.id === "avance") {
        if (action === "preview")
          await previewAvanceTemplate(projectId, undefined, periodDays);
        else await generateAvanceReport(projectId, undefined, periodDays);
      } else {
        if (action === "preview")
          await previewSeguimientoTemplate(projectId, undefined, periodDays);
        else
          await generateSeguimientoReport(
            projectId,
            undefined,
            periodDays,
            periodDays,
          );
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error generando reporte");
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="space-y-3">
      {error ? <Banner variant="danger">{error}</Banner> : null}
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {CATALOG_TEMPLATES.map((t) => (
          <article
            key={t.id}
            className="flex flex-col gap-3 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-sm)]"
          >
            <div className="flex items-start gap-3">
              <div className="flex h-10 w-10 flex-none items-center justify-center rounded-full border border-[var(--border-default)] bg-[var(--color-subtle)] text-[var(--color-tertiary)]">
                <FileText className="h-5 w-5" aria-hidden />
              </div>
              <div className="min-w-0">
                <h3 className="text-sm font-semibold text-[var(--color-primary)]">
                  {t.title}
                </h3>
                <p className="mt-1 text-xs text-[var(--color-tertiary)]">
                  {t.description}
                </p>
              </div>
            </div>
            {/* ENH-063: período antes de los botones. */}
            <label className="flex items-center gap-2 pt-1 text-xs text-[var(--color-secondary)]">
              <span className="font-medium">Período</span>
              <select
                value={periodByTemplate[t.id] ?? 7}
                onChange={(e) =>
                  setPeriodByTemplate((prev) => ({
                    ...prev,
                    [t.id]: Number(e.target.value),
                  }))
                }
                disabled={busy !== null}
                className="rounded-[var(--radius-sm)] border border-[var(--border-default)] bg-[var(--color-surface)] px-2 py-1 text-xs"
              >
                {PERIOD_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </label>
            <div className="flex flex-wrap gap-2 pt-1">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => void run(t, "preview")}
                loading={busy === `${t.id}-preview`}
                disabled={busy !== null && busy !== `${t.id}-preview`}
              >
                <Eye className="h-4 w-4" aria-hidden /> Visualizar
              </Button>
              <Button
                type="button"
                size="sm"
                onClick={() => void run(t, "download")}
                loading={busy === `${t.id}-download`}
                disabled={busy !== null && busy !== `${t.id}-download`}
              >
                <Download className="h-4 w-4" aria-hidden /> Descargar
              </Button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

// ENH-072: ordenamiento configurable de la tabla de historial.
type HistorySortCol = "generated_at" | "report_type" | "generated_by" | "size";
type HistorySortDir = "asc" | "desc" | "none";
type HistorySort = { col: HistorySortCol; dir: HistorySortDir };

const HISTORY_SORT_DEFAULT: HistorySort = { col: "generated_at", dir: "desc" };

function historySortKey(projectId: string): string | null {
  const u = getStoredUser();
  if (!u) return null;
  return `pmo:reports:history-sort:${projectId}:${u.id}`;
}

function loadHistorySort(projectId: string): HistorySort {
  if (typeof window === "undefined") return HISTORY_SORT_DEFAULT;
  const k = historySortKey(projectId);
  if (!k) return HISTORY_SORT_DEFAULT;
  try {
    const raw = window.localStorage.getItem(k);
    if (!raw) return HISTORY_SORT_DEFAULT;
    const parsed = JSON.parse(raw) as HistorySort;
    if (!parsed.col || !parsed.dir) return HISTORY_SORT_DEFAULT;
    return parsed;
  } catch {
    return HISTORY_SORT_DEFAULT;
  }
}

function saveHistorySort(projectId: string, s: HistorySort): void {
  if (typeof window === "undefined") return;
  const k = historySortKey(projectId);
  if (!k) return;
  try {
    window.localStorage.setItem(k, JSON.stringify(s));
  } catch {
    /* ignore */
  }
}

function nextSortDir(d: HistorySortDir): HistorySortDir {
  // 3-state toggle: asc → desc → none → asc
  return d === "asc" ? "desc" : d === "desc" ? "none" : "asc";
}

function sortIndicator(active: boolean, dir: HistorySortDir): string {
  if (!active || dir === "none") return "";
  return dir === "asc" ? " ▲" : " ▼";
}

function sortHistory(
  items: ReportHistoryItem[],
  sort: HistorySort,
): ReportHistoryItem[] {
  if (sort.dir === "none") return items;
  const sign = sort.dir === "asc" ? 1 : -1;
  const cmp = (a: ReportHistoryItem, b: ReportHistoryItem) => {
    let av: string | number | null;
    let bv: string | number | null;
    switch (sort.col) {
      case "generated_at":
        av = a.generated_at;
        bv = b.generated_at;
        break;
      case "report_type":
        av = a.report_type;
        bv = b.report_type;
        break;
      case "generated_by":
        av = a.generated_by_name ?? "";
        bv = b.generated_by_name ?? "";
        break;
      case "size":
        av = a.file_size_bytes ?? -1;
        bv = b.file_size_bytes ?? -1;
        break;
    }
    if (av == null && bv == null) return 0;
    if (av == null) return 1;
    if (bv == null) return -1;
    if (av < bv) return -1 * sign;
    if (av > bv) return 1 * sign;
    return 0;
  };
  return [...items].sort(cmp);
}

// ENH-055 + US-092 — vista Historial.
// ENH-073: KPI summary card con acento pastel + barra de proporción.
function HistoryKPICard({
  label,
  value,
  total,
  tone,
  active,
  onClick,
}: {
  label: string;
  value: number;
  total: number;
  tone: "info" | "success" | "warning" | "neutral";
  active: boolean;
  onClick: () => void;
}) {
  const toneClass =
    tone === "info"
      ? "bg-[var(--color-info-bg)] text-[var(--color-info-fg)] border-[var(--color-info-border)]"
      : tone === "success"
        ? "bg-[var(--color-success-bg)] text-[var(--color-success-fg)] border-[var(--color-success-border)]"
        : tone === "warning"
          ? "bg-[var(--color-warning-bg)] text-[var(--color-warning-fg)] border-[var(--color-warning-border)]"
          : "bg-[var(--color-subtle)] text-[var(--color-secondary)] border-[var(--border-default)]";
  const ratio = total > 0 ? Math.min(100, Math.round((value / total) * 100)) : 0;
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        "flex flex-col gap-2 rounded-[var(--radius-lg)] border p-3 text-left transition-shadow",
        toneClass,
        active
          ? "shadow-[var(--shadow-sm)] ring-2 ring-[var(--color-primary)] ring-offset-1 ring-offset-[var(--color-app)]"
          : "shadow-[var(--shadow-xs)] hover:shadow-[var(--shadow-sm)]",
      )}
    >
      <span className="text-[11px] font-medium uppercase tracking-wide opacity-80">
        {label}
      </span>
      <span className="font-mono text-2xl font-semibold tabular-nums">
        {value}
      </span>
      <div
        className="h-1.5 overflow-hidden rounded-full bg-[var(--color-neutral-0)]/40"
        aria-hidden
      >
        <div
          className="h-full rounded-full bg-current"
          style={{ width: `${ratio}%`, opacity: 0.55 }}
        />
      </div>
    </button>
  );
}

// ENH-073: filtros segmented + búsqueda en historial.
type HistoryBucket = "all" | "avance" | "seguimiento" | "ai_custom";

// BUG-055: label uniforme para todos los tipos de reporte que aparecen en
// el historial. `ai_custom` es el tipo que persiste el endpoint
// `/reports/ai-generate` cuando el usuario activa save_to_history.
function reportTypeLabel(t: string): string {
  if (t === "avance") return "Avance";
  if (t === "seguimiento") return "Seguimiento";
  if (t === "ai_custom") return "IA";
  return t;
}

function ReportHistoryView({ projectId }: { projectId: string }) {
  const [items, setItems] = useState<ReportHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // ENH-072: sort persistido por usuario+proyecto, default generated_at desc.
  const [sort, setSort] = useState<HistorySort>(HISTORY_SORT_DEFAULT);
  // ENH-073: bucket activo + búsqueda inline.
  const [bucket, setBucket] = useState<HistoryBucket>("all");
  const [search, setSearch] = useState("");
  // ENH-081: confirmación de delete (id de la entry en proceso de borrar).
  const [pendingDelete, setPendingDelete] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  async function confirmDelete() {
    if (!pendingDelete) return;
    setDeleting(true);
    try {
      await deleteReportHistory(pendingDelete);
      setItems((prev) => prev.filter((it) => it.id !== pendingDelete));
      setPendingDelete(null);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "No se pudo borrar el reporte",
      );
    } finally {
      setDeleting(false);
    }
  }

  useEffect(() => {
    setSort(loadHistorySort(projectId));
  }, [projectId]);
  useEffect(() => {
    saveHistorySort(projectId, sort);
  }, [projectId, sort]);

  function onHeaderClick(col: HistorySortCol) {
    setSort((prev) =>
      prev.col === col
        ? { col, dir: nextSortDir(prev.dir) }
        : { col, dir: "asc" },
    );
  }

  // ENH-073: counts por bucket — alimentan los KPI cards y los pills.
  const counts = useMemo(() => {
    const c = { all: items.length, avance: 0, seguimiento: 0, ai_custom: 0, week: 0 };
    const weekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
    for (const it of items) {
      if (it.report_type === "avance") c.avance += 1;
      else if (it.report_type === "seguimiento") c.seguimiento += 1;
      else if (it.report_type === "ai_custom") c.ai_custom += 1;
      if (new Date(it.generated_at).getTime() >= weekAgo) c.week += 1;
    }
    return c;
  }, [items]);

  const filteredItems = useMemo(() => {
    const q = search.trim().toLowerCase();
    return items.filter((h) => {
      if (bucket !== "all" && h.report_type !== bucket) return false;
      if (q) {
        const hay = `${h.generated_by_name ?? ""} ${reportTypeLabel(h.report_type)}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [items, bucket, search]);

  const sortedItems = useMemo(
    () => sortHistory(filteredItems, sort),
    [filteredItems, sort],
  );

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    listReportHistory(projectId)
      .then((rows) => {
        if (!cancelled) setItems(rows);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(
            err instanceof ApiError
              ? err.message
              : "No se pudo cargar el historial",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  if (loading) {
    return (
      <section className="space-y-3">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-5">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full rounded-[var(--radius-lg)]" />
          ))}
        </div>
        <section className="space-y-2 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--shadow-sm)]">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </section>
      </section>
    );
  }

  if (error) {
    return <Banner variant="danger">{error}</Banner>;
  }

  if (items.length === 0) {
    return (
      <section className="rounded-[var(--radius-xl)] border border-[var(--color-info-border)] bg-[var(--color-info-bg)] p-10 text-center shadow-[var(--shadow-sm)]">
        <div
          aria-hidden
          className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-[var(--radius-lg)] border border-[var(--color-info-border)] bg-[var(--color-surface)]"
        >
          <CalendarClock className="h-7 w-7 text-[var(--color-info-fg)]" />
        </div>
        <p className="text-sm font-semibold text-[var(--color-info-fg)]">
          Sin historial todavía
        </p>
        <p className="mt-1 text-xs text-[var(--color-secondary)]">
          Genera tu primer reporte de Avance o Seguimiento desde la vista
          Catálogo. Cada generación queda registrada aquí.
        </p>
      </section>
    );
  }

  const bucketTabs: { v: HistoryBucket; label: string; count: number }[] = [
    { v: "all", label: "Todos", count: counts.all },
    { v: "avance", label: "Avance", count: counts.avance },
    { v: "seguimiento", label: "Seguimiento", count: counts.seguimiento },
    { v: "ai_custom", label: "IA", count: counts.ai_custom },
  ];

  return (
    <section className="space-y-3">
      {/* ENH-073: KPI summary cards con acentos pastel — clicables como filtros. */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-5">
        <HistoryKPICard
          label="Total"
          value={counts.all}
          total={counts.all}
          tone="neutral"
          active={bucket === "all"}
          onClick={() => setBucket("all")}
        />
        <HistoryKPICard
          label="Avance"
          value={counts.avance}
          total={counts.all}
          tone="info"
          active={bucket === "avance"}
          onClick={() => setBucket("avance")}
        />
        <HistoryKPICard
          label="Seguimiento"
          value={counts.seguimiento}
          total={counts.all}
          tone="success"
          active={bucket === "seguimiento"}
          onClick={() => setBucket("seguimiento")}
        />
        <HistoryKPICard
          label="IA"
          value={counts.ai_custom}
          total={counts.all}
          tone="warning"
          active={bucket === "ai_custom"}
          onClick={() => setBucket("ai_custom")}
        />
        <HistoryKPICard
          label="Última semana"
          value={counts.week}
          total={counts.all}
          tone="neutral"
          active={false}
          onClick={() => setBucket("all")}
        />
      </div>

      <div className="flex flex-col gap-2 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-3 shadow-[var(--shadow-sm)] sm:flex-row sm:items-center sm:justify-between">
        {/* ENH-073: segmented tabs con pill de conteo. */}
        <div
          role="radiogroup"
          aria-label="Filtro por tipo de reporte"
          className="inline-flex rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-app)] p-0.5"
        >
          {bucketTabs.map((tab) => {
            const active = bucket === tab.v;
            return (
              <button
                key={tab.v}
                type="button"
                role="radio"
                aria-checked={active}
                onClick={() => setBucket(tab.v)}
                className={cn(
                  "flex items-center gap-1.5 rounded-[var(--radius-sm)] px-3 py-1 text-xs font-medium transition-colors",
                  active
                    ? "bg-[var(--color-primary)] text-[var(--color-inverse)]"
                    : "text-[var(--color-secondary)] hover:bg-[var(--color-subtle)]",
                )}
              >
                <span>{tab.label}</span>
                <span
                  className={cn(
                    "rounded-full px-1.5 py-0.5 font-mono text-[10px] tabular-nums",
                    active
                      ? "bg-[var(--color-inverse)]/20 text-[var(--color-inverse)]"
                      : "bg-[var(--color-subtle)] text-[var(--color-tertiary)]",
                  )}
                >
                  {tab.count}
                </span>
              </button>
            );
          })}
        </div>
        {/* ENH-073: búsqueda inline. */}
        <div className="sm:max-w-xs">
          <Input
            type="search"
            placeholder="Buscar por autor o tipo…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {sortedItems.length === 0 ? (
        <section className="rounded-[var(--radius-xl)] border border-[var(--color-warning-border)] bg-[var(--color-warning-bg)] p-8 text-center shadow-[var(--shadow-sm)]">
          <div
            aria-hidden
            className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-[var(--radius-lg)] border border-[var(--color-warning-border)] bg-[var(--color-surface)]"
          >
            <Eye className="h-6 w-6 text-[var(--color-warning-fg)]" />
          </div>
          <p className="text-sm font-semibold text-[var(--color-warning-fg)]">
            Sin coincidencias
          </p>
          <p className="mt-1 text-xs text-[var(--color-secondary)]">
            Ajusta los filtros o la búsqueda para ver resultados.
          </p>
        </section>
      ) : (
    <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]">
      <table className="w-full text-sm">
        <thead className="border-b border-[var(--border-default)] text-left text-xs uppercase tracking-wide text-[var(--color-tertiary)]">
          <tr>
            {(
              [
                ["generated_at", "Fecha"],
                ["report_type", "Tipo"],
                ["generated_by", "Generado por"],
                ["size", "Tamaño"],
              ] as const
            ).map(([col, label]) => {
              const active = sort.col === col;
              return (
                <th key={col} className="px-3 py-2 font-medium">
                  <button
                    type="button"
                    onClick={() => onHeaderClick(col)}
                    className={`flex items-center gap-1 hover:text-[var(--color-primary)] ${
                      active && sort.dir !== "none"
                        ? "text-[var(--color-primary)]"
                        : ""
                    }`}
                    aria-sort={
                      active && sort.dir !== "none"
                        ? sort.dir === "asc"
                          ? "ascending"
                          : "descending"
                        : "none"
                    }
                  >
                    <span>{label}</span>
                    <span aria-hidden className="text-[10px]">
                      {sortIndicator(active, sort.dir)}
                    </span>
                  </button>
                </th>
              );
            })}
            <th className="w-32 px-3 py-2 font-medium" aria-label="Acciones" />
          </tr>
        </thead>
        <tbody>
          {sortedItems.map((h) => (
            <tr
              key={h.id}
              className="border-b border-[var(--border-subtle)] hover:bg-[var(--color-subtle)]"
            >
              <td className="px-3 py-2 text-xs tabular-nums text-[var(--color-secondary)]">
                {new Date(h.generated_at).toLocaleString("es-MX", {
                  dateStyle: "short",
                  timeStyle: "short",
                })}
              </td>
              <td className="px-3 py-2">
                <Badge variant="neutral">
                  {reportTypeLabel(h.report_type)}
                </Badge>
              </td>
              <td className="px-3 py-2 text-xs text-[var(--color-secondary)]">
                {h.generated_by_name ?? "—"}
              </td>
              <td className="px-3 py-2 text-xs tabular-nums text-[var(--color-tertiary)]">
                {h.file_size_bytes != null
                  ? `${Math.max(1, Math.round(h.file_size_bytes / 1024))} KB`
                  : "—"}
              </td>
              <td className="px-3 py-2 text-right">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => previewReportHistory(h.id).catch(() => {})}
                  title="Ver PDF"
                >
                  <Eye className="h-4 w-4" aria-hidden />
                </Button>
                {/* US-111 rework: ver el HTML interactivo (KPIs +
                    filtros vanilla JS embebidos) cuando el reporte
                    fuente lo tiene populado. */}
                {h.source_report_id ? (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() =>
                      previewReportHtml(h.source_report_id as string).catch(() => {})
                    }
                    title="Ver HTML interactivo"
                  >
                    <FileText className="h-4 w-4" aria-hidden />
                  </Button>
                ) : null}
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => downloadReportHistory(h.id).catch(() => {})}
                  title="Descargar"
                >
                  <Download className="h-4 w-4" aria-hidden />
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setPendingDelete(h.id)}
                  title="Borrar"
                  aria-label="Borrar este reporte"
                >
                  <Trash2 className="h-4 w-4" aria-hidden />
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
      )}
      {/* ENH-081: Modal de confirmación para borrar reporte. */}
      <Modal
        open={pendingDelete !== null}
        onClose={() => (deleting ? null : setPendingDelete(null))}
        title="Borrar reporte"
      >
        <div className="space-y-3">
          <p className="text-sm text-[var(--color-secondary)]">
            ¿Borrar este reporte del historial? Esta acción no se puede
            deshacer.
          </p>
          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="ghost"
              onClick={() => setPendingDelete(null)}
              disabled={deleting}
            >
              Cancelar
            </Button>
            <Button
              type="button"
              variant="danger"
              onClick={confirmDelete}
              loading={deleting}
              disabled={deleting}
            >
              Borrar
            </Button>
          </div>
        </div>
      </Modal>
    </section>
  );
}

// ENH-071/ENH-084: filtros del reporte IA. ENH-084 agrega `area_ids`
// (multi-select) — el backend ya lo aceptaba; faltaba en UI.
type AIReportFilters = {
  date_from: string;
  date_to: string;
  area_ids: string[];
  criticalities: string[];
  statuses: string[];
  severities: string[];
};

const EMPTY_FILTERS: AIReportFilters = {
  date_from: "",
  date_to: "",
  area_ids: [],
  criticalities: [],
  statuses: [],
  severities: [],
};

const CRITICALITY_OPTS = ["low", "medium", "high", "critical"] as const;
const STATUS_OPTS = ["not_started", "in_progress", "done"] as const;
const SEVERITY_OPTS = ["low", "medium", "high", "critical"] as const;

const STATUS_LABEL: Record<string, string> = {
  not_started: "No iniciada",
  in_progress: "En curso",
  done: "Hecha",
};

function filtersStorageKey(projectId: string): string | null {
  const u = getStoredUser();
  if (!u) return null;
  return `pmo:reports:filters:${projectId}:${u.id}`;
}

function loadFilters(projectId: string): AIReportFilters {
  if (typeof window === "undefined") return EMPTY_FILTERS;
  const k = filtersStorageKey(projectId);
  if (!k) return EMPTY_FILTERS;
  try {
    const raw = window.localStorage.getItem(k);
    if (!raw) return EMPTY_FILTERS;
    return { ...EMPTY_FILTERS, ...JSON.parse(raw) };
  } catch {
    return EMPTY_FILTERS;
  }
}

function saveFilters(projectId: string, f: AIReportFilters): void {
  if (typeof window === "undefined") return;
  const k = filtersStorageKey(projectId);
  if (!k) return;
  try {
    window.localStorage.setItem(k, JSON.stringify(f));
  } catch {
    /* ignore quota errors */
  }
}

function activeFilterCount(f: AIReportFilters): number {
  return (
    (f.date_from ? 1 : 0) +
    (f.date_to ? 1 : 0) +
    f.area_ids.length +
    f.criticalities.length +
    f.statuses.length +
    f.severities.length
  );
}

function FilterChips<T extends string>({
  label,
  options,
  selected,
  onToggle,
  labelMap,
}: {
  label: string;
  options: readonly T[];
  selected: string[];
  onToggle: (v: T) => void;
  labelMap?: Record<string, string>;
}) {
  return (
    <div>
      <p className="mb-1 text-xs font-medium text-[var(--color-secondary)]">
        {label}
      </p>
      <div className="flex flex-wrap gap-1">
        {options.map((opt) => {
          const active = selected.includes(opt);
          return (
            <button
              key={opt}
              type="button"
              onClick={() => onToggle(opt)}
              className={`rounded-[var(--radius-sm)] border px-2 py-0.5 text-xs transition ${
                active
                  ? "border-[var(--color-accent)] bg-[var(--color-accent)] text-white"
                  : "border-[var(--border-default)] bg-[var(--color-surface)] text-[var(--color-secondary)] hover:bg-[var(--color-subtle)]"
              }`}
            >
              {labelMap?.[opt] ?? opt}
            </button>
          );
        })}
      </div>
    </div>
  );
}

// US-093 — vista Creación con IA + preview.
function ReportCreateAIView({ projectId }: { projectId: string }) {
  const [base, setBase] = useState<"avance" | "seguimiento" | "custom">("avance");
  const [includeKpis, setIncludeKpis] = useState(true);
  const [includeTasks, setIncludeTasks] = useState(true);
  const [includeRaid, setIncludeRaid] = useState(true);
  const [includeMilestones, setIncludeMilestones] = useState(true);
  const [freeNotes, setFreeNotes] = useState("");
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewHtml, setPreviewHtml] = useState<string | null>(null);
  const [savingHistory, setSavingHistory] = useState(false);
  const [savedHistoryId, setSavedHistoryId] = useState<string | null>(null);

  // ENH-071: filtros configurables persistidos por usuario.
  const [filters, setFilters] = useState<AIReportFilters>(EMPTY_FILTERS);
  useEffect(() => {
    setFilters(loadFilters(projectId));
  }, [projectId]);
  useEffect(() => {
    saveFilters(projectId, filters);
  }, [projectId, filters]);

  function toggleArr<K extends keyof AIReportFilters>(key: K, v: string) {
    setFilters((prev) => {
      const cur = prev[key] as string[];
      const next = cur.includes(v) ? cur.filter((x) => x !== v) : [...cur, v];
      return { ...prev, [key]: next } as AIReportFilters;
    });
  }

  const filterCount = activeFilterCount(filters);

  // ENH-084 — listado de áreas del proyecto para el filtro multi-select.
  const [projectAreas, setProjectAreas] = useState<Area[]>([]);
  useEffect(() => {
    let cancelled = false;
    listAreasByProject(projectId)
      .then((rows) => {
        if (!cancelled) setProjectAreas(rows);
      })
      .catch(() => {
        /* opcional — si falla, simplemente no mostramos chips de área. */
      });
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  // ENH-080 — plantillas reusables del reporte IA.
  const [templates, setTemplates] = useState<AIReportTemplate[]>([]);
  const [templateName, setTemplateName] = useState("");
  const [savingTemplate, setSavingTemplate] = useState(false);
  const [templateError, setTemplateError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listAIReportTemplates(projectId)
      .then((rows) => {
        if (!cancelled) setTemplates(rows);
      })
      .catch(() => {
        /* lista de plantillas opcional — fallar silenciosamente. */
      });
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  function applyTemplate(t: AIReportTemplate) {
    setBase(t.base);
    const c = t.config ?? {};
    setIncludeKpis(c.include_kpis ?? true);
    setIncludeTasks(c.include_tasks ?? true);
    setIncludeRaid(c.include_raid ?? true);
    setIncludeMilestones(c.include_milestones ?? true);
    setFreeNotes(c.free_notes ?? "");
    setFilters({
      ...EMPTY_FILTERS,
      date_from: c.date_from ?? "",
      date_to: c.date_to ?? "",
      area_ids: c.area_ids ?? [],
      criticalities: c.criticalities ?? [],
      statuses: c.statuses ?? [],
      severities: c.severities ?? [],
    });
  }

  async function saveAsTemplate() {
    const name = templateName.trim();
    if (!name) {
      setTemplateError("Ingresa un nombre para la plantilla.");
      return;
    }
    setSavingTemplate(true);
    setTemplateError(null);
    try {
      const tpl = await createAIReportTemplate(projectId, {
        name,
        base,
        config: {
          include_kpis: includeKpis,
          include_tasks: includeTasks,
          include_raid: includeRaid,
          include_milestones: includeMilestones,
          free_notes: freeNotes,
          date_from: filters.date_from || null,
          date_to: filters.date_to || null,
          area_ids: filters.area_ids.length ? filters.area_ids : null,
          criticalities: filters.criticalities.length ? filters.criticalities : null,
          statuses: filters.statuses.length ? filters.statuses : null,
          severities: filters.severities.length ? filters.severities : null,
        },
      });
      setTemplates((prev) => [tpl, ...prev]);
      setTemplateName("");
    } catch (err) {
      setTemplateError(
        err instanceof ApiError ? err.message : "No se pudo guardar la plantilla",
      );
    } finally {
      setSavingTemplate(false);
    }
  }

  async function removeTemplate(id: string) {
    try {
      await deleteAIReportTemplate(id);
      setTemplates((prev) => prev.filter((t) => t.id !== id));
    } catch (err) {
      setTemplateError(
        err instanceof ApiError ? err.message : "No se pudo borrar la plantilla",
      );
    }
  }

  async function generate(saveToHistory: boolean) {
    if (saveToHistory) setSavingHistory(true);
    else setGenerating(true);
    setError(null);
    try {
      const res = await aiGenerateReport(projectId, {
        base,
        include_kpis: includeKpis,
        include_tasks: includeTasks,
        include_raid: includeRaid,
        include_milestones: includeMilestones,
        free_notes: freeNotes,
        save_to_history: saveToHistory,
        // ENH-071/ENH-084: filtros enviados al backend.
        date_from: filters.date_from || null,
        date_to: filters.date_to || null,
        area_ids: filters.area_ids.length ? filters.area_ids : null,
        criticalities: filters.criticalities.length ? filters.criticalities : null,
        statuses: filters.statuses.length ? filters.statuses : null,
        severities: filters.severities.length ? filters.severities : null,
      });
      setPreviewHtml(res.html);
      setSavedHistoryId(res.history_id);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "No se pudo generar el reporte",
      );
    } finally {
      setGenerating(false);
      setSavingHistory(false);
    }
  }

  function downloadHtmlAsFile() {
    if (!previewHtml) return;
    const blob = new Blob([previewHtml], { type: "text/html;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `Reporte-IA-${new Date().toISOString().slice(0, 10)}.html`;
    a.click();
  }

  return (
    <div className="space-y-4">
      {/* US-109 (rework): banner que redirige al panel con 2 modos
          (nuevo desde data del proyecto / desde plantilla guardada) +
          tweaker IA HTML iterativo. El form clásico de abajo queda
          como atajo para reportes guiados. */}
      <section className="flex flex-wrap items-center justify-between gap-3 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-subtle)]/40 p-4 shadow-[var(--shadow-sm)]">
        <div>
          <h2 className="flex items-center gap-2 text-sm font-semibold text-[var(--color-primary)]">
            <Sparkles className="h-4 w-4" aria-hidden />
            Crear reporte con tweaker IA HTML
          </h2>
          <p className="mt-1 text-xs text-[var(--color-tertiary)]">
            Elige punto de partida (data del proyecto o plantilla
            guardada) y modifícalo iterativamente con instrucciones IA.
          </p>
        </div>
        <Link href={`/pmo/projects/${projectId}/reports/tweak`}>
          <Button>
            Empezar — elegir modo
          </Button>
        </Link>
      </section>

    <div className="grid gap-4 lg:grid-cols-[360px_1fr]">
      <section className="space-y-3 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--shadow-sm)]">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-[var(--color-primary)]">
          <Sparkles className="h-4 w-4" aria-hidden />
          Creación con IA (clásico)
        </h2>
        <p className="text-xs text-[var(--color-tertiary)]">
          La IA del tenant arma un reporte custom combinando datos del
          proyecto con tus instrucciones. Si tu tenant no tiene IA
          configurada, este panel se rechaza con error claro.
        </p>
        {error ? <Banner variant="danger">{error}</Banner> : null}
        <div>
          <label className="mb-1 block text-xs font-medium text-[var(--color-secondary)]">
            Tipo base
          </label>
          <Select
            value={base}
            onChange={(e) =>
              setBase(e.target.value as "avance" | "seguimiento" | "custom")
            }
          >
            <option value="avance">Avance</option>
            <option value="seguimiento">Seguimiento</option>
            <option value="custom">Personalizado</option>
          </Select>
        </div>
        <fieldset className="space-y-1.5">
          <legend className="mb-1 text-xs font-medium text-[var(--color-secondary)]">
            Secciones a incluir
          </legend>
          {(
            [
              ["KPIs", includeKpis, setIncludeKpis] as const,
              ["Tareas", includeTasks, setIncludeTasks] as const,
              ["RAID (riesgos / incidencias)", includeRaid, setIncludeRaid] as const,
              ["Hitos", includeMilestones, setIncludeMilestones] as const,
            ]
          ).map(([label, checked, set]) => (
            <label key={label} className="flex items-center gap-2 text-xs">
              <input
                type="checkbox"
                checked={checked}
                onChange={(e) => set(e.target.checked)}
              />
              <span>{label}</span>
            </label>
          ))}
        </fieldset>
        {/* ENH-071: filtros configurables sobre el listado del reporte. */}
        <fieldset className="space-y-2 rounded-[var(--radius-md)] border border-[var(--border-subtle)] p-2">
          <legend className="flex items-center gap-1.5 px-1 text-xs font-medium text-[var(--color-secondary)]">
            <span>Filtros</span>
            {filterCount > 0 ? (
              <span className="rounded-full bg-[var(--color-accent)] px-1.5 py-0.5 text-[10px] font-semibold text-white">
                {filterCount}
              </span>
            ) : null}
            {filterCount > 0 ? (
              <button
                type="button"
                onClick={() => setFilters(EMPTY_FILTERS)}
                className="ml-auto text-[10px] uppercase tracking-wide text-[var(--color-tertiary)] hover:text-[var(--color-primary)]"
              >
                Limpiar
              </button>
            ) : null}
          </legend>
          <div className="grid grid-cols-2 gap-2">
            <label className="text-xs">
              <span className="mb-1 block text-[var(--color-tertiary)]">
                Desde
              </span>
              <Input
                type="date"
                value={filters.date_from}
                onChange={(e) =>
                  setFilters((p) => ({ ...p, date_from: e.target.value }))
                }
              />
            </label>
            <label className="text-xs">
              <span className="mb-1 block text-[var(--color-tertiary)]">
                Hasta
              </span>
              <Input
                type="date"
                value={filters.date_to}
                onChange={(e) =>
                  setFilters((p) => ({ ...p, date_to: e.target.value }))
                }
              />
            </label>
          </div>
          {/* ENH-084: chip multi-select de áreas del proyecto. */}
          {projectAreas.length > 0 ? (
            <FilterChips
              label="Área"
              options={projectAreas.map((a) => a.id)}
              selected={filters.area_ids}
              onToggle={(v) => toggleArr("area_ids", v)}
              labelMap={Object.fromEntries(
                projectAreas.map((a) => [a.id, a.name]),
              )}
            />
          ) : null}
          <FilterChips
            label="Criticidad (tareas)"
            options={CRITICALITY_OPTS}
            selected={filters.criticalities}
            onToggle={(v) => toggleArr("criticalities", v)}
          />
          <FilterChips
            label="Status (tareas / issues)"
            options={STATUS_OPTS}
            selected={filters.statuses}
            onToggle={(v) => toggleArr("statuses", v)}
            labelMap={STATUS_LABEL}
          />
          <FilterChips
            label="Severidad (riesgos)"
            options={SEVERITY_OPTS}
            selected={filters.severities}
            onToggle={(v) => toggleArr("severities", v)}
          />
        </fieldset>
        <div>
          <label className="mb-1 block text-xs font-medium text-[var(--color-secondary)]">
            Instrucciones adicionales
          </label>
          {/* ENH-085: aclarar la división filtros vs instrucciones. */}
          <p className="mb-1.5 text-[11px] text-[var(--color-tertiary)]">
            Para filtrar por dato (área, severidad, fechas) usa los filtros
            arriba — la IA los respeta automáticamente. Aquí escribe tono,
            segmentaciones específicas o exclusiones puntuales.
          </p>
          <Textarea
            rows={4}
            value={freeNotes}
            onChange={(e) => setFreeNotes(e.target.value)}
            placeholder="Tono ejecutivo. Énfasis en hitos del Q2. NO incluyas el presupuesto."
          />
        </div>
        {/* ENH-080: plantillas reusables — guardar config + cargar/borrar. */}
        <fieldset className="space-y-2 rounded-[var(--radius-md)] border border-[var(--border-subtle)] p-2">
          <legend className="px-1 text-xs font-medium text-[var(--color-secondary)]">
            Plantillas guardadas
          </legend>
          {templateError ? (
            <p className="text-xs text-[var(--color-danger-fg)]">{templateError}</p>
          ) : null}
          <div className="flex gap-1.5">
            <Input
              type="text"
              value={templateName}
              onChange={(e) => setTemplateName(e.target.value)}
              placeholder="Nombre de la plantilla"
              maxLength={120}
            />
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={saveAsTemplate}
              loading={savingTemplate}
              disabled={savingTemplate || !templateName.trim()}
            >
              Guardar
            </Button>
          </div>
          {templates.length > 0 ? (
            <ul className="space-y-1">
              {templates.map((t) => (
                <li
                  key={t.id}
                  className="flex items-center gap-1.5 rounded-[var(--radius-sm)] border border-[var(--border-subtle)] bg-[var(--color-app)] px-2 py-1.5"
                >
                  <button
                    type="button"
                    onClick={() => applyTemplate(t)}
                    className="flex-1 truncate text-left text-xs font-medium text-[var(--color-primary)] hover:underline"
                    title="Cargar configuración de esta plantilla"
                  >
                    {t.name}
                  </button>
                  <span className="rounded-full bg-[var(--color-surface)] px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-[var(--color-tertiary)]">
                    {t.base}
                  </span>
                  <button
                    type="button"
                    onClick={() => removeTemplate(t.id)}
                    className="text-[var(--color-tertiary)] hover:text-[var(--color-danger-fg)]"
                    title="Borrar plantilla"
                    aria-label={`Borrar plantilla ${t.name}`}
                  >
                    <Trash2 className="h-3.5 w-3.5" aria-hidden />
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-[11px] text-[var(--color-tertiary)]">
              Aún no guardas ninguna plantilla para este proyecto.
            </p>
          )}
        </fieldset>
        <div className="flex flex-col gap-2">
          <Button
            type="button"
            onClick={() => generate(false)}
            loading={generating}
            disabled={generating || savingHistory}
          >
            <Sparkles className="h-4 w-4" aria-hidden />
            Generar con IA
          </Button>
          {previewHtml ? (
            <>
              <Button
                type="button"
                variant="secondary"
                onClick={downloadHtmlAsFile}
                disabled={savingHistory}
              >
                <Download className="h-4 w-4" aria-hidden />
                Descargar HTML
              </Button>
              <Button
                type="button"
                variant="secondary"
                onClick={() => generate(true)}
                loading={savingHistory}
                disabled={savedHistoryId !== null}
              >
                {savedHistoryId
                  ? "Guardado en historial"
                  : "Guardar en Historial"}
              </Button>
            </>
          ) : null}
        </div>
      </section>

      <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]">
        {previewHtml ? (
          <iframe
            title="Vista previa del reporte IA"
            srcDoc={previewHtml}
            className="h-[640px] w-full rounded-[var(--radius-xl)]"
          />
        ) : (
          <div className="flex h-[400px] flex-col items-center justify-center gap-2 p-10 text-center text-sm text-[var(--color-tertiary)]">
            <Sparkles className="h-8 w-8" aria-hidden />
            <p>Configura el reporte y pulsa "Generar con IA" para ver la preview.</p>
          </div>
        )}
      </section>
    </div>
    </div>
  );
}

// ENH-114 — picker de plantillas del Report Builder para el form de
// suscripciones (cuando report_type='custom').
function BuilderTemplatePicker({
  projectId,
  value,
  onChange,
}: {
  projectId: string;
  value: string | null;
  onChange: (id: string | null) => void;
}) {
  const [tpls, setTpls] = useState<ReportBuilderTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let cancelled = false;
    listBuilderTemplates({})
      .then((all) => {
        if (cancelled) return;
        // Mostrar seeds + propias + del proyecto activo.
        setTpls(
          all.filter(
            (t) =>
              t.is_seed ||
              t.visibility === "private" ||
              (t.visibility === "project" && t.project_id === projectId),
          ),
        );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  return (
    <div>
      <label
        htmlFor="sched-builder-tpl"
        className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
      >
        Plantilla del Builder
      </label>
      <Select
        id="sched-builder-tpl"
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value || null)}
        disabled={loading || tpls.length === 0}
      >
        <option value="">
          {loading
            ? "Cargando…"
            : tpls.length === 0
              ? "Sin plantillas disponibles"
              : "Selecciona plantilla…"}
        </option>
        {tpls.map((t) => (
          <option key={t.id} value={t.id}>
            {t.name} {t.is_seed ? "(seed)" : ""} · L{t.level}
          </option>
        ))}
      </Select>
      {!loading && tpls.length === 0 && (
        <p className="mt-1 text-xs text-[var(--color-tertiary)]">
          Abre el Report Builder y guarda una plantilla antes de programar.
        </p>
      )}
    </div>
  );
}

// US-141 — vista Builder: lista solo reportes generados desde el Report
// Builder (generator='builder') con acción "Regenerar PDF" desde
// snapshot (US-140).
function ReportBuilderView({ projectId }: { projectId: string }) {
  const [rows, setRows] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [regeneratingId, setRegeneratingId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    listReports(projectId)
      .then((all) => {
        if (cancelled) return;
        setRows(all.filter((r) => r.generator === "builder"));
      })
      .catch((err) => {
        if (!cancelled)
          setError(
            err instanceof ApiError ? err.message : "Error al cargar reportes",
          );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  async function regenerate(reportId: string) {
    setRegeneratingId(reportId);
    try {
      const blob = await regenerateBuilderPdf(reportId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `reporte-${reportId}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al regenerar PDF");
    } finally {
      setRegeneratingId(null);
    }
  }

  return (
    <section className="rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--color-surface)] p-5">
      <header className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-[var(--text-primary)]">
            Reportes del Builder
          </h2>
          <p className="mt-0.5 text-xs text-[var(--text-tertiary)]">
            Cada export desde `/reports/builder` o cada ejecución de
            una suscripción custom (US-131) queda registrado aquí. El
            PDF se regenera desde el snapshot HTML — el contenido se
            preserva aunque la data del proyecto cambie después.
          </p>
        </div>
        <Link
          href={`/pmo/projects/${projectId}/reports/builder`}
          className="text-xs text-[var(--text-secondary)] hover:underline"
        >
          Abrir builder →
        </Link>
      </header>

      {error && <Banner variant="danger">{error}</Banner>}

      {loading ? (
        <div className="space-y-2">
          <Skeleton className="h-12" />
          <Skeleton className="h-12" />
        </div>
      ) : rows.length === 0 ? (
        <div className="rounded-[var(--radius-md)] border border-dashed border-[var(--border-default)] p-6 text-center text-sm text-[var(--text-tertiary)]">
          Sin reportes generados aún. Abre el Report Builder, configura
          tu plantilla y descarga el PDF para que aparezca aquí.
        </div>
      ) : (
        <ul className="divide-y divide-[var(--border-subtle)]">
          {rows.map((r) => (
            <li
              key={r.id}
              className="flex items-center justify-between gap-3 py-2"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-[var(--text-primary)]">
                  {r.title}
                </p>
                <p className="mt-0.5 flex flex-wrap items-center gap-2 text-[11px] text-[var(--text-tertiary)]">
                  <Badge variant="accent">Builder</Badge>
                  <span>{r.cut_off_date ?? "—"}</span>
                  <span>·</span>
                  <span>{new Date(r.created_at).toLocaleString("es-MX")}</span>
                  {r.status === "sent" && (
                    <Badge variant="success">Enviado</Badge>
                  )}
                </p>
              </div>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => regenerate(r.id)}
                loading={regeneratingId === r.id}
                disabled={!!regeneratingId}
              >
                <Download className="mr-1 h-3.5 w-3.5" /> Regenerar PDF
              </Button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
