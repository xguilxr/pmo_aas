"use client";

// US-097 — Catálogo tenant Áreas → Equipos → Actores.
// Árbol expandible 3 niveles con CRUD por nodo.
import { useEffect, useState, type FormEvent } from "react";
import {
  ArrowRightLeft,
  Building2,
  ChevronDown,
  ChevronRight,
  Network,
  Pencil,
  Plus,
  Trash2,
  User,
  Users,
} from "lucide-react";

import { Banner } from "@/components/ui/banner";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
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
  listAreaAssignments,
  reassignActor,
  setAreaAssignments,
  syncPmoUsers,
  updateActor,
  updateArea,
  updateTeam,
  type AreaAssignment,
  type AreaTreeResponse,
  type AssignmentScope,
  type TreeActor,
  type TreeArea,
  type TreeTeam,
} from "@/lib/api/areas";
import { listOrganizations, listPrograms, type Organization, type Program } from "@/lib/api/organizations";
import { listProjects, type Project } from "@/lib/api/projects";
import { Select } from "@/components/ui/select";
import { cn } from "@/lib/cn";

type NodeKind = "area" | "team" | "actor";

type EditingNode =
  | {
      kind: "area";
      id: string;
      name: string;
      description: string;
      lead_name: string;
    }
  | {
      kind: "team";
      id: string;
      area_id: string;
      name: string;
      description: string;
    }
  | {
      kind: "actor";
      id: string;
      team_id: string | null;
      area_id: string | null;
      name: string;
      email: string;
      phone: string;
    };

type CreatingNode =
  | { kind: "area" }
  | { kind: "team"; area_id: string; area_name: string }
  | {
      kind: "actor";
      team_id: string | null;
      team_label: string;
    };

