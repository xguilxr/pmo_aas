"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ExternalLink, FileText } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { ModuleShell } from "@/components/module-shell";
import { ApiError } from "@/lib/api";
import {
  DOC_CATEGORY_LABEL,
  createDocument,
  listDocuments,
  type DocumentCategory,
  type ProjectDocument,
} from "@/lib/api/modules";

function guessMime(name: string): string {
  const ext = name.split(".").pop()?.toLowerCase() ?? "";
  const map: Record<string, string> = {
    pdf: "application/pdf",
    docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    pptx: "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    png: "image/png",
    jpg: "image/jpeg",
    jpeg: "image/jpeg",
    csv: "text/csv",
  };
  return map[ext] ?? "application/octet-stream";
}

function formatSize(bytes: number | null): string {
  if (!bytes) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export default function DocumentsPage() {
  const { id } = useParams<{ id: string }>();
  const [rows, setRows] = useState<ProjectDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState<{
    title: string;
    description: string;
    category: DocumentCategory;
    file_url: string;
    size_kb: string;
  }>({
    title: "",
    description: "",
    category: "other",
    file_url: "",
    size_kb: "",
  });

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setRows(await listDocuments(id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron cargar los documentos");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function submit() {
    setSubmitting(true);
    try {
      const size = Number(form.size_kb) * 1024 || 0;
      const mime = guessMime(form.title);
      await createDocument(id, {
        title: form.title,
        description: form.description || null,
        category: form.category,
        file_url: form.file_url,
        mime_type: mime,
        size_bytes: size,
      });
      setForm({ title: "", description: "", category: "other", file_url: "", size_kb: "" });
      setOpen(false);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo registrar el documento");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <ModuleShell<ProjectDocument>
      projectId={id}
      title="Documentos"
      subtitle="Documentación del proyecto con control de versiones."
      icon={<FileText className="h-5 w-5" aria-hidden />}
      records={rows}
      loading={loading}
      error={error}
      newButtonLabel="Registrar documento"
      newModalTitle="Registrar documento"
      newModalOpen={open}
      setNewModalOpen={setOpen}
      newModalForm={() => (
        <div className="space-y-3">
          <p className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--color-subtle)] px-3 py-2 text-[12px] text-[var(--text-secondary)]">
            El MVP registra la metadata y un URL al archivo. La subida directa llegará en siguientes
            iteraciones.
          </p>
          <Field label="Título">
            <Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          </Field>
          <Field label="Descripción">
            <Textarea
              rows={2}
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </Field>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Categoría">
              <Select
                value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value as DocumentCategory })}
              >
                {(Object.keys(DOC_CATEGORY_LABEL) as DocumentCategory[]).map((c) => (
                  <option key={c} value={c}>
                    {DOC_CATEGORY_LABEL[c]}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Tamaño (KB)">
              <Input
                type="number"
                min={0}
                value={form.size_kb}
                onChange={(e) => setForm({ ...form, size_kb: e.target.value })}
              />
            </Field>
          </div>
          <Field label="URL del archivo">
            <Input
              type="url"
              placeholder="https://…"
              value={form.file_url}
              onChange={(e) => setForm({ ...form, file_url: e.target.value })}
            />
          </Field>
        </div>
      )}
      newModalFooter={(close) => (
        <>
          <Button variant="secondary" onClick={close} disabled={submitting}>
            Cancelar
          </Button>
          <Button
            onClick={submit}
            loading={submitting}
            disabled={!form.title.trim() || !form.file_url.trim()}
          >
            Registrar
          </Button>
        </>
      )}
      columns={[
        {
          key: "title",
          label: "Documento",
          render: (r) => (
            <div>
              <p className="font-medium">{r.title}</p>
              {r.description ? (
                <p className="text-[11px] text-[var(--text-tertiary)]">{r.description}</p>
              ) : null}
            </div>
          ),
        },
        {
          key: "category",
          label: "Categoría",
          render: (r) =>
            r.category ? <Badge>{DOC_CATEGORY_LABEL[r.category]}</Badge> : <span>—</span>,
        },
        {
          key: "version",
          label: "Versión",
          render: (r) => (
            <span className="tabular-nums text-[var(--text-secondary)]">v{r.version}</span>
          ),
        },
        {
          key: "size",
          label: "Tamaño",
          render: (r) => <span className="tabular-nums">{formatSize(r.size_bytes)}</span>,
        },
        {
          key: "link",
          label: "",
          render: (r) =>
            r.file_url ? (
              <a
                href={r.file_url}
                target="_blank"
                rel="noreferrer noopener"
                className="inline-flex items-center gap-1 text-[12px] text-[var(--color-accent)] hover:underline"
                onClick={(e) => e.stopPropagation()}
              >
                Abrir <ExternalLink className="h-3.5 w-3.5" aria-hidden />
              </a>
            ) : (
              "—"
            ),
        },
      ]}
    />
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-[12px] font-medium text-[var(--text-secondary)]">{label}</span>
      {children}
    </label>
  );
}
