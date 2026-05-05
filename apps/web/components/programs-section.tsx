"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Calendar, Pencil, Plus, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api";
import {
  createProgram,
  deleteProgram,
  hardDeleteProgram,
  listPrograms,
  previewHardDeleteProgram,
  updateProgram,
  type Program,
  type ProgramCreateBody,
  type ProgramUpdateBody,
} from "@/lib/api/organizations";
import { HardDeleteButton } from "@/components/hard-delete-button";

type Props = {
  organizationId: string;
};

type FormState = {
  mode: "create" | "edit";
  program?: Program;
};

function fmtDate(v: string | null): string {
  if (!v) return "";
  try {
    return new Date(v).toLocaleDateString("es-MX");
  } catch {
    return v;
  }
}

export function ProgramsSection({ organizationId }: Props) {
  const [programs, setPrograms] = useState<Program[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState<FormState | null>(null);
  const [deleting, setDeleting] = useState<Program | null>(null);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const rows = await listPrograms({ organization_id: organizationId });
      setPrograms(rows);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "No se pudieron cargar los programas",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [organizationId]);

  const empty = useMemo(
    () => !loading && !error && programs.length === 0,
    [loading, error, programs.length],
  );

  async function handleDelete() {
    if (!deleting) return;
    try {
      await deleteProgram(deleting.id);
      setDeleting(null);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo borrar el programa");
      setDeleting(null);
    }
  }

  return (
    <section className="space-y-4">
      <div className="flex items-end justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-[var(--color-primary)]">Programas</h2>
          <p className="text-sm text-[var(--color-tertiary)]">
            Agrupa proyectos bajo iniciativas estratégicas.
          </p>
        </div>
        <Button onClick={() => setForm({ mode: "create" })}>
          <Plus className="h-4 w-4" aria-hidden />
          Nuevo programa
        </Button>
      </div>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      <div className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]">
        <div className="divide-y divide-[var(--border-subtle)]">
          {loading
            ? Array.from({ length: 2 }).map((_, i) => (
                <div key={i} className="space-y-2 px-4 py-4">
                  <Skeleton className="h-4 w-48" />
                  <Skeleton className="h-3 w-72" />
                </div>
              ))
            : programs.map((p) => (
                <div key={p.id} className="flex items-start gap-3 px-4 py-4">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="truncate text-sm font-medium text-[var(--color-primary)]">
                        {p.name}
                      </span>
                      {!p.is_active ? <Badge variant="danger">Inactivo</Badge> : null}
                    </div>
                    {p.description ? (
                      <p className="mt-1 line-clamp-2 text-xs text-[var(--color-tertiary)]">
                        {p.description}
                      </p>
                    ) : null}
                    {p.start_date || p.end_date ? (
                      <div className="mt-1 inline-flex items-center gap-1 text-xs text-[var(--color-tertiary)]">
                        <Calendar className="h-3 w-3" aria-hidden />
                        {fmtDate(p.start_date)} — {fmtDate(p.end_date) || "—"}
                      </div>
                    ) : null}
                  </div>
                  <div className="flex gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setForm({ mode: "edit", program: p })}
                      aria-label={`Editar ${p.name}`}
                    >
                      <Pencil className="h-4 w-4" aria-hidden />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setDeleting(p)}
                      aria-label={`Borrar ${p.name}`}
                    >
                      <Trash2 className="h-4 w-4" aria-hidden />
                    </Button>
                    {!p.is_active ? (
                      <HardDeleteButton
                        preview={() => previewHardDeleteProgram(p.id)}
                        hardDelete={(slug) => hardDeleteProgram(p.id, slug)}
                        onDeleted={() => void refresh()}
                        entityLabel="Programa"
                        triggerVariant="ghost"
                        triggerLabel="Eliminar"
                      />
                    ) : null}
                  </div>
                </div>
              ))}
          {empty ? (
            <div className="px-4 py-8 text-center text-sm text-[var(--color-tertiary)]">
              Aún no hay programas. Crea el primero.
            </div>
          ) : null}
        </div>
      </div>

      {form ? (
        <ProgramFormModal
          organizationId={organizationId}
          state={form}
          onClose={() => setForm(null)}
          onSaved={async () => {
            setForm(null);
            await refresh();
          }}
        />
      ) : null}

      <Modal
        open={!!deleting}
        onClose={() => setDeleting(null)}
        title="Borrar programa"
        description="Esta acción desactiva el programa. Se puede reactivar desde la edición."
        footer={
          <>
            <Button variant="secondary" onClick={() => setDeleting(null)}>
              Cancelar
            </Button>
            <Button variant="danger" onClick={handleDelete}>
              Borrar
            </Button>
          </>
        }
      >
        <p className="text-sm text-[var(--color-secondary)]">
          ¿Confirmas borrar el programa <strong>{deleting?.name}</strong>?
        </p>
      </Modal>
    </section>
  );
}

