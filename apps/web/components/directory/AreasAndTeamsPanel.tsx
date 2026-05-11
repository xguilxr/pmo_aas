"use client";

// ENH-081 — Panel "Áreas y Equipos": catálogos tenant (áreas, equipos
// operativos, roles de proyecto) con CRUD inline.

import { useEffect, useState } from "react";
import { Pencil, Plus, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api";
import {
  createArea,
  createTeam,
  deleteArea,
  deleteTeam,
  listAreas,
  listTeams,
  updateArea,
  updateTeam,
  type Area,
  type Team,
} from "@/lib/api/areas";
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

export function AreasAndTeamsPanel() {
  const [areas, setAreas] = useState<Area[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [roles, setRoles] = useState<ProjectRole[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modal, setModal] = useState<ActiveModal>(null);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const [a, t, r] = await Promise.all([
        listAreas(),
        listTeams(),
        listProjectRoles(),
      ]);
      setAreas(a);
      setTeams(t);
      setRoles(r);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Error al cargar catálogos");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleDelete(
    kind: "area" | "team" | "role",
    id: string,
    name: string,
  ) {
    if (!confirm(`¿Eliminar ${kind} "${name}"?`)) return;
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
      {error ? (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      {/* Áreas funcionales */}
      <SectionCard
        title="Áreas funcionales"
        description="Catálogo tenant de áreas. Las personas se asocian a un área en su perfil; en el proyecto, los líderes de área se marcan vía participación."
        onAdd={() => setModal({ kind: "area", area: null })}
        addLabel="Nueva área"
        empty={areas.length === 0 ? "Sin áreas en el catálogo." : null}
      >
        {areas.map((a) => (
          <Row
            key={a.id}
            title={a.name}
            subtitle={a.description ?? undefined}
            inactive={!a.is_active}
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
          teams.length === 0
            ? areas.length === 0
              ? "Crea primero un área para poder agregar equipos."
              : "Sin equipos operativos."
            : null
        }
      >
        {teams.map((t) => (
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
    <section className="rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--color-surface)]">
      <header className="flex items-start justify-between gap-3 border-b border-[var(--border-default)] p-3">
        <div>
          <h2 className="text-sm font-semibold text-[var(--color-primary)]">
            {title}
          </h2>
          <p className="text-xs text-[var(--color-tertiary)]">{description}</p>
        </div>
        <Button size="sm" onClick={onAdd} disabled={addDisabled}>
          <Plus className="mr-1 h-4 w-4" /> {addLabel}
        </Button>
      </header>
      <div className="divide-y divide-[var(--border-subtle)]">
        {empty ? (
          <p className="p-6 text-center text-xs text-[var(--color-tertiary)]">
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
  onEdit,
  onDelete,
}: {
  title: string;
  subtitle?: string;
  badge?: string;
  inactive?: boolean;
  onEdit: () => void;
  onDelete: () => void;
}) {
  return (
    <div className="flex items-center gap-3 px-3 py-2 text-sm">
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <span className="font-medium text-[var(--color-primary)]">{title}</span>
          {badge ? <Badge variant="secondary">{badge}</Badge> : null}
          {inactive ? <Badge variant="danger">Inactivo</Badge> : null}
        </div>
        {subtitle ? (
          <p className="text-xs text-[var(--color-tertiary)]">{subtitle}</p>
        ) : null}
      </div>
      <Button size="sm" variant="ghost" onClick={onEdit} title="Editar">
        <Pencil className="h-3.5 w-3.5" />
      </Button>
      <Button size="sm" variant="ghost" onClick={onDelete} title="Eliminar">
        <Trash2 className="h-3.5 w-3.5" />
      </Button>
    </div>
  );
}

// ---------- Modales ----------

function AreaModalForm({
  area,
  onClose,
  onSaved,
}: {
  area: Area | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [name, setName] = useState(area?.name ?? "");
  const [description, setDescription] = useState(area?.description ?? "");
  const [isActive, setIsActive] = useState(area?.is_active ?? true);
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
      if (area) {
        await updateArea(area.id, {
          name: name.trim(),
          description: description.trim() || null,
          is_active: isActive,
        });
      } else {
        await createArea({
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
    <Modal open title={area ? "Editar área" : "Nueva área"} onClose={onClose}>
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
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={isActive}
            onChange={(e) => setIsActive(e.target.checked)}
          />
          <span>Activa</span>
        </label>
        {err ? <p className="text-sm text-red-600">{err}</p> : null}
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
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={isActive}
            onChange={(e) => setIsActive(e.target.checked)}
          />
          <span>Activo</span>
        </label>
        {err ? <p className="text-sm text-red-600">{err}</p> : null}
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
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={isActive}
            onChange={(e) => setIsActive(e.target.checked)}
          />
          <span>Activo</span>
        </label>
        {err ? <p className="text-sm text-red-600">{err}</p> : null}
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
