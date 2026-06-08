"use client";

import { useEffect, useReducer, useRef, useState } from "react";
import { ChevronDown, ChevronRight, Folder, FolderOpen, Globe } from "lucide-react";

import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import {
  getScopeAssignments,
  setScopeAssignments,
  type ScopeAssignmentItem,
  type ScopeType,
} from "@/lib/api/admin";
import { listOrganizations, listPrograms, type Organization, type Program } from "@/lib/api/organizations";
import { listProjects, type Project } from "@/lib/api/projects";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type LoadState<T> = { status: "idle" } | { status: "loading" } | { status: "done"; data: T } | { status: "error" };

type TreeState = {
  orgs: LoadState<Organization[]>;
  programs: Record<string, LoadState<Program[]>>;
  projects: Record<string, LoadState<Project[]>>;
  noProgProjects: Record<string, LoadState<Project[]>>;
  expanded: Set<string>;
};

type TreeAction =
  | { type: "orgs_loading" }
  | { type: "orgs_done"; orgs: Organization[] }
  | { type: "progs_loading"; orgId: string }
  | { type: "progs_done"; orgId: string; progs: Program[] }
  | { type: "projs_loading"; progId: string }
  | { type: "projs_done"; progId: string; projs: Project[] }
  | { type: "no_prog_loading"; orgId: string }
  | { type: "no_prog_done"; orgId: string; projs: Project[] }
  | { type: "toggle"; key: string };

