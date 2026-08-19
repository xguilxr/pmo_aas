"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import {
  Briefcase,
  Building2,
  ChevronRight,
  Folder,
  FolderKanban,
  Layers,
} from "lucide-react";

import {
  type Organization,
  type Portfolio,
  type Program,
  listOrganizations,
  listPortfolios,
  listPrograms,
} from "@/lib/api/organizations";
import { type Project, listProjects } from "@/lib/api/projects";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/cn";

const STORAGE_KEY = "pmoaas:sidebar:org-tree:expanded";

type LoadState = "idle" | "loading" | "loaded" | "error";
type LoadedRecord<T> = { state: LoadState; items: T[]; error?: string };

// US-200 — el árbol gana un nivel: Organización → Portafolio → Programa →
// Proyecto. Los proyectos aparecen en tres sitios distintos porque hay tres
// formas legítimas de colgar: de un programa, del portafolio sin programa, y de
// la organización sin clasificar (un proyecto recién importado, por ejemplo).
type Maps = {
  portfolios: Record<string, LoadedRecord<Portfolio>>; // por orgId
  programs: Record<string, LoadedRecord<Program>>; // por portfolioId
  projects: Record<string, LoadedRecord<Project>>; // por programId
  noProgramProjects: Record<string, LoadedRecord<Project>>; // por portfolioId
  unclassifiedProjects: Record<string, LoadedRecord<Project>>; // por orgId
};

