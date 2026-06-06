"use client";

// US-116 — Toggle Directorio del proyecto.
// ENH-082 — agregado: operational_team_id en modales, inline create de
// área/equipo/rol, botón "Quitar" en fila, nombres legibles (no UUIDs).

import { useEffect, useMemo, useState } from "react";
import { Crown, Plus, Star, Trash2, UserPlus } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  createActor,
  createTeam,
  listActors,
  listAreasByProject,
  listTeams,
  updateActor,
  type Actor,
  type Area,
  type Team,
} from "@/lib/api/areas";
import { createOrAdoptAreaForProject } from "@/lib/api/area-helpers";
import {
  createParticipation,
  createProjectRole,
  deleteParticipation,
  listParticipations,
  listProjectRoles,
  updateParticipation,
  type Participation,
  type ProjectRole,
} from "@/lib/api/project-directory";
import { useSortableRows } from "@/lib/hooks/use-sortable-rows";
import { SortableTh } from "@/components/ui/sortable-th";

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
  const [areas, setAreas] = useState<Area[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [roles, setRoles] = useState<ProjectRole[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [editing, setEditing] = useState<Participation | null>(null);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const [parts, ar, tm, ro, actors] = await Promise.all([
        listParticipations(projectId, { include: "actor" }),
        listAreasByProject(projectId).catch(() => [] as Area[]),
        listTeams().catch(() => [] as Team[]),
        listProjectRoles().catch(() => [] as ProjectRole[]),
        listActors().catch(() => [] as Actor[]),
      ]);
      setParticipations(parts);
      setAreas(ar);
      setTeams(tm);
      setRoles(ro);
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

  const areasById = useMemo(
    () => Object.fromEntries(areas.map((a) => [a.id, a])),
    [areas],
  );
  const teamsById = useMemo(
    () => Object.fromEntries(teams.map((t) => [t.id, t])),
    [teams],
  );
  const rolesById = useMemo(
    () => Object.fromEntries(roles.map((r) => [r.id, r])),
    [roles],
  );

  const rows: Row[] = useMemo(() => {
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

  // ENH-088: orden por columna.
  const { sortedRows, ctrl: sortCtrl } = useSortableRows<Row>(rows);

  async function handleRemove(p: Participation, actorName: string | undefined) {
    if (!confirm(`¿Quitar a "${actorName ?? "esta persona"}" del proyecto?`)) {
      return;
    }
    try {
      await deleteParticipation(projectId, p.id);
      await refresh();
    } catch (e: any) {
      setError(e?.message ?? "Error al quitar");
    }
  }

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
                <SortableTh<Row> sortKey="name" getter={(r) => r.actor?.name ?? ""} ctrl={sortCtrl}>Persona</SortableTh>
                <SortableTh<Row> sortKey="company" getter={(r) => r.actor?.company ?? ""} ctrl={sortCtrl}>Empresa / Cargo</SortableTh>
                <SortableTh<Row> sortKey="area" getter={(r) => r.participation.functional_area_id ? areasById[r.participation.functional_area_id]?.name ?? "" : ""} ctrl={sortCtrl}>Área funcional</SortableTh>
                <SortableTh<Row> sortKey="team" getter={(r) => r.participation.operational_team_id ? teamsById[r.participation.operational_team_id]?.name ?? "" : ""} ctrl={sortCtrl}>Equipo operativo</SortableTh>
                <SortableTh<Row> sortKey="role" getter={(r) => r.participation.project_role_id ? rolesById[r.participation.project_role_id]?.name ?? "" : ""} ctrl={sortCtrl}>Rol</SortableTh>
                <SortableTh<Row> sortKey="period" getter={(r) => r.participation.start_date ?? ""} ctrl={sortCtrl}>Periodo</SortableTh>
                <th className="px-3 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {sortedRows.map(({ participation: p, actor }) => (
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
                  <td className="px-3 py-2">
                    {p.operational_team_id
                      ? teamsById[p.operational_team_id]?.name ?? "—"
                      : "—"}
                  </td>
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
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleRemove(p, actor?.name)}
                      title="Quitar del proyecto"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
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
          initialAreas={areas}
          initialTeams={teams}
          initialRoles={roles}
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
          actor={actorsById[editing.actor_id] ?? editing.actor ?? null}
          initialAreas={areas}
          initialTeams={teams}
          initialRoles={roles}
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
// Add Person modal
// ---------------------------------------------------------------------------
function AddPersonModal({
  projectId,
  initialAreas,
  initialTeams,
  initialRoles,
  onClose,
  onSaved,
}: {
  projectId: string;
  initialAreas: Area[];
  initialTeams: Team[];
  initialRoles: ProjectRole[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [tenantActors, setTenantActors] = useState<Actor[]>([]);
  const [areas, setAreas] = useState<Area[]>(initialAreas);
  const [teams, setTeams] = useState<Team[]>(initialTeams);
  const [roles, setRoles] = useState<ProjectRole[]>(initialRoles);
  const [mode, setMode] = useState<"existing" | "new">("existing");
  const [actorId, setActorId] = useState<string>("");
  const [newActorName, setNewActorName] = useState("");
  const [newActorEmail, setNewActorEmail] = useState("");
  const [newActorCompany, setNewActorCompany] = useState("");
  const [newActorJobTitle, setNewActorJobTitle] = useState("");
  const [functionalAreaId, setFunctionalAreaId] = useState<string>("");
  const [operationalTeamId, setOperationalTeamId] = useState<string>("");
  const [roleId, setRoleId] = useState<string>("");
  const [isAreaLead, setIsAreaLead] = useState(false);
  const [isPrimary, setIsPrimary] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listActors()
      .then((a) => setTenantActors(a))
      .catch(() => setTenantActors([]));
  }, []);

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
        operational_team_id: operationalTeamId || undefined,
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

        <div className="grid grid-cols-1 gap-2">
          <CatalogPickerWithCreate
            label="Área funcional"
            value={functionalAreaId}
            onChange={setFunctionalAreaId}
            options={areas.map((a) => ({ id: a.id, label: a.name }))}
            onCreate={async (name) => {
              // BUG-071: si el área ya existe en el catálogo tenant sin
              // assignment al proyecto, la adoptamos en lugar de tirar
              // 409. Si la asignación falla tras crear el área, ahora
              // SÍ propaga el error (antes lo tragaba en silencio y la
              // dejaba huérfana, por eso "ya existe pero no aparece").
              const result = await createOrAdoptAreaForProject(
                name,
                projectId,
              );
              if (result.area) {
                setAreas((prev) => [...prev, result.area as Area]);
              } else if (!areas.some((a) => a.id === result.id)) {
                // Caso adopted: el área existía en tenant pero no
                // estaba en el state local del modal. La incluimos
                // como placeholder mínimo para que el Select la
                // muestre seleccionada. El próximo refresh del padre
                // traerá la metadata completa vía listAreasByProject.
                setAreas((prev) => [
                  ...prev,
                  { id: result.id, name } as Area,
                ]);
              }
              return result.id;
            }}
            createPlaceholder="Nombre del área"
          />
          <CatalogPickerWithCreate
            label="Equipo operativo"
            value={operationalTeamId}
            onChange={setOperationalTeamId}
            options={teams.map((t) => ({
              id: t.id,
              label: t.name,
              hint:
                areas.find((a) => a.id === t.area_id)?.name ?? undefined,
            }))}
            onCreate={async (name) => {
              const areaForTeam =
                functionalAreaId || areas[0]?.id;
              if (!areaForTeam) {
                throw new Error("Crea o selecciona un área primero");
              }
              const created = await createTeam({
                area_id: areaForTeam,
                name,
                is_active: true,
              });
              setTeams((prev) => [...prev, created]);
              return created.id;
            }}
            createPlaceholder="Nombre del equipo"
          />
          <CatalogPickerWithCreate
            label="Rol proyecto"
            value={roleId}
            onChange={setRoleId}
            options={roles.map((r) => ({ id: r.id, label: r.name }))}
            onCreate={async (name) => {
              const created = await createProjectRole({
                name,
                is_active: true,
              });
              setRoles((prev) => [...prev, created]);
              return created.id;
            }}
            createPlaceholder="Nombre del rol"
          />
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
  actor,
  initialAreas,
  initialTeams,
  initialRoles,
  onClose,
  onSaved,
}: {
  projectId: string;
  participation: Participation;
  actor: Actor | { id: string; name: string; email: string | null; company: string | null; job_title: string | null } | null;
  initialAreas: Area[];
  initialTeams: Team[];
  initialRoles: ProjectRole[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [areas, setAreas] = useState<Area[]>(initialAreas);
  const [teams, setTeams] = useState<Team[]>(initialTeams);
  const [roles, setRoles] = useState<ProjectRole[]>(initialRoles);
  // ENH-087: campos del actor editables desde el modal.
  const [actorName, setActorName] = useState(actor?.name ?? "");
  const [actorEmail, setActorEmail] = useState(actor?.email ?? "");
  const [actorPhone, setActorPhone] = useState(
    (actor as Actor | null)?.phone ?? "",
  );
  const [actorCompany, setActorCompany] = useState(actor?.company ?? "");
  const [actorJobTitle, setActorJobTitle] = useState(actor?.job_title ?? "");
  const [functionalAreaId, setFunctionalAreaId] = useState(
    participation.functional_area_id ?? "",
  );
  const [operationalTeamId, setOperationalTeamId] = useState(
    participation.operational_team_id ?? "",
  );
  const [roleId, setRoleId] = useState(participation.project_role_id ?? "");
  const [isAreaLead, setIsAreaLead] = useState(participation.is_area_lead);
  const [isPrimary, setIsPrimary] = useState(participation.is_primary);
  const [startDate, setStartDate] = useState(participation.start_date ?? "");
  const [endDate, setEndDate] = useState(participation.end_date ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    setSaving(true);
    setError(null);
    try {
      // ENH-087: actualiza actor si cambió algún campo.
      if (actor) {
        const actorChanged =
          (actor.name ?? "") !== actorName ||
          (actor.email ?? "") !== actorEmail ||
          ((actor as Actor).phone ?? "") !== actorPhone ||
          (actor.company ?? "") !== actorCompany ||
          (actor.job_title ?? "") !== actorJobTitle;
        if (actorChanged) {
          await updateActor(actor.id, {
            name: actorName.trim() || undefined,
            email: actorEmail.trim() || null,
            phone: actorPhone.trim() || null,
            company: actorCompany.trim() || null,
            job_title: actorJobTitle.trim() || null,
          } as any);
        }
      }
      await updateParticipation(projectId, participation.id, {
        functional_area_id: functionalAreaId || null,
        operational_team_id: operationalTeamId || null,
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
    if (!confirm("¿Quitar persona del proyecto?")) return;
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
    <Modal open={true} title="Editar persona y participación" onClose={onClose}>
      <div className="space-y-3">
        {/* ENH-087: edición de campos del actor */}
        <div className="space-y-2 rounded border border-[var(--border-default)] p-2">
          <div className="text-xs font-semibold text-[var(--text-secondary)]">
            Datos de la persona
          </div>
          <Input
            placeholder="Nombre completo"
            value={actorName}
            onChange={(e) => setActorName(e.target.value)}
          />
          <div className="grid grid-cols-2 gap-2">
            <Input
              placeholder="Email"
              value={actorEmail}
              onChange={(e) => setActorEmail(e.target.value)}
            />
            <Input
              placeholder="Teléfono"
              value={actorPhone}
              onChange={(e) => setActorPhone(e.target.value)}
            />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <Input
              placeholder="Empresa"
              value={actorCompany}
              onChange={(e) => setActorCompany(e.target.value)}
            />
            <Input
              placeholder="Cargo"
              value={actorJobTitle}
              onChange={(e) => setActorJobTitle(e.target.value)}
            />
          </div>
        </div>

        <CatalogPickerWithCreate
          label="Área funcional"
          value={functionalAreaId}
          onChange={setFunctionalAreaId}
          options={areas.map((a) => ({ id: a.id, label: a.name }))}
          onCreate={async (name) => {
            // BUG-071: mismo patrón que AddPersonModal. createOrAdopt
            // maneja 409 AREA_NAME_DUPLICATE adoptando el área existente
            // y propaga si la asignación falla (no más áreas huérfanas).
            const result = await createOrAdoptAreaForProject(name, projectId);
            if (result.area) {
              setAreas((prev) => [...prev, result.area as Area]);
            } else if (!areas.some((a) => a.id === result.id)) {
              setAreas((prev) => [...prev, { id: result.id, name } as Area]);
            }
            return result.id;
          }}
          createPlaceholder="Nombre del área"
        />
        <CatalogPickerWithCreate
          label="Equipo operativo"
          value={operationalTeamId}
          onChange={setOperationalTeamId}
          options={teams.map((t) => ({
            id: t.id,
            label: t.name,
            hint: areas.find((a) => a.id === t.area_id)?.name ?? undefined,
          }))}
          onCreate={async (name) => {
            const areaForTeam = functionalAreaId || areas[0]?.id;
            if (!areaForTeam) {
              throw new Error("Crea o selecciona un área primero");
            }
            const created = await createTeam({
              area_id: areaForTeam,
              name,
              is_active: true,
            });
            setTeams((prev) => [...prev, created]);
            return created.id;
          }}
          createPlaceholder="Nombre del equipo"
        />
        <CatalogPickerWithCreate
          label="Rol proyecto"
          value={roleId}
          onChange={setRoleId}
          options={roles.map((r) => ({ id: r.id, label: r.name }))}
          onCreate={async (name) => {
            const created = await createProjectRole({ name, is_active: true });
            setRoles((prev) => [...prev, created]);
            return created.id;
          }}
          createPlaceholder="Nombre del rol"
        />

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
            <Trash2 className="mr-1 h-4 w-4" /> Quitar del proyecto
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

// ---------------------------------------------------------------------------
// Select con opción "+ Crear nuevo" inline. onCreate recibe el nombre y
// devuelve el id del item creado, que se setea automáticamente.
// ---------------------------------------------------------------------------
function CatalogPickerWithCreate({
  label,
  value,
  onChange,
  options,
  onCreate,
  createPlaceholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { id: string; label: string; hint?: string }[];
  onCreate: (name: string) => Promise<string>;
  createPlaceholder: string;
}) {
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function submitCreate() {
    if (!newName.trim()) return;
    setBusy(true);
    setErr(null);
    try {
      const id = await onCreate(newName.trim());
      onChange(id);
      setNewName("");
      setCreating(false);
    } catch (e: any) {
      setErr(e?.message ?? "Error al crear");
    } finally {
      setBusy(false);
    }
  }

  return (
    <label className="block text-xs">
      <div className="flex items-center justify-between">
        <span>{label}</span>
        {!creating ? (
          <button
            type="button"
            className="text-[var(--color-accent)] hover:underline"
            onClick={() => setCreating(true)}
          >
            + Crear nuevo
          </button>
        ) : (
          <button
            type="button"
            className="text-[var(--color-tertiary)] hover:underline"
            onClick={() => {
              setCreating(false);
              setNewName("");
              setErr(null);
            }}
          >
            Cancelar
          </button>
        )}
      </div>
      {creating ? (
        <div className="mt-1 space-y-1">
          <div className="flex gap-1">
            <Input
              placeholder={createPlaceholder}
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  submitCreate();
                }
              }}
            />
            <Button size="sm" onClick={submitCreate} disabled={busy || !newName.trim()}>
              {busy ? "…" : "Crear"}
            </Button>
          </div>
          {err ? <p className="text-red-600">{err}</p> : null}
        </div>
      ) : (
        <Select value={value} onChange={(e) => onChange(e.target.value)}>
          <option value="">—</option>
          {options.map((o) => (
            <option key={o.id} value={o.id}>
              {o.label}
              {o.hint ? ` (${o.hint})` : ""}
            </option>
          ))}
        </Select>
      )}
    </label>
  );
}
