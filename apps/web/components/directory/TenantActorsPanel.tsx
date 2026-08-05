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
  type ActorSeniority,
  type Area,
  type Discipline,
  type ResourceType,
  type ScarcityLevel,
} from "@/lib/api/areas";
import { useSortableRows } from "@/lib/hooks/use-sortable-rows";
import { SortableTh } from "@/components/ui/sortable-th";

// US-182: labels ES del pool de recursos con capacidad.
const RESOURCE_TYPE_LABELS: Record<ResourceType, string> = {
  cliente_negocio: "Cliente Negocio",
  cliente_it: "Cliente IT",
  e4_pmo: "E4 PMO",
  e4_tecnologia: "E4 Tecnología",
  vendor_externo: "Vendor Externo",
};

const DISCIPLINE_LABELS: Record<Discipline, string> = {
  pm: "PM",
  pmo: "PMO",
  arquitectura: "Arquitectura",
  infraestructura: "Infraestructura",
  aplicaciones: "Aplicaciones",
  datos: "Datos",
  seguridad: "Seguridad",
  integraciones: "Integraciones",
  negocio: "Negocio",
  change: "Change",
  testing: "Testing",
  vendor: "Vendor",
};

const SENIORITY_LABELS: Record<ActorSeniority, string> = {
  junior: "Junior",
  mid: "Mid",
  senior: "Senior",
  lead: "Lead",
};

const SCARCITY_LABELS: Record<ScarcityLevel, string> = {
  alta: "Alta",
  media: "Media",
  baja: "Baja",
};

function resourceTypeLabel(v?: ResourceType | null): string {
  return v ? RESOURCE_TYPE_LABELS[v] ?? v : "—";
}

function disciplineLabel(v?: Discipline | null): string {
  return v ? DISCIPLINE_LABELS[v] ?? v : "—";
}