export default function AreasAdminPage() {
  const [tree, setTree] = useState<AreaTreeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  // ENH-080: cache de assignments por área. Lazy-load al expandir.
  // null = no cargado, [] = cargado vacío, [...] = cargado con assignments.
  const [assignments, setAssignments] = useState<
    Record<string, AreaAssignment[] | null>
  >({});

  // ENH-083: catálogo de Orgs/Programas/Proyectos del tenant para el
  // editor de assignments. Se carga 1 vez al montar.
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [programs, setPrograms] = useState<Program[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  // Set de scopes seleccionados en el modal de edit (mientras se edita).
  // Format: "global" | `org:${id}` | `prog:${id}` | `proj:${id}`.
  const [editingScopes, setEditingScopes] = useState<Set<string>>(new Set());

  const [creating, setCreating] = useState<CreatingNode | null>(null);
  const [editing, setEditing] = useState<EditingNode | null>(null);
  const [submitting, setSubmitting] = useState(false);
  // US-099: state del modal de reasignación masiva.
  const [reassigning, setReassigning] = useState<{
    source: TreeActor;
    targetId: string;
  } | null>(null);

  const [form, setForm] = useState<{
    name: string;
    description: string;
    lead_name: string;
    email: string;
    phone: string;
    /** BUG-061: scope del área. "" = global; uuid = atada a esa org. */
    organization_id: string;
  }>({
    name: "",
    description: "",
    lead_name: "",
    email: "",
    phone: "",
    organization_id: "",
  });

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await getAreasTree({ includeInactive: true });
      setTree(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar áreas");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    // ENH-082: sincroniza tenant users → Actores PMO al entrar al
    // catálogo. Idempotente; el load reentra después para refrescar
    // el árbol con los nuevos actores.
    (async () => {
      try {
        await syncPmoUsers();
      } catch {
        // Si el sync falla, seguimos cargando — no es bloqueante.
      }
      await load();
    })();
    // ENH-083: catálogo de scopes para el editor de assignments.
    (async () => {
      try {
        const [o, p, pr] = await Promise.all([
          listOrganizations(),
          listPrograms(),
          listProjects(),
        ]);
        setOrgs(o);
        setPrograms(p);
        setProjects(pr);
      } catch {
        // No-op; sin catálogo el editor queda con sólo el toggle Global.
      }
    })();
  }, []);

  function toggle(id: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  // ENH-080: carga lazy de assignments cuando se expande un área.
  async function ensureAssignmentsLoaded(areaId: string) {
    if (assignments[areaId] !== undefined) return;
    // Marca como "cargando" con array vacío para evitar dobles fetches.
    setAssignments((prev) => ({ ...prev, [areaId]: prev[areaId] ?? null }));
    try {
      const rows = await listAreaAssignments(areaId);
      setAssignments((prev) => ({ ...prev, [areaId]: rows }));
    } catch {
      setAssignments((prev) => ({ ...prev, [areaId]: [] }));
    }
  }

  function toggleArea(areaId: string) {
    if (!expanded.has(areaId)) {
      void ensureAssignmentsLoaded(areaId);
    }
    toggle(areaId);
  }

  function openCreate(node: CreatingNode) {
    setForm({ name: "", description: "", lead_name: "", email: "", phone: "", organization_id: "" });
    setCreating(node);
  }

  function openEditArea(a: TreeArea) {
    setForm({ name: "", description: "", lead_name: "", email: "", phone: "", organization_id: "" });
    setEditing({
      kind: "area",
      id: a.id,
      name: a.name,
      description: a.description ?? "",
      // ENH-078: lead_name fue removido del shape; el lead se gestiona
      // como Actor con is_lead=true. Edit panel inline sigue diferido.
      lead_name: "",
    });
    // ENH-083: hidrata scopes desde el cache local. Si todavía no se
    // cargó, lo trae ahora.
    void (async () => {
      let rows = assignments[a.id] ?? null;
      if (rows === null || rows === undefined) {
        try {
          rows = await listAreaAssignments(a.id);
          setAssignments((prev) => ({ ...prev, [a.id]: rows ?? [] }));
        } catch {
          rows = [];
        }
      }
      const set = new Set<string>();
      for (const r of rows) {
        if (r.is_global) set.add("global");
        else if (r.organization_id) set.add(`org:${r.organization_id}`);
        else if (r.program_id) set.add(`prog:${r.program_id}`);
        else if (r.project_id) set.add(`proj:${r.project_id}`);
      }
      setEditingScopes(set);
    })();
  }

  function toggleScope(key: string) {
    setEditingScopes((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        // Global es mutex con todo lo demás.
        if (key === "global") next.clear();
        else next.delete("global");
        next.add(key);
      }
      return next;
    });
  }

  function openEditTeam(area_id: string, t: TreeTeam) {
    setEditing({
      kind: "team",
      id: t.id,
      area_id,
      name: t.name,
      description: t.description ?? "",
    });
  }

  function openEditActor(team_id: string | null, a: TreeActor) {
    setEditing({
      kind: "actor",
      id: a.id,
      team_id,
      // ENH-084 rework: hidrata area_id desde el actor (puede venir
      // del catálogo) o derivado del team padre si está disponible.
      area_id: a.area_id ?? null,
      name: a.name,
      email: a.email ?? "",
      phone: a.phone ?? "",
    });
  }

  async function submitCreate(e: FormEvent) {
    e.preventDefault();
    if (!creating) return;
    setSubmitting(true);
    setError(null);
    try {
      if (creating.kind === "area") {
        const leadName = form.lead_name.trim();
        await createArea({
          name: form.name.trim(),
          description: form.description.trim() || null,
          // BUG-061: scope opcional. "" = global; uuid = atada a esa org.
          organization_id: form.organization_id || null,
          // ENH-078: líder se persiste como Actor con is_lead=true.
          lead: leadName
            ? {
                name: leadName,
                email: form.email.trim() || null,
                phone: form.phone.trim() || null,
              }
            : null,
        });
      } else if (creating.kind === "team") {
        await createTeam({
          area_id: creating.area_id,
          name: form.name.trim(),
          description: form.description.trim() || null,
        });
      } else {
        await createActor({
          team_id: creating.team_id,
          name: form.name.trim(),
          email: form.email.trim() || null,
          phone: form.phone.trim() || null,
        });
      }
      setCreating(null);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al crear");
    } finally {
      setSubmitting(false);
    }
  }

  async function submitEdit(e: FormEvent) {
    e.preventDefault();
    if (!editing) return;
    setSubmitting(true);
    setError(null);
    try {
      if (editing.kind === "area") {
        // ENH-078: lead_name ya no existe; el líder se gestiona vía
        // lead_actor_id (selector de actor). En esta versión legacy
        // del modal admin sólo persistimos los campos básicos.
        await updateArea(editing.id, {
          name: editing.name.trim(),
          description: editing.description.trim() || null,
        });
        // ENH-083: persistir assignments (replace strategy).
        const scopes: AssignmentScope[] = [];
        for (const key of editingScopes) {
          if (key === "global") scopes.push({ is_global: true });
          else if (key.startsWith("org:"))
            scopes.push({ organization_id: key.slice(4) });
          else if (key.startsWith("prog:"))
            scopes.push({ program_id: key.slice(5) });
          else if (key.startsWith("proj:"))
            scopes.push({ project_id: key.slice(5) });
        }
        await setAreaAssignments(editing.id, scopes);
        // Refetch para obtener nombres legibles (PUT no resuelve joins).
        try {
          const refreshed = await listAreaAssignments(editing.id);
          setAssignments((prev) => ({ ...prev, [editing.id]: refreshed }));
        } catch {
          /* ignore */
        }
      } else if (editing.kind === "team") {
        await updateTeam(editing.id, {
          name: editing.name.trim(),
          description: editing.description.trim() || null,
        });
      } else {
        await updateActor(editing.id, {
          name: editing.name.trim(),
          email: editing.email.trim() || null,
          phone: editing.phone.trim() || null,
          // ENH-084: permite mover el actor entre teams (de cualquier
          // área) o dejarlo sin team via NULL.
          team_id: editing.team_id ?? null,
          // ENH-084 rework: área directa (Actor sin team puede vivir
          // bajo Área). Si team_id está set, backend la mantiene en
          // sync automáticamente.
          area_id: editing.area_id ?? null,
        });
      }
      setEditing(null);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al guardar");
    } finally {
      setSubmitting(false);
    }
  }

  async function submitReassign() {
    if (!reassigning || !reassigning.targetId) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await reassignActor(reassigning.source.id, {
        target_actor_id: reassigning.targetId,
        scopes: ["tasks"],
        deactivate_source: true,
      });
      alert(
        `Reasignados ${res.tasks_moved} tareas. Actor origen ${
          res.source_deactivated ? "desactivado" : "activo"
        }.`,
      );
      setReassigning(null);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al reasignar");
    } finally {
      setSubmitting(false);
    }
  }

  async function onDelete(kind: NodeKind, id: string, name: string) {
    if (!confirm(`¿Eliminar ${kind === "area" ? "Área" : kind === "team" ? "Equipo" : "Actor"} "${name}"?`)) return;
    setError(null);
    try {
      if (kind === "area") await deleteArea(id);
      else if (kind === "team") await deleteTeam(id);
      else await deleteActor(id);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al eliminar");
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <Breadcrumb
        items={[
          { href: "/admin", label: "Admin" },
          { label: "Áreas" },
        ]}
      />
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-[var(--color-primary)]">
            Áreas → Equipos → Actores
          </h1>
          <p className="mt-1 text-sm text-[var(--color-tertiary)]">
            Catálogo tenant reutilizable a través de proyectos.
          </p>
        </div>
        <Button onClick={() => openCreate({ kind: "area" })}>
          <Plus className="h-4 w-4" aria-hidden /> Nueva Área
        </Button>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      ) : tree && (tree.areas.length > 0 || tree.orphan_actors.length > 0) ? (
        <div className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]">
          <ul>
            {tree.areas.map((a) => (
              <AreaNode
                key={a.id}
                area={a}
                orgName={
                  a.organization_id
                    ? orgs.find((o) => o.id === a.organization_id)?.name ?? null
                    : null
                }
                expanded={expanded}
                toggle={toggle}
                toggleArea={toggleArea}
                assignments={assignments[a.id] ?? null}
                openCreate={openCreate}
                openEditArea={openEditArea}
                openEditTeam={openEditTeam}
                openEditActor={openEditActor}
                onDelete={onDelete}
                onReassign={(ac) =>
                  setReassigning({ source: ac, targetId: "" })
                }
              />
            ))}
            {tree.orphan_actors.length > 0 ? (
              <li className="border-t border-[var(--border-default)]">
                <div className="flex items-center gap-2 px-4 py-2 text-xs uppercase tracking-wide text-[var(--color-tertiary)]">
                  Actores sin área asignada ({tree.orphan_actors.length})
                  <span className="ml-2 normal-case text-[var(--color-tertiary)]">
                    — usa "Editar" para moverlos a un equipo/área.
                  </span>
                </div>
                <ul>
                  {tree.orphan_actors.map((ac) => (
                    <ActorRow
                      key={ac.id}
                      actor={ac}
                      teamId={null}
                      depth={1}
                      openEditActor={openEditActor}
                      onDelete={onDelete}
                      onReassign={(a) =>
                        setReassigning({ source: a, targetId: "" })
                      }
                    />
                  ))}
                </ul>
              </li>
            ) : null}
          </ul>
        </div>
      ) : (
        <div className="rounded-[var(--radius-xl)] border border-dashed border-[var(--border-default)] bg-[var(--color-surface)] p-8 text-center text-sm text-[var(--color-tertiary)]">
          Sin áreas registradas. Crea la primera con el botón arriba.
        </div>
      )}

      {/* Modal: crear */}
      <Modal
        open={creating !== null}
        onClose={() => setCreating(null)}
        title={
          creating?.kind === "area"
            ? "Nueva Área"
            : creating?.kind === "team"
              ? `Nuevo Equipo en ${creating.area_name}`
              : creating?.kind === "actor"
                ? `Nuevo Actor en ${creating.team_label}`
                : ""
        }
      >
        {creating ? (
          <form onSubmit={submitCreate} className="space-y-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-[var(--color-secondary)]">
                Nombre
              </label>
              <Input
                value={form.name}
                onChange={(e) =>
                  setForm((f) => ({ ...f, name: e.target.value }))
                }
                required
                minLength={2}
                maxLength={200}
                autoFocus
              />
            </div>
            {creating.kind === "area" ? (
              <>
                <div>
                  <label className="mb-1 block text-xs font-medium text-[var(--color-secondary)]">
                    Alcance del área
                  </label>
                  <Select
                    value={form.organization_id}
                    onChange={(e) =>
                      setForm((f) => ({
                        ...f,
                        organization_id: e.target.value,
                      }))
                    }
                  >
                    <option value="">
                      Global (visible en todas las organizaciones)
                    </option>
                    {orgs.map((o) => (
                      <option key={o.id} value={o.id}>
                        Solo en {o.name}
                      </option>
                    ))}
                  </Select>
                  <p className="mt-1 text-[11px] text-[var(--color-tertiary)]">
                    Áreas con el mismo nombre pueden coexistir en
                    organizaciones distintas con recursos diferentes.
                  </p>
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-[var(--color-secondary)]">
                    Líder del área (opcional)
                  </label>
                  <Input
                    value={form.lead_name}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, lead_name: e.target.value }))
                    }
                    maxLength={200}
                    placeholder="Nombre del líder (puede ser un actor sin cuenta)"
                  />
                </div>
              </>
            ) : null}
            {creating.kind !== "actor" ? (
              <div>
                <label className="mb-1 block text-xs font-medium text-[var(--color-secondary)]">
                  Descripción (opcional)
                </label>
                <Textarea
                  value={form.description}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, description: e.target.value }))
                  }
                  maxLength={2000}
                  rows={2}
                />
              </div>
            ) : (
              <>
                <div>
                  <label className="mb-1 block text-xs font-medium text-[var(--color-secondary)]">
                    Email (opcional)
                  </label>
                  <Input
                    type="email"
                    value={form.email}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, email: e.target.value }))
                    }
                    maxLength={200}
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-[var(--color-secondary)]">
                    Teléfono (opcional)
                  </label>
                  <Input
                    value={form.phone}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, phone: e.target.value }))
                    }
                    maxLength={32}
                  />
                </div>
              </>
            )}
            <div className="flex justify-end gap-2 pt-2">
              <Button
                type="button"
                variant="ghost"
                onClick={() => setCreating(null)}
              >
                Cancelar
              </Button>
              <Button type="submit" loading={submitting}>
                Crear
              </Button>
            </div>
          </form>
        ) : null}
      </Modal>

      {/* Modal: editar */}
      <Modal
        open={editing !== null}
        onClose={() => setEditing(null)}
        title={
          editing?.kind === "area"
            ? "Editar Área"
            : editing?.kind === "team"
              ? "Editar Equipo"
              : editing?.kind === "actor"
                ? "Editar Actor"
                : ""
        }
      >
        {editing ? (
          <form onSubmit={submitEdit} className="space-y-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-[var(--color-secondary)]">
                Nombre
              </label>
              <Input
                value={editing.name}
                onChange={(e) =>
                  setEditing((prev) =>
                    prev ? { ...prev, name: e.target.value } : prev,
                  )
                }
                required
                minLength={2}
                maxLength={200}
                autoFocus
              />
            </div>
            {editing.kind === "area" ? (
              <div>
                <label className="mb-1 block text-xs font-medium text-[var(--color-secondary)]">
                  Líder del área (opcional)
                </label>
                <Input
                  value={editing.lead_name}
                  onChange={(e) =>
                    setEditing((prev) =>
                      prev && prev.kind === "area"
                        ? { ...prev, lead_name: e.target.value }
                        : prev,
                    )
                  }
                  maxLength={200}
                  placeholder="Nombre del líder (puede ser un actor sin cuenta)"
                />
              </div>
            ) : null}
            {editing.kind === "area" ? (
              <AssignmentsEditor
                orgs={orgs}
                programs={programs}
                projects={projects}
                selected={editingScopes}
                onToggle={toggleScope}
              />
            ) : null}
            {editing.kind !== "actor" ? (
              <div>
                <label className="mb-1 block text-xs font-medium text-[var(--color-secondary)]">
                  Descripción (opcional)
                </label>
                <Textarea
                  value={editing.description}
                  onChange={(e) =>
                    setEditing((prev) =>
                      prev && prev.kind !== "actor"
                        ? { ...prev, description: e.target.value }
                        : prev,
                    )
                  }
                  maxLength={2000}
                  rows={2}
                />
              </div>
            ) : (
              <>
                <div>
                  <label className="mb-1 block text-xs font-medium text-[var(--color-secondary)]">
                    Email (opcional)
                  </label>
                  <Input
                    type="email"
                    value={editing.email}
                    onChange={(e) =>
                      setEditing((prev) =>
                        prev && prev.kind === "actor"
                          ? { ...prev, email: e.target.value }
                          : prev,
                      )
                    }
                    maxLength={200}
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-[var(--color-secondary)]">
                    Teléfono (opcional)
                  </label>
                  <Input
                    value={editing.phone}
                    onChange={(e) =>
                      setEditing((prev) =>
                        prev && prev.kind === "actor"
                          ? { ...prev, phone: e.target.value }
                          : prev,
                      )
                    }
                    maxLength={32}
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-[var(--color-secondary)]">
                    Área
                  </label>
                  <Select
                    value={editing.area_id ?? ""}
                    onChange={(e) => {
                      const newAreaId = e.target.value || null;
                      setEditing((prev) =>
                        prev && prev.kind === "actor"
                          ? {
                              ...prev,
                              area_id: newAreaId,
                              // Si cambia el área, limpia team que ya
                              // no pertenece.
                              team_id:
                                prev.team_id &&
                                (tree?.areas ?? [])
                                  .find((a) => a.id === newAreaId)
                                  ?.teams.some((t) => t.id === prev.team_id)
                                  ? prev.team_id
                                  : null,
                            }
                          : prev,
                      );
                    }}
                  >
                    <option value="">— Sin área —</option>
                    {(tree?.areas ?? []).map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.name}
                      </option>
                    ))}
                  </Select>
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-[var(--color-secondary)]">
                    Equipo (opcional)
                  </label>
                  <Select
                    value={editing.team_id ?? ""}
                    disabled={!editing.area_id}
                    onChange={(e) =>
                      setEditing((prev) =>
                        prev && prev.kind === "actor"
                          ? { ...prev, team_id: e.target.value || null }
                          : prev,
                      )
                    }
                  >
                    <option value="">— Sin equipo —</option>
                    {(tree?.areas ?? [])
                      .find((a) => a.id === editing.area_id)
                      ?.teams.map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.name}
                        </option>
                      ))}
                  </Select>
                  <p className="mt-1 text-xs text-[var(--color-tertiary)]">
                    Selecciona Área primero. El actor puede vivir bajo
                    un Área sin equipo (recurso libre del área) o
                    asignado a un Equipo específico.
                  </p>
                </div>
              </>
            )}
            <div className="flex justify-end gap-2 pt-2">
              <Button
                type="button"
                variant="ghost"
                onClick={() => setEditing(null)}
              >
                Cancelar
              </Button>
              <Button type="submit" loading={submitting}>
                Guardar
              </Button>
            </div>
          </form>
        ) : null}
      </Modal>

      {/* Modal: reasignación masiva (US-099) */}
      <Modal
        open={reassigning !== null}
        onClose={() => setReassigning(null)}
        title={
          reassigning
            ? `Reasignar tareas de ${reassigning.source.name}`
            : ""
        }
      >
        {reassigning && tree ? (
          <div className="space-y-3">
            <p className="text-sm text-[var(--color-secondary)]">
              Todas las tareas asignadas a <strong>{reassigning.source.name}</strong>{" "}
              se moverán al actor seleccionado. El actor origen se desactivará
              tras la operación.
            </p>
            <p className="text-xs text-[var(--color-tertiary)]">
              MVP: sólo se mueven tareas. RAID y minutas quedan diferidos
              hasta que el modelo de actores en esos módulos se valide.
            </p>
            <label>
              <span className="mb-1 block text-xs font-medium text-[var(--color-secondary)]">
                Actor destino
              </span>
              <Select
                value={reassigning.targetId}
                onChange={(e) =>
                  setReassigning((prev) =>
                    prev ? { ...prev, targetId: e.target.value } : prev,
                  )
                }
              >
                <option value="">Selecciona un actor…</option>
                {/* Lista plana de todos los actores activos del tree
                    excepto el origen. */}
                {[
                  ...tree.areas.flatMap((a) =>
                    a.teams.flatMap((t) =>
                      t.actors.map((ac) => ({
                        id: ac.id,
                        label: `${a.name} / ${t.name} / ${ac.name}`,
                      })),
                    ),
                  ),
                  ...tree.orphan_actors.map((ac) => ({
                    id: ac.id,
                    label: `(sin equipo) ${ac.name}`,
                  })),
                ]
                  .filter((x) => x.id !== reassigning.source.id)
                  .map((x) => (
                    <option key={x.id} value={x.id}>
                      {x.label}
                    </option>
                  ))}
              </Select>
            </label>
            <div className="flex justify-end gap-2 pt-2">
              <Button
                type="button"
                variant="ghost"
                onClick={() => setReassigning(null)}
                disabled={submitting}
              >
                Cancelar
              </Button>
              <Button
                type="button"
                onClick={submitReassign}
                loading={submitting}
                disabled={!reassigning.targetId}
              >
                Reasignar y desactivar
              </Button>
            </div>
          </div>
        ) : null}
      </Modal>
    </div>
  );
}

