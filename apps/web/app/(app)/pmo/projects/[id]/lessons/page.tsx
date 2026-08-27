"use client";

// ENH-187: la vista de Lecciones aprendidas hereda estructura/funcionalidades
// de las listas RAID (sort por columna, filtros, edición inline, export
// propio), mismo patrón aplicado a Cambios en ENH-186.

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { InlineSelectCell, InlineTextCell } from "@/components/inline-select-cell";
import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Icono } from "@/components/ui/icono";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { SortableTh } from "@/components/ui/sortable-th";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, apiBase } from "@/lib/api";
import { listEligibleActors, type ActorMini } from "@/lib/api/project-directory";
import { useSortableRows } from "@/lib/hooks/use-sortable-rows";
import {
  LESSON_CATEGORY_LABEL,
  LESSON_PHASE_LABEL,
  LESSON_PHASE_ORDER,
  createLesson,
  listLessons,
  updateLesson,
  type Lesson,
  type LessonCategory,
  type LessonUpdateBody,
} from "@/lib/api/modules";

type InlineOption = { value: string; label: string };

export default function LessonsPage() {
  const { id } = useParams<{ id: string }>();
  const [rows, setRows] = useState<Lesson[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
    phase: "ejecucion",
    recommendation: "",
    tags: "",
  });

  // ENH-187: filtros estilo RAID (categoría + fase) + búsqueda simple.
  const [categoryFilter, setCategoryFilter] = useState<string>("");
  const [phaseFilter, setPhaseFilter] = useState<string>("");
  const [search, setSearch] = useState("");
  const [exporting, setExporting] = useState(false);

  // ENH-187: actores elegibles para el select inline de Responsable — mismo
  // endpoint que usa RAID (US-117/BUG-086). El backend de Lecciones no
  // resuelve `responsible_name` (a diferencia de Risk/Issue), así que el
  // nombre se resuelve en cliente contra esta lista.
  const [actorOptions, setActorOptions] = useState<InlineOption[]>([]);

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
    listEligibleActors(id)
      .then((actors: ActorMini[]) =>
        setActorOptions(actors.map((a) => ({ value: a.id, label: a.name }))),
      )
      .catch(() => setActorOptions([]));
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
        phase: "ejecucion",
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

  // ENH-187: edición inline (título/categoría/fase/responsable), patrón
  // US-178 de RAID — update optimista + revert si el PATCH falla.
  async function patchLesson(lessonId: string, patch: LessonUpdateBody) {
    setError(null);
    const prev = rows.find((r) => r.id === lessonId);
    setRows((rs) => rs.map((r) => (r.id === lessonId ? ({ ...r, ...patch } as Lesson) : r)));
    try {
      const updated = await updateLesson(lessonId, patch);
      setRows((rs) => rs.map((r) => (r.id === updated.id ? { ...r, ...updated } : r)));
    } catch (err) {
      if (prev) setRows((rs) => rs.map((r) => (r.id === lessonId ? prev : r)));
      setError(err instanceof ApiError ? err.message : "No se pudo actualizar la lección");
    }
  }

  // ENH-187: export propio (1 hoja "Lecciones"), misma descarga autenticada
  // que Cambios (ENH-186) / RAID (ENH-152/168) vía /lessons/export.
  async function downloadLessons() {
    if (exporting) return;
    setExporting(true);
    setError(null);
    try {
      const headers: Record<string, string> = { Accept: "application/octet-stream" };
      const res = await fetch(`${apiBase()}/api/v1/projects/${id}/lessons/export`, {
        method: "GET",
        headers,
        credentials: "include",
      });
      if (!res.ok) {
        throw new ApiError(res.status, "EXPORT_FAILED", `Exportación falló (HTTP ${res.status})`);
      }
      const cd = res.headers.get("Content-Disposition") ?? "";
      const match = /filename="([^"]+)"/.exec(cd);
      const name = match ? match[1] : `lecciones-${id}.xlsx`;
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = name;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo exportar las lecciones");
    } finally {
      setExporting(false);
    }
  }

  // ENH-187: filtros (categoría/fase) + búsqueda simple por texto en
  // título/descripción/recomendación/tags — barata (client-side, ya está
  // todo cargado en memoria).
  const filteredRows = useMemo(() => {
    const q = search.trim().toLowerCase();
    return rows.filter((r) => {
      if (categoryFilter && r.category !== categoryFilter) return false;
      if (phaseFilter && r.phase !== phaseFilter) return false;
      if (q) {
        const haystack = [r.title, r.description ?? "", r.recommendation ?? "", ...r.tags]
          .join(" ")
          .toLowerCase();
        if (!haystack.includes(q)) return false;
      }
      return true;
    });
  }, [rows, categoryFilter, phaseFilter, search]);

  const { sortedRows, ctrl: sortCtrl } = useSortableRows<Lesson>(filteredRows);

  function categoryOpts(): InlineOption[] {
    return (Object.keys(LESSON_CATEGORY_LABEL) as LessonCategory[]).map((c) => ({
      value: c,
      label: LESSON_CATEGORY_LABEL[c],
    }));
  }

  function phaseOpts(r: Lesson): InlineOption[] {
    const opts: InlineOption[] = LESSON_PHASE_ORDER.map((p) => ({
      value: p,
      label: LESSON_PHASE_LABEL[p],
    }));
    if (r.phase && !opts.some((o) => o.value === r.phase)) {
      opts.push({ value: r.phase, label: r.phase });
    }
    return opts;
  }

  function respOpts(r: Lesson): InlineOption[] {
    const opts = [...actorOptions];
    if (r.owner_actor_id && !opts.some((o) => o.value === r.owner_actor_id)) {
      opts.unshift({ value: r.owner_actor_id, label: "(responsable)" });
    }
    return [{ value: "", label: "— sin responsable —" }, ...opts];
  }

  function actorLabel(actorId: string | null | undefined): string {
    if (!actorId) return "";
    return actorOptions.find((o) => o.value === actorId)?.label ?? "";
  }

  return (
    <>
      <div className="space-y-5">
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
              <span>Lecciones</span>
            </nav>
            <h1 className="mt-1 text-[22px] font-semibold tracking-[-0.02em] text-[var(--text-primary)]">
              Lecciones aprendidas
            </h1>
            <p className="mt-1 text-[13px] text-[var(--text-tertiary)]">
              Éxitos, mejoras y errores para capitalizar el conocimiento.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button type="button" onClick={() => setOpen(true)}>
              <Icono nombre="plus" size={15} />
              Nueva lección
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => void downloadLessons()}
              disabled={exporting}
            >
              <Icono nombre="download" size={15} />
              {exporting ? "Exportando…" : "Exportar"}
            </Button>
          </div>
        </header>

        {error ? <Banner variant="danger">{error}</Banner> : null}

        {/* ENH-187: filtros estilo RAID (categoría + fase) + búsqueda simple. */}
        <div className="flex flex-wrap items-center gap-2.5">
          <span className="text-[10.5px] font-semibold uppercase tracking-[0.06em] text-[var(--text-tertiary)]">
            Filtros
          </span>
          <Select
            aria-label="Categoría"
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="w-[150px] text-[12.5px]"
          >
            <option value="">Todas las categorías</option>
            {(Object.keys(LESSON_CATEGORY_LABEL) as LessonCategory[]).map((c) => (
              <option key={c} value={c}>
                {LESSON_CATEGORY_LABEL[c]}
              </option>
            ))}
          </Select>
          <Select
            aria-label="Fase"
            value={phaseFilter}
            onChange={(e) => setPhaseFilter(e.target.value)}
            className="w-[120px] text-[12.5px]"
          >
            <option value="">Todas las fases</option>
            {LESSON_PHASE_ORDER.map((p) => (
              <option key={p} value={p}>
                {LESSON_PHASE_LABEL[p]}
              </option>
            ))}
          </Select>
          <div className="relative ml-auto w-[220px]">
            <Icono
              nombre="search"
              size={13}
              className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--text-faint)]"
            />
            <Input
              type="search"
              aria-label="Buscar"
              placeholder="Buscar título, tag…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-8 text-[12.5px]"
            />
          </div>
        </div>

        {loading ? (
          <div className="space-y-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-14 w-full" />
            ))}
          </div>
        ) : rows.length === 0 ? (
          <div className="rounded-[var(--radius-xl)] border border-dashed border-[var(--border-default)] bg-[var(--color-surface)] p-10 text-center text-sm text-[var(--color-tertiary)]">
            Sin lecciones registradas. Usa el botón <strong>+ Nueva lección</strong> arriba
            para crear la primera.
          </div>
        ) : sortedRows.length === 0 ? (
          <div className="rounded-[var(--radius-xl)] border border-dashed border-[var(--border-default)] bg-[var(--color-surface)] p-10 text-center text-sm text-[var(--color-tertiary)]">
            Ninguna lección coincide con los filtros activos.
          </div>
        ) : (
          <section className="overflow-hidden rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--relieve-isla)]">
            <div className="overflow-x-auto">
              <table className="w-full table-fixed text-[13px]">
                <thead className="border-b border-[var(--border-default)] bg-[var(--color-subtle)] text-left text-[10.5px] font-semibold uppercase tracking-[0.06em] text-[var(--text-tertiary)] shadow-[var(--linea-surco)]">
                  <tr>
                    <SortableTh<Lesson>
                      sortKey="folio"
                      getter={(r) => r.folio}
                      ctrl={sortCtrl}
                      className="h-8.5 w-[110px] px-4"
                    >
                      Folio
                    </SortableTh>
                    <SortableTh<Lesson>
                      sortKey="title"
                      getter={(r) => r.title}
                      ctrl={sortCtrl}
                      className="h-8.5 px-4"
                    >
                      Lección
                    </SortableTh>
                    <SortableTh<Lesson>
                      sortKey="category"
                      getter={(r) => r.category ?? ""}
                      ctrl={sortCtrl}
                      className="h-8.5 w-[110px] px-4"
                    >
                      Categoría
                    </SortableTh>
                    <SortableTh<Lesson>
                      sortKey="phase"
                      getter={(r) => r.phase ?? ""}
                      ctrl={sortCtrl}
                      className="h-8.5 w-[110px] px-4"
                    >
                      Fase
                    </SortableTh>
                    <SortableTh<Lesson>
                      sortKey="responsible"
                      getter={(r) => actorLabel(r.owner_actor_id)}
                      ctrl={sortCtrl}
                      className="h-8.5 w-[140px] px-4"
                    >
                      Responsable
                    </SortableTh>
                    <th className="h-8.5 w-[160px] px-4">Tags</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedRows.map((r) => (
                    <tr
                      key={r.id}
                      className="h-11 border-b border-[var(--border-subtle)] shadow-[var(--linea-surco)] hover:bg-[var(--color-subtle)]"
                    >
                      {/* US-178 (patrón RAID): folio = único link que abre el detalle. */}
                      <td className="truncate px-4 text-[12px] tracking-[0.01em] text-[var(--color-tertiary)]">
                        <Link
                          href={`/pmo/projects/${id}/lessons/${r.id}`}
                          className="hover:text-[var(--color-accent)] hover:underline"
                        >
                          {r.folio}
                        </Link>
                      </td>
                      {/* ENH-187: título editable inline. */}
                      <td className="px-4 text-[var(--color-primary)]">
                        <InlineTextCell
                          value={r.title}
                          onChange={(v) => patchLesson(r.id, { title: v })}
                          title="Lección"
                          ariaLabel={`Lección ${r.folio}`}
                        />
                      </td>
                      {/* ENH-187: categoría — chip de color, editable inline. */}
                      <td className="px-4">
                        <ChipSelectCell
                          label={r.category ? LESSON_CATEGORY_LABEL[r.category] : null}
                          variant={
                            r.category === "success"
                              ? "success"
                              : r.category === "error"
                                ? "danger"
                                : "warning"
                          }
                          options={categoryOpts()}
                          value={r.category ?? ""}
                          onChange={(v) => patchLesson(r.id, { category: v as LessonCategory })}
                          title="Categoría"
                          ariaLabel={`Categoría de ${r.folio}`}
                        />
                      </td>
                      {/* ENH-187: fase — texto plano, editable inline (sin chip: mockup 7b
                          sólo colorea la categoría). */}
                      <td className="px-4 text-[12.5px] text-[var(--color-secondary)]">
                        <InlineSelectCell
                          value={r.phase ?? ""}
                          options={phaseOpts(r)}
                          onChange={(v) => patchLesson(r.id, { phase: v || null })}
                          placeholder="—"
                          title="Fase"
                          ariaLabel={`Fase de ${r.folio}`}
                        />
                      </td>
                      {/* ENH-187: responsable (Actor del catálogo) editable inline. */}
                      <td className="px-4 text-[12.5px] text-[var(--color-secondary)]">
                        <InlineSelectCell
                          value={r.owner_actor_id ?? ""}
                          options={respOpts(r)}
                          onChange={(v) => patchLesson(r.id, { owner_actor_id: v || null })}
                          placeholder="—"
                          title="Responsable"
                          ariaLabel={`Responsable de ${r.folio}`}
                        />
                      </td>
                      {/* Tags: sólo lectura (chips de texto). */}
                      <td className="px-4">
                        {r.tags.length ? (
                          <div className="flex flex-wrap gap-1.25">
                            {r.tags.map((t) => (
                              <span
                                key={t}
                                className="inline-flex items-center rounded-full bg-[var(--color-muted)] px-2 py-0.5 text-[11px] text-[var(--color-secondary)]"
                              >
                                {t}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <span className="text-[11px] text-[var(--text-tertiary)]">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}
      </div>

      <Modal
        open={open}
        onClose={() => !submitting && setOpen(false)}
        title="Registrar lección aprendida"
        footer={
          <>
            <Button variant="secondary" onClick={() => setOpen(false)} disabled={submitting}>
              Cancelar
            </Button>
            <Button onClick={submit} loading={submitting} disabled={!form.title.trim()}>
              Registrar
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <Field label="Título">
            <Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          </Field>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Categoría">
              <Select
                value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value as LessonCategory })}
              >
                {(Object.keys(LESSON_CATEGORY_LABEL) as LessonCategory[]).map((c) => (
                  <option key={c} value={c}>
                    {LESSON_CATEGORY_LABEL[c]}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Fase">
              <Select value={form.phase} onChange={(e) => setForm({ ...form, phase: e.target.value })}>
                {LESSON_PHASE_ORDER.map((p) => (
                  <option key={p} value={p}>
                    {LESSON_PHASE_LABEL[p]}
                  </option>
                ))}
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
      </Modal>
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

/**
 * ENH-187: chip de color (Badge) + edición inline on-click — mismo patrón
 * visual que `TaskStatusInlineCell` del Plan (ENH-188). En modo lectura
 * muestra el chip de color; al hacer click se convierte en `<select>` nativo.
 */
function ChipSelectCell({
  label,
  variant,
  options,
  value,
  onChange,
  title,
  ariaLabel,
  placeholder = "—",
}: {
  label: string | null;
  variant: "success" | "warning" | "danger";
  options: InlineOption[];
  value: string;
  onChange: (value: string) => void;
  title?: string;
  ariaLabel?: string;
  placeholder?: string;
}) {
  const [editing, setEditing] = useState(false);

  if (!editing) {
    return (
      <button
        type="button"
        onClick={() => setEditing(true)}
        title={title ? `${title} (clic para editar)` : "Clic para editar"}
        aria-label={ariaLabel}
        className="rounded focus:outline-none focus-visible:ring-1 focus-visible:ring-[var(--border-strong)]"
      >
        {label ? (
          <Badge variant={variant}>{label}</Badge>
        ) : (
          <span className="text-[11px] text-[var(--color-tertiary)]">{placeholder}</span>
        )}
      </button>
    );
  }

  return (
    <select
      autoFocus
      value={value}
      aria-label={ariaLabel}
      onChange={(e) => {
        onChange(e.target.value);
        setEditing(false);
      }}
      onBlur={() => setEditing(false)}
      onKeyDown={(e) => {
        if (e.key === "Escape") {
          e.preventDefault();
          setEditing(false);
        }
      }}
      className="rounded border border-[var(--border-default)] bg-[var(--color-surface)] px-1 py-0.5 text-xs text-[var(--color-secondary)] focus:outline-none"
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  );
}
