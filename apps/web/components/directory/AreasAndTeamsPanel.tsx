"use client";

// ENH-081 — Panel "Áreas y Equipos": catálogos tenant (áreas, equipos
// operativos, roles de proyecto) con CRUD inline.

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Icono } from "@/components/ui/icono";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/cn";
import {
  createArea,
  createTeam,
  deleteArea,
  deleteTeam,
  listAreaAssignments,
  listAreas,
  listAreasByProject,
  listTeams,
  setAreaAssignments,
  updateArea,
  updateTeam,
  type Area,
  type Team,
} from "@/lib/api/areas";
import { ensureProjectAssignment } from "@/lib/api/area-helpers";
import { confirmarDestructivo } from "@/lib/confirmar";
import {
  createProjectRole,
  deleteProjectRole,
  listProjectRoles,
  updateProjectRole,
  type ProjectRole,
} from "@/lib/api/project-directory";

type AreaModal = { kind: "area"; area: Area | null } | null;
type TeamModal = { kind: "team"; team: Team | null } | null;
type RoleModal = { kind: "role"; role: ProjectRole | null } | null;
type ActiveModal = AreaModal | TeamModal | RoleModal;

export function AreasAndTeamsPanel({
  projectId,
  organizationId,
}: {
  projectId?: string;
  /** US-170: si se pasa, filtra el catálogo a áreas de esta org. */
  organizationId?: string;
}) {
  const [areas, setAreas] = useState<Area[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [roles, setRoles] = useState<ProjectRole[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modal, setModal] = useState<ActiveModal>(null);
  // BUG-076: qué áreas del catálogo tenant están visibles/asignadas a este
  // proyecto (cascade), para indicarlo y permitir asignar/quitar inline. El
  // catálogo tenant es soporte para asignar; el scoping real es por proyecto.
  const [assignedAreaIds, setAssignedAreaIds] = useState<Set<string>>(
    new Set(),
  );
  const [assigningId, setAssigningId] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const [a, t, r] = await Promise.all([
        listAreas(
          organizationId
            ? { organization_id: organizationId, include_global: false }
            : undefined
        ),
        listTeams(),
        listProjectRoles(),
      ]);
      setAreas(a);
      setTeams(t);
      setRoles(r);
      if (projectId) {
        const assigned = await listAreasByProject(projectId).catch(
          () => [] as Area[],
        );
        setAssignedAreaIds(new Set(assigned.map((x) => x.id)));
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Error al cargar catálogos");
    } finally {
      setLoading(false);
    }
  }

  // BUG-076: asignar/quitar un área del catálogo a este proyecto sin pisar
  // otros alcances (org/program/global). Una vez asignada, aparece en los
  // pickers de tarea/RAID y en el Plan (todos project-scoped).
  async function toggleAreaAssignment(areaId: string) {
    if (!projectId) return;
    setAssigningId(areaId);
    setError(null);
    try {
      const existing = await listAreaAssignments(areaId);
      const hasDirect = existing.some((x) => x.project_id === projectId);
      const rest = existing
        .filter((x) => x.project_id !== projectId)
        .map((x) => ({
          organization_id: x.organization_id,
          program_id: x.program_id,
          project_id: x.project_id,
          is_global: x.is_global,
        }));
      await setAreaAssignments(
        areaId,
        hasDirect ? rest : [...rest, { project_id: projectId }],
      );
      await refresh();
    } catch (e) {
      setError(
        e instanceof ApiError ? e.message : "Error al cambiar la asignación",
      );
    } finally {
      setAssigningId(null);
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [organizationId]);

  async function handleDelete(
    kind: "area" | "team" | "role",
    id: string,
    name: string,
  ) {
    if (
      !confirmarDestructivo({
        objeto: `${kind} «${name}»`,
        consecuencia: "Las personas asignadas dejan de estar agrupadas ahí; no se borra a nadie.",
        reversibilidad: "definitiva",
      })
    )
      return;
    try {
      if (kind === "area") await deleteArea(id);
      else if (kind === "team") await deleteTeam(id);
      else await deleteProjectRole(id);
      await refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Error al eliminar");
    }
  }

  const areaById = Object.fromEntries(areas.map((a) => [a.id, a]));

  // ENH-183: en contexto de proyecto, la lista muestra SÓLO lo asignado.
  // Las no asignadas se ofrecen al crear ("traer existente").
  const visibleAreas = projectId
    ? areas.filter((a) => assignedAreaIds.has(a.id))
    : areas;
  const unassignedAreas = projectId
    ? areas.filter((a) => !assignedAreaIds.has(a.id))
    : [];
  // Un equipo "está en el proyecto" si su área está asignada (los equipos
  // siguen la visibilidad de su área).
  const visibleTeams = projectId
    ? teams.filter((t) => assignedAreaIds.has(t.area_id))
    : teams;

  if (loading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {error ? <Banner variant="danger">{error}</Banner> : null}

      {/* Áreas funcionales */}
      <SectionCard
        title="Áreas funcionales"
        description={
          projectId
            ? "Áreas de este proyecto. «Nueva área» permite crear una o traer una existente del catálogo del tenant."
            : "Catálogo tenant de áreas. Las personas se asocian a un área en su perfil; en el proyecto, los líderes de área se marcan vía participación."
        }
        onAdd={() => setModal({ kind: "area", area: null })}
        addLabel="Nueva área"
        empty={
          visibleAreas.length === 0
            ? projectId
              ? "Sin áreas en este proyecto. Usá «Nueva área» para crear o traer una."
              : "Sin áreas en el catálogo."
            : null
        }
      >
        {visibleAreas.map((a) => (
          <Row
            key={a.id}
            title={a.name}
            subtitle={a.description ?? undefined}
            inactive={!a.is_active}
            // ENH-183: en proyecto sólo se listan asignadas → la acción es Quitar.
            assigned={projectId ? true : undefined}
            assignBusy={assigningId === a.id}
            onToggleAssign={
              projectId ? () => toggleAreaAssignment(a.id) : undefined
            }
            onEdit={() => setModal({ kind: "area", area: a })}
            onDelete={() => handleDelete("area", a.id, a.name)}
          />
        ))}
      </SectionCard>

      {/* Equipos operativos */}
      <SectionCard
        title="Equipos operativos"
        description="Catálogo de equipos operativos (Testing, Deployment, etc.). Cada equipo pertenece a un área; las personas se asignan a un equipo vía su participación en el proyecto."
        onAdd={() => setModal({ kind: "team", team: null })}
        addLabel="Nuevo equipo"
        addDisabled={areas.length === 0}
        empty={
          visibleTeams.length === 0
            ? areas.length === 0
              ? "Crea primero un área para poder agregar equipos."
              : "Sin equipos operativos."
            : null
        }
      >
        {visibleTeams.map((t) => (
          <Row
            key={t.id}
            title={t.name}
            subtitle={t.description ?? undefined}
            badge={areaById[t.area_id]?.name}
            inactive={!t.is_active}
            onEdit={() => setModal({ kind: "team", team: t })}
            onDelete={() => handleDelete("team", t.id, t.name)}
          />
        ))}
      </SectionCard>

      {/* Roles de proyecto */}
      <SectionCard
        title="Roles de proyecto"
        description="Catálogo de roles asignables en una participación (PM, Sponsor, SME, etc.)."
        onAdd={() => setModal({ kind: "role", role: null })}
        addLabel="Nuevo rol"
        empty={roles.length === 0 ? "Sin roles en el catálogo." : null}
      >
        {roles.map((r) => (
          <Row
            key={r.id}
            title={r.name}
            subtitle={r.description ?? undefined}
            inactive={!r.is_active}
            onEdit={() => setModal({ kind: "role", role: r })}
            onDelete={() => handleDelete("role", r.id, r.name)}
          />
        ))}
      </SectionCard>

      {modal?.kind === "area" ? (
        <AreaModalForm
          area={modal.area}
          projectId={projectId}
          organizationId={organizationId}
          unassignedAreas={unassignedAreas}
          onClose={() => setModal(null)}
          onSaved={() => {
            setModal(null);
            refresh();
          }}
        />
      ) : null}
      {modal?.kind === "team" ? (
        <TeamModalForm
          team={modal.team}
          areas={areas}
          onClose={() => setModal(null)}
          onSaved={() => {
            setModal(null);
            refresh();
          }}
        />
      ) : null}
      {modal?.kind === "role" ? (
        <RoleModalForm
          role={modal.role}
          onClose={() => setModal(null)}
          onSaved={() => {
            setModal(null);
            refresh();
          }}
        />
      ) : null}
    </div>
  );
}

function SectionCard({
  title,
  description,
  onAdd,
  addLabel,
  addDisabled,
  empty,
  children,
}: {
  title: string;
  description: string;
  onAdd: () => void;
  addLabel: string;
  addDisabled?: boolean;
  empty: string | null;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--relieve-isla)]">
      <header className="flex items-start justify-between gap-3 border-b border-[var(--border-default)] px-3.5 py-3 shadow-[var(--linea-surco)]">
        <div>
          <h2 className="text-[13px] font-semibold text-[var(--text-primary)]">
            {title}
          </h2>
          <p className="text-[11.5px] text-[var(--text-tertiary)]">{description}</p>
        </div>
        <Button size="sm" onClick={onAdd} disabled={addDisabled}>
          <Icono nombre="plus" size={14} /> {addLabel}
        </Button>
      </header>
      <div className="divide-y divide-[var(--border-subtle)]">
        {empty ? (
          <p className="p-6 text-center text-[12.5px] text-[var(--text-tertiary)]">
            {empty}
          </p>
        ) : (
          children
        )}
      </div>
    </section>
  );
}

