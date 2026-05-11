"use client";

import { useEffect, useState } from "react";
import { Plus, PowerOff, Users } from "lucide-react";

import { Banner } from "@/components/ui/banner";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api";
import { useSortableRows } from "@/lib/hooks/use-sortable-rows";
import { SortableTh } from "@/components/ui/sortable-th";
import {
  createStakeholder,
  deleteStakeholder,
  hardDeleteStakeholder,
  listStakeholders,
  previewHardDeleteStakeholder,
  type Stakeholder,
} from "@/lib/api/stakeholders";
import { HardDeleteButton } from "@/components/hard-delete-button";

export default function StakeholdersPage() {
  const [rows, setRows] = useState<Stakeholder[]>([]);
  const { sortedRows, ctrl: skCtrl } = useSortableRows<Stakeholder>(rows);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    phone: "",
    company: "",
    job_title: "",
    notes: "",
  });

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setRows(await listStakeholders({ q: q || undefined }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar el catálogo");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function submit() {
    if (!form.full_name.trim()) {
      setError("El nombre es obligatorio");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await createStakeholder({
        full_name: form.full_name.trim(),
        email: form.email.trim() || null,
        phone: form.phone.trim() || null,
        company: form.company.trim() || null,
        job_title: form.job_title.trim() || null,
        notes: form.notes.trim() || null,
      });
      setForm({ full_name: "", email: "", phone: "", company: "", job_title: "", notes: "" });
      setOpen(false);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el stakeholder");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("¿Desactivar stakeholder? Quedará inactivo pero no se borra.")) return;
    try {
      await deleteStakeholder(id);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo eliminar");
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <Breadcrumb
        items={[
          { href: "/admin", label: "Admin" },
          { label: "Stakeholders" },
        ]}
      />
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Users className="h-5 w-5" aria-hidden />
          <h1 className="text-2xl font-semibold text-[var(--color-primary)]">
            Stakeholders
          </h1>
          <span className="rounded-full bg-[var(--color-subtle)] px-2 py-0.5 text-[11px] tabular-nums text-[var(--color-secondary)]">
            {rows.length}
          </span>
        </div>
        <div className="flex gap-2">
          <Input
            placeholder="Buscar por nombre, email o empresa…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void load();
            }}
            className="w-64"
          />
          <Button onClick={() => setOpen(true)}>
            <Plus className="h-4 w-4" aria-hidden /> Nuevo stakeholder
          </Button>
        </div>
      </header>

      <p className="text-sm text-[var(--color-tertiary)]">
        Catálogo único de personas reutilizable en Charter (Sponsor / Líder Negocio /
        Líder Técnico) y miembros de Áreas.
      </p>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      <section className="overflow-hidden rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)]">
        <table className="w-full text-sm">
          <thead className="bg-[var(--color-subtle)] text-[12px] uppercase tracking-wide text-[var(--color-tertiary)]">
            <tr>
              <SortableTh<Stakeholder> sortKey="name" getter={(s) => s.full_name} ctrl={skCtrl} className="px-4 py-3">Nombre</SortableTh>
              <SortableTh<Stakeholder> sortKey="company" getter={(s) => s.company ?? ""} ctrl={skCtrl} className="px-4 py-3">Empresa / Puesto</SortableTh>
              <SortableTh<Stakeholder> sortKey="contact" getter={(s) => s.email ?? s.phone ?? ""} ctrl={skCtrl} className="px-4 py-3">Contacto</SortableTh>
              <th className="px-4 py-3 text-right" />
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border-subtle)]">
            {loading ? (
              <tr>
                <td colSpan={4} className="px-4 py-12 text-center text-[var(--color-tertiary)]">
                  Cargando…
                </td>
              </tr>
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-12 text-center text-[var(--color-tertiary)]">
                  Sin stakeholders todavía. Crea el primero.
                </td>
              </tr>
            ) : (
              sortedRows.map((s) => (
                <tr key={s.id}>
                  <td className="px-4 py-3 font-medium text-[var(--color-primary)]">
                    {s.full_name}
                    {!s.is_active ? (
                      <span className="ml-2 rounded bg-[var(--color-subtle)] px-1.5 py-0.5 text-[10px] text-[var(--color-tertiary)]">
                        Inactivo
                      </span>
                    ) : null}
                  </td>
                  <td className="px-4 py-3 text-[var(--color-secondary)]">
                    <div>{s.company ?? "—"}</div>
                    <div className="text-xs text-[var(--color-tertiary)]">
                      {s.job_title ?? ""}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-[var(--color-secondary)]">
                    <div>{s.email ?? "—"}</div>
                    <div className="text-xs text-[var(--color-tertiary)]">
                      {s.phone ?? ""}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="inline-flex gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(s.id)}
                        aria-label={`Desactivar ${s.full_name}`}
                        title="Desactivar"
                      >
                        <PowerOff className="h-4 w-4" aria-hidden />
                        <span className="ml-1 text-xs">Desactivar</span>
                      </Button>
                      {!s.is_active ? (
                        <HardDeleteButton
                          preview={() => previewHardDeleteStakeholder(s.id)}
                          hardDelete={(slug) => hardDeleteStakeholder(s.id, slug)}
                          onDeleted={() => void load()}
                          entityLabel="Stakeholder"
                          triggerVariant="ghost"
                          triggerLabel="Eliminar"
                        />
                      ) : null}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </section>

      <Modal
        open={open}
        onClose={() => !submitting && setOpen(false)}
        title="Nuevo stakeholder"
        footer={
          <>
            <Button variant="secondary" onClick={() => setOpen(false)} disabled={submitting}>
              Cancelar
            </Button>
            <Button onClick={submit} loading={submitting}>
              Crear
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <Field label="Nombre completo *">
            <Input
              value={form.full_name}
              onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              autoFocus
            />
          </Field>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Email">
              <Input
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
              />
            </Field>
            <Field label="Teléfono">
              <Input
                value={form.phone}
                onChange={(e) => setForm({ ...form, phone: e.target.value })}
              />
            </Field>
            <Field label="Empresa">
              <Input
                value={form.company}
                onChange={(e) => setForm({ ...form, company: e.target.value })}
              />
            </Field>
            <Field label="Puesto">
              <Input
                value={form.job_title}
                onChange={(e) => setForm({ ...form, job_title: e.target.value })}
              />
            </Field>
          </div>
          <Field label="Notas">
            <Textarea
              rows={3}
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
            />
          </Field>
        </div>
      </Modal>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-[12px] font-medium text-[var(--color-secondary)]">
        {label}
      </span>
      {children}
    </label>
  );
}
