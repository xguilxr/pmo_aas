"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { BarChart3, ListTree, Plus, Trash2, Upload } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import {
  TASK_STATUS_LABEL,
  createTask,
  deleteTask,
  importMsProject,
  listTasks,
  updateTask,
  type Task,
  type TaskStatus,
} from "@/lib/api/tasks";
import { cn } from "@/lib/cn";

export default function TasksPage() {
  const { id } = useParams<{ id: string }>();
  const [rows, setRows] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [newOpen, setNewOpen] = useState(false);
  const [newForm, setNewForm] = useState({
    name: "",
    wbs: "",
    start_date: "",
    end_date: "",
    duration_days: "",
    progress: "0",
    is_milestone: false,
    status: "not_started" as TaskStatus,
  });
  const [creating, setCreating] = useState(false);

  const [importOpen, setImportOpen] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importStrategy, setImportStrategy] = useState<"merge" | "replace">("replace");
  const [importing, setImporting] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setRows(await listTasks(id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron cargar las tareas");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function submitNew() {
    setCreating(true);
    try {
      await createTask(id, {
        name: newForm.name,
        wbs: newForm.wbs || null,
        start_date: newForm.start_date || null,
        end_date: newForm.end_date || null,
        duration_days: newForm.duration_days ? Number(newForm.duration_days) : null,
        progress: Number(newForm.progress) || 0,
        is_milestone: newForm.is_milestone,
        status: newForm.status,
      });
      setNewOpen(false);
      setNewForm({
        name: "",
        wbs: "",
        start_date: "",
        end_date: "",
        duration_days: "",
        progress: "0",
        is_milestone: false,
        status: "not_started",
      });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear la tarea");
    } finally {
      setCreating(false);
    }
  }

  async function submitImport() {
    if (!importFile) return;
    setImporting(true);
    try {
      const res = await importMsProject(id, importFile, importStrategy);
      setImportOpen(false);
      setImportFile(null);
      setNotice(
        `Importadas ${res.imported} tareas · ${res.dependencies_created} dependencias` +
          (res.errors.length ? ` · ${res.errors.length} errores` : ""),
      );
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo importar el archivo");
    } finally {
      setImporting(false);
    }
  }

  async function handleDelete(t: Task) {
    if (!confirm(`Eliminar "${t.name}"?`)) return;
    try {
      await deleteTask(t.id);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo eliminar");
    }
  }

  async function toggleProgress(t: Task, delta: number) {
    try {
      await updateTask(t.id, {
        progress: Math.min(100, Math.max(0, t.progress + delta)),
      });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo actualizar");
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-5">
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
            <span>Tareas</span>
          </nav>
          <h1 className="mt-1 flex items-center gap-2 text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
            <ListTree className="h-6 w-6" aria-hidden /> Tareas
            <span className="rounded-full bg-[var(--color-subtle)] px-2 py-0.5 text-[11px] tabular-nums text-[var(--text-secondary)]">
              {rows.length}
            </span>
          </h1>
          <p className="mt-1 text-[13px] text-[var(--text-tertiary)]">
            Gestiona tareas manualmente o impórtalas desde MS Project (.xml).
          </p>
        </div>
        <div className="flex gap-2">
          <Link href={`/admin/projects/${id}/gantt`}>
            <Button variant="secondary">
              <BarChart3 className="h-4 w-4" aria-hidden /> Ver Gantt
            </Button>
          </Link>
          {/* ENH-008: EP009 MSP import pasa a v1.1 (post-MVP) */}
          <Button
            variant="secondary"
            disabled
            title="Disponible en v1.1"
            aria-label="Importar MSP — disponible en v1.1"
          >
            <Upload className="h-4 w-4" aria-hidden /> Importar MSP (v1.1)
          </Button>
          <Button onClick={() => setNewOpen(true)}>
            <Plus className="h-4 w-4" aria-hidden /> Nueva tarea
          </Button>
        </div>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}
      {notice ? <Banner variant="success">{notice}</Banner> : null}

      <section className="rounded-[var(--radius-window)] border border-[var(--border-subtle)] bg-[var(--color-surface)]">
        <div className="overflow-x-auto">
          <table className="w-full text-[13px]">
            <thead className="border-b border-[var(--border-subtle)] bg-[var(--color-subtle)] text-left text-[11px] uppercase tracking-[0.01em] text-[var(--text-secondary)]">
              <tr>
                <th className="h-10 px-4 font-medium">WBS</th>
                <th className="h-10 px-4 font-medium">Nombre</th>
                <th className="h-10 px-4 font-medium">Inicio</th>
                <th className="h-10 px-4 font-medium">Fin</th>
                <th className="h-10 px-4 font-medium">Avance</th>
                <th className="h-10 px-4 font-medium">Estado</th>
                <th className="h-10 px-4 font-medium">Origen</th>
                <th className="h-10 px-4 w-12" />
              </tr>
            </thead>
            <tbody>
              {loading ? (
                Array.from({ length: 6 }).map((_, i) => (
                  <tr key={i} className="border-b border-[var(--border-subtle)]">
                    {Array.from({ length: 8 }).map((_, j) => (
                      <td key={j} className="h-12 px-4">
                        <Skeleton className="h-4 w-20" />
                      </td>
                    ))}
                  </tr>
                ))
              ) : rows.length ? (
                rows.map((t) => (
                  <tr key={t.id} className="border-b border-[var(--border-subtle)]">
                    <td className="px-4 font-mono text-[11px] text-[var(--text-secondary)]">
                      {t.wbs ?? "—"}
                    </td>
                    <td className="px-4">
                      <div className="flex items-center gap-2">
                        {t.is_milestone ? (
                          <span className="inline-block h-2.5 w-2.5 rotate-45 bg-[var(--color-warning-fg)]" />
                        ) : null}
                        <span className="font-medium text-[var(--text-primary)]">{t.name}</span>
                      </div>
                    </td>
                    <td className="px-4 text-[var(--text-secondary)]">{t.start_date ?? "—"}</td>
                    <td className="px-4 text-[var(--text-secondary)]">{t.end_date ?? "—"}</td>
                    <td className="px-4 w-44">
                      <div className="flex items-center gap-1.5">
                        <button
                          type="button"
                          className="inline-flex h-6 w-6 items-center justify-center rounded-[var(--radius-sm)] border border-[var(--border-default)] text-[12px] hover:bg-[var(--color-subtle)]"
                          onClick={() => toggleProgress(t, -10)}
                          aria-label="Restar 10%"
                        >
                          −
                        </button>
                        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-[var(--color-muted)]">
                          <div
                            className={cn(
                              "h-full rounded-full",
                              t.progress >= 100 ? "bg-[var(--color-success-fg)]" : "bg-[var(--text-primary)]",
                            )}
                            style={{ width: `${t.progress}%` }}
                          />
                        </div>
                        <button
                          type="button"
                          className="inline-flex h-6 w-6 items-center justify-center rounded-[var(--radius-sm)] border border-[var(--border-default)] text-[12px] hover:bg-[var(--color-subtle)]"
                          onClick={() => toggleProgress(t, 10)}
                          aria-label="Sumar 10%"
                        >
                          +
                        </button>
                        <span className="w-9 text-right text-[11px] tabular-nums text-[var(--text-secondary)]">
                          {t.progress}%
                        </span>
                      </div>
                    </td>
                    <td className="px-4">
                      <Badge
                        variant={
                          t.status === "completed"
                            ? "success"
                            : t.status === "in_progress"
                              ? "info"
                              : t.status === "on_hold"
                                ? "warning"
                                : "neutral"
                        }
                      >
                        {TASK_STATUS_LABEL[t.status] ?? t.status}
                      </Badge>
                    </td>
                    <td className="px-4">
                      <Badge>{t.source === "msproject" ? "MSP" : "Manual"}</Badge>
                    </td>
                    <td className="px-2 text-right">
                      <button
                        type="button"
                        onClick={() => handleDelete(t)}
                        aria-label="Eliminar tarea"
                        className="inline-flex h-7 w-7 items-center justify-center rounded-[var(--radius-sm)] text-[var(--text-tertiary)] hover:bg-[var(--color-subtle)] hover:text-[var(--color-danger-fg)]"
                      >
                        <Trash2 className="h-3.5 w-3.5" aria-hidden />
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={8} className="px-4 py-16 text-center text-[var(--text-tertiary)]">
                    Aún no hay tareas. Crea una o importa desde MS Project.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <Modal
        open={newOpen}
        onClose={() => !creating && setNewOpen(false)}
        title="Nueva tarea"
        size="lg"
        footer={
          <>
            <Button variant="secondary" onClick={() => setNewOpen(false)} disabled={creating}>
              Cancelar
            </Button>
            <Button onClick={submitNew} loading={creating} disabled={newForm.name.trim().length < 2}>
              Crear
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <Field label="Nombre">
            <Input
              value={newForm.name}
              onChange={(e) => setNewForm({ ...newForm, name: e.target.value })}
            />
          </Field>
          <div className="grid gap-3 sm:grid-cols-3">
            <Field label="WBS">
              <Input
                value={newForm.wbs}
                onChange={(e) => setNewForm({ ...newForm, wbs: e.target.value })}
                placeholder="1.2.3"
              />
            </Field>
            <Field label="Duración (días)">
              <Input
                type="number"
                min={0}
                value={newForm.duration_days}
                onChange={(e) => setNewForm({ ...newForm, duration_days: e.target.value })}
              />
            </Field>
            <Field label="Avance %">
              <Input
                type="number"
                min={0}
                max={100}
                value={newForm.progress}
                onChange={(e) => setNewForm({ ...newForm, progress: e.target.value })}
              />
            </Field>
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            <Field label="Inicio">
              <Input
                type="date"
                value={newForm.start_date}
                onChange={(e) => setNewForm({ ...newForm, start_date: e.target.value })}
              />
            </Field>
            <Field label="Fin">
              <Input
                type="date"
                value={newForm.end_date}
                onChange={(e) => setNewForm({ ...newForm, end_date: e.target.value })}
              />
            </Field>
            <Field label="Estado">
              <Select
                value={newForm.status}
                onChange={(e) => setNewForm({ ...newForm, status: e.target.value as TaskStatus })}
              >
                {Object.entries(TASK_STATUS_LABEL).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
              </Select>
            </Field>
          </div>
          <label className="inline-flex items-center gap-2 text-[12px] text-[var(--text-secondary)]">
            <input
              type="checkbox"
              checked={newForm.is_milestone}
              onChange={(e) => setNewForm({ ...newForm, is_milestone: e.target.checked })}
            />
            Es hito
          </label>
        </div>
      </Modal>

      <Modal
        open={importOpen}
        onClose={() => !importing && setImportOpen(false)}
        title="Importar desde MS Project"
        description="Formato aceptado: XML exportado desde MS Project (≤ 50 MB). XLSX y .mpp llegarán en versiones posteriores."
        footer={
          <>
            <Button variant="secondary" onClick={() => setImportOpen(false)} disabled={importing}>
              Cancelar
            </Button>
            <Button onClick={submitImport} loading={importing} disabled={!importFile}>
              Importar
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <Field label="Archivo XML">
            <input
              type="file"
              accept=".xml,application/xml,text/xml"
              onChange={(e) => setImportFile(e.target.files?.[0] ?? null)}
              className="block w-full cursor-pointer rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-surface)] px-3 py-2 text-[13px] file:mr-3 file:rounded-[var(--radius-sm)] file:border-0 file:bg-[var(--color-subtle)] file:px-3 file:py-1 file:text-[12px] file:font-medium file:text-[var(--text-primary)]"
            />
          </Field>
          <Field label="Estrategia">
            <Select
              value={importStrategy}
              onChange={(e) => setImportStrategy(e.target.value as "merge" | "replace")}
            >
              <option value="replace">Reemplazar todo (borra tareas existentes)</option>
              <option value="merge">Merge por external_id (actualiza y agrega)</option>
            </Select>
          </Field>
        </div>
      </Modal>
    </div>
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
