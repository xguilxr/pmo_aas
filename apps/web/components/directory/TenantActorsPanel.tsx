"use client";

// ENH-086 — Panel admin tenant para personas (actors enriquecidos).
// Reemplaza la vista legacy de "Actores" (que asumía Area→Team→Actor)
// por una tabla plana del catálogo tenant con CRUD sobre los campos
// enriquecidos de US-114 (company, job_title, manager_actor_id) +
// area_id (área funcional).

import { useEffect, useMemo, useState } from "react";
import { Pencil, Plus, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import {
  createActor,
  deleteActor,
  listActors,
  listAreas,
  updateActor,
  type Actor,
  type Area,
} from "@/lib/api/areas";

export function TenantActorsPanel() {
  const [actors, setActors] = useState<Actor[]>([]);
  const [areas, setAreas] = useState<Area[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [areaFilter, setAreaFilter] = useState("");
  const [editing, setEditing] = useState<Actor | null>(null);
  const [creating, setCreating] = useState(false);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const [a, ar] = await Promise.all([listActors(), listAreas()]);
      setActors(a);
      setAreas(ar);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Error al cargar");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  const areaById = useMemo(
    () => Object.fromEntries(areas.map((a) => [a.id, a])),
    [areas],
  );

  const filtered = useMemo(() => {
    let rows = actors;
    if (areaFilter) rows = rows.filter((a) => a.area_id === areaFilter);
    const q = search.trim().toLowerCase();
    if (q) {
      rows = rows.filter(
        (a) =>
          a.name.toLowerCase().includes(q) ||
          (a.email ?? "").toLowerCase().includes(q) ||
          (a.company ?? "").toLowerCase().includes(q) ||
          (a.job_title ?? "").toLowerCase().includes(q),
      );
    }
    return rows;
  }, [actors, areaFilter, search]);

  async function handleDelete(actor: Actor) {
    if (!confirm(`¿Eliminar persona "${actor.name}"?`)) return;
    try {
      await deleteActor(actor.id);
      await refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Error al eliminar");
    }
  }

  if (loading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <Input
          placeholder="Buscar persona, email, empresa…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-sm"
        />
        <Select
          value={areaFilter}
          onChange={(e) => setAreaFilter(e.target.value)}
          className="max-w-xs"
        >
          <option value="">Todas las áreas</option>
          {areas.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name}
            </option>
          ))}
        </Select>
        <div className="ml-auto">
          <Button size="sm" onClick={() => setCreating(true)}>
            <Plus className="mr-1 h-4 w-4" /> Nueva persona
          </Button>
        </div>
      </div>

      {error ? (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      <div className="overflow-x-auto rounded-md border">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 text-left text-xs uppercase">
            <tr>
              <th className="px-3 py-2">Nombre</th>
              <th className="px-3 py-2">Email</th>
              <th className="px-3 py-2">Empresa / Cargo</th>
              <th className="px-3 py-2">Área funcional</th>
              <th className="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td
                  colSpan={5}
                  className="p-8 text-center text-xs text-[var(--color-tertiary)]"
                >
                  {actors.length === 0
                    ? "Sin personas en el catálogo tenant."
                    : "Ningún match para el filtro."}
                </td>
              </tr>
            ) : (
              filtered.map((a) => (
                <tr key={a.id} className="border-t hover:bg-muted/30">
                  <td className="px-3 py-2">
                    <span className="font-medium text-[var(--color-primary)]">
                      {a.name}
                    </span>
                    {!a.is_active ? (
                      <Badge variant="danger" className="ml-2">
                        Inactivo
                      </Badge>
                    ) : null}
                  </td>
                  <td className="px-3 py-2 text-xs text-[var(--color-secondary)]">
                    {a.email ?? "—"}
                  </td>
                  <td className="px-3 py-2 text-xs">
                    <div>{a.company ?? "—"}</div>
                    <div className="text-[var(--color-tertiary)]">
                      {a.job_title ?? ""}
                    </div>
                  </td>
                  <td className="px-3 py-2 text-xs">
                    {a.area_id ? areaById[a.area_id]?.name ?? "—" : "—"}
                  </td>
                  <td className="px-3 py-2 text-right">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setEditing(a)}
                      title="Editar"
                    >
                      <Pencil className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleDelete(a)}
                      title="Eliminar"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {creating ? (
        <ActorModal
          actor={null}
          areas={areas}
          onClose={() => setCreating(false)}
          onSaved={() => {
            setCreating(false);
            refresh();
          }}
        />
      ) : null}
      {editing ? (
        <ActorModal
          actor={editing}
          areas={areas}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            refresh();
          }}
        />
      ) : null}
    </div>
  );
}

function ActorModal({
  actor,
  areas,
  onClose,
  onSaved,
}: {
  actor: Actor | null;
  areas: Area[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [name, setName] = useState(actor?.name ?? "");
  const [email, setEmail] = useState(actor?.email ?? "");
  const [phone, setPhone] = useState(actor?.phone ?? "");
  const [company, setCompany] = useState(actor?.company ?? "");
  const [jobTitle, setJobTitle] = useState(actor?.job_title ?? "");
  const [areaId, setAreaId] = useState(actor?.area_id ?? "");
  const [isActive, setIsActive] = useState(actor?.is_active ?? true);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function submit() {
    if (!name.trim()) {
      setErr("Nombre requerido");
      return;
    }
    setSaving(true);
    setErr(null);
    try {
      const payload = {
        name: name.trim(),
        email: email.trim() || null,
        phone: phone.trim() || null,
        company: company.trim() || null,
        job_title: jobTitle.trim() || null,
        area_id: areaId || null,
        is_active: isActive,
      };
      if (actor) {
        await updateActor(actor.id, payload as any);
      } else {
        await createActor(payload as any);
      }
      onSaved();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Error al guardar");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal
      open
      title={actor ? "Editar persona" : "Nueva persona"}
      onClose={onClose}
    >
      <div className="space-y-3">
        <FieldLabel label="Nombre" required>
          <Input value={name} onChange={(e) => setName(e.target.value)} />
        </FieldLabel>
        <div className="grid grid-cols-2 gap-2">
          <FieldLabel label="Email">
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </FieldLabel>
          <FieldLabel label="Teléfono">
            <Input
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
            />
          </FieldLabel>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <FieldLabel label="Empresa">
            <Input
              value={company}
              onChange={(e) => setCompany(e.target.value)}
            />
          </FieldLabel>
          <FieldLabel label="Cargo">
            <Input
              value={jobTitle}
              onChange={(e) => setJobTitle(e.target.value)}
            />
          </FieldLabel>
        </div>
        <FieldLabel label="Área funcional">
          <Select value={areaId} onChange={(e) => setAreaId(e.target.value)}>
            <option value="">— Sin área —</option>
            {areas.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </Select>
        </FieldLabel>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={isActive}
            onChange={(e) => setIsActive(e.target.checked)}
          />
          <span>Activa</span>
        </label>
        {err ? <p className="text-sm text-red-600">{err}</p> : null}
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="ghost" onClick={onClose} disabled={saving}>
            Cancelar
          </Button>
          <Button onClick={submit} disabled={saving}>
            {saving ? "Guardando…" : "Guardar"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}

function FieldLabel({
  label,
  required,
  children,
}: {
  label: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-xs font-medium text-[var(--text-secondary)]">
        {label}
        {required ? " *" : ""}
      </span>
      {children}
    </label>
  );
}
