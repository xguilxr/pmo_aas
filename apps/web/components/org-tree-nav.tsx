"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import {
  Building2,
  ChevronRight,
  FolderKanban,
  Network,
} from "lucide-react";

import {
  type Organization,
  type Program,
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
  programs: Record<string, LoadedRecord<Program>>; // by orgId
  projects: Record<string, LoadedRecord<Project>>; // by programId
};

function emptyMaps(): Maps {
  return { programs: {}, projects: {} };
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

function rowClass(active: boolean, top: boolean): string {
  return cn(
    "flex items-center gap-2 rounded-[var(--radius-md)] pr-1.5 transition-colors",
    top ? "h-9 text-[13px]" : "h-8 text-[12.5px]",
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
  top = false,
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
  top?: boolean;
}) {
  const indent = { paddingLeft: `${(top ? 0.625 : 0.5) + depth * 0.75}rem` };
  return (
    <div className={rowClass(active, top)} style={indent}>
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
            className={cn("h-3.5 w-3.5 transition-transform", isOpen && "rotate-90")}
            aria-hidden
          />
        </button>
      ) : null}
    </div>
  );
}

function PlaceholderRow({ depth, text }: { depth: number; text: string }) {
  const indent = { paddingLeft: `${0.5 + depth * 0.75}rem` };
  return (
    <div
      className="text-[11.5px] italic text-[var(--chrome-text-muted)]/70 py-1"
      style={indent}
    >
      {text}
    </div>
  );
}

/**
 * Drill-down real del tenant en el sidebar principal (US-NEW-032):
 * Organizaciones → Programas → Proyectos. La jerarquía administrativa
 * (BUs / Departamentos) vive sólo bajo `/admin/organizations`, no aquí.
 */
export function OrgTreeNav({ onNavigate }: { onNavigate: () => void }) {
  const pathname = usePathname();
  const [orgs, setOrgs] = useState<LoadedRecord<Organization>>({
    state: "idle",
    items: [],
  });
  const [maps, setMaps] = useState<Maps>(() => emptyMaps());
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set());

  useEffect(() => {
    setExpanded(loadExpanded());
  }, []);

  useEffect(() => {
    saveExpanded(expanded);
  }, [expanded]);

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
  const sectionActive =
    pathname.startsWith("/admin/organizations") ||
    pathname.startsWith("/admin/programs") ||
    pathname.startsWith("/admin/projects");

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

  const ensureProgramsByOrg = useCallback(async (orgId: string) => {
    setMaps((m) => {
      const cur = m.programs[orgId];
      if (cur && cur.state !== "idle") return m;
      return { ...m, programs: { ...m.programs, [orgId]: { state: "loading", items: [] } } };
    });
    try {
      const items = await listPrograms({ organization_id: orgId, is_active: true });
      setMaps((m) => ({
        ...m,
        programs: { ...m.programs, [orgId]: { state: "loaded", items } },
      }));
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Error";
      setMaps((m) => ({
        ...m,
        programs: { ...m.programs, [orgId]: { state: "error", items: [], error: msg } },
      }));
    }
  }, []);

  const ensureProjects = useCallback(async (programId: string) => {
    setMaps((m) => {
      const cur = m.projects[programId];
      if (cur && cur.state !== "idle") return m;
      return {
        ...m,
        projects: { ...m.projects, [programId]: { state: "loading", items: [] } },
      };
    });
    try {
      const items = await listProjects({ program_id: programId, limit: 100 });
      setMaps((m) => ({
        ...m,
        projects: { ...m.projects, [programId]: { state: "loaded", items } },
      }));
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Error";
      setMaps((m) => ({
        ...m,
        projects: { ...m.projects, [programId]: { state: "error", items: [], error: msg } },
      }));
    }
  }, []);

  useEffect(() => {
    if (orgs.state !== "loaded") return;
    for (const org of orgs.items) {
      const orgKey = `org:${org.id}`;
      if (expanded.has(orgKey) && !maps.programs[org.id]) {
        void ensureProgramsByOrg(org.id);
      }
      const programs = maps.programs[org.id]?.items ?? [];
      for (const prog of programs) {
        if (expanded.has(`prog:${prog.id}`) && !maps.projects[prog.id]) {
          void ensureProjects(prog.id);
        }
      }
    }
  }, [expanded, orgs.state, orgs.items, maps, ensureProgramsByOrg, ensureProjects]);

  const isProjectActive = useMemo(
    () => (id: string) => pathname.startsWith(`/admin/projects/${id}`),
    [pathname],
  );

  return (
    <div>
      <NodeRow
        depth={0}
        top
        icon={<Building2 className="h-4 w-4" aria-hidden />}
        label="Organizaciones"
        active={sectionActive && !sectionOpen}
        hasChildren
        isOpen={sectionOpen}
        onToggle={() => toggle("__orgs__")}
        href="/admin/organizations"
        onNavigate={onNavigate}
      />
      {sectionOpen ? (
        <div className="mt-0.5">
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
            const progRec = maps.programs[org.id];
            return (
              <div key={org.id}>
                <NodeRow
                  depth={1}
                  icon={<Building2 className="h-3.5 w-3.5" aria-hidden />}
                  label={org.name}
                  href={`/admin/organizations/${org.id}/panel`}
                  active={pathname.startsWith(`/admin/organizations/${org.id}/panel`)}
                  hasChildren
                  isOpen={orgOpen}
                  onToggle={() => toggle(orgKey)}
                  onNavigate={onNavigate}
                />
                {orgOpen ? (
                  <ProgramsList
                    rec={progRec}
                    depth={2}
                    expanded={expanded}
                    toggle={toggle}
                    projectsMap={maps.projects}
                    isProjectActive={isProjectActive}
                    onNavigate={onNavigate}
                  />
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
                {projects?.state === "loaded" && projects.items.length === 0 ? (
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
