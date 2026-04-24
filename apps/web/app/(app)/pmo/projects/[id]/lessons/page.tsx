"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Eye, Lightbulb } from "lucide-react";

import { ItemPreviewModal } from "@/components/item-preview-modal";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { ModuleShell } from "@/components/module-shell";
import { ApiError } from "@/lib/api";
import {
  LESSON_CATEGORY_LABEL,
  createLesson,
  listLessons,
  type Lesson,
  type LessonCategory,
} from "@/lib/api/modules";

export default function LessonsPage() {
  const { id } = useParams<{ id: string }>();
  const [rows, setRows] = useState<Lesson[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<Lesson | null>(null);

  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState<{
    title: string;
    description: string;
    category: LessonCategory;
    phase: string;
    recommendation: string;
    tags: string;
  }>({
    title: "",
    description: "",
    category: "improvement",
    phase: "execution",
    recommendation: "",
    tags: "",
  });

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setRows(await listLessons({ project_id: id }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron cargar las lecciones");
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
      const tags = form.tags
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);
      await createLesson(id, {
        title: form.title,
        description: form.description || null,
        category: form.category,
        phase: form.phase || null,
        recommendation: form.recommendation || null,
        tags,
      });
      setForm({
        title: "",
        description: "",
        category: "improvement",
        phase: "execution",
        recommendation: "",
        tags: "",
      });
      setOpen(false);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo registrar la lección");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
    <ModuleShell<Lesson>
      projectId={id}
      title="Lecciones aprendidas"
      subtitle="Éxitos, mejoras y errores para capitalizar el conocimiento."
      icon={<Lightbulb className="h-5 w-5" aria-hidden />}
      records={rows}
      loading={loading}
      error={error}
      newButtonLabel="Nueva lección"
      newModalTitle="Registrar lección aprendida"
      newModalOpen={open}
      setNewModalOpen={setOpen}
      newModalForm={() => (
        <div className="space-y-3">
          <Field label="Título">
            <Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          </Field>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Categoría">
              <Select
                value={form.category}
                onChange={(e) =>
                  setForm({ ...form, category: e.target.value as LessonCategory })
                }
              >
                {(Object.keys(LESSON_CATEGORY_LABEL) as LessonCategory[]).map((c) => (
                  <option key={c} value={c}>
                    {LESSON_CATEGORY_LABEL[c]}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Fase">
              <Select
                value={form.phase}
                onChange={(e) => setForm({ ...form, phase: e.target.value })}
              >
                <option value="planning">Planificación</option>
                <option value="execution">Ejecución</option>
                <option value="support">Soporte</option>
                <option value="closed">Cierre</option>
              </Select>
            </Field>
          </div>
          <Field label="Descripción">
            <Textarea
              rows={3}
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </Field>
          <Field label="Recomendación">
            <Textarea
              rows={3}
              value={form.recommendation}
              onChange={(e) => setForm({ ...form, recommendation: e.target.value })}
            />
          </Field>
          <Field label="Tags (separadas por coma)">
            <Input
              placeholder="onboarding, comunicación, alcance"
              value={form.tags}
              onChange={(e) => setForm({ ...form, tags: e.target.value })}
            />
          </Field>
        </div>
      )}
      newModalFooter={(close) => (
        <>
          <Button variant="secondary" onClick={close} disabled={submitting}>
            Cancelar
          </Button>
          <Button onClick={submit} loading={submitting} disabled={!form.title.trim()}>
            Registrar
          </Button>
        </>
      )}
      columns={[
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
          key: "title",
          label: "Lección",
          render: (r) => (
            <div>
              <p className="font-medium">{r.title}</p>
              {r.recommendation ? (
                <p className="mt-0.5 line-clamp-1 text-[11px] text-[var(--text-tertiary)]">
                  {r.recommendation}
                </p>
              ) : null}
            </div>
          ),
        },
        {
          key: "category",
          label: "Categoría",
          render: (r) =>
            r.category ? (
              <Badge
                variant={
                  r.category === "success"
                    ? "success"
                    : r.category === "error"
                      ? "danger"
                      : "warning"
                }
              >
                {LESSON_CATEGORY_LABEL[r.category]}
              </Badge>
            ) : null,
        },
        {
          key: "phase",
          label: "Fase",
          render: (r) => r.phase ?? "—",
        },
        {
          key: "tags",
          label: "Tags",
          render: (r) =>
            r.tags.length ? (
              <div className="flex flex-wrap gap-1">
                {r.tags.map((t) => (
                  <Badge key={t}>{t}</Badge>
                ))}
              </div>
            ) : (
              "—"
            ),
        },
      ]}
    />
    <ItemPreviewModal
      open={preview !== null}
      onClose={() => setPreview(null)}
      title={preview?.title ?? ""}
      subtitle={preview?.folio}
      fields={
        preview
          ? [
              { label: "ID", value: preview.id, mono: true },
              { label: "Folio", value: preview.folio, mono: true },
              {
                label: "Categoría",
                value: preview.category
                  ? LESSON_CATEGORY_LABEL[preview.category]
                  : "—",
              },
              { label: "Fase", value: preview.phase ?? "—" },
              {
                label: "Tags",
                value: preview.tags.length ? preview.tags.join(", ") : "—",
              },
              {
                label: "Recomendación",
                value: preview.recommendation ?? "—",
              },
            ]
          : []
      }
      description={preview?.description ?? null}
    />
    </>
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
