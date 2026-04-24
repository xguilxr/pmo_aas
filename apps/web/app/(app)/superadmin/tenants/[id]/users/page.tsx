"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { Shield, ShieldAlert, ShieldCheck, ShieldX } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import { getStoredUser } from "@/lib/auth-storage";
import {
  getTenantDetail,
  listTenantUsers,
  updateUserRoleType,
  type SuperadminUserRow,
  type TenantDetail,
} from "@/lib/api/superadmin";

type RoleType = "admin" | "user" | "viewer";

const ROLE_LABELS: Record<RoleType, string> = {
  admin: "Admin",
  user: "User",
  viewer: "Viewer",
};

export default function SuperadminTenantUsersPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const tenantId = params.id;

  const me = getStoredUser();
  const [tenant, setTenant] = useState<TenantDetail["tenant"] | null>(null);
  const [users, setUsers] = useState<SuperadminUserRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [pendingChanges, setPendingChanges] = useState<Record<string, RoleType>>({});

  const [filterQ, setFilterQ] = useState("");
  const [filterRoleType, setFilterRoleType] = useState<"" | RoleType>("");

  useEffect(() => {
    if (!tenantId) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all([
      getTenantDetail(tenantId),
      listTenantUsers(tenantId, {
        q: filterQ || undefined,
        role_type: filterRoleType || undefined,
      }),
    ])
      .then(([t, u]) => {
        if (cancelled) return;
        setTenant(t.tenant);
        setUsers(u);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(
            err instanceof ApiError
              ? err.message
              : "No se pudieron cargar los usuarios del tenant",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [tenantId, filterQ, filterRoleType]);

  if (me && !me.is_superadmin) {
    return (
      <div className="mx-auto max-w-2xl p-6">
        <Banner variant="danger">
          Solo los super administradores pueden ver esta página.
        </Banner>
      </div>
    );
  }

  async function saveRoleType(user: SuperadminUserRow, next: RoleType) {
    if (savingId) return;
    if (
      !window.confirm(
        `Cambiar role_type de ${user.email}: ${user.role_type ?? "(none)"} → ${next}?`,
      )
    ) {
      return;
    }
    setSavingId(user.id);
    try {
      const result = await updateUserRoleType(user.id, next);
      setUsers((rows) =>
        rows.map((r) =>
          r.id === user.id
            ? { ...r, role_type: result.role_type as RoleType }
            : r,
        ),
      );
      setPendingChanges((m) => {
        const { [user.id]: _, ...rest } = m;
        return rest;
      });
    } catch (err) {
      alert(
        err instanceof ApiError ? err.message : "No se pudo actualizar el role_type",
      );
    } finally {
      setSavingId(null);
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <Breadcrumb
        items={[
          { label: "Superadmin", href: "/superadmin" },
          { label: "Tenants", href: "/superadmin/tenants" },
          {
            label: tenant?.name ?? "Tenant",
            href: `/superadmin/tenants/${tenantId}`,
          },
          { label: "Usuarios" },
        ]}
      />

      <header>
        <h1 className="text-2xl font-semibold text-[var(--color-primary)]">
          Usuarios del tenant {tenant?.name ? `— ${tenant.name}` : ""}
        </h1>
        <p className="mt-1 text-sm text-[var(--color-tertiary)]">
          Gestión del <code>role_type</code> (admin / user / viewer). Útil
          como vía de rescate cuando un admin pierde acceso (ver BUG-031).
        </p>
      </header>

      <section className="flex flex-wrap gap-3">
        <Input
          placeholder="Buscar email o username…"
          value={filterQ}
          onChange={(e) => setFilterQ(e.target.value)}
          className="w-64"
        />
        <Select
          value={filterRoleType}
          onChange={(e) =>
            setFilterRoleType((e.target.value || "") as "" | RoleType)
          }
        >
          <option value="">Todos los roles</option>
          <option value="admin">Admin</option>
          <option value="user">User</option>
          <option value="viewer">Viewer</option>
        </Select>
      </section>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      ) : users.length === 0 ? (
        <p className="rounded-md border border-[var(--border-default)] bg-[var(--color-surface)] p-6 text-center text-sm text-[var(--color-tertiary)]">
          No hay usuarios para los filtros aplicados.
        </p>
      ) : (
        <table className="w-full overflow-hidden rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--color-surface)] text-sm">
          <thead className="bg-[var(--color-subtle)] text-left text-xs uppercase text-[var(--color-tertiary)]">
            <tr>
              <th className="px-3 py-2">Usuario</th>
              <th className="px-3 py-2">Email</th>
              <th className="px-3 py-2">Estado</th>
              <th className="px-3 py-2">Role type</th>
              <th className="px-3 py-2 text-right">Acción</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border-default)]">
            {users.map((u) => {
              const pending = pendingChanges[u.id];
              const current = (u.role_type ?? "") as RoleType | "";
              const next = pending ?? current;
              const hasChange = pending !== undefined && pending !== current;
              return (
                <tr key={u.id} className="align-middle">
                  <td className="px-3 py-2">
                    <div className="flex items-center gap-2">
                      <RoleIcon role={u.role_type} />
                      <span className="font-medium text-[var(--color-primary)]">
                        {u.full_name || u.username}
                      </span>
                      {u.is_superadmin ? (
                        <Badge variant="warning">superadmin</Badge>
                      ) : null}
                    </div>
                    <div className="text-xs text-[var(--color-tertiary)]">
                      @{u.username}
                    </div>
                  </td>
                  <td className="px-3 py-2 font-mono text-xs">{u.email}</td>
                  <td className="px-3 py-2">
                    {u.is_active ? (
                      <Badge variant="success">activo</Badge>
                    ) : (
                      <Badge variant="danger">inactivo</Badge>
                    )}
                  </td>
                  <td className="px-3 py-2">
                    <Select
                      value={next}
                      disabled={u.is_superadmin || savingId === u.id}
                      onChange={(e) => {
                        const v = e.target.value as RoleType | "";
                        if (!v) return;
                        setPendingChanges((m) => ({ ...m, [u.id]: v as RoleType }));
                      }}
                    >
                      <option value="">— sin role_type —</option>
                      <option value="admin">Admin</option>
                      <option value="user">User</option>
                      <option value="viewer">Viewer</option>
                    </Select>
                  </td>
                  <td className="px-3 py-2 text-right">
                    <Button
                      type="button"
                      size="sm"
                      disabled={!hasChange || savingId === u.id || u.is_superadmin}
                      loading={savingId === u.id}
                      onClick={() => pending && saveRoleType(u, pending)}
                    >
                      Guardar
                    </Button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}

function RoleIcon({ role }: { role: string | null }) {
  if (role === "admin")
    return <ShieldAlert className="h-4 w-4 text-rose-600" aria-hidden />;
  if (role === "user")
    return <ShieldCheck className="h-4 w-4 text-emerald-600" aria-hidden />;
  if (role === "viewer")
    return <Shield className="h-4 w-4 text-blue-600" aria-hidden />;
  return <ShieldX className="h-4 w-4 text-[var(--color-tertiary)]" aria-hidden />;
}