function Row({
  title,
  subtitle,
  badge,
  inactive,
  assigned,
  assignBusy,
  onToggleAssign,
  onEdit,
  onDelete,
}: {
  title: string;
  subtitle?: string;
  badge?: string;
  inactive?: boolean;
  // BUG-076: cuando se renderiza en contexto de proyecto, indica si el área
  // está asignada a este proyecto y ofrece el toggle de asignación.
  assigned?: boolean;
  assignBusy?: boolean;
  onToggleAssign?: () => void;
  onEdit: () => void;
  onDelete: () => void;
}) {
  return (
    <div className="flex min-h-11 items-center gap-3 px-3.5 py-2 text-[13px]">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="font-medium text-[var(--text-primary)]">{title}</span>
          {badge ? <Badge variant="neutral">{badge}</Badge> : null}
          {assigned !== undefined ? (
            <Badge variant={assigned ? "success" : "neutral"}>
              {assigned ? "En este proyecto" : "No asignada"}
            </Badge>
          ) : null}
          {inactive ? <Badge variant="danger">Inactivo</Badge> : null}
        </div>
        {subtitle ? (
          <p className="text-[11.5px] text-[var(--text-tertiary)]">{subtitle}</p>
        ) : null}
      </div>
      {onToggleAssign ? (
        <Button
          size="sm"
          variant={assigned ? "ghost" : "secondary"}
          onClick={onToggleAssign}
          disabled={assignBusy}
          title={assigned ? "Quitar del proyecto" : "Asignar al proyecto"}
        >
          {assignBusy ? "…" : assigned ? "Quitar" : "Asignar"}
        </Button>
      ) : null}
      <Button size="sm" variant="ghost" onClick={onEdit} title="Editar">
        <Icono nombre="pen" size={14} />
      </Button>
      <Button size="sm" variant="ghost" onClick={onDelete} title="Eliminar">
        <Icono nombre="bin" size={14} />
      </Button>
    </div>
  );
}

