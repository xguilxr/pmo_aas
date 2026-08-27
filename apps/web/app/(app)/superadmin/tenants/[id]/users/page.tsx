"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { MarcaDeDatos, useLectura } from "@/components/ui/marca-de-datos";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import { getStoredUser } from "@/lib/auth-storage";
import { confirmarDestructivo } from "@/lib/confirmar";
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
  // DAT-11: cuándo cambió lo que se está mostrando.
  const leido = useLectura(tenant);
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
      <div>
        <Banner variant="danger">
          Solo los super administradores pueden ver esta página.
        </Banner>
      </div>
    );
  }

  async function saveRoleType(user: SuperadminUserRow, next: RoleType) {
    if (savingId) return;
    if (
      !confirmarDestructivo({
        objeto: `el rol de ${user.email} (${user.role_type ?? "sin rol"} → ${next})`,
        consecuencia: "Cambia lo que puede ver y hacer en toda la plataforma, de inmediato.",
        reversibilidad: "definitiva",
      })
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
    <div className="space-y-6">
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

      <header className="flex flex-col gap-1">
        <h1 className="text-[24px] font-semibold tracking-[-0.02em] text-[var(--text-primary)]">
          Usuarios del tenant {tenant?.name ? `— ${tenant.name}` : ""}
        </h1>
        {leido && <MarcaDeDatos periodo="vivo" actualizado={leido} />}
        <p className="text-[13px] text-[var(--text-tertiary)]">
          Gestión del <code className="font-mono">role_type</code> (admin / user / viewer). Útil
          como vía de rescate cuando un admin pierde acceso (ver BUG-031).
        </p>
      </header>

      <section className="flex flex-wrap gap-2">
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
          className="w-40"
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
        <p className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-6 text-center text-[13px] text-[var(--text-tertiary)] shadow-[var(--relieve-isla)]">
          No hay usuarios para los filtros aplicados.
        </p>
      ) : (
        <div className="overflow-x-auto rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--relieve-isla)]">
          <table className="w-full text-[13px]">
            <thead className="border-b border-[var(--border-default)] bg-[var(--color-subtle)] text-left text-[11px] uppercase tracking-[0.01em] text-[var(--text-secondary)] shadow-[var(--linea-surco)]">
              <tr>
                <th className="h-8.5 px-3 font-medium">Usuario</th>
                <th className="h-8.5 px-3 font-medium">Email</th>
                <th className="h-8.5 px-3 font-medium">Estado</th>
                <th className="h-8.5 px-3 font-medium">Role type</th>
                <th className="h-8.5 px-3 pr-3.5 text-right font-medium">Acción</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => {
                const pending = pendingChanges[u.id];
                const current = (u.role_type ?? "") as RoleType | "";
                const next = pending ?? current;
                const hasChange = pending !== undefined && pending !== current;
                return (
                  <tr
                    key={u.id}
                    className="border-b border-[var(--border-subtle)] shadow-[var(--linea-surco)] last:border-0"
                  >
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-2">
                        <span className="overflow-hidden text-ellipsis whitespace-nowrap font-medium text-[var(--text-primary)]">
                          {u.full_name || u.username}
                        </span>
                        {u.is_superadmin ? (
                          <Badge variant="warning">superadmin</Badge>
                        ) : null}
                      </div>
                      <div className="text-[11px] text-[var(--text-tertiary)]">
                        @{u.username}
                      </div>
                    </td>
                    <td className="px-3 py-2 text-[12px] tracking-[0.01em] text-[var(--text-secondary)]">
                      {u.email}
                    </td>
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
                        className="w-36"
                      >
                        <option value="">— sin role_type —</option>
                        <option value="admin">Admin</option>
                        <option value="user">User</option>
                        <option value="viewer">Viewer</option>
                      </Select>
                    </td>
                    <td className="px-3 py-2 pr-3.5 text-right">
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
        </div>
      )}
    </div>
  );
}
