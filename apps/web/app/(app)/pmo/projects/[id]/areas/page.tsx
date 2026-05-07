"use client";

// ENH-078 (2026-05-07) — rediseño post Op A. Las áreas viven en el
// catálogo tenant; esta página muestra las asignadas al proyecto vía
// `area_assignments` y permite crear áreas/equipos/recursos que se
// auto-asignan al proyecto.

import { useParams } from "next/navigation";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import {
  Building2,
  Crown,
  Pencil,
  Plus,
  Trash2,
  User,
  Users,
} from "lucide-react";

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
  createActor,
  createArea,
  createTeam,
  deleteActor,
  deleteArea,
  deleteTeam,
  getAreasTree,
  listAreasByProject,
  setAreaAssignments,
  type Area as CatalogArea,
  type AreaTreeResponse,
  type TreeActor,
  type TreeArea,
  type TreeTeam,
} from "@/lib/api/areas";
import { cn } from "@/lib/cn";

type View = "areas" | "actors";
type ModalKind = "area" | "team" | "actor" | null;

type FlatActor = TreeActor & {
  area_id: string;
  area_name: string;
  team_id: string | null;
  team_name: string | null;
};

export default function ProjectAreasPage() {
  const { id: projectId } = useParams<{ id: string }>();
  const [tree, setTree] = useState<AreaTreeResponse | null>(null);
  const [assignedIds, setAssignedIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [view, setView] = useState<View>("areas");
  const [modal, setModal] = useState<ModalKind>(null);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const [t, byProj] = await Promise.all([
        getAreasTree(false),
        listAreasByProject(projectId),
      ]);
      setTree(t);
      setAssignedIds(new Set(byProj.map((a) => a.id)));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Error al cargar áreas");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  // Áreas visibles del proyecto = catálogo filtrado por assignedIds
  const projectAreas: TreeArea[] = useMemo(() => {
    if (!tree) return [];
    return tree.areas.filter((a) => assignedIds.has(a.id));
  }, [tree, assignedIds]);

  // Tabla actores (vista 2)
  const actorsFlat: FlatActor[] = useMemo(() => {
    const out: FlatActor[] = [];
    for (const a of projectAreas) {
      for (const t of a.teams) {
        for (const r of t.actors) {
          out.push({
            ...r,
            area_id: a.id,
            area_name: a.name,
            team_id: t.id,
            team_name: t.name,
          });
        }
      }
      for (const r of a.unassigned_actors ?? []) {
        out.push({
          ...r,
          area_id: a.id,
          area_name: a.name,
          team_id: null,
          team_name: null,
        });
      }
    }
    return out;
  }, [projectAreas]);

  const filteredAreas = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return projectAreas;
    return projectAreas.filter((a) => a.name.toLowerCase().includes(q));
  }, [projectAreas, search]);

  const filteredActors = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return actorsFlat;
    return actorsFlat.filter(
      (a) =>
        a.name.toLowerCase().includes(q) ||
        (a.email ?? "").toLowerCase().includes(q) ||
        a.area_name.toLowerCase().includes(q),
    );
  }, [actorsFlat, search]);

  // ---------- handlers ----------
  async function ensureAssigned(areaId: string) {
    if (assignedIds.has(areaId)) return;
    // Auto-assign al proyecto. Si ya tiene assignments, los preserva
    // tal cual y agrega project_id.
    // Por simplicidad: enviamos un único scope project_id (replace).
    // Esto puede borrar otros assignments — ENH-078 v1 acepta tradeoff.
    try {
      await setAreaAssignments(areaId, [{ project_id: projectId }]);
    } catch {
      // si falla el auto-assign, no rompemos la creación
    }
  }

  async function handleCreateArea(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setFormError(null);
    setSaving(true);
    const form = new FormData(e.currentTarget);
    const name = String(form.get("name") || "").trim();
    const description = String(form.get("description") || "").trim() || null;
    const leadName = String(form.get("lead_name") || "").trim();
    const leadEmail = String(form.get("lead_email") || "").trim();
    const leadPhone = String(form.get("lead_phone") || "").trim();
    if (!name) {
      setFormError("Nombre es requerido");
      setSaving(false);
      return;
    }
    try {
      const created = await createArea({
        name,
        description,
        is_active: true,
        lead: leadName
          ? {
              name: leadName,
              email: leadEmail || null,
              phone: leadPhone || null,
            }
          : null,
      });
      await ensureAssigned(created.id);
      setModal(null);
      await refresh();
    } catch (err) {
      setFormError(
        err instanceof ApiError ? err.message : "No se pudo crear el área",
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleCreateTeam(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setFormError(null);
    setSaving(true);
    const form = new FormData(e.currentTarget);
    const area_id = String(form.get("area_id") || "");
    const name = String(form.get("name") || "").trim();
    if (!area_id || !name) {
      setFormError("Área y nombre son requeridos");
      setSaving(false);
      return;
    }
    try {
      await createTeam({ area_id, name });
      setModal(null);
      await refresh();
    } catch (err) {
      setFormError(
        err instanceof ApiError ? err.message : "No se pudo crear el equipo",
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleCreateActor(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setFormError(null);
    setSaving(true);
    const form = new FormData(e.currentTarget);
    const area_id = String(form.get("area_id") || "");
    const team_id_raw = String(form.get("team_id") || "");
    const new_team_name = String(form.get("new_team_name") || "").trim();
    const name = String(form.get("name") || "").trim();
    const email = String(form.get("email") || "").trim();
    const phone = String(form.get("phone") || "").trim();
    if (!area_id || !name) {
      setFormError("Área y nombre son requeridos");
      setSaving(false);
      return;
    }
    try {
      let team_id: string | null = team_id_raw || null;
      if (!team_id && new_team_name) {
        const t = await createTeam({ area_id, name: new_team_name });
        team_id = t.id;
      }
      await createActor({
        team_id,
        name,
        email: email || null,
        phone: phone || null,
      });
      setModal(null);
      await refresh();
    } catch (err) {
      setFormError(
        err instanceof ApiError ? err.message : "No se pudo crear el recurso",
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(kind: "area" | "team" | "actor", id: string, name: string) {
    if (!confirm(`¿Eliminar ${kind} "${name}"?`)) return;
    try {
      if (kind === "area") await deleteArea(id);
      else if (kind === "team") await deleteTeam(id);
      else await deleteActor(id);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al eliminar");
    }
  }

  return (
    <div className="space-y-4 p-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-[var(--color-primary)]">
            Áreas del proyecto
          </h1>
          <p className="text-sm text-[var(--color-tertiary)]">
            Catálogo compartido — las áreas creadas aquí quedan en el catálogo
            tenant y se auto-asignan a este proyecto.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => { setFormError(null); setModal("area"); }} size="sm">
            <Plus className="mr-1 h-4 w-4" /> Nueva área
          </Button>
          <Button
            onClick={() => { setFormError(null); setModal("team"); }}
            size="sm"
            variant="secondary"
            disabled={projectAreas.length === 0}
          >
            <Plus className="mr-1 h-4 w-4" /> Nuevo equipo
          </Button>
          <Button
            onClick={() => { setFormError(null); setModal("actor"); }}
            size="sm"
            variant="secondary"
            disabled={projectAreas.length === 0}
          >
            <Plus className="mr-1 h-4 w-4" /> Nuevo recurso
          </Button>
        </div>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]">
        <div className="flex flex-wrap items-center gap-3 border-b border-[var(--border-default)] p-4">
          <Input
            type="search"
            value={search}
            placeholder="Buscar"
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Buscar"
            className="min-w-[240px] flex-1"
          />
          <div
            role="radiogroup"
            aria-label="Vista"
            className="inline-flex rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-surface)] p-0.5"
          >
            {(
              [
                { v: "areas", label: "Áreas" },
                { v: "actors", label: "Actores" },
              ] as const
            ).map((opt) => {
              const active = view === opt.v;
              return (
                <button
                  key={opt.v}
                  type="button"
                  role="radio"
                  aria-checked={active}
                  onClick={() => setView(opt.v)}
                  className={cn(
                    "rounded-[var(--radius-sm)] px-3 py-1.5 text-xs font-medium transition-colors",
                    active
                      ? "bg-[var(--color-primary)] text-[var(--color-inverse)]"
                      : "text-[var(--text-secondary)] hover:bg-[var(--color-subtle)]",
                  )}
                >
                  {opt.label}
                </button>
              );
            })}
          </div>
        </div>

        {loading ? (
          <div className="space-y-2 p-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        ) : view === "areas" ? (
          filteredAreas.length === 0 ? (
            <div className="p-10 text-center text-sm text-[var(--color-tertiary)]">
              {projectAreas.length === 0
                ? "Aún no hay áreas asignadas a este proyecto."
                : "Ningún área coincide con la búsqueda."}
            </div>
          ) : (
            <div className="divide-y divide-[var(--border-subtle)]">
              {filteredAreas.map((area) => (
                <AreaTreeNode
                  key={area.id}
                  area={area}
                  onDelete={handleDelete}
                />
              ))}
            </div>
          )
        ) : filteredActors.length === 0 ? (
          <div className="p-10 text-center text-sm text-[var(--color-tertiary)]">
            {actorsFlat.length === 0
              ? "Aún no hay actores registrados en las áreas asignadas."
              : "Ningún actor coincide con la búsqueda."}
          </div>
        ) : (
          <ActorsTable rows={filteredActors} onDelete={handleDelete} />
        )}
      </section>

      {/* Modales */}
      <Modal open={modal === "area"} onClose={() => setModal(null)} title="Nueva área">
        <form onSubmit={handleCreateArea} className="space-y-3">
          {formError ? <Banner variant="danger">{formError}</Banner> : null}
          <Field label="Nombre del área" required>
            <Input name="name" required />
          </Field>
          <Field label="Líder del área">
            <Input name="lead_name" placeholder="Nombre completo (opcional)" />
          </Field>
          <Field label="Contacto líder (correo)">
            <Input name="lead_email" type="email" placeholder="lider@empresa.com" />
          </Field>
          <Field label="Teléfono líder (opcional)">
            <Input name="lead_phone" type="tel" />
          </Field>
          <Field label="Descripción">
            <Textarea name="description" rows={2} />
          </Field>
          <p className="text-xs text-[var(--color-tertiary)]">
            Equipos y recursos se agregan después con los botones "Nuevo
            equipo" / "Nuevo recurso". El líder se persiste como Actor del
            área con flag is_lead=true.
          </p>
          <FormActions onCancel={() => setModal(null)} saving={saving} label="Crear área" />
        </form>
      </Modal>

      <Modal open={modal === "team"} onClose={() => setModal(null)} title="Nuevo equipo">
        <form onSubmit={handleCreateTeam} className="space-y-3">
          {formError ? <Banner variant="danger">{formError}</Banner> : null}
          <Field label="Área" required>
            <Select name="area_id" required>
              <option value="">— Selecciona —</option>
              {projectAreas.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Nombre del equipo" required>
            <Input name="name" required />
          </Field>
          <p className="text-xs text-[var(--color-tertiary)]">
            Los recursos del equipo se agregan después con "Nuevo recurso".
          </p>
          <FormActions onCancel={() => setModal(null)} saving={saving} label="Crear equipo" />
        </form>
      </Modal>

      <Modal open={modal === "actor"} onClose={() => setModal(null)} title="Nuevo recurso">
        <form onSubmit={handleCreateActor} className="space-y-3">
          {formError ? <Banner variant="danger">{formError}</Banner> : null}
          <NewResourceForm areas={projectAreas} />
          <FormActions onCancel={() => setModal(null)} saving={saving} label="Crear recurso" />
        </form>
      </Modal>
    </div>
  );
}

function Field({
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

function FormActions({
  onCancel,
  saving,
  label,
}: {
  onCancel: () => void;
  saving: boolean;
  label: string;
}) {
  return (
    <div className="flex justify-end gap-2 pt-2">
      <Button type="button" variant="ghost" onClick={onCancel} disabled={saving}>
        Cancelar
      </Button>
      <Button type="submit" disabled={saving}>
        {saving ? "Guardando…" : label}
      </Button>
    </div>
  );
}

function NewResourceForm({ areas }: { areas: TreeArea[] }) {
  const [areaId, setAreaId] = useState<string>(areas[0]?.id ?? "");
  const teamsInArea = areas.find((a) => a.id === areaId)?.teams ?? [];
  return (
    <>
      <Field label="Área" required>
        <Select
          name="area_id"
          required
          value={areaId}
          onChange={(e) => setAreaId(e.target.value)}
        >
          <option value="">— Selecciona —</option>
          {areas.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name}
            </option>
          ))}
        </Select>
      </Field>
      <Field label="Equipo (opcional — si vacío, se crea o queda sin equipo)">
        <Select name="team_id">
          <option value="">— Sin equipo —</option>
          {teamsInArea.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </Select>
      </Field>
      <Field label="Nuevo equipo (si no existe, se crea con este nombre)">
        <Input name="new_team_name" placeholder="Opcional" />
      </Field>
      <Field label="Nombre del recurso" required>
        <Input name="name" required />
      </Field>
      <Field label="Correo">
        <Input name="email" type="email" />
      </Field>
      <Field label="Teléfono (opcional)">
        <Input name="phone" type="tel" />
      </Field>
    </>
  );
}

function AreaTreeNode({
  area,
  onDelete,
}: {
  area: TreeArea;
  onDelete: (kind: "area" | "team" | "actor", id: string, name: string) => void;
}) {
  return (
    <div className="px-4 py-3">
      <div className="flex items-center gap-2">
        <Building2 className="h-4 w-4 text-[var(--color-primary)]" />
        <span className="font-medium text-[var(--color-primary)]">
          {area.name}
        </span>
        {!area.is_active ? <Badge variant="danger">Inactiva</Badge> : null}
        <span className="ml-auto flex gap-1">
          <Button size="sm" variant="ghost" disabled title="Editar (próximamente)">
            <Pencil className="h-3.5 w-3.5" />
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => onDelete("area", area.id, area.name)}
            title="Eliminar"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </span>
      </div>
      <div className="ml-6 mt-2 space-y-1 border-l border-[var(--border-subtle)] pl-3">
        {area.teams.map((t) => (
          <TeamNode
            key={t.id}
            team={t}
            leadActorId={area.lead_actor_id ?? null}
            onDelete={onDelete}
          />
        ))}
        {(area.unassigned_actors ?? []).map((r) => (
          <ActorRow
            key={r.id}
            actor={r}
            isLead={r.id === area.lead_actor_id}
            onDelete={(id, name) => onDelete("actor", id, name)}
          />
        ))}
        {area.teams.length === 0 && (area.unassigned_actors ?? []).length === 0 ? (
          <p className="text-xs text-[var(--color-tertiary)]">
            Sin equipos ni recursos. Usa "Nuevo equipo" o "Nuevo recurso".
          </p>
        ) : null}
      </div>
    </div>
  );
}

function TeamNode({
  team,
  leadActorId,
  onDelete,
}: {
  team: TreeTeam;
  leadActorId: string | null;
  onDelete: (kind: "area" | "team" | "actor", id: string, name: string) => void;
}) {
  return (
    <div>
      <div className="flex items-center gap-2 text-sm">
        <Users className="h-3.5 w-3.5 text-[var(--text-secondary)]" />
        <span className="text-[var(--text-secondary)]">{team.name}</span>
        <Button
          size="sm"
          variant="ghost"
          onClick={() => onDelete("team", team.id, team.name)}
          title="Eliminar equipo"
          className="ml-1"
        >
          <Trash2 className="h-3 w-3" />
        </Button>
      </div>
      <div className="ml-5 space-y-0.5">
        {team.actors.map((a) => (
          <ActorRow
            key={a.id}
            actor={a}
            isLead={a.id === leadActorId}
            onDelete={(id, name) => onDelete("actor", id, name)}
          />
        ))}
      </div>
    </div>
  );
}

function ActorRow({
  actor,
  isLead,
  onDelete,
}: {
  actor: TreeActor;
  isLead: boolean;
  onDelete: (id: string, name: string) => void;
}) {
  const lead = isLead || actor.is_lead;
  return (
    <div className="flex items-center gap-2 text-xs">
      {lead ? (
        <Crown className="h-3 w-3 text-[var(--color-warning)]" />
      ) : (
        <User className="h-3 w-3 text-[var(--color-tertiary)]" />
      )}
      <span className={cn(
        lead ? "font-medium text-[var(--color-primary)]" : "text-[var(--text-secondary)]",
      )}>
        {actor.name}
      </span>
      {lead ? (
        <span className="text-[var(--color-warning)]">*Líder de área</span>
      ) : null}
      {actor.email ? (
        <span className="text-[var(--color-tertiary)]">· {actor.email}</span>
      ) : null}
      <Button
        size="sm"
        variant="ghost"
        onClick={() => onDelete(actor.id, actor.name)}
        title="Eliminar"
        className="ml-auto"
      >
        <Trash2 className="h-3 w-3" />
      </Button>
    </div>
  );
}

function ActorsTable({
  rows,
  onDelete,
}: {
  rows: FlatActor[];
  onDelete: (kind: "area" | "team" | "actor", id: string, name: string) => void;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="border-b border-[var(--border-default)] text-left text-xs uppercase tracking-wide text-[var(--color-tertiary)]">
          <tr>
            <th className="px-3 py-2 font-medium">Nombre</th>
            <th className="px-3 py-2 font-medium">Correo</th>
            <th className="px-3 py-2 font-medium">Teléfono</th>
            <th className="px-3 py-2 font-medium">Equipo</th>
            <th className="px-3 py-2 font-medium">Área</th>
            <th className="w-20 px-3 py-2" aria-label="Acciones" />
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id} className="border-b border-[var(--border-subtle)] hover:bg-[var(--color-subtle)]">
              <td className="px-3 py-2 text-[var(--color-primary)]">
                <span className="font-medium">{r.name}</span>
                {r.is_lead ? (
                  <Badge variant="warning" className="ml-2">Líder</Badge>
                ) : null}
              </td>
              <td className="px-3 py-2 text-[var(--color-secondary)]">
                {r.email ? (
                  <a href={`mailto:${r.email}`} className="hover:underline">
                    {r.email}
                  </a>
                ) : (
                  "—"
                )}
              </td>
              <td className="px-3 py-2 text-[var(--color-secondary)]">{r.phone || "—"}</td>
              <td className="px-3 py-2 text-[var(--color-secondary)]">{r.team_name || "—"}</td>
              <td className="px-3 py-2 text-[var(--color-secondary)]">{r.area_name}</td>
              <td className="px-3 py-2 text-right">
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => onDelete("actor", r.id, r.name)}
                  title="Eliminar"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
