"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import {
  ChevronRight,
  ExternalLink,
  Pencil,
  Plus,
  Trash2,
  Users,
  Workflow,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api";
import {
  createBusinessUnit,
  createDepartment,
  deleteBusinessUnit,
  deleteDepartment,
  listBusinessUnits,
  listDepartments,
  updateBusinessUnit,
  updateDepartment,
  type BusinessUnit,
  type Department,
} from "@/lib/api/organizations";
import { cn } from "@/lib/cn";

type DeptsByBu = Record<string, Department[] | "loading" | "error">;

function useBusAndDepts(orgId: string) {
  const [bus, setBus] = useState<BusinessUnit[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [depts, setDepts] = useState<DeptsByBu>({});

  async function refreshBus() {
    setLoading(true);
    setError(null);
    try {
      const rows = await listBusinessUnits(orgId);
      setBus(rows);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Error al cargar unidades de negocio",
      );
    } finally {
      setLoading(false);
    }
  }

  async function refreshDepts(buId: string) {
    setDepts((s) => ({ ...s, [buId]: "loading" }));
    try {
      const rows = await listDepartments(buId);
      setDepts((s) => ({ ...s, [buId]: rows }));
    } catch {
      setDepts((s) => ({ ...s, [buId]: "error" }));
    }
  }

  useEffect(() => {
    void refreshBus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orgId]);

  return {
    bus,
    loading,
    error,
    depts,
    refreshBus,
    refreshDepts,
  };
}

type NameDescState = { name: string; description: string };

const EMPTY: NameDescState = { name: "", description: "" };

