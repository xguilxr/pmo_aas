"use client";

// ENH-086 — Panel admin tenant para personas (actors enriquecidos).
// Reemplaza la vista legacy de "Actores" (que asumía Area→Team→Actor)
// por una tabla plana del catálogo tenant con CRUD sobre los campos
// enriquecidos de US-114 (company, job_title, manager_actor_id) +
// area_id (área funcional).

import { useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Icono } from "@/components/ui/icono";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
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
import {
  PERIODO_TARIFA_LABEL,
  type PeriodoTarifa,
} from "@/lib/api/project-directory";
import { useSortableRows } from "@/lib/hooks/use-sortable-rows";
import { SortableTh } from "@/components/ui/sortable-th";
import { confirmarDestructivo } from "@/lib/confirmar";

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
    if (
      !confirmarDestructivo({
        objeto: `a «${actor.name}» del directorio`,
        consecuencia: "Se retira de todos los proyectos donde estuviera asignada.",
        reversibilidad: "definitiva",
      })
    )
      return;
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
        <div className="relative max-w-sm flex-1">
          <Icono
            nombre="search"
            size={14}
            className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--text-faint)]"
          />
          <Input
            placeholder="Buscar persona, email, empresa…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8"
          />
        </div>
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
            <Icono nombre="plus" size={14} /> Nueva persona
          </Button>
        </div>
      </div>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      <div className="overflow-x-auto rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--relieve-isla)]">
        <table className="w-full table-fixed text-sm">
          <colgroup>
            <col />
            <col style={{ width: 170 }} />
            <col style={{ width: 150 }} />
            <col style={{ width: 130 }} />
            <col style={{ width: 120 }} />
            <col style={{ width: 110 }} />
            <col style={{ width: 96 }} />
            <col style={{ width: 44 }} />
            <col style={{ width: 84 }} />
          </colgroup>
          <thead className="border-b border-[var(--border-default)] bg-[var(--color-subtle)] text-left text-[10.5px] font-semibold uppercase tracking-[0.07em] text-[var(--text-tertiary)] shadow-[var(--linea-surco)]">
            <tr>
              <SortableTh<Actor> sortKey="name" getter={(a) => a.name} ctrl={sortCtrl} className="h-8.5">Nombre</SortableTh>
              <SortableTh<Actor> sortKey="email" getter={(a) => a.email ?? ""} ctrl={sortCtrl} className="h-8.5">Email</SortableTh>
              <SortableTh<Actor> sortKey="company" getter={(a) => a.company ?? ""} ctrl={sortCtrl} className="h-8.5">Empresa / Cargo</SortableTh>
              <SortableTh<Actor> sortKey="area" getter={(a) => a.area_id ? areaById[a.area_id]?.name ?? "" : ""} ctrl={sortCtrl} className="h-8.5">Área funcional</SortableTh>
              <SortableTh<Actor> sortKey="resource_type" getter={(a) => resourceTypeLabel(a.resource_type)} ctrl={sortCtrl} className="h-8.5">Tipo</SortableTh>
              <SortableTh<Actor> sortKey="discipline" getter={(a) => disciplineLabel(a.discipline)} ctrl={sortCtrl} className="h-8.5">Función</SortableTh>
              <SortableTh<Actor> sortKey="project_capacity_pct" getter={(a) => a.project_capacity_pct ?? 100} ctrl={sortCtrl} align="right" className="h-8.5 pr-3.5">Cap. %</SortableTh>
              <SortableTh<Actor> sortKey="is_key_resource" getter={(a) => a.is_key_resource ?? false} ctrl={sortCtrl} align="center" className="h-8.5">Clave</SortableTh>
              <th className="h-8.5 px-3"></th>
            </tr>
          </thead>
          <tbody>
            {sortedRows.length === 0 ? (
              <tr>
                <td
                  colSpan={9}
                  className="p-8 text-center text-[12.5px] text-[var(--text-tertiary)]"
                >
                  {actors.length === 0
                    ? "Sin personas en el catálogo tenant."
                    : "Ningún match para el filtro."}
                </td>
              </tr>
            ) : (
              sortedRows.map((a) => (
                <tr
                  key={a.id}
                  className="h-10.5 border-b border-[var(--border-subtle)] shadow-[var(--linea-surco)] even:bg-[var(--color-subtle)] hover:bg-[var(--color-subtle)]"
                >
                  <td className="overflow-hidden px-3 text-ellipsis whitespace-nowrap">
                    <span className="font-medium text-[var(--text-primary)]">
                      {a.name}
                    </span>
                    {!a.is_active ? (
                      <Badge variant="danger" className="ml-2">
                        Inactivo
                      </Badge>
                    ) : null}
                  </td>
                  <td className="overflow-hidden px-3 text-ellipsis whitespace-nowrap text-[12.5px] text-[var(--text-secondary)]">
                    {a.email ?? "—"}
                  </td>
                  <td className="overflow-hidden px-3 text-ellipsis whitespace-nowrap text-[12.5px]">
                    <div className="text-[var(--text-secondary)]">{a.company ?? "—"}</div>
                    <div className="text-[var(--text-tertiary)]">
                      {a.job_title ?? ""}
                    </div>
                  </td>
                  <td className="overflow-hidden px-3 text-ellipsis whitespace-nowrap text-[12.5px] text-[var(--text-secondary)]">
                    {a.area_id ? areaById[a.area_id]?.name ?? "—" : "—"}
                  </td>
                  <td className="overflow-hidden px-3 text-ellipsis whitespace-nowrap text-[12.5px] text-[var(--text-secondary)]">
                    {resourceTypeLabel(a.resource_type)}
                  </td>
                  <td className="overflow-hidden px-3 text-ellipsis whitespace-nowrap text-[12.5px] text-[var(--text-secondary)]">
                    {disciplineLabel(a.discipline)}
                  </td>
                  <td className="pr-3.5 text-right font-mono text-[12.5px] text-[var(--text-secondary)]">
                    {a.project_capacity_pct ?? 100}%
                  </td>
                  <td className="text-center">
                    {a.is_key_resource ? (
                      <span
                        className="inline-flex justify-center"
                        role="img"
                        aria-label="Recurso clave"
                        title="Recurso clave"
                      >
                        <Icono nombre="lock" size={13} className="text-[var(--color-warning-fg)]" />
                      </span>
                    ) : null}
                  </td>
                  <td className="px-3 text-right">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setEditing(a)}
                      title="Editar"
                    >
                      <Icono nombre="pen" size={14} />
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleDelete(a)}
                      title="Eliminar"
                    >
                      <Icono nombre="bin" size={14} />
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
  // US-215 — tarifa y su unidad de tiempo. `fte_cost_rate` existía en la API
  // desde US-182 y no se capturaba desde ninguna pantalla: un campo que nadie
  // puede llenar es un campo que no existe (CLAUDE.md §13).
  const [costRate, setCostRate] = useState(
    actor?.fte_cost_rate !== null && actor?.fte_cost_rate !== undefined
      ? String(actor.fte_cost_rate)
      : "",
  );
  const [costRatePeriod, setCostRatePeriod] = useState<string>(
    actor?.cost_rate_period ?? "",
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
        // US-215: la tarifa vacía es `null` y no 0. Una tarifa de cero sería un
        // recurso gratuito, que es un dato distinto de «no se capturó».
        fte_cost_rate: costRate.trim() === "" ? null : Number(costRate),
        cost_rate_period: costRatePeriod || null,
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
        <Switch checked={isActive} onChange={setIsActive} label="Activa" />

        {/* US-182: pool de recursos con capacidad. */}
        <div className="space-y-3 border-t border-[var(--border-default)] pt-3">
          <p className="text-[10.5px] font-semibold uppercase tracking-[0.07em] text-[var(--text-tertiary)]">
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
          {/* US-215 — la tarifa y su unidad van juntas y en ese orden, porque
              una sin la otra no sirve: el importe sin unidad de tiempo no se
              puede multiplicar por nada, y la unidad sin importe no dice nada. */}
          <div className="grid grid-cols-2 gap-2">
            <FieldLabel label="Tarifa">
              <Input
                type="number"
                min={0}
                step="0.01"
                value={costRate}
                onChange={(e) => setCostRate(e.target.value)}
                placeholder="ej. 2100"
              />
              <span className="text-[11px] text-[var(--color-tertiary)]">
                En la moneda del proyecto donde se asigne
              </span>
            </FieldLabel>
            <FieldLabel label="Unidad de la tarifa">
              <Select
                value={costRatePeriod}
                onChange={(e) => setCostRatePeriod(e.target.value)}
              >
                <option value="">Sin declarar</option>
                {(Object.keys(PERIODO_TARIFA_LABEL) as PeriodoTarifa[]).map(
                  (per) => (
                    <option key={per} value={per}>
                      {PERIODO_TARIFA_LABEL[per]}
                    </option>
                  ),
                )}
              </Select>
              <span className="text-[11px] text-[var(--color-tertiary)]">
                Sin declararla no hay costo: 2.100 por hora y 2.100 por mes son
                dos tarifas distintas
              </span>
            </FieldLabel>
          </div>
          <div className="flex flex-wrap items-center gap-4">
            <label className="flex items-center gap-2 text-sm text-[var(--text-secondary)]">
              <Checkbox
                checked={isKeyResource}
                onChange={(e) => setIsKeyResource(e.target.checked)}
              />
              <span>Recurso clave</span>
            </label>
            <label className="flex items-center gap-2 text-sm text-[var(--text-secondary)]">
              <Checkbox
                checked={isSharedResource}
                onChange={(e) => setIsSharedResource(e.target.checked)}
              />
              <span>Recurso compartido</span>
            </label>
          </div>
        </div>

        {err ? <Banner variant="danger">{err}</Banner> : null}
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
