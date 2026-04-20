"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import {
  Building2,
  ChevronRight,
  FolderKanban,
  Network,
  Users,
  Workflow,
} from "lucide-react";

import {
  type BusinessUnit,
  type Department,
  type Organization,
  type Program,
  listBusinessUnits,
  listDepartments,
  listOrganizations,
  listPrograms,
} from "@/lib/api/organizations";
import { type Project, listProjects } from "@/lib/api/projects";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/cn";

const STORAGE_KEY = "pmoaas:sidebar:org-tree:expanded";

type LoadState = "idle" | "loading" | "loaded" | "error";

type LoadedRecord<T> = { state: LoadState; items: T[]; error?: string };

type Maps = {
  bus: Record<string, LoadedRecord<BusinessUnit>>; // by orgId
  depts: Record<string, LoadedRecord<Department>>; // by buId
  programs: Record<string, LoadedRecord<Program>>; // by deptId or orgId
  projects: Record<string, LoadedRecord<Project>>; // by programId
};

function emptyMaps(): Maps {
  return { bus: {}, depts: {}, programs: {}, projects: {} };
}

function loadExpanded(): Set<string> {
  if (typeof window === "undefined") return new Set();
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return new Set();
    const arr = JSON.parse(raw);
    return new Set(Array.isArray(arr) ? arr.map(String) : []);
  } catch {
    return new Set();
  }
}

function saveExpanded(s: Set<string>): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(Array.from(s)));
  } catch {
    /* ignore */
  }
}

function rowClass(active: boolean): string {
  return cn(
    "flex h-8 items-center gap-2 rounded-[var(--radius-md)] pr-1.5 text-[12.5px] transition-colors",
    active
      ? "bg-[var(--chrome-active)] font-semibold text-[var(--chrome-text)]"
      : "text-[var(--chrome-text-muted)] hover:bg-[var(--chrome-hover)] hover:text-[var(--chrome-text)]",
  );
}

function NodeRow({
  href,
  onNavigate,
  icon,
  label,
  active,
  hasChildren,
  isOpen,
  onToggle,
  depth,
}: {
  href?: string;
  onNavigate: () => void;
  icon: ReactNode;
  label: string;
  active: boolean;
  hasChildren: boolean;
  isOpen: boolean;
  onToggle: () => void;
  depth: number;
}) {
  const indent = { paddingLeft: `${0.5 + depth * 0.7}rem` };
  return (
    <div className={rowClass(active)} style={indent}>
      {href ? (
        <Link
          href={href}
          onClick={onNavigate}
          className="flex min-w-0 flex-1 items-center gap-2"
        >
          {icon}
          <span className="truncate">{label}</span>
        </Link>
      ) : (
        <button
          type="button"
          onClick={onToggle}
          className="flex min-w-0 flex-1 items-center gap-2 text-left"
        >
          {icon}
          <span className="truncate">{label}</span>
        </button>
      )}
      {hasChildren ? (
        <button
          type="button"
          onClick={onToggle}
          aria-expanded={isOpen}
          aria-label={isOpen ? `Colapsar ${label}` : `Expandir ${label}`}
          className="inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-[var(--radius-sm)] text-[var(--chrome-text-muted)] hover:bg-[var(--chrome-hover)] hover:text-[var(--chrome-text)]"
        >
          <ChevronRight
            className={cn("h-3 w-3 transition-transform", isOpen && "rotate-90")}
            aria-hidden
          />
        </button>
      ) : null}
    </div>
  );
}

function PlaceholderRow({ depth, text }: { depth: number; text: string }) {
  const indent = { paddingLeft: `${0.5 + depth * 0.7}rem` };
  return (
    <div
      className="text-[11.5px] italic text-[var(--chrome-text-muted)]/70 py-1"
      style={indent}
    >
      {text}
    </div>
  );
}