function treeReducer(state: TreeState, action: TreeAction): TreeState {
  switch (action.type) {
    case "orgs_loading":
      return { ...state, orgs: { status: "loading" } };
    case "orgs_done":
      return { ...state, orgs: { status: "done", data: action.orgs } };
    case "progs_loading":
      return { ...state, programs: { ...state.programs, [action.orgId]: { status: "loading" } } };
    case "progs_done":
      return { ...state, programs: { ...state.programs, [action.orgId]: { status: "done", data: action.progs } } };
    case "projs_loading":
      return { ...state, projects: { ...state.projects, [action.progId]: { status: "loading" } } };
    case "projs_done":
      return { ...state, projects: { ...state.projects, [action.progId]: { status: "done", data: action.projs } } };
    case "no_prog_loading":
      return { ...state, noProgProjects: { ...state.noProgProjects, [action.orgId]: { status: "loading" } } };
    case "no_prog_done":
      return { ...state, noProgProjects: { ...state.noProgProjects, [action.orgId]: { status: "done", data: action.projs } } };
    case "toggle": {
      const next = new Set(state.expanded);
      if (next.has(action.key)) next.delete(action.key);
      else next.add(action.key);
      return { ...state, expanded: next };
    }
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function key(type: ScopeType, id: string) {
  return `${type}:${id}`;
}

function hasAssignment(assignments: ScopeAssignmentItem[], type: ScopeType, id: string) {
  return assignments.some((a) => a.scope_type === type && a.scope_id === id);
}

function toggleAssignment(
  prev: ScopeAssignmentItem[],
  type: ScopeType,
  id: string,
  checked: boolean
): ScopeAssignmentItem[] {
  if (checked) {
    if (hasAssignment(prev, type, id)) return prev;
    return [...prev, { scope_type: type, scope_id: id }];
  }
  return prev.filter((a) => !(a.scope_type === type && a.scope_id === id));
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function UserScopeAssignmentPicker({
  userId,
  roleType,
}: {
  userId: string;
  roleType: string | null;
}) {
  const [tree, dispatch] = useReducer(treeReducer, {
    orgs: { status: "idle" },
    programs: {},
    projects: {},
    noProgProjects: {},
    expanded: new Set<string>(),
  });

  const [assignments, setAssignments] = useState<ScopeAssignmentItem[]>([]);
  const [originalAssignments, setOriginalAssignments] = useState<ScopeAssignmentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<{ kind: "success" | "danger"; msg: string } | null>(null);
  const loadedOrgs = useRef(false);

  const isPM = roleType === "user";

  // Load current assignments + orgs on mount
  useEffect(() => {
    if (!isPM) return;
    let cancelled = false;
    setLoading(true);
    Promise.all([
      getScopeAssignments(userId).catch(() => ({ assignments: [] as ScopeAssignmentItem[] })),
      listOrganizations({ is_active: true }),
    ])
      .then(([asgn, orgs]) => {
        if (cancelled) return;
        setAssignments(asgn.assignments);
        setOriginalAssignments(asgn.assignments);
        dispatch({ type: "orgs_done", orgs });
        loadedOrgs.current = true;
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [userId, isPM]);

  async function ensurePrograms(orgId: string) {
    if (tree.programs[orgId]) return;
    dispatch({ type: "progs_loading", orgId });
    const progs = await listPrograms({ organization_id: orgId, is_active: true }).catch(() => [] as Program[]);
    dispatch({ type: "progs_done", orgId, progs });
    const noProgs = await listProjects({ organization_id: orgId, no_program: true, limit: 100 }).catch(() => [] as Project[]);
    dispatch({ type: "no_prog_done", orgId, projs: noProgs });
  }

  async function ensureProjects(progId: string) {
    if (tree.projects[progId]) return;
    dispatch({ type: "projs_loading", progId });
    const projs = await listProjects({ program_id: progId, limit: 100 }).catch(() => [] as Project[]);
    dispatch({ type: "projs_done", progId, projs });
  }

  function handleToggle(k: string, afterExpand?: () => void) {
    dispatch({ type: "toggle", key: k });
    afterExpand?.();
  }

  async function handleSave() {
    setSaving(true);
    setNotice(null);
    try {
      const result = await setScopeAssignments(userId, assignments);
      setOriginalAssignments(result.assignments);
      setAssignments(result.assignments);
      setNotice({ kind: "success", msg: "Asignaciones guardadas" });
    } catch (err) {
      setNotice({
        kind: "danger",
        msg: err instanceof ApiError ? err.message : "No se pudo guardar",
      });
    } finally {
      setSaving(false);
    }
  }

  const isDirty = JSON.stringify([...assignments].sort((a, b) => `${a.scope_type}${a.scope_id}`.localeCompare(`${b.scope_type}${b.scope_id}`)))
    !== JSON.stringify([...originalAssignments].sort((a, b) => `${a.scope_type}${a.scope_id}`.localeCompare(`${b.scope_type}${b.scope_id}`)));

  // Non-PM users: show unrestricted badge
  if (!isPM) {
    return (
      <div className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-sm)]">
        <h2 className="mb-1 text-base font-semibold text-[var(--color-primary)]">Visibilidad PM</h2>
        <div className="flex items-center gap-2 text-sm text-[var(--color-secondary)]">
          <Globe className="h-4 w-4 text-[var(--color-tertiary)]" aria-hidden />
          <span>Acceso total (sin restricciones) — {roleType === "pm_sr" ? "PM Sr" : "Admin"}</span>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="space-y-2 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-sm)]">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  const orgs = tree.orgs.status === "done" ? tree.orgs.data : [];

  return (
    <section className="space-y-4 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-sm)]">
      <header>
        <h2 className="text-base font-semibold text-[var(--color-primary)]">Visibilidad PM</h2>
        <p className="text-xs text-[var(--color-tertiary)]">
          Selecciona las organizaciones, programas o proyectos que este PM puede ver.
          Una org seleccionada da visibilidad a todos sus programas y proyectos.
          Sin asignaciones → no ve nada.
        </p>
      </header>

      {notice ? (
        <Banner variant={notice.kind === "success" ? "success" : "danger"}>{notice.msg}</Banner>
      ) : null}

      <div className="max-h-96 overflow-y-auto rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-subtle)]">
        {orgs.length === 0 ? (
          <p className="px-4 py-3 text-sm text-[var(--color-tertiary)]">
            Sin organizaciones activas en el tenant.
          </p>
        ) : (
          <ul className="divide-y divide-[var(--border-default)]">
            {orgs.map((org) => {
              const orgKey = `org:${org.id}`;
              const expanded = tree.expanded.has(orgKey);
              const orgChecked = hasAssignment(assignments, "organization", org.id);
              const progs = tree.programs[org.id];
              const noProgs = tree.noProgProjects[org.id];

              return (
                <li key={org.id}>
                  <div className="flex items-center gap-2 px-3 py-2 hover:bg-[var(--color-muted)]">
                    <button
                      type="button"
                      aria-label={expanded ? "Colapsar" : "Expandir"}
                      onClick={() => handleToggle(orgKey, () => { if (!expanded) void ensurePrograms(org.id); })}
                      className="flex h-5 w-5 flex-shrink-0 items-center justify-center text-[var(--color-tertiary)]"
                    >
                      {expanded
                        ? <ChevronDown className="h-3.5 w-3.5" />
                        : <ChevronRight className="h-3.5 w-3.5" />}
                    </button>
                    <Checkbox
                      checked={orgChecked}
                      onChange={(e) =>
                        setAssignments((prev) => toggleAssignment(prev, "organization", org.id, e.target.checked))
                      }
                    />
                    {expanded
                      ? <FolderOpen className="h-4 w-4 flex-shrink-0 text-[var(--color-tertiary)]" aria-hidden />
                      : <Folder className="h-4 w-4 flex-shrink-0 text-[var(--color-tertiary)]" aria-hidden />}
                    <span className="text-sm font-medium text-[var(--color-primary)]">{org.name}</span>
                  </div>

                  {expanded && (
                    <div className="ml-8 border-l border-[var(--border-default)]">
                      {/* Programs */}
                      {(!progs || progs.status === "loading") ? (
                        <div className="px-3 py-2"><Skeleton className="h-3 w-32" /></div>
                      ) : progs.status === "done" ? (
                        <>
                          {progs.data.map((prog) => {
                            const progKey = `prog:${prog.id}`;
                            const progExpanded = tree.expanded.has(progKey);
                            const progChecked = hasAssignment(assignments, "program", prog.id);
                            const projs = tree.projects[prog.id];

                            return (
                              <div key={prog.id}>
                                <div className="flex items-center gap-2 px-3 py-1.5 hover:bg-[var(--color-muted)]">
                                  <button
                                    type="button"
                                    aria-label={progExpanded ? "Colapsar" : "Expandir"}
                                    onClick={() => handleToggle(progKey, () => { if (!progExpanded) void ensureProjects(prog.id); })}
                                    className="flex h-5 w-5 flex-shrink-0 items-center justify-center text-[var(--color-tertiary)]"
                                  >
                                    {progExpanded
                                      ? <ChevronDown className="h-3.5 w-3.5" />
                                      : <ChevronRight className="h-3.5 w-3.5" />}
                                  </button>
                                  <Checkbox
                                    checked={progChecked}
                                    onChange={(e) =>
                                      setAssignments((prev) => toggleAssignment(prev, "program", prog.id, e.target.checked))
                                    }
                                  />
                                  <span className="text-sm text-[var(--color-primary)]">{prog.name}</span>
                                </div>

                                {progExpanded && (
                                  <div className="ml-8 border-l border-[var(--border-default)]">
                                    {(!projs || projs.status === "loading") ? (
                                      <div className="px-3 py-1.5"><Skeleton className="h-3 w-28" /></div>
                                    ) : projs.status === "done" ? (
                                      projs.data.length === 0 ? (
                                        <p className="px-3 py-1.5 text-xs text-[var(--color-tertiary)]">Sin proyectos</p>
                                      ) : (
                                        projs.data.map((proj) => (
                                          <ProjectRow
                                            key={proj.id}
                                            proj={proj}
                                            checked={hasAssignment(assignments, "project", proj.id)}
                                            onChange={(checked) =>
                                              setAssignments((prev) => toggleAssignment(prev, "project", proj.id, checked))
                                            }
                                          />
                                        ))
                                      )
                                    ) : null}
                                  </div>
                                )}
                              </div>
                            );
                          })}

                          {/* No-program projects */}
                          {noProgs?.status === "done" && noProgs.data.length > 0 && (
                            <div>
                              <div className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-[var(--color-tertiary)]">
                                <span className="ml-6">Sin programa</span>
                              </div>
                              <div className="ml-8 border-l border-[var(--border-default)]">
                                {noProgs.data.map((proj) => (
                                  <ProjectRow
                                    key={proj.id}
                                    proj={proj}
                                    checked={hasAssignment(assignments, "project", proj.id)}
                                    onChange={(checked) =>
                                      setAssignments((prev) => toggleAssignment(prev, "project", proj.id, checked))
                                    }
                                  />
                                ))}
                              </div>
                            </div>
                          )}

                          {progs.data.length === 0 && (noProgs?.status !== "done" || noProgs.data.length === 0) && (
                            <p className="px-3 py-1.5 text-xs text-[var(--color-tertiary)]">Sin programas ni proyectos</p>
                          )}
                        </>
                      ) : null}
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>

      <div className="flex items-center justify-between gap-2 border-t border-[var(--border-default)] pt-4">
        <p className="text-xs text-[var(--color-tertiary)]">
          {assignments.length === 0
            ? "Sin asignaciones — el PM no ve nada."
            : `${assignments.length} asignación${assignments.length !== 1 ? "es" : ""}`}
        </p>
        <div className="flex gap-2">
          <Button
            type="button"
            variant="secondary"
            disabled={saving || !isDirty}
            onClick={() => setAssignments(originalAssignments)}
          >
            Descartar
          </Button>
          <Button
            type="button"
            loading={saving}
            disabled={!isDirty}
            onClick={handleSave}
          >
            Guardar visibilidad
          </Button>
        </div>
      </div>
    </section>
  );
}

function ProjectRow({
  proj,
  checked,
  onChange,
}: {
  proj: Project;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="flex cursor-pointer items-center gap-2 px-3 py-1.5 hover:bg-[var(--color-muted)]">
      <Checkbox checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span className="text-sm text-[var(--color-primary)]">
        {proj.folio ? <span className="text-[var(--color-tertiary)]">{proj.folio} — </span> : null}
        {proj.name}
      </span>
    </label>
  );
}
