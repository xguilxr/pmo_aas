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
  reassignActor,
  updateActor,
  updateArea,
  updateTeam,
  type AreaTreeResponse,
  type TreeActor,
  type TreeArea,
  type TreeTeam,
} from "@/lib/api/areas";
import { Select } from "@/components/ui/select";
import { cn } from "@/lib/cn";

type NodeKind = "area" | "team" | "actor";

type EditingNode =
  | { kind: "area"; id: string; name: string; description: string }
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

  const [creating, setCreating] = useState<CreatingNode | null>(null);
  const [editing, setEditing] = useState<EditingNode | null>(null);
  const [submitting, setSubmitting] = useState(false);
  // US-099: state del modal de reasignación masiva.
  const [reassigning, setReassigning] = useState<{
    source: TreeActor;
    targetId: string;
  } | null>(null);

  const [form, setForm] = useState({
    name: "",
    description: "",
    email: "",
    phone: "",
  });

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await getAreasTree(true);
      setTree(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar áreas");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  function toggle(id: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function openCreate(node: CreatingNode) {
    setForm({ name: "", description: "", email: "", phone: "" });
    setCreating(node);
  }

  function openEditArea(a: TreeArea) {
    setForm({ name: "", description: "", email: "", phone: "" });
    setEditing({
      kind: "area",
      id: a.id,
      name: a.name,
      description: a.description ?? "",
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
        await createArea({
          name: form.name.trim(),
          description: form.description.trim() || null,
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
        await updateArea(editing.id, {
          name: editing.name.trim(),
          description: editing.description.trim() || null,
        });
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
                expanded={expanded}
                toggle={toggle}
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
                  Actores sin equipo asignado ({tree.orphan_actors.length})
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
  expanded,
  toggle,
  openCreate,
  openEditArea,
  openEditTeam,
  openEditActor,
  onDelete,
  onReassign,
}: {
  area: TreeArea;
  expanded: Set<string>;
  toggle: (id: string) => void;
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
          onClick={() => toggle(area.id)}
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
          <div className="font-medium text-[var(--color-primary)]">
            {area.name}
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
        <ul className="bg-[var(--color-subtle)]/40">
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
      ) : null}
    </li>
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