function ProgramFormModal({
  organizationId,
  state,
  onClose,
  onSaved,
}: {
  organizationId: string;
  state: FormState;
  onClose: () => void;
  onSaved: () => void;
}) {
  const initial = state.program;
  const [name, setName] = useState(initial?.name ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [strategic, setStrategic] = useState(initial?.strategic_alignment ?? "");
  const [startDate, setStartDate] = useState(initial?.start_date ?? "");
  const [endDate, setEndDate] = useState(initial?.end_date ?? "");
  const [isActive, setIsActive] = useState(initial?.is_active ?? true);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const canSubmit = name.trim().length >= 2;

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!canSubmit) return;
    setSaving(true);
    setErr(null);
    try {
      if (state.mode === "create") {
        const body: ProgramCreateBody = {
          name: name.trim(),
          organization_id: organizationId,
          description: description.trim() || null,
          strategic_alignment: strategic.trim() || null,
          start_date: startDate || null,
          end_date: endDate || null,
          is_active: isActive,
        };
        await createProgram(body);
      } else if (initial) {
        const body: ProgramUpdateBody = {
          name: name.trim(),
          description: description.trim() || null,
          strategic_alignment: strategic.trim() || null,
          start_date: startDate || null,
          end_date: endDate || null,
          is_active: isActive,
        };
        await updateProgram(initial.id, body);
      }
      onSaved();
    } catch (e2) {
      setErr(e2 instanceof ApiError ? e2.message : "No se pudo guardar el programa");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={state.mode === "create" ? "Nuevo programa" : "Editar programa"}
      size="lg"
    >
      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        {err ? <Banner variant="danger">{err}</Banner> : null}
        <div>
          <label
            htmlFor="prog_name"
            className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
          >
            Nombre
          </label>
          <Input
            id="prog_name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            disabled={saving}
            required
            minLength={2}
          />
        </div>
        <div>
          <label
            htmlFor="prog_desc"
            className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
          >
            Descripción
          </label>
          <Textarea
            id="prog_desc"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            disabled={saving}
            rows={2}
          />
        </div>
        <div>
          <label
            htmlFor="prog_strategic"
            className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
          >
            Alineación estratégica
          </label>
          <Textarea
            id="prog_strategic"
            value={strategic}
            onChange={(e) => setStrategic(e.target.value)}
            disabled={saving}
            rows={2}
          />
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <label
              htmlFor="prog_start"
              className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
            >
              Inicio
            </label>
            <Input
              id="prog_start"
              type="date"
              value={startDate ?? ""}
              onChange={(e) => setStartDate(e.target.value)}
              disabled={saving}
            />
          </div>
          <div>
            <label
              htmlFor="prog_end"
              className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
            >
              Fin
            </label>
            <Input
              id="prog_end"
              type="date"
              value={endDate ?? ""}
              onChange={(e) => setEndDate(e.target.value)}
              disabled={saving}
            />
          </div>
        </div>
        <div className="flex items-center justify-between rounded-[var(--radius-md)] border border-[var(--border-default)] px-4 py-3">
          <span className="text-sm font-medium text-[var(--color-primary)]">Activo</span>
          <Switch
            checked={isActive}
            onChange={(v) => setIsActive(v)}
            disabled={saving}
          />
        </div>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose} disabled={saving}>
            Cancelar
          </Button>
          <Button type="submit" loading={saving} disabled={!canSubmit}>
            {state.mode === "create" ? "Crear" : "Guardar"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