function AreaNode({
  area,
  orgName,
  expanded,
  toggle,
  toggleArea,
  assignments,
  openCreate,
  openEditArea,
  openEditTeam,
  openEditActor,
  onDelete,
  onReassign,
}: {
  area: TreeArea;
  orgName: string | null;
  expanded: Set<string>;
  toggle: (id: string) => void;
  toggleArea: (id: string) => void;
  assignments: AreaAssignment[] | null;
  openCreate: (n: CreatingNode) => void;
  openEditArea: (a: TreeArea) => void;
  openEditTeam: (area_id: string, t: TreeTeam) => void;
  openEditActor: (team_id: string | null, a: TreeActor) => void;
  onDelete: (kind: NodeKind, id: string, name: string) => void;
  onReassign: (a: TreeActor) => void;
}) {
  const isOpen = expanded.has(area.id);
  return (
    <li className="border-t border-[var(--border-default)] first:border-t-0">
      <div
        className={cn(
          "flex items-center gap-2 px-4 py-2.5 hover:bg-[var(--color-subtle)]",
          !area.is_active && "opacity-60",
        )}
      >
        <button
          type="button"
          onClick={() => toggleArea(area.id)}
          className="inline-flex h-6 w-6 items-center justify-center text-[var(--color-tertiary)] hover:text-[var(--color-primary)]"
          aria-label={isOpen ? "Colapsar" : "Expandir"}
        >
          {isOpen ? (
            <ChevronDown className="h-4 w-4" aria-hidden />
          ) : (
            <ChevronRight className="h-4 w-4" aria-hidden />
          )}
        </button>
        <Network className="h-4 w-4 text-[var(--color-tertiary)]" aria-hidden />
        <div className="flex-1 min-w-0">
          <div className="font-medium text-[var(--color-primary)] flex items-center gap-1.5">
            <span className="truncate">{area.name}</span>
            <span
              className={cn(
                "shrink-0 rounded-[var(--radius-sm)] px-1.5 py-0.5 text-[10px] uppercase tracking-wide",
                orgName
                  ? "bg-[var(--color-info-subtle)] text-[var(--color-info-fg)]"
                  : "bg-[var(--color-success-subtle)] text-[var(--color-success-fg)]",
              )}
              title={
                orgName
                  ? `Área scoped a la organización ${orgName}`
                  : "Área tenant-global (visible en todas las organizaciones)"
              }
            >
              {orgName ?? "Global"}
            </span>
          </div>
          {area.description ? (
            <div className="text-xs text-[var(--color-tertiary)] truncate">
              {area.description}
            </div>
          ) : null}
        </div>
        <span className="text-xs tabular-nums text-[var(--color-tertiary)]">
          {area.teams.length} equipos
        </span>
        <Button
          size="sm"
          variant="ghost"
          onClick={() =>
            openCreate({ kind: "team", area_id: area.id, area_name: area.name })
          }
          title="Nuevo equipo"
        >
          <Plus className="h-3.5 w-3.5" aria-hidden />
        </Button>
        <button
          type="button"
          onClick={() => openEditArea(area)}
          className="inline-flex h-7 w-7 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-tertiary)] hover:bg-[var(--color-subtle)] hover:text-[var(--color-primary)]"
          aria-label="Editar Área"
          title="Editar"
        >
          <Pencil className="h-3.5 w-3.5" aria-hidden />
        </button>
        <button
          type="button"
          onClick={() => onDelete("area", area.id, area.name)}
          className="inline-flex h-7 w-7 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-tertiary)] hover:bg-[var(--color-danger-bg)] hover:text-[var(--color-danger-fg)]"
          aria-label="Eliminar Área"
          title="Eliminar"
        >
          <Trash2 className="h-3.5 w-3.5" aria-hidden />
        </button>
      </div>
      {isOpen ? (
        <div className="bg-[var(--color-subtle)]/40">
          <AssignmentsSection assignments={assignments} />
          <ul>
          {area.teams.map((t) => (
            <TeamNode
              key={t.id}
              team={t}
              areaId={area.id}
              expanded={expanded}
              toggle={toggle}
              openCreate={openCreate}
              openEditTeam={openEditTeam}
              openEditActor={openEditActor}
              onDelete={onDelete}
              onReassign={onReassign}
            />
          ))}
          {area.teams.length === 0 ? (
            <li className="px-12 py-2 text-xs text-[var(--color-tertiary)]">
              Sin equipos. Usa el botón + para crear el primero.
            </li>
          ) : null}
          </ul>
          {area.unassigned_actors && area.unassigned_actors.length > 0 ? (
            <div>
              <div className="flex items-center gap-2 px-12 py-2 text-xs uppercase tracking-wide text-[var(--color-tertiary)]">
                Actores sin equipo ({area.unassigned_actors.length})
              </div>
              <ul>
                {area.unassigned_actors.map((ac) => (
                  <ActorRow
                    key={ac.id}
                    actor={ac}
                    teamId={null}
                    depth={2}
                    openEditActor={openEditActor}
                    onDelete={onDelete}
                    onReassign={onReassign}
                  />
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}
    </li>
  );
}

function AssignmentsSection({
  assignments,
}: {
  assignments: AreaAssignment[] | null;
}) {
  if (assignments === null) {
    return (
      <div className="px-12 py-2 text-xs text-[var(--color-tertiary)]">
        Cargando habilitaciones…
      </div>
    );
  }
  if (assignments.length === 0) {
    return (
      <div className="px-12 py-2 text-xs text-[var(--color-tertiary)]">
        <span className="font-medium uppercase tracking-wide">Habilitada en:</span>{" "}
        no asignada a ningún scope todavía.
      </div>
    );
  }
  const items = assignments.map((a) => {
    if (a.is_global)
      return { key: a.id, kind: "Global", label: "Todos los proyectos del tenant" };
    if (a.organization_id)
      return {
        key: a.id,
        kind: "Org",
        label: a.organization_name ?? `Org ${a.organization_id.slice(0, 8)}`,
      };
    if (a.program_id)
      return {
        key: a.id,
        kind: "Programa",
        label: a.program_name ?? `Programa ${a.program_id.slice(0, 8)}`,
      };
    if (a.project_id)
      return {
        key: a.id,
        kind: "Proyecto",
        label: a.project_name ?? `Proyecto ${a.project_id.slice(0, 8)}`,
      };
    return { key: a.id, kind: "?", label: "(scope desconocido)" };
  });
  return (
    <div className="px-12 py-2 text-xs">
      <span className="font-medium uppercase tracking-wide text-[var(--color-tertiary)]">
        Habilitada en
      </span>
      <div className="mt-1 flex flex-wrap gap-1.5">
        {items.map((it) => (
          <span
            key={it.key}
            className="inline-flex items-center gap-1 rounded-[var(--radius-sm)] border border-[var(--border-default)] bg-[var(--color-surface)] px-2 py-0.5 text-[var(--color-secondary)]"
          >
            <span className="text-[var(--color-tertiary)]">{it.kind}:</span>
            <span className="font-medium text-[var(--color-primary)]">
              {it.label}
            </span>
          </span>
        ))}
      </div>
    </div>
  );
}

function TeamNode({
  team,
  areaId,
  expanded,
  toggle,
  openCreate,
  openEditTeam,
  openEditActor,
  onDelete,
  onReassign,
}: {
  team: TreeTeam;
  areaId: string;
  expanded: Set<string>;
  toggle: (id: string) => void;
  openCreate: (n: CreatingNode) => void;
  openEditTeam: (area_id: string, t: TreeTeam) => void;
  openEditActor: (team_id: string | null, a: TreeActor) => void;
  onReassign: (a: TreeActor) => void;
  onDelete: (kind: NodeKind, id: string, name: string) => void;
}) {
  const isOpen = expanded.has(team.id);
  return (
    <li className="border-t border-[var(--border-default)]">
      <div
        className={cn(
          "flex items-center gap-2 px-4 py-2 pl-12 hover:bg-[var(--color-subtle)]",
          !team.is_active && "opacity-60",
        )}
      >
        <button
          type="button"
          onClick={() => toggle(team.id)}
          className="inline-flex h-6 w-6 items-center justify-center text-[var(--color-tertiary)] hover:text-[var(--color-primary)]"
          aria-label={isOpen ? "Colapsar" : "Expandir"}
        >
          {isOpen ? (
            <ChevronDown className="h-4 w-4" aria-hidden />
          ) : (
            <ChevronRight className="h-4 w-4" aria-hidden />
          )}
        </button>
        <Users className="h-4 w-4 text-[var(--color-tertiary)]" aria-hidden />
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-[var(--color-primary)]">
            {team.name}
          </div>
        </div>
        <span className="text-xs tabular-nums text-[var(--color-tertiary)]">
          {team.actors.length} actores
        </span>
        <Button
          size="sm"
          variant="ghost"
          onClick={() =>
            openCreate({
              kind: "actor",
              team_id: team.id,
              team_label: team.name,
            })
          }
          title="Nuevo actor"
        >
          <Plus className="h-3.5 w-3.5" aria-hidden />
        </Button>
        <button
          type="button"
          onClick={() => openEditTeam(areaId, team)}
          className="inline-flex h-7 w-7 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-tertiary)] hover:bg-[var(--color-subtle)] hover:text-[var(--color-primary)]"
          aria-label="Editar Equipo"
          title="Editar"
        >
          <Pencil className="h-3.5 w-3.5" aria-hidden />
        </button>
        <button
          type="button"
          onClick={() => onDelete("team", team.id, team.name)}
          className="inline-flex h-7 w-7 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-tertiary)] hover:bg-[var(--color-danger-bg)] hover:text-[var(--color-danger-fg)]"
          aria-label="Eliminar Equipo"
          title="Eliminar"
        >
          <Trash2 className="h-3.5 w-3.5" aria-hidden />
        </button>
      </div>
      {isOpen ? (
        <ul>
          {team.actors.map((ac) => (
            <ActorRow
              key={ac.id}
              actor={ac}
              teamId={team.id}
              depth={2}
              openEditActor={openEditActor}
              onDelete={onDelete}
              onReassign={onReassign}
            />
          ))}
          {team.actors.length === 0 ? (
            <li className="px-20 py-2 text-xs text-[var(--color-tertiary)]">
              Sin actores. Usa el botón + para agregar el primero.
            </li>
          ) : null}
        </ul>
      ) : null}
    </li>
  );
}

function ActorRow({
  actor,
  teamId,
  depth,
  openEditActor,
  onDelete,
  onReassign,
}: {
  actor: TreeActor;
  teamId: string | null;
  depth: number;
  openEditActor: (team_id: string | null, a: TreeActor) => void;
  onDelete: (kind: NodeKind, id: string, name: string) => void;
  onReassign?: (a: TreeActor) => void;
}) {
  return (
    <li
      className={cn(
        "flex items-center gap-2 border-t border-[var(--border-subtle)] py-1.5 hover:bg-[var(--color-subtle)]/60",
        !actor.is_active && "opacity-60",
        depth === 2 ? "pl-20 pr-4" : "pl-12 pr-4",
      )}
    >
      <User className="h-4 w-4 text-[var(--color-tertiary)]" aria-hidden />
      <div className="flex-1 min-w-0">
        <div className="text-sm text-[var(--color-primary)]">{actor.name}</div>
        {actor.email || actor.phone ? (
          <div className="text-xs text-[var(--color-tertiary)] truncate">
            {[actor.email, actor.phone].filter(Boolean).join(" · ")}
          </div>
        ) : null}
      </div>
      {onReassign ? (
        <button
          type="button"
          onClick={() => onReassign(actor)}
          className="inline-flex h-7 w-7 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-tertiary)] hover:bg-[var(--color-subtle)] hover:text-[var(--color-primary)]"
          aria-label="Reasignar tareas a otro actor"
          title="Reasignar tareas"
        >
          <ArrowRightLeft className="h-3.5 w-3.5" aria-hidden />
        </button>
      ) : null}
      <button
        type="button"
        onClick={() => openEditActor(teamId, actor)}
        className="inline-flex h-7 w-7 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-tertiary)] hover:bg-[var(--color-subtle)] hover:text-[var(--color-primary)]"
        aria-label="Editar Actor"
        title="Editar"
      >
        <Pencil className="h-3.5 w-3.5" aria-hidden />
      </button>
      <button
        type="button"
        onClick={() => onDelete("actor", actor.id, actor.name)}
        className="inline-flex h-7 w-7 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-tertiary)] hover:bg-[var(--color-danger-bg)] hover:text-[var(--color-danger-fg)]"
        aria-label="Eliminar Actor"
        title="Eliminar"
      >
        <Trash2 className="h-3.5 w-3.5" aria-hidden />
      </button>
    </li>
  );
}

// ENH-083 — editor de assignments en cascada (Org/Programa/Proyecto/Global).
function AssignmentsEditor({
  orgs,
  programs,
  projects,
  selected,
  onToggle,
}: {
  orgs: Organization[];
  programs: Program[];
  projects: Project[];
  selected: Set<string>;
  onToggle: (key: string) => void;
}) {
  const isGlobal = selected.has("global");
  const programsByOrg = new Map<string, Program[]>();
  for (const p of programs) {
    const list = programsByOrg.get(p.organization_id) ?? [];
    list.push(p);
    programsByOrg.set(p.organization_id, list);
  }
  const projectsByOrg = new Map<string, Project[]>();
  const projectsByProgram = new Map<string, Project[]>();
  for (const pr of projects) {
    const list = projectsByOrg.get(pr.organization_id) ?? [];
    list.push(pr);
    projectsByOrg.set(pr.organization_id, list);
    if (pr.program_id) {
      const l2 = projectsByProgram.get(pr.program_id) ?? [];
      l2.push(pr);
      projectsByProgram.set(pr.program_id, l2);
    }
  }

  return (
    <div className="rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-subtle)]/40 p-3">
      <div className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--color-secondary)]">
        Habilitada en
      </div>
      <label className="mb-2 flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={isGlobal}
          onChange={() => onToggle("global")}
        />
        <span className="font-medium">
          Global — todos los proyectos del tenant
        </span>
      </label>
      <div
        className={cn(
          "max-h-64 space-y-2 overflow-y-auto",
          isGlobal && "pointer-events-none opacity-50",
        )}
      >
        {orgs.length === 0 ? (
          <div className="text-xs text-[var(--color-tertiary)]">
            Sin organizaciones registradas en este tenant.
          </div>
        ) : null}
        {orgs.map((o) => {
          const orgKey = `org:${o.id}`;
          const orgPrograms = programsByOrg.get(o.id) ?? [];
          const orgProjectsNoProgram = (projectsByOrg.get(o.id) ?? []).filter(
            (pr) => !pr.program_id,
          );
          return (
            <div key={o.id} className="rounded-[var(--radius-sm)] border border-[var(--border-subtle)] bg-[var(--color-surface)] p-2">
              <label className="flex items-center gap-2 text-sm font-medium">
                <input
                  type="checkbox"
                  checked={selected.has(orgKey)}
                  onChange={() => onToggle(orgKey)}
                />
                <Building2 className="h-3.5 w-3.5 text-[var(--color-tertiary)]" aria-hidden />
                <span>{o.name}</span>
                <span className="text-xs font-normal text-[var(--color-tertiary)]">
                  (toda la org)
                </span>
              </label>
              {orgPrograms.length > 0 || orgProjectsNoProgram.length > 0 ? (
                <div className="ml-6 mt-1 space-y-1">
                  {orgPrograms.map((p) => {
                    const progKey = `prog:${p.id}`;
                    const projInProg = projectsByProgram.get(p.id) ?? [];
                    return (
                      <div key={p.id}>
                        <label className="flex items-center gap-2 text-xs">
                          <input
                            type="checkbox"
                            checked={selected.has(progKey)}
                            onChange={() => onToggle(progKey)}
                          />
                          <span className="font-medium text-[var(--color-secondary)]">
                            {p.name}
                          </span>
                          <span className="text-[var(--color-tertiary)]">
                            (todo el programa)
                          </span>
                        </label>
                        {projInProg.length > 0 ? (
                          <div className="ml-5 mt-0.5 space-y-0.5">
                            {projInProg.map((pr) => (
                              <label
                                key={pr.id}
                                className="flex items-center gap-2 text-xs text-[var(--color-secondary)]"
                              >
                                <input
                                  type="checkbox"
                                  checked={selected.has(`proj:${pr.id}`)}
                                  onChange={() => onToggle(`proj:${pr.id}`)}
                                />
                                <span>{pr.name}</span>
                              </label>
                            ))}
                          </div>
                        ) : null}
                      </div>
                    );
                  })}
                  {orgProjectsNoProgram.map((pr) => (
                    <label
                      key={pr.id}
                      className="flex items-center gap-2 text-xs text-[var(--color-secondary)]"
                    >
                      <input
                        type="checkbox"
                        checked={selected.has(`proj:${pr.id}`)}
                        onChange={() => onToggle(`proj:${pr.id}`)}
                      />
                      <span>{pr.name}</span>
                      <span className="text-[var(--color-tertiary)]">
                        (sin programa)
                      </span>
                    </label>
                  ))}
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
      {isGlobal ? (
        <p className="mt-2 text-xs text-[var(--color-tertiary)]">
          Global excluye selecciones específicas. Desactívalo para elegir
          scopes individuales.
        </p>
      ) : null}
    </div>
  );
}