export function TenantActorsPanel() {
  const [actors, setActors] = useState<Actor[]>([]);
  const [areas, setAreas] = useState<Area[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [areaFilter, setAreaFilter] = useState("");
  // US-182: filtros client-side por tipo de recurso / función de portafolio.
  const [resourceTypeFilter, setResourceTypeFilter] = useState("");
  const [disciplineFilter, setDisciplineFilter] = useState("");
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
    if (resourceTypeFilter)
      rows = rows.filter((a) => a.resource_type === resourceTypeFilter);
    if (disciplineFilter)
      rows = rows.filter(
        (a) => a.discipline === disciplineFilter,
      );
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
  }, [actors, areaFilter, resourceTypeFilter, disciplineFilter, search]);

  const { sortedRows, ctrl: sortCtrl } = useSortableRows<Actor>(filtered);

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
        <Select
          value={resourceTypeFilter}
          onChange={(e) => setResourceTypeFilter(e.target.value)}
          className="max-w-xs"
        >
          <option value="">Todos los tipos</option>
          {(Object.keys(RESOURCE_TYPE_LABELS) as ResourceType[]).map((rt) => (
            <option key={rt} value={rt}>
              {RESOURCE_TYPE_LABELS[rt]}
            </option>
          ))}
        </Select>
        <Select
          value={disciplineFilter}
          onChange={(e) => setDisciplineFilter(e.target.value)}
          className="max-w-xs"
        >
          <option value="">Todas las funciones</option>
          {(Object.keys(DISCIPLINE_LABELS) as Discipline[]).map(
            (pf) => (
              <option key={pf} value={pf}>
                {DISCIPLINE_LABELS[pf]}
              </option>
            ),
          )}
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
              <SortableTh<Actor> sortKey="name" getter={(a) => a.name} ctrl={sortCtrl}>Nombre</SortableTh>
              <SortableTh<Actor> sortKey="email" getter={(a) => a.email ?? ""} ctrl={sortCtrl}>Email</SortableTh>
              <SortableTh<Actor> sortKey="company" getter={(a) => a.company ?? ""} ctrl={sortCtrl}>Empresa / Cargo</SortableTh>
              <SortableTh<Actor> sortKey="area" getter={(a) => a.area_id ? areaById[a.area_id]?.name ?? "" : ""} ctrl={sortCtrl}>Área funcional</SortableTh>
              <SortableTh<Actor> sortKey="resource_type" getter={(a) => resourceTypeLabel(a.resource_type)} ctrl={sortCtrl}>Tipo</SortableTh>
              <SortableTh<Actor> sortKey="discipline" getter={(a) => disciplineLabel(a.discipline)} ctrl={sortCtrl}>Función</SortableTh>
              <SortableTh<Actor> sortKey="project_capacity_pct" getter={(a) => a.project_capacity_pct ?? 100} ctrl={sortCtrl} align="right">Cap. proyectos %</SortableTh>
              <SortableTh<Actor> sortKey="is_key_resource" getter={(a) => a.is_key_resource ?? false} ctrl={sortCtrl} align="center">🔑</SortableTh>
              <th className="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {sortedRows.length === 0 ? (
              <tr>
                <td
                  colSpan={9}
                  className="p-8 text-center text-xs text-[var(--color-tertiary)]"
                >
                  {actors.length === 0
                    ? "Sin personas en el catálogo tenant."
                    : "Ningún match para el filtro."}
                </td>
              </tr>
            ) : (
              sortedRows.map((a) => (
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
                  <td className="px-3 py-2 text-xs">
                    {resourceTypeLabel(a.resource_type)}
                  </td>
                  <td className="px-3 py-2 text-xs">
                    {disciplineLabel(a.discipline)}
                  </td>
                  <td className="px-3 py-2 text-right text-xs">
                    {a.project_capacity_pct ?? 100}%
                  </td>
                  <td className="px-3 py-2 text-center">
                    {a.is_key_resource ? (
                      <span title="Recurso clave">🔑</span>
                    ) : null}
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
  // US-182: pool de recursos con capacidad.
  const [resourceType, setResourceType] = useState(actor?.resource_type ?? "");
  const [discipline, setDiscipline] = useState(
    actor?.discipline ?? "",
  );
  const [seniority, setSeniority] = useState(actor?.seniority ?? "");
  const [scarcityLevel, setScarcityLevel] = useState(
    actor?.scarcity_level ?? "",
  );
  const [location, setLocation] = useState(actor?.location ?? "");
  const [skillsTags, setSkillsTags] = useState(
    (actor?.skills_tags ?? []).join(", "),
  );
  const [nominalCapacityPct, setNominalCapacityPct] = useState(
    String(actor?.nominal_capacity_pct ?? 100),
  );
  const [projectCapacityPct, setProjectCapacityPct] = useState(
    String(actor?.project_capacity_pct ?? 100),
  );
  const [isKeyResource, setIsKeyResource] = useState(
    actor?.is_key_resource ?? false,
  );
  const [isSharedResource, setIsSharedResource] = useState(
    actor?.is_shared_resource ?? true,
  );
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
        // US-182: pool de recursos con capacidad.
        resource_type: resourceType || null,
        discipline: discipline || null,
        seniority: seniority || null,
        scarcity_level: scarcityLevel || null,
        location: location.trim() || null,
        skills_tags: skillsTags
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        nominal_capacity_pct:
          nominalCapacityPct.trim() === "" ? 100 : Number(nominalCapacityPct),
        project_capacity_pct:
          projectCapacityPct.trim() === "" ? 100 : Number(projectCapacityPct),
        is_key_resource: isKeyResource,
        is_shared_resource: isSharedResource,
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

        {/* US-182: pool de recursos con capacidad. */}
        <div className="space-y-3 border-t border-[var(--border-default)] pt-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--color-tertiary)]">
            Recurso y capacidad
          </p>
          <div className="grid grid-cols-2 gap-2">
            <FieldLabel label="Tipo de recurso">
              <Select
                value={resourceType}
                onChange={(e) =>
                  setResourceType(e.target.value as ResourceType | "")
                }
              >
                <option value="">Sin clasificar</option>
                {(Object.keys(RESOURCE_TYPE_LABELS) as ResourceType[]).map(
                  (rt) => (
                    <option key={rt} value={rt}>
                      {RESOURCE_TYPE_LABELS[rt]}
                    </option>
                  ),
                )}
              </Select>
            </FieldLabel>
            <FieldLabel label="Función de portafolio">
              <Select
                value={discipline}
                onChange={(e) =>
                  setDiscipline(
                    e.target.value as Discipline | "",
                  )
                }
              >
                <option value="">Sin clasificar</option>
                {(
                  Object.keys(DISCIPLINE_LABELS) as Discipline[]
                ).map((pf) => (
                  <option key={pf} value={pf}>
                    {DISCIPLINE_LABELS[pf]}
                  </option>
                ))}
              </Select>
            </FieldLabel>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <FieldLabel label="Seniority">
              <Select
                value={seniority}
                onChange={(e) =>
                  setSeniority(e.target.value as ActorSeniority | "")
                }
              >
                <option value="">Sin clasificar</option>
                {(Object.keys(SENIORITY_LABELS) as ActorSeniority[]).map(
                  (s) => (
                    <option key={s} value={s}>
                      {SENIORITY_LABELS[s]}
                    </option>
                  ),
                )}
              </Select>
            </FieldLabel>
            <FieldLabel label="Escasez">
              <Select
                value={scarcityLevel}
                onChange={(e) =>
                  setScarcityLevel(e.target.value as ScarcityLevel | "")
                }
              >
                <option value="">Sin clasificar</option>
                {(Object.keys(SCARCITY_LABELS) as ScarcityLevel[]).map((s) => (
                  <option key={s} value={s}>
                    {SCARCITY_LABELS[s]}
                  </option>
                ))}
              </Select>
            </FieldLabel>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <FieldLabel label="Capacidad nominal %">
              <Input
                type="number"
                min={0}
                max={100}
                value={nominalCapacityPct}
                onChange={(e) => setNominalCapacityPct(e.target.value)}
              />
            </FieldLabel>
            <FieldLabel label="Capacidad para proyectos %">
              <Input
                type="number"
                min={0}
                max={100}
                value={projectCapacityPct}
                onChange={(e) => setProjectCapacityPct(e.target.value)}
              />
              <span className="text-[11px] text-[var(--color-tertiary)]">
                % real disponible para proyectos, descontando BAU
              </span>
            </FieldLabel>
          </div>
          <FieldLabel label="Ubicación">
            <Input
              value={location}
              onChange={(e) => setLocation(e.target.value)}
            />
          </FieldLabel>
          <FieldLabel label="Skills (separados por coma)">
            <Input
              value={skillsTags}
              onChange={(e) => setSkillsTags(e.target.value)}
              placeholder="ej. sap, scrum, azure"
            />
          </FieldLabel>
          <div className="flex flex-wrap items-center gap-4">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={isKeyResource}
                onChange={(e) => setIsKeyResource(e.target.checked)}
              />
              <span>Recurso clave</span>
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={isSharedResource}
                onChange={(e) => setIsSharedResource(e.target.checked)}
              />
              <span>Recurso compartido</span>
            </label>
          </div>
        </div>

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
