"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Plus, Search } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
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
    <div className="mx-auto max-w-6xl space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-[var(--color-primary)]">Usuarios</h1>
          <p className="mt-1 text-sm text-[var(--color-tertiary)]">
            Da de alta, edita y administra el acceso de tu equipo.
          </p>
        </div>
        {canCreateUser ? (
          <Link href="/admin/users/new">
            <Button size="md">
              <Plus className="h-4 w-4" aria-hidden />
              Nuevo usuario
            </Button>
          </Link>
        ) : null}
      </header>

      <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]">
        <div className="grid gap-3 border-b border-[var(--border-default)] p-4 sm:grid-cols-[1fr_180px_160px]">
          <div className="relative">
            <Search
              className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--color-tertiary)]"
              aria-hidden
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
          <table className="w-full text-sm">
            <thead className="border-b border-[var(--border-default)] text-left text-xs uppercase tracking-wide text-[var(--color-tertiary)]">
              <tr>
                <SortableTh<AdminUser> sortKey="user" getter={(u) => u.full_name ?? u.email} ctrl={usersCtrl} className="px-4 py-3">Usuario</SortableTh>
                <SortableTh<AdminUser> sortKey="roles" getter={(u) => (u.roles ?? []).join(",")} ctrl={usersCtrl} className="px-4 py-3">Roles</SortableTh>
                <SortableTh<AdminUser> sortKey="status" getter={(u) => (u.is_active ? "activo" : "inactivo")} ctrl={usersCtrl} className="px-4 py-3">Estado</SortableTh>
                <SortableTh<AdminUser> sortKey="last_login" getter={(u) => (u as any).last_login_at ?? ""} ctrl={usersCtrl} className="px-4 py-3">Último ingreso</SortableTh>
                <th className="px-4 py-3" aria-label="Acciones" />
              </tr>
            </thead>
            <tbody>
              {loading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="border-b border-[var(--border-subtle)]">
                    <td className="px-4 py-3">
                      <Skeleton className="h-4 w-40" />
                      <Skeleton className="mt-1 h-3 w-56" />
                    </td>
                    <td className="px-4 py-3">
                      <Skeleton className="h-4 w-24" />
                    </td>
                    <td className="px-4 py-3">
                      <Skeleton className="h-4 w-16" />
                    </td>
                    <td className="px-4 py-3">
                      <Skeleton className="h-4 w-24" />
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Skeleton className="ml-auto h-4 w-12" />
                    </td>
                  </tr>
                ))
              ) : data && sortedUsers.length > 0 ? (
                sortedUsers.map((u: AdminUser) => (
                  <tr
                    key={u.id}
                    className="border-b border-[var(--border-subtle)] hover:bg-[var(--color-subtle)]"
                  >
                    <td className="px-4 py-3">
                      <div className="font-medium text-[var(--color-primary)]">{u.full_name}</div>
                      <div className="text-xs text-[var(--color-tertiary)]">
                        {u.username} · {u.email}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <Badge>
                        {u.role_type ? ROLE_TYPE_LABEL[u.role_type as keyof typeof ROLE_TYPE_LABEL] ?? u.role_type : "PM"}
                      </Badge>
                    </td>
                    <td className="px-4 py-3">
                      {u.is_active ? (
                        <Badge variant="success">Activo</Badge>
                      ) : (
                        <Badge variant="danger">Inactivo</Badge>
                      )}
                      {u.must_change_password ? (
                        <Badge variant="warning" className="ml-1">
                          Cambio pendiente
                        </Badge>
                      ) : null}
                    </td>
                    <td className="px-4 py-3 text-[var(--color-secondary)]">
                      {formatDate(u.last_login)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        href={`/admin/users/${u.id}`}
                        className="text-sm font-medium text-[var(--color-primary)] hover:underline"
                      >
                        Editar
                      </Link>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="px-4 py-12 text-center text-sm text-[var(--color-tertiary)]">
                    No hay usuarios que coincidan con los filtros.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {data && data.total > 0 ? (
          <div className="flex items-center justify-between gap-3 border-t border-[var(--border-default)] px-4 py-3 text-sm text-[var(--color-secondary)]">
            <div>
              Página <span className="font-medium text-[var(--color-primary)]">{data.page}</span> de{" "}
              <span className="font-medium text-[var(--color-primary)]">{totalPages}</span> ·{" "}
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
