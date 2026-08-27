"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { Icono } from "@/components/ui/icono";
import { Input } from "@/components/ui/input";
import { MarcaDeDatos, useLectura } from "@/components/ui/marca-de-datos";
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
  // DAT-11: cuándo cambió lo que se está mostrando.
  const leido = useLectura(tenant);
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
      <div>
        <Banner variant="danger">
          Solo los super administradores pueden ver esta página.
        </Banner>
      </div>
    );
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
          { label: "Permisos" },
        ]}
      />

      <header className="flex flex-col gap-1">
        <h1 className="text-[24px] font-semibold tracking-[-0.02em] text-[var(--text-primary)]">
          Overrides de permisos {tenant?.name ? `— ${tenant.name}` : ""}
        </h1>
        {leido && <MarcaDeDatos periodo="vivo" actualizado={leido} />}
        <p className="text-[13px] text-[var(--text-tertiary)]">
          DEC-021 · capa opcional sobre el mapping estático de DEC-020.
          Cada override exige una razón para auditoría.
        </p>
      </header>

      {overrides.length > 0 ? (
        <Banner variant="warning">
          Este tenant tiene <strong>{overrides.length}</strong> override(s)
          activo(s). Cada uno modifica el comportamiento default de
          permisos para el rol indicado.
        </Banner>
      ) : null}
      {error ? <Banner variant="danger">{error}</Banner> : null}
      {notice ? <Banner variant="success">{notice}</Banner> : null}

      <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--relieve-isla)]">
        <h2 className="mb-3 text-[13px] font-semibold text-[var(--text-primary)]">
          Agregar override
        </h2>
        <form onSubmit={handleAdd} className="grid gap-3 sm:grid-cols-5">
          <div>
            <label className="block text-[10.5px] font-semibold uppercase tracking-[0.07em] text-[var(--text-tertiary)]">
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
            <label className="block text-[10.5px] font-semibold uppercase tracking-[0.07em] text-[var(--text-tertiary)]">
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
            <label className="block text-[10.5px] font-semibold uppercase tracking-[0.07em] text-[var(--text-tertiary)]">
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
            <label className="block text-[10.5px] font-semibold uppercase tracking-[0.07em] text-[var(--text-tertiary)]">
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
            <label className="block text-[10.5px] font-semibold uppercase tracking-[0.07em] text-[var(--text-tertiary)]">
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

      <section className="flex flex-col gap-2.5">
        <h2 className="text-[13px] font-semibold text-[var(--text-primary)]">
          Overrides activos
        </h2>
        {loading ? (
          <div className="space-y-2">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
          </div>
        ) : overrides.length === 0 ? (
          <p className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-6 text-center text-[13px] text-[var(--text-tertiary)] shadow-[var(--relieve-isla)]">
            Sin overrides — el tenant usa los permisos default del mapping
            estático.
          </p>
        ) : (
          <div className="overflow-x-auto rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--relieve-isla)]">
            <table className="w-full text-[13px]">
              <thead className="border-b border-[var(--border-default)] bg-[var(--color-subtle)] text-left text-[11px] uppercase tracking-[0.01em] text-[var(--text-secondary)] shadow-[var(--linea-surco)]">
                <tr>
                  <th className="h-8.5 px-3 font-medium">Rol</th>
                  <th className="h-8.5 px-3 font-medium">Módulo</th>
                  <th className="h-8.5 px-3 font-medium">Acción</th>
                  <th className="h-8.5 px-3 font-medium">Granted</th>
                  <th className="h-8.5 px-3 font-medium">Razón</th>
                  <th className="h-8.5 px-3 pr-3.5 text-right font-medium">Acción</th>
                </tr>
              </thead>
              <tbody>
                {overrides.map((o) => (
                  <tr
                    key={o.id}
                    className="border-b border-[var(--border-subtle)] shadow-[var(--linea-surco)] last:border-0"
                  >
                    <td className="px-3 py-2 align-top">
                      <Badge>{o.role_type}</Badge>
                    </td>
                    <td className="px-3 py-2 align-top text-[12px] tracking-[0.01em] text-[var(--text-secondary)]">
                      {o.module}
                    </td>
                    <td className="px-3 py-2 align-top text-[12px] tracking-[0.01em] text-[var(--text-secondary)]">
                      {o.action}
                    </td>
                    <td className="px-3 py-2 align-top">
                      {o.granted ? (
                        <Badge variant="success">otorga</Badge>
                      ) : (
                        <Badge variant="danger">deniega</Badge>
                      )}
                    </td>
                    <td className="px-3 py-2 align-top text-[12.5px] text-[var(--text-secondary)]">
                      {o.reason}
                    </td>
                    <td className="px-3 py-2 pr-3.5 text-right align-top">
                      <Button
                        type="button"
                        size="sm"
                        variant="danger"
                        onClick={() => handleDelete(o)}
                        aria-label="Eliminar override"
                      >
                        <Icono nombre="bin" size={14} />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