export function OrgTreeNav({ onNavigate }: { onNavigate: () => void }) {
  const pathname = usePathname();
  const [orgs, setOrgs] = useState<LoadedRecord<Organization>>({
    state: "idle",
    items: [],
  });
  const [maps, setMaps] = useState<Maps>(() => emptyMaps());
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set());

  // Hidratar expandidos desde localStorage en cliente
  useEffect(() => {
    setExpanded(loadExpanded());
  }, []);

  useEffect(() => {
    saveExpanded(expanded);
  }, [expanded]);

  // Carga inicial de orgs cuando se expande la sección
  const loadOrgs = useCallback(async () => {
    setOrgs((s) => (s.state === "loading" ? s : { ...s, state: "loading" }));
    try {
      const items = await listOrganizations({ is_active: true });
      setOrgs({ state: "loaded", items });
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Error";
      setOrgs({ state: "error", items: [], error: msg });
    }
  }, []);

  const sectionOpen = expanded.has("__orgs__");

  useEffect(() => {
    if (sectionOpen && orgs.state === "idle") {
      void loadOrgs();
    }
  }, [sectionOpen, orgs.state, loadOrgs]);

  const toggle = useCallback((id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const ensureBus = useCallback(async (orgId: string) => {
    setMaps((m) => {
      const cur = m.bus[orgId];
      if (cur && cur.state !== "idle") return m;
      return { ...m, bus: { ...m.bus, [orgId]: { state: "loading", items: [] } } };
    });
    try {
      const items = await listBusinessUnits(orgId, { is_active: true });
      setMaps((m) => ({
        ...m,
        bus: { ...m.bus, [orgId]: { state: "loaded", items } },
      }));
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Error";
      setMaps((m) => ({
        ...m,
        bus: { ...m.bus, [orgId]: { state: "error", items: [], error: msg } },
      }));
    }
  }, []);

  const ensureDepts = useCallback(async (buId: string) => {
    setMaps((m) => {
      const cur = m.depts[buId];
      if (cur && cur.state !== "idle") return m;
      return {
        ...m,
        depts: { ...m.depts, [buId]: { state: "loading", items: [] } },
      };
    });
    try {
      const items = await listDepartments(buId, { is_active: true });
      setMaps((m) => ({
        ...m,
        depts: { ...m.depts, [buId]: { state: "loaded", items } },
      }));
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Error";
      setMaps((m) => ({
        ...m,
        depts: { ...m.depts, [buId]: { state: "error", items: [], error: msg } },
      }));
    }
  }, []);

  const ensureProgramsByOrg = useCallback(async (orgId: string) => {
    const key = `org:${orgId}`;
    setMaps((m) => {
      const cur = m.programs[key];
      if (cur && cur.state !== "idle") return m;
      return {
        ...m,
        programs: { ...m.programs, [key]: { state: "loading", items: [] } },
      };
    });
    try {
      const items = await listPrograms({ organization_id: orgId, is_active: true });
      setMaps((m) => ({
        ...m,
        programs: { ...m.programs, [key]: { state: "loaded", items } },
      }));
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Error";
      setMaps((m) => ({
        ...m,
        programs: {
          ...m.programs,
          [key]: { state: "error", items: [], error: msg },
        },
      }));
    }
  }, []);

  const ensureProjects = useCallback(async (programId: string) => {
    setMaps((m) => {
      const cur = m.projects[programId];
      if (cur && cur.state !== "idle") return m;
      return {
        ...m,
        projects: {
          ...m.projects,
          [programId]: { state: "loading", items: [] },
        },
      };
    });
    try {
      const items = await listProjects({ program_id: programId, limit: 100 });
      setMaps((m) => ({
        ...m,
        projects: {
          ...m.projects,
          [programId]: { state: "loaded", items },
        },
      }));
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Error";
      setMaps((m) => ({
        ...m,
        projects: {
          ...m.projects,
          [programId]: { state: "error", items: [], error: msg },
        },
      }));
    }
  }, []);

  // Disparadores lazy según expanded ids
  useEffect(() => {
    if (orgs.state !== "loaded") return;
    for (const org of orgs.items) {
      const orgKey = `org:${org.id}`;
      if (expanded.has(orgKey)) {
        if (!maps.bus[org.id]) void ensureBus(org.id);
        const progKey = `org-progs:${org.id}`;
        if (expanded.has(progKey) && !maps.programs[`org:${org.id}`]) {
          void ensureProgramsByOrg(org.id);
        }
        const bus = maps.bus[org.id]?.items ?? [];
        for (const bu of bus) {
          if (expanded.has(`bu:${bu.id}`) && !maps.depts[bu.id]) {
            void ensureDepts(bu.id);
          }
        }
        const programs = maps.programs[`org:${org.id}`]?.items ?? [];
        for (const prog of programs) {
          if (expanded.has(`prog:${prog.id}`) && !maps.projects[prog.id]) {
            void ensureProjects(prog.id);
          }
        }
      }
    }
  }, [
    expanded,
    orgs.state,
    orgs.items,
    maps,
    ensureBus,
    ensureDepts,
    ensureProgramsByOrg,
    ensureProjects,
  ]);

  const isProjectActive = useMemo(
    () => (id: string) => pathname.startsWith(`/admin/projects/${id}`),
    [pathname],
  );

  return (
    <div className="mt-3">
      <NodeRow
        depth={0}
        icon={<Building2 className="h-4 w-4" aria-hidden />}
        label="Organizaciones"
        active={false}
        hasChildren
        isOpen={sectionOpen}
        onToggle={() => toggle("__orgs__")}
        onNavigate={onNavigate}
      />
      {sectionOpen ? (
        <div>
          {orgs.state === "loading" ? (
            <PlaceholderRow depth={1} text="Cargando…" />
          ) : null}
          {orgs.state === "error" ? (
            <PlaceholderRow depth={1} text={`Error: ${orgs.error ?? ""}`} />
          ) : null}
          {orgs.state === "loaded" && orgs.items.length === 0 ? (
            <PlaceholderRow depth={1} text="Sin organizaciones" />
          ) : null}
          {orgs.items.map((org) => {
            const orgKey = `org:${org.id}`;
            const orgOpen = expanded.has(orgKey);
            const buRec = maps.bus[org.id];
            const progRec = maps.programs[`org:${org.id}`];
            const orgProgKey = `org-progs:${org.id}`;
            const orgProgsOpen = expanded.has(orgProgKey);

            return (
              <div key={org.id}>
                <NodeRow
                  depth={1}
                  icon={<Building2 className="h-3.5 w-3.5" aria-hidden />}
                  label={org.name}
                  href={`/admin/organizations/${org.id}`}
                  active={pathname === `/admin/organizations/${org.id}`}
                  hasChildren
                  isOpen={orgOpen}
                  onToggle={() => toggle(orgKey)}
                  onNavigate={onNavigate}
                />
                {orgOpen ? (
                  <div>
                    {/* Programas directos al org */}
                    <NodeRow
                      depth={2}
                      icon={<Network className="h-3.5 w-3.5" aria-hidden />}
                      label="Programas"
                      active={false}
                      hasChildren
                      isOpen={orgProgsOpen}
                      onToggle={() => toggle(orgProgKey)}
                      onNavigate={onNavigate}
                    />
                    {orgProgsOpen ? (
                      <ProgramsList
                        rec={progRec}
                        depth={3}
                        expanded={expanded}
                        toggle={toggle}
                        projectsMap={maps.projects}
                        isProjectActive={isProjectActive}
                        onNavigate={onNavigate}
                      />
                    ) : null}

                    {/* Unidades de negocio */}
                    {buRec?.state === "loading" ? (
                      <PlaceholderRow depth={2} text="Cargando BUs…" />
                    ) : null}
                    {buRec?.state === "error" ? (
                      <PlaceholderRow
                        depth={2}
                        text={`Error: ${buRec.error ?? ""}`}
                      />
                    ) : null}
                    {(buRec?.items ?? []).map((bu) => {
                      const buKey = `bu:${bu.id}`;
                      const buOpen = expanded.has(buKey);
                      const deptRec = maps.depts[bu.id];
                      return (
                        <div key={bu.id}>
                          <NodeRow
                            depth={2}
                            icon={<Workflow className="h-3.5 w-3.5" aria-hidden />}
                            label={bu.name}
                            active={false}
                            hasChildren
                            isOpen={buOpen}
                            onToggle={() => toggle(buKey)}
                            onNavigate={onNavigate}
                          />
                          {buOpen ? (
                            <div>
                              {deptRec?.state === "loading" ? (
                                <PlaceholderRow depth={3} text="Cargando deptos…" />
                              ) : null}
                              {deptRec?.state === "error" ? (
                                <PlaceholderRow
                                  depth={3}
                                  text={`Error: ${deptRec.error ?? ""}`}
                                />
                              ) : null}
                              {(deptRec?.items ?? []).map((dept) => (
                                <NodeRow
                                  key={dept.id}
                                  depth={3}
                                  icon={<Users className="h-3.5 w-3.5" aria-hidden />}
                                  label={dept.name}
                                  active={false}
                                  hasChildren={false}
                                  isOpen={false}
                                  onToggle={() => undefined}
                                  onNavigate={onNavigate}
                                />
                              ))}
                              {deptRec?.state === "loaded" &&
                              deptRec.items.length === 0 ? (
                                <PlaceholderRow depth={3} text="Sin departamentos" />
                              ) : null}
                            </div>
                          ) : null}
                        </div>
                      );
                    })}
                    {buRec?.state === "loaded" && buRec.items.length === 0 ? (
                      <PlaceholderRow depth={2} text="Sin unidades de negocio" />
                    ) : null}
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}

function ProgramsList({
  rec,
  depth,
  expanded,
  toggle,
  projectsMap,
  isProjectActive,
  onNavigate,
}: {
  rec: LoadedRecord<Program> | undefined;
  depth: number;
  expanded: Set<string>;
  toggle: (id: string) => void;
  projectsMap: Record<string, LoadedRecord<Project>>;
  isProjectActive: (id: string) => boolean;
  onNavigate: () => void;
}) {
  if (!rec || rec.state === "loading") {
    return <PlaceholderRow depth={depth} text="Cargando programas…" />;
  }
  if (rec.state === "error") {
    return <PlaceholderRow depth={depth} text={`Error: ${rec.error ?? ""}`} />;
  }
  if (rec.items.length === 0) {
    return <PlaceholderRow depth={depth} text="Sin programas" />;
  }
  return (
    <>
      {rec.items.map((prog) => {
        const progKey = `prog:${prog.id}`;
        const open = expanded.has(progKey);
        const projects = projectsMap[prog.id];
        return (
          <div key={prog.id}>
            <NodeRow
              depth={depth}
              icon={<Network className="h-3.5 w-3.5" aria-hidden />}
              label={prog.name}
              href={`/admin/projects?program_id=${prog.id}`}
              active={false}
              hasChildren
              isOpen={open}
              onToggle={() => toggle(progKey)}
              onNavigate={onNavigate}
            />
            {open ? (
              <>
                {projects?.state === "loading" ? (
                  <PlaceholderRow depth={depth + 1} text="Cargando proyectos…" />
                ) : null}
                {projects?.state === "error" ? (
                  <PlaceholderRow
                    depth={depth + 1}
                    text={`Error: ${projects.error ?? ""}`}
                  />
                ) : null}
                {(projects?.items ?? []).map((p) => (
                  <NodeRow
                    key={p.id}
                    depth={depth + 1}
                    icon={<FolderKanban className="h-3.5 w-3.5" aria-hidden />}
                    label={p.name}
                    href={`/admin/projects/${p.id}`}
                    active={isProjectActive(p.id)}
                    hasChildren={false}
                    isOpen={false}
                    onToggle={() => undefined}
                    onNavigate={onNavigate}
                  />
                ))}
                {projects?.state === "loaded" &&
                projects.items.length === 0 ? (
                  <PlaceholderRow depth={depth + 1} text="Sin proyectos" />
                ) : null}
              </>
            ) : null}
          </div>
        );
      })}
    </>
  );
}
