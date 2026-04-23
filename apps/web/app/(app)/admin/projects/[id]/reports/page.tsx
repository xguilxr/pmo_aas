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
import { draftReport, sendReport } from "@/lib/api/ai";
import { useAIJobPolling } from "@/lib/hooks/use-ai-job-polling";
import {
  PERIOD_LABEL,
  SECTION_LABELS,
  createReport,
  deleteReport,
  downloadAvanceReport,
  downloadSeguimientoReport,
  generateAvanceReport,
  generateSeguimientoReport,
  getReport,
  listReports,
  previewAvanceReport,
  previewSeguimientoReport,
  updateReport,
  type Report,
  type ReportPeriod,
} from "@/lib/api/reports";
import {
  CADENCE_LABEL,
  REPORT_TYPE_LABEL,
  createScheduledReport,
  deleteScheduledReport,
  listScheduledReports,
  updateScheduledReport,
  type ScheduledReport,
  type ScheduledReportCadence,
  type ScheduledReportType,
} from "@/lib/api/scheduled-reports";
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
  return null;
}

function GeneratedReportActions({ report }: { report: Report }) {
  const [busy, setBusy] = useState<"preview" | "download" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const isAvance = report.generator === "avance";
  const isSeguimiento = report.generator === "seguimiento";
  if (!isAvance && !isSeguimiento) return null;

  async function run(kind: "preview" | "download") {
    setBusy(kind);
    setError(null);
    try {
      if (kind === "preview") {
        await (isAvance
          ? previewAvanceReport(report.id)
          : previewSeguimientoReport(report.id));
      } else {
        await (isAvance
          ? downloadAvanceReport(report.id)
          : downloadSeguimientoReport(report.id));
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="flex items-center gap-1">
      <Button
        type="button"
        variant="ghost"
        size="sm"
        aria-label="Preview PDF"
        title="Preview PDF en el navegador"
        loading={busy === "preview"}
        disabled={busy !== null}
        onClick={(e) => {
          e.stopPropagation();
          void run("preview");
        }}
      >
        <Eye className="h-4 w-4" aria-hidden />
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        aria-label="Descargar PDF"
        title="Descargar PDF"
        loading={busy === "download"}
        disabled={busy !== null}
        onClick={(e) => {
          e.stopPropagation();
          void run("download");
        }}
      >
        <Download className="h-4 w-4" aria-hidden />
      </Button>
      {error ? (
        <span className="text-[11px] text-[var(--color-danger-fg)]">{error}</span>
      ) : null}
    </div>
  );
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
    router.replace(`/admin/projects/${id}/reports?${params.toString()}`);
  }
  function closeEditor() {
    const params = new URLSearchParams(searchParams.toString());
    params.delete("report");
    const qs = params.toString();
    router.replace(
      qs ? `/admin/projects/${id}/reports?${qs}` : `/admin/projects/${id}/reports`,
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
            <Link href="/admin/projects" className="hover:underline">
              Proyectos
            </Link>
            <span className="mx-1">/</span>
            <Link href={`/admin/projects/${id}`} className="hover:underline">
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
        <div className="flex flex-wrap gap-2">
          <GenerateAvanceButton projectId={id} onDone={() => void refresh()} />
          <GenerateSeguimientoButton projectId={id} onDone={() => void refresh()} />
          <GenerateWithAIButton projectId={id} onCreated={openReport} />
          <Button onClick={() => setCreateOpen(true)}>
            <Plus className="h-4 w-4" aria-hidden /> Nuevo reporte
          </Button>
        </div>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]">
        {loading ? (
          <div className="space-y-2 p-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        ) : rows.length === 0 ? (
          <div className="p-10 text-center text-sm text-[var(--color-tertiary)]">
            Aún no hay reportes. Crea el primero manualmente o con IA.
          </div>
        ) : (
          <ul className="divide-y divide-[var(--border-subtle)]">
            {rows.map((r) => (
              <li
                key={r.id}
                className="flex items-center gap-3 px-4 py-3 hover:bg-[var(--color-subtle)]"
              >
                <div className="flex h-9 w-9 flex-none items-center justify-center rounded-full border border-[var(--border-default)] bg-[var(--color-subtle)] text-[var(--color-tertiary)]">
                  <FileText className="h-4 w-4" aria-hidden />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      onClick={() => openReport(r.id)}
                      className="truncate text-left text-sm font-medium text-[var(--color-primary)] hover:underline"
                    >
                      {r.title}
                    </button>
                    <StatusBadge status={r.status} />
                    <GeneratorBadge generator={r.generator} />
                    {r.generated_by_ai ? (
                      <Badge variant="info">IA</Badge>
                    ) : null}
                    {r.period ? (
                      <Badge variant="neutral">
                        {PERIOD_LABEL[r.period as ReportPeriod] ?? r.period}
                      </Badge>
                    ) : null}
                  </div>
                  <div className="mt-0.5 flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-[var(--color-tertiary)]">
                    <span>Creado {fmtDate(r.created_at)}</span>
                    {r.sent_at ? (
                      <span>Enviado {fmtDate(r.sent_at)}</span>
                    ) : null}
                    {r.recipients.length > 0 ? (
                      <span className="inline-flex items-center gap-1">
                        <Mail className="h-3 w-3" aria-hidden />
                        {r.recipients.length} destinatarios
                      </span>
                    ) : null}
                  </div>
                </div>
                <GeneratedReportActions report={r} />
              </li>
            ))}
          </ul>
        )}
      </section>

      <ScheduledReportsSection projectId={id} />

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
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    if (existing) {
      setReportType(existing.report_type);
      setCadence(existing.cadence);
      setRecipients(existing.recipients.join(", "));
      setEnabled(existing.enabled);
    } else {
      setReportType("avance");
      setCadence("weekly");
      setRecipients("");
      setEnabled(true);
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
      if (existing) {
        await updateScheduledReport(existing.id, {
          report_type: reportType,
          cadence,
          recipients: list,
          enabled,
        });
      } else {
        await createScheduledReport(projectId, {
          report_type: reportType,
          cadence,
          recipients: list,
          enabled,
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
          </Select>
        </div>
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
          </Select>
        </div>
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
