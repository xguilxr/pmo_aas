"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Download, Eye, MessageSquare, Sparkles, Trash2 } from "lucide-react";

import { ItemPreviewModal } from "@/components/item-preview-modal";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { ModuleShell } from "@/components/module-shell";
import { ApiError } from "@/lib/api";
import {
  deleteMinute,
  exportMinute,
  listMinutes,
  type MeetingMinute,
  type MinuteExportFormat,
} from "@/lib/api/modules";

export default function MinutesPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [rows, setRows] = useState<MeetingMinute[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<MeetingMinute | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<MeetingMinute | null>(null);
  const [deleting, setDeleting] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setRows(await listMinutes(id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron cargar las minutas");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function handleDelete() {
    if (!confirmDelete) return;
    setDeleting(true);
    try {
      await deleteMinute(confirmDelete.id);
      setConfirmDelete(null);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo borrar la minuta");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <>
    <ModuleShell<MeetingMinute>
      projectId={id}
      title="Minutas"
      subtitle="Minutas de reunión con temas, participantes y acuerdos."
      icon={<MessageSquare className="h-5 w-5" aria-hidden />}
      records={rows}
      loading={loading}
      error={error}
      headerExtras={
        // ENH-117 + US-142: un solo botón "Generar Minuta" → minutes/new
        // (generador unificado con 3 modos: transcript / minuta / manual).
        <Link
          href={`/pmo/projects/${id}/minutes/new`}
          title="Genera una minuta nueva desde transcript, minuta existente, o llenado manual."
        >
          <Button>
            <Sparkles className="h-4 w-4" aria-hidden /> Generar Minuta
          </Button>
        </Link>
      }
      onRowClick={(r) => router.push(`/pmo/projects/${id}/minutes/${r.id}`)}
      columns={[
        {
          key: "title",
          label: "Minuta",
          render: (r) => (
            <div>
              <p className="font-medium">{r.title}</p>
              <p className="text-[11px] text-[var(--text-tertiary)]">
                {r.participants.length} participantes · {r.topics.length} temas ·{" "}
                {r.agreements.length} acuerdos
              </p>
            </div>
          ),
        },
        {
          key: "date",
          label: "Fecha",
          render: (r) => new Date(r.meeting_date).toLocaleDateString("es-MX"),
        },
        {
          key: "type",
          label: "Tipo",
          render: (r) =>
            r.generated_by_ai ? (
              <Badge variant="info">IA</Badge>
            ) : (
              <Badge variant="neutral">Manual</Badge>
            ),
        },
        {
          key: "export",
          label: "Exportar",
          render: (r) => <ExportMinuteButtons minuteId={r.id} />,
        },
        {
          key: "eye",
          label: "",
          render: (r) => (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setPreview(r);
              }}
              aria-label={`Preview ${r.title}`}
              title="Vista rápida"
              className="inline-flex h-7 w-7 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-tertiary)] hover:bg-[var(--color-subtle)] hover:text-[var(--color-primary)]"
            >
              <Eye className="h-3.5 w-3.5" aria-hidden />
            </button>
          ),
        },
        {
          key: "actions",
          label: "",
          render: (r) => (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setConfirmDelete(r);
              }}
              aria-label={`Borrar ${r.title}`}
              title="Borrar minuta"
              className="inline-flex h-7 w-7 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-tertiary)] hover:bg-[var(--color-danger-bg)] hover:text-[var(--color-danger-fg)]"
            >
              <Trash2 className="h-3.5 w-3.5" aria-hidden />
            </button>
          ),
        },
      ]}
    />
    <Modal
      open={confirmDelete !== null}
      onClose={() => !deleting && setConfirmDelete(null)}
      title="¿Borrar minuta?"
      footer={
        <>
          <Button
            variant="secondary"
            onClick={() => setConfirmDelete(null)}
            disabled={deleting}
          >
            Cancelar
          </Button>
          <Button variant="danger" onClick={handleDelete} loading={deleting}>
            <Trash2 className="h-3.5 w-3.5" aria-hidden /> Borrar
          </Button>
        </>
      }
    >
      <p className="text-[13px] text-[var(--text-primary)]">
        ¿Borrar minuta <strong>{confirmDelete?.title}</strong>? Esta acción
        no se puede deshacer.
      </p>
      <p className="mt-2 text-[12px] text-[var(--text-tertiary)]">
        Tickets RAID generados a partir de esta minuta NO se borrarán; solo
        se rompe el link de origen.
      </p>
    </Modal>
    <ItemPreviewModal
      open={preview !== null}
      onClose={() => setPreview(null)}
      title={preview?.title ?? ""}
      subtitle={preview?.folio}
      openHref={preview ? `/pmo/projects/${id}/minutes/${preview.id}` : undefined}
      fields={
        preview
          ? [
              { label: "ID", value: preview.id, mono: true },
              { label: "Folio", value: preview.folio, mono: true },
              {
                label: "Fecha",
                value: new Date(preview.meeting_date).toLocaleDateString("es-MX"),
              },
              { label: "Participantes", value: preview.participants.length },
              { label: "Temas", value: preview.topics.length },
              { label: "Acuerdos", value: preview.agreements.length },
              {
                label: "Origen",
                value: preview.generated_by_ai ? "IA" : "Manual",
              },
            ]
          : []
      }
      description={
        preview
          ? preview.topics.map((t) => `• ${t.title}`).join("\n") || null
          : null
      }
    />
    </>
  );
}

// ENH-117 + ENH-118: solo PDF y DOCX. MD y TXT deprecados.
const EXPORT_FORMATS: Array<{ key: MinuteExportFormat; label: string }> = [
  { key: "pdf", label: "PDF" },
  { key: "docx", label: "DOCX" },
];

function ExportMinuteButtons({ minuteId }: { minuteId: string }) {
  const [busy, setBusy] = useState<MinuteExportFormat | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function download(format: MinuteExportFormat) {
    setBusy(format);
    setError(null);
    try {
      await exportMinute(minuteId, format);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al exportar");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-1">
      {EXPORT_FORMATS.map((f) => (
        <button
          key={f.key}
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            void download(f.key);
          }}
          disabled={busy !== null}
          className="inline-flex h-7 items-center gap-1 rounded-[var(--radius-sm)] border border-[var(--border-default)] bg-[var(--color-surface)] px-2 text-[11px] text-[var(--color-secondary)] hover:bg-[var(--color-subtle)] disabled:opacity-60"
          aria-label={`Descargar minuta en ${f.label}`}
        >
          {busy === f.key ? (
            <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-[var(--color-accent)]" />
          ) : (
            <Download className="h-3 w-3" aria-hidden />
          )}
          {f.label}
        </button>
      ))}
      {error ? (
        <span className="text-[10px] text-[var(--color-danger-fg)]">{error}</span>
      ) : null}
    </div>
  );
}
