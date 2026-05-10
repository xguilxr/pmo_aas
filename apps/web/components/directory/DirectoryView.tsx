"use client";

// US-116 — Toggle 1 del rediseño de /pmo/projects/[id]/areas.
// Lista actores con primary participation en el proyecto (directorio
// navegable). Acciones: agregar persona del catálogo tenant, crear nueva
// persona inline, editar participation, desactivar.
//
// La vista es self-contained: convive con la vista legacy de áreas/actores
// de la misma página. Los catálogos del Toggle 2 viven en componentes
// separados (CatalogTabs).

import { useEffect, useMemo, useState } from "react";
import { Crown, Plus, Star, UserPlus, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  createActor,
  listActors,
  type Actor,
  type Area,
  listAreasByProject,
} from "@/lib/api/areas";

const listActorsTenant = () => listActors();
import {
  createParticipation,
  deleteParticipation,
  listParticipations,
  listProjectRoles,
  type Participation,
  type ProjectRole,
  updateParticipation,
} from "@/lib/api/project-directory";

type Props = {
  projectId: string;
};

type Row = {
  participation: Participation;
  actor: Actor | null;
};

export function DirectoryView({ projectId }: Props) {
  const [participations, setParticipations] = useState<Participation[]>([]);
  const [actorsById, setActorsById] = useState<Record<string, Actor>>({});
  const [areasById, setAreasById] = useState<Record<string, Area>>({});
  const [rolesById, setRolesById] = useState<Record<string, ProjectRole>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [editing, setEditing] = useState<Participation | null>(null);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const [parts, areas, roles, actors] = await Promise.all([
        listParticipations(projectId, { include: "actor" }),
        listAreasByProject(projectId).catch(() => [] as Area[]),
        listProjectRoles().catch(() => [] as ProjectRole[]),
        listActorsTenant().catch(() => [] as Actor[]),
      ]);
      setParticipations(parts);
      setAreasById(Object.fromEntries(areas.map((a) => [a.id, a])));
      setRolesById(Object.fromEntries(roles.map((r) => [r.id, r])));
      setActorsById(Object.fromEntries(actors.map((a) => [a.id, a])));
    } catch (e: any) {
      setError(e?.message ?? "Error cargando directorio");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  const rows: Row[] = useMemo(() => {
    // Solo primary participation por (actor) — el resto se ve en el modal de detalle.
    const byActor: Record<string, Participation> = {};
    for (const p of participations) {
      if (!p.is_active) continue;
      if (p.is_primary || !byActor[p.actor_id]) {
        byActor[p.actor_id] = p;
      }
    }
    const list = Object.values(byActor).map((p) => ({
      participation: p,
      actor: actorsById[p.actor_id] ?? p.actor ?? null,
    }));
    if (!search) return list;
    const q = search.toLowerCase();
    return list.filter(
      (r) =>
        r.actor?.name?.toLowerCase().includes(q) ||
        r.actor?.email?.toLowerCase().includes(q) ||
        r.actor?.company?.toLowerCase().includes(q),
    );
  }, [participations, actorsById, search]);

  if (loading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <Input
          placeholder="Buscar persona, email o empresa…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-sm"
        />
        <Button onClick={() => setShowAdd(true)}>
          <Plus className="mr-1 h-4 w-4" /> Agregar al proyecto
        </Button>
      </div>

      {error && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</div>
      )}

      {rows.length === 0 ? (
        <div className="rounded-md border border-dashed p-8 text-center text-sm text-muted-foreground">
          No hay personas en el directorio del proyecto. Usá "Agregar al
          proyecto" para empezar.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-md border">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 text-left text-xs uppercase">
              <tr>
                <th className="px-3 py-2">Persona</th>
                <th className="px-3 py-2">Empresa / Cargo</th>
                <th className="px-3 py-2">Área funcional</th>
                <th className="px-3 py-2">Equipo operativo</th>
                <th className="px-3 py-2">Rol</th>
                <th className="px-3 py-2">Periodo</th>
                <th className="px-3 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {rows.map(({ participation: p, actor }) => (
                <tr key={p.id} className="border-t hover:bg-muted/30">
                  <td className="px-3 py-2">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{actor?.name ?? "—"}</span>
                      {p.is_area_lead && (
                        <Badge className="gap-1">
                          <Crown className="h-3 w-3" /> Líder área
                        </Badge>
                      )}
                      {p.is_primary && (
                        <Star
                          className="h-3 w-3 text-yellow-500"
                          aria-label="Participación primaria"
                        />
                      )}
                    </div>
                    {actor?.email && (
                      <div className="text-xs text-muted-foreground">{actor.email}</div>
                    )}
                  </td>
                  <td className="px-3 py-2 text-xs">
                    <div>{actor?.company ?? "—"}</div>
                    <div className="text-muted-foreground">{actor?.job_title ?? ""}</div>
                  </td>
                  <td className="px-3 py-2">
                    {p.functional_area_id
                      ? areasById[p.functional_area_id]?.name ?? "—"
                      : "—"}
                  </td>
                  <td className="px-3 py-2">{p.operational_team_id ?? "—"}</td>
                  <td className="px-3 py-2">
                    {p.project_role_id
                      ? rolesById[p.project_role_id]?.name ?? "—"
                      : "—"}
                  </td>
                  <td className="px-3 py-2 text-xs">
                    {p.start_date ?? "—"} → {p.end_date ?? "—"}
                  </td>
                  <td className="px-3 py-2 text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setEditing(p)}
                    >
                      Editar
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showAdd && (
        <AddPersonModal
          projectId={projectId}
          onClose={() => setShowAdd(false)}
          onSaved={() => {
            setShowAdd(false);
            refresh();
          }}
        />
      )}

      {editing && (
        <EditParticipationModal
          projectId={projectId}
          participation={editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            refresh();
          }}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Add Person modal — Toggle 1 entry-point. Permite (a) seleccionar del
// catálogo tenant o (b) crear actor nuevo inline + crear participation.
// ---------------------------------------------------------------------------
function AddPersonModal({
  projectId,
  onClose,
  onSaved,
}: {
  projectId: string;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [tenantActors, setTenantActors] = useState<Actor[]>([]);
  const [areas, setAreas] = useState<Area[]>([]);
  const [roles, setRoles] = useState<ProjectRole[]>([]);
  const [mode, setMode] = useState<"existing" | "new">("existing");
  const [actorId, setActorId] = useState<string>("");
  const [newActorName, setNewActorName] = useState("");
  const [newActorEmail, setNewActorEmail] = useState("");
  const [newActorCompany, setNewActorCompany] = useState("");
  const [newActorJobTitle, setNewActorJobTitle] = useState("");
  const [functionalAreaId, setFunctionalAreaId] = useState<string>("");
  const [roleId, setRoleId] = useState<string>("");
  const [isAreaLead, setIsAreaLead] = useState(false);
  const [isPrimary, setIsPrimary] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      listActorsTenant().catch(() => []),
      listAreasByProject(projectId).catch(() => []),
      listProjectRoles({ is_active: true }).catch(() => []),
    ]).then(([a, ar, ro]) => {
      setTenantActors(a as Actor[]);
      setAreas(ar as Area[]);
      setRoles(ro as ProjectRole[]);
    });
  }, [projectId]);

  async function submit() {
    setSaving(true);
    setError(null);
    try {
      let aid = actorId;
      if (mode === "new") {
        if (!newActorName.trim()) throw new Error("Nombre requerido");
        const created = await createActor({
          name: newActorName.trim(),
          email: newActorEmail.trim() || undefined,
          company: newActorCompany.trim() || undefined,
          job_title: newActorJobTitle.trim() || undefined,
          area_id: functionalAreaId || undefined,
        } as any);
        aid = created.id;
      }
      if (!aid) throw new Error("Seleccioná o creá una persona");
      await createParticipation(projectId, {
        actor_id: aid,
        functional_area_id: functionalAreaId || undefined,
        project_role_id: roleId || undefined,
        is_area_lead: isAreaLead,
        is_primary: isPrimary,
        is_active: true,
      });
      onSaved();
    } catch (e: any) {
      setError(e?.message ?? "Error guardando");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal open={true} title="Agregar persona al proyecto" onClose={onClose}>
      <div className="space-y-3">
        <div className="flex gap-2">
          <Button
            variant={mode === "existing" ? "primary" : "secondary"}
            size="sm"
            onClick={() => setMode("existing")}
          >
            Del catálogo
          </Button>
          <Button
            variant={mode === "new" ? "primary" : "secondary"}
            size="sm"
            onClick={() => setMode("new")}
          >
            <UserPlus className="mr-1 h-4 w-4" /> Crear nueva
          </Button>
        </div>

        {mode === "existing" ? (
          <Select
            value={actorId}
            onChange={(e) => setActorId(e.target.value)}
          >
            <option value="">Seleccioná persona…</option>
            {tenantActors.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name} {a.email ? `— ${a.email}` : ""}
              </option>
            ))}
          </Select>
        ) : (
          <div className="space-y-2">
            <Input
              placeholder="Nombre completo *"
              value={newActorName}
              onChange={(e) => setNewActorName(e.target.value)}
            />
            <Input
              placeholder="Email"
              value={newActorEmail}
              onChange={(e) => setNewActorEmail(e.target.value)}
            />
            <Input
              placeholder="Empresa"
              value={newActorCompany}
              onChange={(e) => setNewActorCompany(e.target.value)}
            />
            <Input
              placeholder="Cargo organizacional"
              value={newActorJobTitle}
              onChange={(e) => setNewActorJobTitle(e.target.value)}
            />
          </div>
        )}

        <div className="grid grid-cols-2 gap-2">
          <label className="text-xs">
            Área funcional
            <Select
              value={functionalAreaId}
              onChange={(e) => setFunctionalAreaId(e.target.value)}
            >
              <option value="">—</option>
              {areas.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </Select>
          </label>
          <label className="text-xs">
            Rol proyecto
            <Select value={roleId} onChange={(e) => setRoleId(e.target.value)}>
              <option value="">—</option>
              {roles.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
            </Select>
          </label>
        </div>

        <div className="flex gap-4 text-xs">
          <label className="flex items-center gap-1">
            <input
              type="checkbox"
              checked={isAreaLead}
              onChange={(e) => setIsAreaLead(e.target.checked)}
            />
            Líder de área
          </label>
          <label className="flex items-center gap-1">
            <input
              type="checkbox"
              checked={isPrimary}
              onChange={(e) => setIsPrimary(e.target.checked)}
            />
            Participación primaria
          </label>
        </div>

        {error && <div className="text-sm text-red-600">{error}</div>}

        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button onClick={submit} disabled={saving}>
            {saving ? "Guardando…" : "Agregar"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// Edit Participation modal
// ---------------------------------------------------------------------------
function EditParticipationModal({
  projectId,
  participation,
  onClose,
  onSaved,
}: {
  projectId: string;
  participation: Participation;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [areas, setAreas] = useState<Area[]>([]);
  const [roles, setRoles] = useState<ProjectRole[]>([]);
  const [functionalAreaId, setFunctionalAreaId] = useState(
    participation.functional_area_id ?? "",
  );
  const [roleId, setRoleId] = useState(participation.project_role_id ?? "");
  const [isAreaLead, setIsAreaLead] = useState(participation.is_area_lead);
  const [isPrimary, setIsPrimary] = useState(participation.is_primary);
  const [startDate, setStartDate] = useState(participation.start_date ?? "");
  const [endDate, setEndDate] = useState(participation.end_date ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      listAreasByProject(projectId).catch(() => []),
      listProjectRoles({ is_active: true }).catch(() => []),
    ]).then(([ar, ro]) => {
      setAreas(ar as Area[]);
      setRoles(ro as ProjectRole[]);
    });
  }, [projectId]);

  async function save() {
    setSaving(true);
    setError(null);
    try {
      await updateParticipation(projectId, participation.id, {
        functional_area_id: functionalAreaId || null,
        project_role_id: roleId || null,
        is_area_lead: isAreaLead,
        is_primary: isPrimary,
        start_date: startDate || null,
        end_date: endDate || null,
      });
      onSaved();
    } catch (e: any) {
      setError(e?.message ?? "Error guardando");
    } finally {
      setSaving(false);
    }
  }

  async function removeFromProject() {
    if (!confirm("¿Quitar persona del proyecto? (soft-delete)")) return;
    setSaving(true);
    try {
      await deleteParticipation(projectId, participation.id);
      onSaved();
    } catch (e: any) {
      setError(e?.message ?? "Error");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal open={true} title="Editar participación" onClose={onClose}>
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-2">
          <label className="text-xs">
            Área funcional
            <Select
              value={functionalAreaId}
              onChange={(e) => setFunctionalAreaId(e.target.value)}
            >
              <option value="">—</option>
              {areas.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </Select>
          </label>
          <label className="text-xs">
            Rol proyecto
            <Select value={roleId} onChange={(e) => setRoleId(e.target.value)}>
              <option value="">—</option>
              {roles.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
            </Select>
          </label>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <label className="text-xs">
            Desde
            <Input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
          </label>
          <label className="text-xs">
            Hasta
            <Input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </label>
        </div>

        <div className="flex gap-4 text-xs">
          <label className="flex items-center gap-1">
            <input
              type="checkbox"
              checked={isAreaLead}
              onChange={(e) => setIsAreaLead(e.target.checked)}
            />
            Líder de área
          </label>
          <label className="flex items-center gap-1">
            <input
              type="checkbox"
              checked={isPrimary}
              onChange={(e) => setIsPrimary(e.target.checked)}
            />
            Primaria
          </label>
        </div>

        {error && <div className="text-sm text-red-600">{error}</div>}

        <div className="flex justify-between pt-2">
          <Button variant="secondary" onClick={removeFromProject} disabled={saving}>
            <X className="mr-1 h-4 w-4" /> Quitar del proyecto
          </Button>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={onClose}>
              Cancelar
            </Button>
            <Button onClick={save} disabled={saving}>
              {saving ? "Guardando…" : "Guardar"}
            </Button>
          </div>
        </div>
      </div>
    </Modal>
  );
}
