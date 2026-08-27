"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Icono } from "@/components/ui/icono";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useMyPermissions } from "@/hooks/use-my-permissions";
import { ApiError } from "@/lib/api";
import { useSortableRows } from "@/lib/hooks/use-sortable-rows";
import { SortableTh } from "@/components/ui/sortable-th";
import {
  ROLE_TYPE_LABEL,
  listRoles,
  listUsers,
  type AdminRole,
  type AdminUser,
  type PaginatedUsers,
} from "@/lib/api/admin";

const PAGE_SIZE = 20;

function formatDate(iso: string | null): string {
  if (!iso) return "Nunca";
  try {
    return new Date(iso).toLocaleString("es-MX", {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return iso;
  }
}

function useDebounced<T>(value: T, delayMs = 300): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(t);
  }, [value, delayMs]);
  return debounced;
}

export default function UsersListPage() {
  const { canCreate } = useMyPermissions();
  const canCreateUser = canCreate("users");
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebounced(search, 300);
  const [roleFilter, setRoleFilter] = useState<string>("");
  const [activeFilter, setActiveFilter] = useState<string>("all");
  const [page, setPage] = useState(1);

  const [roles, setRoles] = useState<AdminRole[]>([]);
  const [data, setData] = useState<PaginatedUsers | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { sortedRows: sortedUsers, ctrl: usersCtrl } = useSortableRows<AdminUser>(data?.items ?? []);

  useEffect(() => {
    setPage(1);
  }, [debouncedSearch, roleFilter, activeFilter]);

  useEffect(() => {
    let cancelled = false;
    listRoles()
      .then((r) => {
        if (!cancelled) setRoles(r);
      })
      .catch(() => {
        // si no se pueden cargar roles, no se muestra el filtro pero la lista sigue
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    listUsers({
      q: debouncedSearch.trim() || undefined,
      role_id: roleFilter || undefined,
      is_active: activeFilter === "all" ? undefined : activeFilter === "active",
      page,
      limit: PAGE_SIZE,
    })
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof ApiError ? err.message : "No se pudieron cargar los usuarios");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [debouncedSearch, roleFilter, activeFilter, page]);

  const totalPages = useMemo(() => {
    if (!data) return 1;
    return Math.max(1, Math.ceil(data.total / data.limit));
  }, [data]);

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-[var(--text-primary)]">Usuarios</h1>
          <p className="mt-1 text-[13px] text-[var(--text-tertiary)]">
            Da de alta, edita y administra el acceso de tu equipo.
          </p>
        </div>
        {canCreateUser ? (
          <Link href="/admin/users/new">
            <Button size="md">
              <Icono nombre="plus" size={15} />
              Nuevo usuario
            </Button>
          </Link>
        ) : null}
      </header>

      <section className="rounded-[var(--radius-window)] border border-[var(--border-subtle)] bg-[var(--color-surface)]">
        <div className="grid gap-3 border-b border-[var(--border-subtle)] p-4 sm:grid-cols-[1fr_180px_160px]">
          <div className="relative">
            <Icono
              nombre="search"
              size={15}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-tertiary)]"
            />
            <Input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar por nombre, usuario o email"
              className="pl-9"
              aria-label="Buscar usuarios"
            />
          </div>
          <Select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            aria-label="Filtrar por rol"
          >
            <option value="">Todos los roles</option>
            {/* DIS-03: sin roles cargados el filtro queda con una sola opción.
                Se dice, en vez de dejar un desplegable que no despliega nada. */}
            {roles.length === 0 ? (
              <option value="" disabled>
                (aún no hay roles definidos)
              </option>
            ) : null}
            {roles.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
          </Select>
          <Select
            value={activeFilter}
            onChange={(e) => setActiveFilter(e.target.value)}
            aria-label="Filtrar por estado"
          >
            <option value="all">Todos los estados</option>
            <option value="active">Activos</option>
            <option value="inactive">Inactivos</option>
          </Select>
        </div>

        {error ? (
          <div className="p-4">
            <Banner variant="danger">{error}</Banner>
          </div>
        ) : null}

        <div className="overflow-x-auto">
          <table className="w-full table-fixed text-[13px]">
            <thead className="border-b border-[var(--border-subtle)] bg-[var(--color-subtle)] text-left text-[11px] uppercase tracking-[0.01em] text-[var(--text-secondary)]">
              <tr>
                <SortableTh<AdminUser> sortKey="user" getter={(u) => u.full_name ?? u.email} ctrl={usersCtrl} className="h-8.5 px-4">Usuario</SortableTh>
                <SortableTh<AdminUser> sortKey="roles" getter={(u) => (u.roles ?? []).join(",")} ctrl={usersCtrl} className="h-8.5 px-4 w-25">Rol</SortableTh>
                <SortableTh<AdminUser> sortKey="status" getter={(u) => (u.is_active ? "activo" : "inactivo")} ctrl={usersCtrl} className="h-8.5 px-4 w-44">Estado</SortableTh>
                <SortableTh<AdminUser> sortKey="last_login" getter={(u) => (u as any).last_login_at ?? ""} ctrl={usersCtrl} className="h-8.5 px-4 w-43">Último ingreso</SortableTh>
                <th className="h-8.5 w-20 px-4" aria-label="Acciones" />
              </tr>
            </thead>
            <tbody>
              {loading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="h-11 border-b border-[var(--border-subtle)]">
                    <td className="px-4">
                      <Skeleton className="h-4 w-40" />
                      <Skeleton className="mt-1 h-3 w-56" />
                    </td>
                    <td className="px-4">
                      <Skeleton className="h-4 w-16" />
                    </td>
                    <td className="px-4">
                      <Skeleton className="h-4 w-20" />
                    </td>
                    <td className="px-4">
                      <Skeleton className="h-4 w-24" />
                    </td>
                    <td className="px-4 text-right">
                      <Skeleton className="ml-auto h-4 w-12" />
                    </td>
                  </tr>
                ))
              ) : data && sortedUsers.length > 0 ? (
                sortedUsers.map((u: AdminUser) => (
                  <tr
                    key={u.id}
                    className="h-11 border-b border-[var(--border-subtle)] transition-colors hover:bg-[var(--color-subtle)]/60"
                  >
                    <td className="min-w-0 px-4">
                      <div className="flex min-w-0 flex-col">
                        <span className="overflow-hidden text-ellipsis whitespace-nowrap font-medium text-[var(--text-primary)]">
                          {u.full_name}
                        </span>
                        <span className="overflow-hidden text-ellipsis whitespace-nowrap text-[11.5px] text-[var(--text-tertiary)]">
                          {u.username} · {u.email}
                        </span>
                      </div>
                    </td>
                    <td className="px-4">
                      <Badge>
                        {u.role_type ? ROLE_TYPE_LABEL[u.role_type as keyof typeof ROLE_TYPE_LABEL] ?? u.role_type : "PM"}
                      </Badge>
                    </td>
                    <td className="px-4">
                      <div className="flex items-center gap-1.5">
                        {u.is_active ? (
                          <Badge variant="success">Activo</Badge>
                        ) : (
                          <Badge variant="danger">Inactivo</Badge>
                        )}
                        {u.must_change_password ? (
                          <Badge variant="warning">Cambio pendiente</Badge>
                        ) : null}
                      </div>
                    </td>
                    <td className="px-4 text-[12.5px] text-[var(--text-secondary)]">
                      {formatDate(u.last_login)}
                    </td>
                    <td className="px-4 text-right">
                      <Link
                        href={`/admin/users/${u.id}`}
                        className="text-[12.5px] font-medium text-[var(--text-primary)] hover:underline"
                      >
                        Editar
                      </Link>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="px-4 py-16 text-center text-[var(--text-tertiary)]">
                    No hay usuarios que coincidan con los filtros.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {data && data.total > 0 ? (
          <div className="flex items-center justify-between gap-3 border-t border-[var(--border-subtle)] px-4 py-3 text-[13px] text-[var(--text-secondary)]">
            <div>
              Página <span className="font-medium text-[var(--text-primary)]">{data.page}</span> de{" "}
              <span className="font-medium text-[var(--text-primary)]">{totalPages}</span> ·{" "}
              {data.total} resultados
            </div>
            <div className="flex gap-2">
              <Button
                variant="secondary"
                size="sm"
                disabled={page <= 1 || loading}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                Anterior
              </Button>
              <Button
                variant="secondary"
                size="sm"
                disabled={page >= totalPages || loading}
                onClick={() => setPage((p) => p + 1)}
              >
                Siguiente
              </Button>
            </div>
          </div>
        ) : null}
      </section>
    </div>
  );
}