function emptyMaps(): Maps {
  return {
    portfolios: {},
    programs: {},
    projects: {},
    noProgramProjects: {},
    unclassifiedProjects: {},
  };
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
      ? "bg-[var(--chrome-active)] font-semibold text-[var(--chrome-text-strong)]"
      : "text-[var(--chrome-text-muted)] hover:bg-[var(--chrome-hover)] hover:text-[var(--chrome-text-strong)]",
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
 * Drill-down del inquilino en el sidebar principal (US-032, ampliado en US-200):
 * Organizaciones → Portafolios → Programas → Proyectos.
 *
 * Cada nivel se carga **al abrirlo**, no antes: un inquilino con diez
 * organizaciones y cinco portafolios cada una pediría cincuenta listas para
 * pintar un árbol que empieza colapsado.
 *
 * El CRUD de la jerarquía vive en `/admin/organizations`; aquí solo se navega.
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
  // US-075 (DEC-022): el portafolio informativo vive bajo /pmo. El
  // CRUD de orgs (BUs/Deptos) sigue en /admin/organizations y NO
  // marca esta sección activa — ya está en el ADMIN_NAV.
  const sectionActive =
    pathname === "/pmo" ||
    pathname.startsWith("/pmo/organizations") ||
    pathname.startsWith("/pmo/programs") ||
    pathname.startsWith("/pmo/projects");

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

  const ensurePortfolios = useCallback(async (orgId: string) => {
    setMaps((m) => {
      const cur = m.portfolios[orgId];
      if (cur && cur.state !== "idle") return m;
      return {
        ...m,
        portfolios: { ...m.portfolios, [orgId]: { state: "loading", items: [] } },
      };
    });
    try {
      const items = await listPortfolios(orgId, { is_active: true });
      setMaps((m) => ({
        ...m,
        portfolios: { ...m.portfolios, [orgId]: { state: "loaded", items } },
      }));
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Error";
      setMaps((m) => ({
        ...m,
        portfolios: { ...m.portfolios, [orgId]: { state: "error", items: [], error: msg } },
      }));
    }
  }, []);

  const ensurePrograms = useCallback(
    async (orgId: string, portfolioId: string) => {
      setMaps((m) => {
        const cur = m.programs[portfolioId];
        if (cur && cur.state !== "idle") return m;
        return {
          ...m,
          programs: { ...m.programs, [portfolioId]: { state: "loading", items: [] } },
        };
      });
      try {
        const items = await listPrograms({
          organization_id: orgId,
          portfolio_id: portfolioId,
          is_active: true,
        });
        setMaps((m) => ({
          ...m,
          programs: { ...m.programs, [portfolioId]: { state: "loaded", items } },
        }));
      } catch (e) {
        const msg = e instanceof ApiError ? e.message : "Error";
        setMaps((m) => ({
          ...m,
          programs: {
            ...m.programs,
            [portfolioId]: { state: "error", items: [], error: msg },
          },
        }));
      }
    },
    [],
  );

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

  /** Los proyectos que cuelgan del portafolio sin programa que los coordine. */
  const ensureNoProgProjects = useCallback(async (portfolioId: string) => {
    setMaps((m) => {
      const cur = m.noProgramProjects[portfolioId];
      if (cur && cur.state !== "idle") return m;
      return {
        ...m,
        noProgramProjects: {
          ...m.noProgramProjects,
          [portfolioId]: { state: "loading", items: [] },
        },
      };
    });
    try {
      const items = await listProjects({
        portfolio_id: portfolioId,
        no_program: true,
        limit: 100,
      });
      setMaps((m) => ({
        ...m,
        noProgramProjects: {
          ...m.noProgramProjects,
          [portfolioId]: { state: "loaded", items },
        },
      }));
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Error";
      setMaps((m) => ({
        ...m,
        noProgramProjects: {
          ...m.noProgramProjects,
          [portfolioId]: { state: "error", items: [], error: msg },
        },
      }));
    }
  }, []);

  /** Los que no tienen portafolio todavía — importación masiva, sobre todo.
   *  Si no aparecieran en el árbol serían invisibles hasta clasificarlos, que
   *  es exactamente cuando alguien necesita encontrarlos. */
  const ensureUnclassified = useCallback(async (orgId: string) => {
    setMaps((m) => {
      const cur = m.unclassifiedProjects[orgId];
      if (cur && cur.state !== "idle") return m;
      return {
        ...m,
        unclassifiedProjects: {
          ...m.unclassifiedProjects,
          [orgId]: { state: "loading", items: [] },
        },
      };
    });
    try {
      const items = await listProjects({
        organization_id: orgId,
        no_portfolio: true,
        limit: 100,
      });
      setMaps((m) => ({
        ...m,
        unclassifiedProjects: {
          ...m.unclassifiedProjects,
          [orgId]: { state: "loaded", items },
        },
      }));
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Error";
      setMaps((m) => ({
        ...m,
        unclassifiedProjects: {
          ...m.unclassifiedProjects,
          [orgId]: { state: "error", items: [], error: msg },
        },
      }));
    }
  }, []);

  useEffect(() => {
    if (orgs.state !== "loaded") return;
    for (const org of orgs.items) {
      if (expanded.has(`org:${org.id}`)) {
        if (!maps.portfolios[org.id]) void ensurePortfolios(org.id);
        if (!maps.unclassifiedProjects[org.id]) void ensureUnclassified(org.id);
      }
      for (const pf of maps.portfolios[org.id]?.items ?? []) {
        if (expanded.has(`pf:${pf.id}`)) {
          if (!maps.programs[pf.id]) void ensurePrograms(org.id, pf.id);
          if (!maps.noProgramProjects[pf.id]) void ensureNoProgProjects(pf.id);
        }
        for (const prog of maps.programs[pf.id]?.items ?? []) {
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
    ensurePortfolios,
    ensurePrograms,
    ensureProjects,
    ensureNoProgProjects,
    ensureUnclassified,
  ]);

  const isProjectActive = useMemo(
    () => (id: string) => pathname.startsWith(`/pmo/projects/${id}`),
    [pathname],
  );

  // ENH-190: label configurable por tenant para "Organización(es)".

  return (
    <div>
      <NodeRow
        depth={0}
        top
        icon={<Building2 className="h-4 w-4" aria-hidden />}
        label="PMO"
        active={sectionActive && !sectionOpen}
        hasChildren
        isOpen={sectionOpen}
        onToggle={() => toggle("__orgs__")}
        href="/pmo"
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
            return (
              <div key={org.id}>
                <NodeRow
                  depth={1}
                  icon={<Building2 className="h-3.5 w-3.5" aria-hidden />}
                  label={org.name}
                  href={`/pmo/organizations/${org.id}`}
                  active={
                    pathname === `/pmo/organizations/${org.id}` ||
                    pathname.startsWith(`/pmo/organizations/${org.id}/`)
                  }
                  hasChildren
                  isOpen={orgOpen}
                  onToggle={() => toggle(orgKey)}
                  onNavigate={onNavigate}
                />
                {orgOpen ? (
                  <PortfoliosList
                    orgId={org.id}
                    rec={maps.portfolios[org.id]}
                    unclassifiedRec={maps.unclassifiedProjects[org.id]}
                    maps={maps}
                    depth={2}
                    expanded={expanded}
                    toggle={toggle}
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

function ProjectRows({
  rec,
  depth,
  isProjectActive,
  onNavigate,
  vacio,
}: {
  rec: LoadedRecord<Project> | undefined;
  depth: number;
  isProjectActive: (id: string) => boolean;
  onNavigate: () => void;
  vacio: string;
}) {
  if (!rec || rec.state === "loading") {
    return <PlaceholderRow depth={depth} text="Cargando proyectos…" />;
  }
  if (rec.state === "error") {
    return <PlaceholderRow depth={depth} text={`Error: ${rec.error ?? ""}`} />;
  }
  if (rec.items.length === 0) {
    return <PlaceholderRow depth={depth} text={vacio} />;
  }
  return (
    <>
      {rec.items.map((p) => (
        <NodeRow
          key={p.id}
          depth={depth}
          icon={<FolderKanban className="h-3.5 w-3.5" aria-hidden />}
          label={p.name}
          href={`/pmo/projects/${p.id}`}
          active={isProjectActive(p.id)}
          hasChildren={false}
          isOpen={false}
          onToggle={() => undefined}
          onNavigate={onNavigate}
        />
      ))}
    </>
  );
}

/** US-200 — el nivel nuevo: los portafolios de una organización, y al final el
 *  cajón de los proyectos que todavía no están en ninguno. */
function PortfoliosList({
  orgId,
  rec,
  unclassifiedRec,
  maps,
  depth,
  expanded,
  toggle,
  isProjectActive,
  onNavigate,
}: {
  orgId: string;
  rec: LoadedRecord<Portfolio> | undefined;
  unclassifiedRec: LoadedRecord<Project> | undefined;
  maps: Maps;
  depth: number;
  expanded: Set<string>;
  toggle: (id: string) => void;
  isProjectActive: (id: string) => boolean;
  onNavigate: () => void;
}) {
  const haySinClasificar =
    unclassifiedRec?.state === "loaded" && unclassifiedRec.items.length > 0;
  // La clave lleva el id de la organización y no se deduce del primer
  // portafolio: una organización **sin** portafolios pero con proyectos sin
  // clasificar no tiene primer portafolio, y la clave se compartiría con las
  // demás — abrir una abriría todas.
  const sinClasificarKey = `unclassified:${orgId}`;
  const sinClasificarOpen = expanded.has(sinClasificarKey);

  if (!rec || rec.state === "loading") {
    return <PlaceholderRow depth={depth} text="Cargando portafolios…" />;
  }
  if (rec.state === "error") {
    return <PlaceholderRow depth={depth} text={`Error: ${rec.error ?? ""}`} />;
  }
  if (rec.items.length === 0 && !haySinClasificar) {
    return <PlaceholderRow depth={depth} text="Sin portafolios" />;
  }
  return (
    <>
      {rec.items.map((pf) => {
        const pfKey = `pf:${pf.id}`;
        const abierto = expanded.has(pfKey);
        return (
          <div key={pf.id}>
            <NodeRow
              depth={depth}
              icon={<Briefcase className="h-3.5 w-3.5" aria-hidden />}
              label={pf.code ? `${pf.code} — ${pf.name}` : pf.name}
              active={false}
              hasChildren
              isOpen={abierto}
              onToggle={() => toggle(pfKey)}
              onNavigate={onNavigate}
            />
            {abierto ? (
              <ProgramsList
                rec={maps.programs[pf.id]}
                noProgramRec={maps.noProgramProjects[pf.id]}
                portfolioId={pf.id}
                depth={depth + 1}
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
      {haySinClasificar ? (
        <div>
          <NodeRow
            depth={depth}
            icon={<Folder className="h-3.5 w-3.5" aria-hidden />}
            label="Sin clasificar"
            active={false}
            hasChildren
            isOpen={sinClasificarOpen}
            onToggle={() => toggle(sinClasificarKey)}
            onNavigate={onNavigate}
          />
          {sinClasificarOpen ? (
            <ProjectRows
              rec={unclassifiedRec}
              depth={depth + 1}
              isProjectActive={isProjectActive}
              onNavigate={onNavigate}
              vacio="Sin proyectos"
            />
          ) : null}
        </div>
      ) : null}
    </>
  );
}

function ProgramsList({
  rec,
  noProgramRec,
  portfolioId,
  depth,
  expanded,
  toggle,
  projectsMap,
  isProjectActive,
  onNavigate,
}: {
  rec: LoadedRecord<Program> | undefined;
  noProgramRec: LoadedRecord<Project> | undefined;
  portfolioId: string;
  depth: number;
  expanded: Set<string>;
  toggle: (id: string) => void;
  projectsMap: Record<string, LoadedRecord<Project>>;
  isProjectActive: (id: string) => boolean;
  onNavigate: () => void;
}) {
  const haySinPrograma =
    noProgramRec?.state === "loaded" && noProgramRec.items.length > 0;
  const sinProgramaKey = `no_prog:${portfolioId}`;
  const sinProgramaOpen = expanded.has(sinProgramaKey);

  if (!rec || rec.state === "loading") {
    return <PlaceholderRow depth={depth} text="Cargando programas…" />;
  }
  if (rec.state === "error") {
    return <PlaceholderRow depth={depth} text={`Error: ${rec.error ?? ""}`} />;
  }
  if (rec.items.length === 0 && !haySinPrograma) {
    return <PlaceholderRow depth={depth} text="Sin programas ni proyectos" />;
  }
  return (
    <>
      {rec.items.map((prog) => {
        const progKey = `prog:${prog.id}`;
        const abierto = expanded.has(progKey);
        return (
          <div key={prog.id}>
            <NodeRow
              depth={depth}
              icon={<Layers className="h-3.5 w-3.5" aria-hidden />}
              label={prog.name}
              href={`/pmo/programs/${prog.id}`}
              active={false}
              hasChildren
              isOpen={abierto}
              onToggle={() => toggle(progKey)}
              onNavigate={onNavigate}
            />
            {abierto ? (
              <ProjectRows
                rec={projectsMap[prog.id]}
                depth={depth + 1}
                isProjectActive={isProjectActive}
                onNavigate={onNavigate}
                vacio="Sin proyectos"
              />
            ) : null}
          </div>
        );
      })}
      {haySinPrograma ? (
        <div>
          <NodeRow
            depth={depth}
            icon={<Folder className="h-3.5 w-3.5" aria-hidden />}
            label="Sin programa"
            active={false}
            hasChildren
            isOpen={sinProgramaOpen}
            onToggle={() => toggle(sinProgramaKey)}
            onNavigate={onNavigate}
          />
          {sinProgramaOpen ? (
            <ProjectRows
              rec={noProgramRec}
              depth={depth + 1}
              isProjectActive={isProjectActive}
              onNavigate={onNavigate}
              vacio="Sin proyectos"
            />
          ) : null}
        </div>
      ) : null}
    </>
  );
}
