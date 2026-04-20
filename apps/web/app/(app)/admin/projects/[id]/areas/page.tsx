"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Building2, Mail, Pencil, Plus, Trash2, User, Users } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api";
import {
  createProjectArea,
  deleteProjectArea,
  listProjectAreas,
  updateProjectArea,
  type ProjectArea,
  type ProjectAreaType,
} from "@/lib/api/project-areas";
import { cn } from "@/lib/cn";

const TYPE_LABEL: Record<ProjectAreaType, string> = {
  area: "Área",
  actor: "Actor",
  team: "Equipo",
};

const TYPE_ICON: Record<ProjectAreaType, React.ComponentType<{ className?: string }>> = {
  area: Building2,
  actor: User,
  team: Users,
};

type FormState = {
  name: string;
  type: ProjectAreaType;
  description: string;
  contact_name: string;
  contact_email: string;
};

const EMPTY_FORM: FormState = {
  name: "",
  type: "area",
  description: "",
  contact_name: "",
  contact_email: "",
};

export default function ProjectAreasPage() {
  const { id } = useParams<{ id: string }>();
  const [rows, setRows] = useState<ProjectArea[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [typeFilter, setTypeFilter] = useState<string>("");
  const [search, setSearch] = useState("");

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<ProjectArea | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<ProjectArea | null>(null);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const r = await listProjectAreas(id, {
        type: (typeFilter || undefined) as ProjectAreaType | undefined,
      });
      setRows(r);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar áreas");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, typeFilter]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter(
      (r) =>
        r.name.toLowerCase().includes(q) ||
        (r.contact_name ?? "").toLowerCase().includes(q),
    );
  }, [rows, search]);

  function openCreate() {
    setEditing(null);
    setForm(EMPTY_FORM);
    setFormError(null);
    setModalOpen(true);
  }

  function openEdit(area: ProjectArea) {
    setEditing(area);
    setForm({
      name: area.name,
      type: area.type,
      description: area.description ?? "",
      contact_name: area.contact_name ?? "",
      contact_email: area.contact_email ?? "",
    });
    setFormError(null);
    setModalOpen(true);
  }

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (form.name.trim().length < 2) {
      setFormError("El nombre es obligatorio (min 2 caracteres)");
      return;
    }
    const emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (form.contact_email && !emailRe.test(form.contact_email.trim())) {
      setFormError("Email inválido");
      return;
    }
    setSaving(true);
    setFormError(null);
    try {
      const payload = {
        name: form.name.trim(),
        type: form.type,
        description: form.description.trim() || null,
        contact_name: form.contact_name.trim() || null,
        contact_email: form.contact_email.trim() || null,
      };
      if (editing) {
        await updateProjectArea(editing.id, payload);
      } else {
        await createProjectArea(id, payload);
      }
      setModalOpen(false);
      await refresh();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Error al guardar");
    } finally {
      setSaving(false);
    }
  }

  async function confirmRemove() {
    if (!confirmDelete) return;
    try {
      await deleteProjectArea(confirmDelete.id);
      setConfirmDelete(null);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al eliminar");
    }
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
            <span>Áreas</span>
          </nav>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
            Áreas y actores
          </h1>
          <p className="mt-1 text-[13px] text-[var(--text-tertiary)]">
            Registra áreas, equipos y actores stakeholder del proyecto. Pueden
            referenciarse desde tareas, RAIDs y minutas aunque no tengan
            cuenta en la plataforma.
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="h-4 w-4" aria-hidden />
          Nueva área
        </Button>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]">
        <div className="grid gap-3 border-b border-[var(--border-default)] p-4 sm:grid-cols-[1fr_180px]">
          <Input
            type="search"
            value={search}
            placeholder="Buscar por nombre o contacto"
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Buscar áreas"
          />
          <Select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            aria-label="Filtrar por tipo"
          >
            <option value="">Todos los tipos</option>
            <option value="area">Áreas</option>
            <option value="actor">Actores</option>
            <option value="team">Equipos</option>
          </Select>
        </div>

        {loading ? (
          <div className="space-y-2 p-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-14 w-full" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-10 text-center text-sm text-[var(--color-tertiary)]">
            {rows.length === 0
              ? "Aún no hay áreas registradas."
              : "Ningún área coincide con los filtros."}
          </div>
        ) : (
          <ul className="divide-y divide-[var(--border-subtle)]">
            {filtered.map((a) => {
              const Icon = TYPE_ICON[a.type];
              return (
                <li
                  key={a.id}
                  className="flex items-center gap-3 px-4 py-3 hover:bg-[var(--color-subtle)]"
                >
                  <div
                    className={cn(
                      "flex h-9 w-9 items-center justify-center rounded-full border border-[var(--border-default)] bg-[var(--color-subtle)] text-[var(--color-tertiary)]",
                    )}
                  >
                    <Icon className="h-4 w-4" aria-hidden />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="truncate text-sm font-medium text-[var(--color-primary)]">
                        {a.name}
                      </span>
                      <Badge variant="neutral">{TYPE_LABEL[a.type]}</Badge>
                      {!a.is_active ? <Badge variant="danger">Inactiva</Badge> : null}
                    </div>
                    <div className="mt-0.5 flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-[var(--color-tertiary)]">
                      {a.contact_name ? <span>{a.contact_name}</span> : null}
                      {a.contact_email ? (
                        <a
                          href={`mailto:${a.contact_email}`}
                          className="inline-flex items-center gap-1 hover:underline"
                        >
                          <Mail className="h-3 w-3" aria-hidden />
                          {a.contact_email}
                        </a>
                      ) : null}
                      {a.description ? (
                        <span className="line-clamp-1">{a.description}</span>
                      ) : null}
                    </div>
                  </div>
                  <div className="flex gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => openEdit(a)}
                      title="Editar"
                    >
                      <Pencil className="h-4 w-4" aria-hidden />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setConfirmDelete(a)}
                      title="Eliminar"
                    >
                      <Trash2 className="h-4 w-4" aria-hidden />
                    </Button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editing ? "Editar área" : "Nueva área"}
      >
        <form onSubmit={handleSubmit} noValidate className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label
                htmlFor="area-name"
                className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
              >
                Nombre
              </label>
              <Input
                id="area-name"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                required
                minLength={2}
                maxLength={200}
              />
            </div>
            <div>
              <label
                htmlFor="area-type"
                className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
              >
                Tipo
              </label>
              <Select
                id="area-type"
                value={form.type}
                onChange={(e) =>
                  setForm({ ...form, type: e.target.value as ProjectAreaType })
                }
              >
                <option value="area">Área</option>
                <option value="actor">Actor</option>
                <option value="team">Equipo</option>
              </Select>
            </div>
            <div>
              <label
                htmlFor="contact-name"
                className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
              >
                Contacto (nombre)
              </label>
              <Input
                id="contact-name"
                value={form.contact_name}
                onChange={(e) =>
                  setForm({ ...form, contact_name: e.target.value })
                }
              />
            </div>
            <div>
              <label
                htmlFor="contact-email"
                className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
              >
                Contacto (email)
              </label>
              <Input
                id="contact-email"
                type="email"
                value={form.contact_email}
                onChange={(e) =>
                  setForm({ ...form, contact_email: e.target.value })
                }
              />
            </div>
          </div>
          <div>
            <label
              htmlFor="area-desc"
              className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
            >
              Descripción
            </label>
            <Textarea
              id="area-desc"
              rows={3}
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </div>
          {formError ? <Banner variant="danger">{formError}</Banner> : null}
          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="ghost"
              onClick={() => setModalOpen(false)}
            >
              Cancelar
            </Button>
            <Button type="submit" loading={saving}>
              {editing ? "Guardar" : "Crear"}
            </Button>
          </div>
        </form>
      </Modal>

      <Modal
        open={confirmDelete !== null}
        onClose={() => setConfirmDelete(null)}
        title="Eliminar área"
      >
        <p className="text-sm text-[var(--color-secondary)]">
          ¿Seguro que quieres eliminar "{confirmDelete?.name}"? Esta acción no
          se puede deshacer.
        </p>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="ghost" onClick={() => setConfirmDelete(null)}>
            Cancelar
          </Button>
          <Button variant="danger" onClick={confirmRemove}>
            Eliminar
          </Button>
        </div>
      </Modal>
    </div>
  );
}
