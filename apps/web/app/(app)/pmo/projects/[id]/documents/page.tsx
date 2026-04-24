"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ExternalLink, FileText, Upload } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { ModuleShell } from "@/components/module-shell";
import { ApiError, apiBase } from "@/lib/api";
import { getAccessToken } from "@/lib/auth-storage";
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
    file?: File;
  }>({
    title: "",
    description: "",
    category: "other",
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
    if (!form.file || !form.title.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        title: form.title,
        description: form.description || "",
        category: form.category,
      });
      const formData = new FormData();
      formData.append("file", form.file);

      // BUG-029: usar apiBase() + Authorization header (el fetch nativo
      // ignoraba el JWT y el backend respondía 401 → el frontend mostraba
      // el mensaje genérico "No se pudo subir el documento").
      const token = getAccessToken();
      const headers: Record<string, string> = { Accept: "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const response = await fetch(
        `${apiBase()}/api/v1/projects/${id}/documents/upload?${params}`,
        {
          method: "POST",
          body: formData,
          headers,
          credentials: "include",
        },
      );
      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => ({} as Record<string, unknown>));
        // FastAPI serializa el error con shape `{detail: "..."}` o
        // `{detail: {code, message, fields}}`. Capturamos el texto
        // más descriptivo disponible en vez del fallback genérico.
        const detail = errorData.detail as unknown;
        const message =
          typeof detail === "string"
            ? detail
            : typeof detail === "object" && detail !== null
              ? String(
                  (detail as Record<string, unknown>).message ??
                    JSON.stringify(detail),
                )
              : `Upload falló (HTTP ${response.status})`;
        throw new ApiError(response.status, "upload_failed", message);
      }
      setForm({ title: "", description: "", category: "other" });
      setOpen(false);
      await load();
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "No se pudo registrar el documento",
      );
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
          </div>
          <Field label="Archivo">
            <div className="flex items-center gap-3">
              <label className="inline-flex h-9 shrink-0 cursor-pointer items-center gap-2 whitespace-nowrap rounded-[var(--radius-md)] border border-[var(--border-strong)] bg-[var(--color-surface)] px-3 text-sm font-medium text-[var(--color-primary)] shadow-[var(--shadow-sm)] transition-colors hover:bg-[var(--color-subtle)]">
                <Upload className="h-4 w-4" aria-hidden />
                {form.file ? "Cambiar archivo" : "Seleccionar archivo…"}
                <input
                  type="file"
                  accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.png,.jpg,.jpeg,.csv"
                  onChange={(e) =>
                    setForm({ ...form, file: e.target.files?.[0] })
                  }
                  className="sr-only"
                />
              </label>
              {form.file ? (
                <span className="truncate text-sm text-[var(--color-secondary)]">
                  {form.file.name}
                  <span className="ml-2 text-xs text-[var(--color-tertiary)]">
                    ({Math.round((form.file.size / 1024) * 10) / 10} KB)
                  </span>
                </span>
              ) : (
                <span className="text-sm text-[var(--color-tertiary)]">
                  PDF, XLSX, DOCX, PPTX, PNG, JPG o CSV · máx. 50 MB
                </span>
              )}
            </div>
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
            disabled={!form.title.trim() || !form.file}
          >
            Subir
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
          render: (r) => {
            // BUG-028: el charter siempre ofrece "Editar" además del
            // "Abrir" (ir al editor en vez de sólo descargar el .docx).
            const isCharter = r.category === "charter";
            const parts: React.ReactNode[] = [];
            if (r.file_url) {
              parts.push(
                <a
                  key="open"
                  href={r.file_url}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="inline-flex items-center gap-1 text-[12px] text-[var(--color-accent)] hover:underline"
                  onClick={(e) => e.stopPropagation()}
                >
                  Abrir <ExternalLink className="h-3.5 w-3.5" aria-hidden />
                </a>,
              );
            }
            if (isCharter) {
              parts.push(
                <Link
                  key="edit"
                  href={`/pmo/projects/${id}/charter`}
                  className="inline-flex items-center gap-1 text-[12px] text-[var(--color-accent)] hover:underline"
                  onClick={(e) => e.stopPropagation()}
                >
                  Editar <ExternalLink className="h-3.5 w-3.5" aria-hidden />
                </Link>,
              );
            }
            if (parts.length === 0) {
              return (
                <span
                  className="text-[12px] italic text-[var(--color-tertiary)]"
                  title="Este documento no tiene archivo adjunto. Sube un archivo para poder abrirlo."
                >
                  Sin archivo
                </span>
              );
            }
            return <div className="flex items-center gap-3">{parts}</div>;
          },
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