// ---------- Modales ----------
// BUG-071: ensureProjectAssignment vive ahora en @/lib/api/area-helpers
// para que el inline-create del DirectoryView lo reuse.

function AreaModalForm({
  area,
  projectId,
  organizationId,
  unassignedAreas = [],
  onClose,
  onSaved,
}: {
  area: Area | null;
  projectId?: string;
  /** US-170: org a la que se asigna el área nueva. */
  organizationId?: string;
  /** ENH-183: áreas del catálogo aún no asignadas (para "traer existente"). */
  unassignedAreas?: Area[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [name, setName] = useState(area?.name ?? "");
  const [description, setDescription] = useState(area?.description ?? "");
  const [isActive, setIsActive] = useState(area?.is_active ?? true);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  // ENH-183: al crear dentro de un proyecto, ofrecer traer una existente.
  const canBring = !area && !!projectId && unassignedAreas.length > 0;
  const [mode, setMode] = useState<"create" | "existing">("create");
  const [bringId, setBringId] = useState<string>("");

  async function submit() {
    setSaving(true);
    setErr(null);
    try {
      if (mode === "existing" && canBring) {
        if (!bringId) {
          setErr("Seleccioná un área del catálogo");
          setSaving(false);
          return;
        }
        await ensureProjectAssignment(bringId, projectId!);
        onSaved();
        return;
      }
      if (!name.trim()) {
        setErr("Nombre requerido");
        setSaving(false);
        return;
      }
      if (area) {
        await updateArea(area.id, {
          name: name.trim(),
          description: description.trim() || null,
          is_active: isActive,
        });
        // En contexto de proyecto, "adoptar" el área existente: dejarla
        // visible en este proyecto (recupera áreas creadas sin asignar).
        if (projectId) await ensureProjectAssignment(area.id, projectId);
      } else {
        // BUG-085: dentro de un proyecto el org_id es el del proyecto —
        // pasamos project_id y el backend deriva el org + crea el
        // AreaAssignment del proyecto. En contexto org (sin projectId) se
        // pasa organization_id y el área se propaga a sus hijos.
        await createArea({
          name: name.trim(),
          description: description.trim() || null,
          is_active: isActive,
          project_id: projectId ?? null,
          organization_id: projectId ? null : organizationId ?? null,
        });
      }
      onSaved();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Error al guardar");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal open title={area ? "Editar área" : "Nueva área"} onClose={onClose}>
      <div className="space-y-3">
        {canBring ? (
          <div
            role="radiogroup"
            aria-label="Modo"
            className="inline-flex rounded-[var(--radius-md)] border border-[var(--border-default)] p-0.5 text-xs"
          >
            {(
              [
                { v: "create", label: "Crear nueva" },
                { v: "existing", label: "Traer existente" },
              ] as const
            ).map((opt) => (
              <button
                key={opt.v}
                type="button"
                onClick={() => setMode(opt.v)}
                className={cn(
                  "rounded-[var(--radius-sm)] px-3 py-1 font-medium",
                  mode === opt.v
                    ? "bg-[var(--color-primary)] text-[var(--color-inverse)]"
                    : "text-[var(--text-secondary)]",
                )}
              >
                {opt.label}
              </button>
            ))}
          </div>
        ) : null}
        {projectId && mode === "create" ? (
          <p className="rounded-[var(--radius-sm)] bg-[var(--color-subtle)] px-2 py-1 text-xs text-[var(--color-tertiary)]">
            {area
              ? "Al guardar, esta área queda disponible en este proyecto."
              : "El área se agrega a este proyecto automáticamente."}
          </p>
        ) : null}
        {mode === "existing" && canBring ? (
          <FieldLabel label="Área del catálogo" required>
            <Select value={bringId} onChange={(e) => setBringId(e.target.value)}>
              <option value="">— Selecciona —</option>
              {unassignedAreas.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </Select>
          </FieldLabel>
        ) : (
          <>
        <FieldLabel label="Nombre" required>
          <Input value={name} onChange={(e) => setName(e.target.value)} />
        </FieldLabel>
        <FieldLabel label="Descripción">
          <Textarea
            rows={2}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </FieldLabel>
        <Switch checked={isActive} onChange={setIsActive} label="Activa" />
          </>
        )}
        {err ? <Banner variant="danger">{err}</Banner> : null}
        <ModalActions onCancel={onClose} onSave={submit} saving={saving} />
      </div>
    </Modal>
  );
}

function TeamModalForm({
  team,
  areas,
  onClose,
  onSaved,
}: {
  team: Team | null;
  areas: Area[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [name, setName] = useState(team?.name ?? "");
  const [description, setDescription] = useState(team?.description ?? "");
  const [areaId, setAreaId] = useState(team?.area_id ?? areas[0]?.id ?? "");
  const [isActive, setIsActive] = useState(team?.is_active ?? true);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function submit() {
    if (!name.trim() || !areaId) {
      setErr("Área y nombre requeridos");
      return;
    }
    setSaving(true);
    setErr(null);
    try {
      if (team) {
        await updateTeam(team.id, {
          area_id: areaId,
          name: name.trim(),
          description: description.trim() || null,
          is_active: isActive,
        });
      } else {
        await createTeam({
          area_id: areaId,
          name: name.trim(),
          description: description.trim() || null,
          is_active: isActive,
        });
      }
      onSaved();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Error al guardar");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal open title={team ? "Editar equipo" : "Nuevo equipo"} onClose={onClose}>
      <div className="space-y-3">
        <FieldLabel label="Área" required>
          <Select value={areaId} onChange={(e) => setAreaId(e.target.value)}>
            <option value="">— Selecciona —</option>
            {areas.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </Select>
        </FieldLabel>
        <FieldLabel label="Nombre" required>
          <Input value={name} onChange={(e) => setName(e.target.value)} />
        </FieldLabel>
        <FieldLabel label="Descripción">
          <Textarea
            rows={2}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </FieldLabel>
        <Switch checked={isActive} onChange={setIsActive} label="Activo" />
        {err ? <Banner variant="danger">{err}</Banner> : null}
        <ModalActions onCancel={onClose} onSave={submit} saving={saving} />
      </div>
    </Modal>
  );
}

function RoleModalForm({
  role,
  onClose,
  onSaved,
}: {
  role: ProjectRole | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [name, setName] = useState(role?.name ?? "");
  const [description, setDescription] = useState(role?.description ?? "");
  const [isActive, setIsActive] = useState(role?.is_active ?? true);
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
      if (role) {
        await updateProjectRole(role.id, {
          name: name.trim(),
          description: description.trim() || null,
          is_active: isActive,
        });
      } else {
        await createProjectRole({
          name: name.trim(),
          description: description.trim() || null,
          is_active: isActive,
        });
      }
      onSaved();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Error al guardar");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal open title={role ? "Editar rol" : "Nuevo rol"} onClose={onClose}>
      <div className="space-y-3">
        <FieldLabel label="Nombre" required>
          <Input value={name} onChange={(e) => setName(e.target.value)} />
        </FieldLabel>
        <FieldLabel label="Descripción">
          <Textarea
            rows={2}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </FieldLabel>
        <Switch checked={isActive} onChange={setIsActive} label="Activo" />
        {err ? <Banner variant="danger">{err}</Banner> : null}
        <ModalActions onCancel={onClose} onSave={submit} saving={saving} />
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

function ModalActions({
  onCancel,
  onSave,
  saving,
}: {
  onCancel: () => void;
  onSave: () => void;
  saving: boolean;
}) {
  return (
    <div className="flex justify-end gap-2 pt-2">
      <Button variant="ghost" onClick={onCancel} disabled={saving}>
        Cancelar
      </Button>
      <Button onClick={onSave} disabled={saving}>
        {saving ? "Guardando…" : "Guardar"}
      </Button>
    </div>
  );
}