export function OrgHierarchySection({ orgId }: { orgId: string }) {
  const {
    bus,
    loading,
    error,
    depts,
    refreshBus,
    refreshDepts,
  } = useBusAndDepts(orgId);

  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const [buModal, setBuModal] = useState<
    { mode: "create" } | { mode: "edit"; bu: BusinessUnit } | null
  >(null);
  const [deptModal, setDeptModal] = useState<
    | { mode: "create"; buId: string }
    | { mode: "edit"; dept: Department }
    | null
  >(null);
  const [confirmBu, setConfirmBu] = useState<BusinessUnit | null>(null);
  const [confirmDept, setConfirmDept] = useState<Department | null>(null);

  function toggle(buId: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(buId)) {
        next.delete(buId);
      } else {
        next.add(buId);
        if (!depts[buId]) void refreshDepts(buId);
      }
      return next;
    });
  }

  async function removeBu(bu: BusinessUnit, force: boolean) {
    await deleteBusinessUnit(bu.id, force);
    setConfirmBu(null);
    await refreshBus();
  }

  async function removeDept(dept: Department, force: boolean) {
    await deleteDepartment(dept.id, force);
    setConfirmDept(null);
    await refreshDepts(dept.business_unit_id);
  }

  return (
    <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--border-default)] px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold text-[var(--color-primary)]">
            Jerarquía: unidades de negocio y departamentos
          </h2>
          <p className="text-xs text-[var(--color-tertiary)]">
            Estructura la organización en BUs → Departamentos para filtrar
            programas y proyectos.
          </p>
        </div>
        <div className="flex gap-2">
          <Link href={`/pmo/projects?organization_id=${orgId}`}>
            <Button variant="secondary" size="sm">
              <ExternalLink className="h-4 w-4" aria-hidden />
              Ver proyectos
            </Button>
          </Link>
          <Button size="sm" onClick={() => setBuModal({ mode: "create" })}>
            <Plus className="h-4 w-4" aria-hidden /> Nueva BU
          </Button>
        </div>
      </header>

      {error ? (
        <div className="p-4">
          <Banner variant="danger">{error}</Banner>
        </div>
      ) : null}

      {loading ? (
        <div className="space-y-2 p-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      ) : bus.length === 0 ? (
        <div className="p-8 text-center text-sm text-[var(--color-tertiary)]">
          Aún no hay unidades de negocio. Crea la primera con "Nueva BU".
        </div>
      ) : (
        <ul className="divide-y divide-[var(--border-subtle)]">
          {bus.map((bu) => {
            const isOpen = expanded.has(bu.id);
            const bucketDepts = depts[bu.id];
            return (
              <li key={bu.id}>
                <div className="flex items-center gap-2 px-3 py-2.5 hover:bg-[var(--color-subtle)]">
                  <button
                    type="button"
                    onClick={() => toggle(bu.id)}
                    aria-expanded={isOpen}
                    aria-label={isOpen ? "Colapsar" : "Expandir"}
                    className="inline-flex h-6 w-6 flex-none items-center justify-center text-[var(--color-tertiary)]"
                  >
                    <ChevronRight
                      className={cn("h-4 w-4 transition-transform", isOpen && "rotate-90")}
                      aria-hidden
                    />
                  </button>
                  <Workflow
                    className="h-4 w-4 flex-none text-[var(--color-tertiary)]"
                    aria-hidden
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="truncate text-sm font-medium text-[var(--color-primary)]">
                        {bu.name}
                      </span>
                      {!bu.is_active ? (
                        <Badge variant="danger">Inactiva</Badge>
                      ) : null}
                    </div>
                    {bu.description ? (
                      <div className="truncate text-xs text-[var(--color-tertiary)]">
                        {bu.description}
                      </div>
                    ) : null}
                  </div>
                  <div className="flex gap-1">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() =>
                        setDeptModal({ mode: "create", buId: bu.id })
                      }
                      title="Nuevo departamento"
                    >
                      <Plus className="h-4 w-4" aria-hidden />
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setBuModal({ mode: "edit", bu })}
                      title="Editar"
                    >
                      <Pencil className="h-4 w-4" aria-hidden />
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setConfirmBu(bu)}
                      title="Desactivar"
                    >
                      <Trash2 className="h-4 w-4" aria-hidden />
                    </Button>
                  </div>
                </div>

                {isOpen ? (
                  <ul className="divide-y divide-[var(--border-subtle)] bg-[var(--color-app)]">
                    {bucketDepts === "loading" ? (
                      <li className="px-10 py-2 text-xs text-[var(--color-tertiary)]">
                        Cargando departamentos…
                      </li>
                    ) : bucketDepts === "error" ? (
                      <li className="px-10 py-2 text-xs text-[var(--color-danger-fg)]">
                        Error al cargar departamentos.
                      </li>
                    ) : !bucketDepts || bucketDepts.length === 0 ? (
                      <li className="px-10 py-2 text-xs italic text-[var(--color-tertiary)]">
                        Sin departamentos. Usa "+" para crear uno.
                      </li>
                    ) : (
                      bucketDepts.map((d) => (
                        <li
                          key={d.id}
                          className="flex items-center gap-2 py-2 pl-10 pr-3 hover:bg-[var(--color-subtle)]"
                        >
                          <Users
                            className="h-4 w-4 flex-none text-[var(--color-tertiary)]"
                            aria-hidden
                          />
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2">
                              <span className="truncate text-sm text-[var(--color-primary)]">
                                {d.name}
                              </span>
                              {!d.is_active ? (
                                <Badge variant="danger">Inactivo</Badge>
                              ) : null}
                            </div>
                            {d.description ? (
                              <div className="truncate text-xs text-[var(--color-tertiary)]">
                                {d.description}
                              </div>
                            ) : null}
                          </div>
                          <div className="flex gap-1">
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() =>
                                setDeptModal({ mode: "edit", dept: d })
                              }
                              title="Editar"
                            >
                              <Pencil className="h-4 w-4" aria-hidden />
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => setConfirmDept(d)}
                              title="Desactivar"
                            >
                              <Trash2 className="h-4 w-4" aria-hidden />
                            </Button>
                          </div>
                        </li>
                      ))
                    )}
                  </ul>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}

      <NameDescModal
        title={buModal?.mode === "edit" ? "Editar unidad de negocio" : "Nueva unidad de negocio"}
        open={buModal !== null}
        onClose={() => setBuModal(null)}
        initial={
          buModal?.mode === "edit"
            ? { name: buModal.bu.name, description: buModal.bu.description ?? "" }
            : EMPTY
        }
        onSubmit={async (state) => {
          if (buModal?.mode === "edit") {
            await updateBusinessUnit(buModal.bu.id, {
              name: state.name,
              description: state.description || null,
            });
          } else {
            await createBusinessUnit(orgId, {
              name: state.name,
              description: state.description || null,
            });
          }
          setBuModal(null);
          await refreshBus();
        }}
      />

      <NameDescModal
        title={
          deptModal?.mode === "edit" ? "Editar departamento" : "Nuevo departamento"
        }
        open={deptModal !== null}
        onClose={() => setDeptModal(null)}
        initial={
          deptModal?.mode === "edit"
            ? {
                name: deptModal.dept.name,
                description: deptModal.dept.description ?? "",
              }
            : EMPTY
        }
        onSubmit={async (state) => {
          if (deptModal?.mode === "edit") {
            await updateDepartment(deptModal.dept.id, {
              name: state.name,
              description: state.description || null,
            });
            setDeptModal(null);
            await refreshDepts(deptModal.dept.business_unit_id);
          } else if (deptModal?.mode === "create") {
            await createDepartment(deptModal.buId, {
              name: state.name,
              description: state.description || null,
            });
            const buId = deptModal.buId;
            setDeptModal(null);
            await refreshDepts(buId);
            setExpanded((prev) => new Set(prev).add(buId));
          }
        }}
      />

      <ConfirmDeactivateModal
        target={confirmBu}
        label="unidad de negocio"
        onClose={() => setConfirmBu(null)}
        onConfirm={async (force) => {
          if (confirmBu) await removeBu(confirmBu, force);
        }}
      />

      <ConfirmDeactivateModal
        target={confirmDept}
        label="departamento"
        onClose={() => setConfirmDept(null)}
        onConfirm={async (force) => {
          if (confirmDept) await removeDept(confirmDept, force);
        }}
      />
    </section>
  );
}

