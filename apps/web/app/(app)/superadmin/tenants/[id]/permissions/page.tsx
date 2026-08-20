"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { AlertTriangle, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api";
import { getStoredUser } from "@/lib/auth-storage";
import { confirmarDestructivo } from "@/lib/confirmar";
import {
  deletePermissionOverride,
  getTenantDetail,
  listPermissionOverrides,
  upsertPermissionOverrides,
  type PermissionOverride,
  type TenantDetail,
} from "@/lib/api/superadmin";

type RoleType = "admin" | "user" | "viewer";

export default function SuperadminTenantPermissionsPage() {
  const params = useParams<{ id: string }>();
  const tenantId = params.id;
  const me = getStoredUser();

  const [tenant, setTenant] = useState<TenantDetail["tenant"] | null>(null);
  const [overrides, setOverrides] = useState<PermissionOverride[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // Form para nuevo override.
  const [formRoleType, setFormRoleType] = useState<RoleType>("user");
  const [formModule, setFormModule] = useState("");
  const [formAction, setFormAction] = useState("read");
  const [formGranted, setFormGranted] = useState(true);
  const [formReason, setFormReason] = useState("");

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const [t, o] = await Promise.all([
        getTenantDetail(tenantId),
        listPermissionOverrides(tenantId),
      ]);
      setTenant(t.tenant);
      setOverrides(o);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "No se pudieron cargar los overrides",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (tenantId) refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenantId]);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!formModule.trim() || !formReason.trim()) {
      setError("Module y reason son obligatorios.");
      return;
    }
    if (saving) return;
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const updated = await upsertPermissionOverrides(tenantId, [
        {
          role_type: formRoleType,
          module: formModule.trim(),
          action: formAction.trim(),
          granted: formGranted,
          reason: formReason.trim(),
        },
      ]);
      setOverrides(updated);
      setFormModule("");
      setFormReason("");
      setNotice("Override aplicado.");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "No se pudo aplicar el override",
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(o: PermissionOverride) {
    if (
      !confirmarDestructivo({
        objeto: `el override de ${o.role_type} sobre ${o.module}.${o.action}`,
        consecuencia: "El permiso vuelve al valor por defecto del mapeo de roles.",
        reversibilidad: "definitiva",
      })
    ) {
      return;
    }
    try {
      await deletePermissionOverride(tenantId, o.id);
      await refresh();
      setNotice("Override eliminado.");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "No se pudo eliminar el override",
      );
    }
  }

  if (me && !me.is_superadmin) {
    return (
      <div className="p-6">
        <Banner variant="danger">
          Solo los super administradores pueden ver esta página.
        </Banner>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <Breadcrumb
        items={[
          { label: "Superadmin", href: "/superadmin" },
          { label: "Tenants", href: "/superadmin/tenants" },
          {
            label: tenant?.name ?? "Tenant",
            href: `/superadmin/tenants/${tenantId}`,
          },
          { label: "Permisos" },
        ]}
      />

      <header>
        <h1 className="text-2xl font-semibold text-[var(--color-primary)]">
          Overrides de permisos {tenant?.name ? `— ${tenant.name}` : ""}
        </h1>
        <p className="mt-1 text-sm text-[var(--color-tertiary)]">
          DEC-021 · capa opcional sobre el mapping estático de DEC-020.
          Cada override exige una razón para auditoría.
        </p>
      </header>

      {overrides.length > 0 ? (
        <Banner variant="warning">
          <AlertTriangle className="mr-2 inline h-4 w-4" aria-hidden />
          Este tenant tiene <strong>{overrides.length}</strong> override(s)
          activo(s). Cada uno modifica el comportamiento default de
          permisos para el rol indicado.
        </Banner>
      ) : null}
      {error ? <Banner variant="danger">{error}</Banner> : null}
      {notice ? <Banner variant="success">{notice}</Banner> : null}

      <section className="rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--color-surface)] p-6">
        <h2 className="mb-3 text-base font-semibold text-[var(--color-primary)]">
          Agregar override
        </h2>
        <form onSubmit={handleAdd} className="grid gap-3 sm:grid-cols-5">
          <div>
            <label className="block text-xs font-semibold uppercase text-[var(--color-tertiary)]">
              Rol
            </label>
            <Select
              value={formRoleType}
              onChange={(e) => setFormRoleType(e.target.value as RoleType)}
              className="mt-1"
            >
              <option value="admin">admin</option>
              <option value="user">user</option>
              <option value="viewer">viewer</option>
            </Select>
          </div>
          <div>
            <label className="block text-xs font-semibold uppercase text-[var(--color-tertiary)]">
              Módulo
            </label>
            <Input
              value={formModule}
              onChange={(e) => setFormModule(e.target.value)}
              placeholder="ej. tasks"
              required
              className="mt-1"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold uppercase text-[var(--color-tertiary)]">
              Acción
            </label>
            <Select
              value={formAction}
              onChange={(e) => setFormAction(e.target.value)}
              className="mt-1"
            >
              <option value="read">read</option>
              <option value="create">create</option>
              <option value="update">update</option>
              <option value="delete">delete</option>
              <option value="approve">approve</option>
              <option value="reject">reject</option>
            </Select>
          </div>
          <div>
            <label className="block text-xs font-semibold uppercase text-[var(--color-tertiary)]">
              Granted
            </label>
            <Select
              value={formGranted ? "yes" : "no"}
              onChange={(e) => setFormGranted(e.target.value === "yes")}
              className="mt-1"
            >
              <option value="yes">Sí (otorgar)</option>
              <option value="no">No (denegar)</option>
            </Select>
          </div>
          <div className="self-end">
            <Button type="submit" loading={saving} disabled={saving}>
              Aplicar
            </Button>
          </div>
          <div className="sm:col-span-5">
            <label className="block text-xs font-semibold uppercase text-[var(--color-tertiary)]">
              Razón (obligatoria — queda en audit log)
            </label>
            <Textarea
              value={formReason}
              onChange={(e) => setFormReason(e.target.value)}
              required
              rows={2}
              placeholder="Ej.: tenant Globex pidió permitir delete de tareas a usuarios regulares por flujo interno aprobado por…"
              className="mt-1"
            />
          </div>
        </form>
      </section>

      <section>
        <h2 className="mb-3 text-base font-semibold text-[var(--color-primary)]">
          Overrides activos
        </h2>
        {loading ? (
          <div className="space-y-2">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
          </div>
        ) : overrides.length === 0 ? (
          <p className="rounded-md border border-[var(--border-default)] bg-[var(--color-surface)] p-6 text-center text-sm text-[var(--color-tertiary)]">
            Sin overrides — el tenant usa los permisos default del mapping
            estático.
          </p>
        ) : (
          <table className="w-full overflow-hidden rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--color-surface)] text-sm">
            <thead className="bg-[var(--color-subtle)] text-left text-xs uppercase text-[var(--color-tertiary)]">
              <tr>
                <th className="px-3 py-2">Rol</th>
                <th className="px-3 py-2">Módulo</th>
                <th className="px-3 py-2">Acción</th>
                <th className="px-3 py-2">Granted</th>
                <th className="px-3 py-2">Razón</th>
                <th className="px-3 py-2 text-right">Acción</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-default)]">
              {overrides.map((o) => (
                <tr key={o.id} className="align-top">
                  <td className="px-3 py-2">
                    <Badge>{o.role_type}</Badge>
                  </td>
                  <td className="px-3 py-2 font-mono text-xs">{o.module}</td>
                  <td className="px-3 py-2 font-mono text-xs">{o.action}</td>
                  <td className="px-3 py-2">
                    {o.granted ? (
                      <Badge variant="success">otorga</Badge>
                    ) : (
                      <Badge variant="danger">deniega</Badge>
                    )}
                  </td>
                  <td className="px-3 py-2 text-xs text-[var(--color-secondary)]">
                    {o.reason}
                  </td>
                  <td className="px-3 py-2 text-right">
                    <Button
                      type="button"
                      size="sm"
                      variant="danger"
                      onClick={() => handleDelete(o)}
                      aria-label="Eliminar override"
                    >
                      <Trash2 className="h-4 w-4" aria-hidden />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