function NameDescModal({
  open,
  onClose,
  title,
  initial,
  onSubmit,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  initial: NameDescState;
  onSubmit: (state: NameDescState) => Promise<void>;
}) {
  const [state, setState] = useState(initial);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setState(initial);
      setError(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (state.name.trim().length < 2) {
      setError("El nombre es obligatorio (mínimo 2 caracteres)");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await onSubmit({
        name: state.name.trim(),
        description: state.description.trim(),
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al guardar");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={title}>
      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]">
            Nombre
          </label>
          <Input
            value={state.name}
            onChange={(e) => setState({ ...state, name: e.target.value })}
            minLength={2}
            maxLength={200}
            required
          />
        </div>
        <div>
          <label className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]">
            Descripción
          </label>
          <Textarea
            rows={3}
            value={state.description}
            onChange={(e) =>
              setState({ ...state, description: e.target.value })
            }
          />
        </div>
        {error ? <Banner variant="danger">{error}</Banner> : null}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" loading={saving}>
            Guardar
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function ConfirmDeactivateModal<T extends { name: string }>({
  target,
  label,
  onClose,
  onConfirm,
}: {
  target: T | null;
  label: string;
  onClose: () => void;
  onConfirm: (force: boolean) => Promise<void> | void;
}) {
  const [loading, setLoading] = useState(false);
  const [force, setForce] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (target) {
      setForce(false);
      setError(null);
    }
  }, [target]);

  async function go() {
    if (!target) return;
    setLoading(true);
    setError(null);
    try {
      await onConfirm(force);
    } catch (err) {
      if (err instanceof ApiError && err.code === "BUSINESS_RULE") {
        setError(`${err.message}. Activa "Forzar" para cascada.`);
      } else {
        setError(err instanceof ApiError ? err.message : "Error al desactivar");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <Modal
      open={target !== null}
      onClose={onClose}
      title={`Desactivar ${label}`}
    >
      <p className="text-sm text-[var(--color-secondary)]">
        ¿Confirmas desactivar <strong>{target?.name}</strong>? Queda como
        inactivo; sus hijos pueden impedir la acción a menos que uses force.
      </p>
      <label className="mt-3 inline-flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={force}
          onChange={(e) => setForce(e.target.checked)}
        />
        Forzar (desactiva en cascada)
      </label>
      {error ? (
        <div className="mt-3">
          <Banner variant="danger">{error}</Banner>
        </div>
      ) : null}
      <div className="mt-4 flex justify-end gap-2">
        <Button variant="ghost" onClick={onClose}>
          Cancelar
        </Button>
        <Button variant="danger" loading={loading} onClick={go}>
          Desactivar
        </Button>
      </div>
    </Modal>
  );
}
