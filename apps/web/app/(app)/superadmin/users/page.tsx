"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { CheckCircle2, Pencil, PowerOff, Search, Shield, User } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import {
  listSuperadminUsers,
  toggleSuperadminUserActive,
  updateSuperadminUser,
  updateSuperadminUserRoleType,
  type SuperadminRoleType,
  type SuperadminUserRow,
} from "@/lib/api/superadmin-panel";

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("es-MX", {
      year: "numeric",
      month: "short",
      day: "2-digit",
    });
  } catch {
    return iso;
  }
}

export default function SuperadminUsersPage() {
  const [rows, setRows] = useState<SuperadminUserRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [activeFilter, setActiveFilter] = useState<"all" | "active" | "inactive">("all");
  const [editing, setEditing] = useState<SuperadminUserRow | null>(null);
  const [toggling, setToggling] = useState<SuperadminUserRow | null>(null);

  const load = useCallback(async (search: string, filter: typeof activeFilter) => {
    setLoading(true);
    setError(null);
    try {
      const res = await listSuperadminUsers({
        q: search || undefined,
        is_active:
          filter === "active" ? true : filter === "inactive" ? false : undefined,
        limit: 100,
      });
      setRows(res.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar usuarios");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const t = setTimeout(() => void load(q, activeFilter), q ? 300 : 0);
    return () => clearTimeout(t);
  }, [q, activeFilter, load]);

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
          Usuarios
        </h1>
        <p className="mt-1 text-sm text-[var(--color-tertiary)]">
          Lista global de usuarios de todos los tenants. Acciones auditadas con <code>scope=platform</code>.
        </p>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}
      {notice ? <Banner variant="success">{notice}</Banner> : null}

      <section className="flex flex-wrap items-center gap-2">
        <div className="relative flex-1 min-w-[240px]">
          <Search className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-[var(--color-tertiary)]" aria-hidden />
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Buscar por username, email o nombre"
            className="pl-8"
          />
        </div>
        <div className="flex gap-1">
          {(["all", "active", "inactive"] as const).map((f) => (
            <Button
              key={f}
              type="button"
              variant={activeFilter === f ? "primary" : "secondary"}
              size="sm"
              onClick={() => setActiveFilter(f)}
            >
              {f === "all" ? "Todos" : f === "active" ? "Activos" : "Inactivos"}
            </Button>
          ))}
        </div>
      </section>

      <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]">
        {loading ? (
          <div className="space-y-2 p-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        ) : rows.length === 0 ? (
          <div className="p-10 text-center text-sm text-[var(--color-tertiary)]">
            Sin usuarios que coincidan con los filtros.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border-subtle)] text-left text-xs uppercase tracking-wide text-[var(--color-tertiary)]">
                <th className="px-4 py-2">Usuario</th>
                <th className="px-4 py-2">Tenant</th>
                <th className="px-4 py-2">Roles</th>
                <th className="px-4 py-2">Estado</th>
                <th className="px-4 py-2">Creado</th>
                <th className="px-4 py-2 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((u) => (
                <tr key={u.id} className="border-b border-[var(--border-subtle)] last:border-0">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <User className="h-4 w-4 text-[var(--color-tertiary)]" aria-hidden />
                      <div>
                        <div className="font-medium text-[var(--color-primary)]">
                          {u.full_name || u.username}
                        </div>
                        <div className="text-xs text-[var(--color-tertiary)]">
                          @{u.username} · {u.email}
                        </div>
                      </div>
                      {u.is_superadmin ? (
                        <Badge variant="warning">
                          <Shield className="mr-1 h-3 w-3" aria-hidden />
                          Super
                        </Badge>
                      ) : null}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-xs text-[var(--color-secondary)]">
                    {u.tenant_slug ?? "—"}
                  </td>
                  <td className="px-4 py-3 text-xs">
                    {u.roles.length === 0 ? (
                      <span className="text-[var(--color-tertiary)]">—</span>
                    ) : (
                      <div className="flex flex-wrap gap-1">
                        {u.roles.map((r) => (
                          <Badge key={r} variant="neutral">{r}</Badge>
                        ))}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {u.is_active ? (
                      <Badge variant="success">
                        <CheckCircle2 className="mr-1 h-3 w-3" aria-hidden />
                        Activo
                      </Badge>
                    ) : (
                      <Badge variant="danger">Inactivo</Badge>
                    )}
                  </td>
                  <td className="px-4 py-3 text-xs text-[var(--color-tertiary)]">
                    {fmtDate(u.created_at)}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-1">
                      <Button
                        type="button"
                        variant="secondary"
                        size="sm"
                        onClick={() => setEditing(u)}
                        disabled={u.is_superadmin}
                      >
                        <Pencil className="h-3.5 w-3.5" aria-hidden /> Editar
                      </Button>
                      <Button
                        type="button"
                        variant={u.is_active ? "danger" : "primary"}
                        size="sm"
                        onClick={() => setToggling(u)}
                        disabled={u.is_superadmin}
                      >
                        <PowerOff className="h-3.5 w-3.5" aria-hidden />
                        {u.is_active ? "Desactivar" : "Activar"}
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {editing ? (
        <EditUserModal
          user={editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            setNotice("Usuario actualizado");
            void load(q, activeFilter);
          }}
          onError={(msg) => setError(msg)}
        />
      ) : null}

      {toggling ? (
        <ToggleActiveModal
          user={toggling}
          onClose={() => setToggling(null)}
          onDone={() => {
            setToggling(null);
            setNotice("Estado del usuario actualizado");
            void load(q, activeFilter);
          }}
          onError={(msg) => setError(msg)}
        />
      ) : null}
    </div>
  );
}

function EditUserModal({
  user,
  onClose,
  onSaved,
  onError,
}: {
  user: SuperadminUserRow;
  onClose: () => void;
  onSaved: () => void;
  onError: (msg: string) => void;
}) {
  const [fullName, setFullName] = useState(user.full_name ?? "");
  const [email, setEmail] = useState(user.email);
  const [username, setUsername] = useState(user.username);
  const [roleType, setRoleType] = useState<SuperadminRoleType | "">(
    user.role_type ?? "",
  );
  const [saving, setSaving] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      // BUG-033: role_type tiene endpoint propio (US-072 audit-log).
      if (roleType && roleType !== (user.role_type ?? "")) {
        await updateSuperadminUserRoleType(user.id, roleType);
      }
      await updateSuperadminUser(user.id, {
        full_name: fullName !== (user.full_name ?? "") ? fullName || undefined : undefined,
        email: email !== user.email ? email : undefined,
        username: username !== user.username ? username : undefined,
      });
      onSaved();
    } catch (err) {
      onError(err instanceof ApiError ? err.message : "Error al guardar");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={`Editar ${user.username}`}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancelar
          </Button>
          <Button onClick={submit as unknown as () => void} loading={saving}>
            Guardar
          </Button>
        </>
      }
    >
      <form onSubmit={submit} className="space-y-3">
        <Field label="Nombre completo">
          <Input value={fullName} onChange={(e) => setFullName(e.target.value)} />
        </Field>
        <Field label="Email">
          <Input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </Field>
        <Field label="Username">
          <Input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            minLength={2}
            maxLength={64}
          />
        </Field>
        {user.is_superadmin ? null : (
          <Field label="Rol">
            <select
              value={roleType}
              onChange={(e) => setRoleType(e.target.value as SuperadminRoleType | "")}
              className="block w-full rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-surface)] px-3 py-2 text-sm text-[var(--color-primary)]"
            >
              <option value="">— sin asignar —</option>
              <option value="admin">admin</option>
              <option value="user">user</option>
              <option value="viewer">viewer</option>
            </select>
          </Field>
        )}
      </form>
    </Modal>
  );
}

function ToggleActiveModal({
  user,
  onClose,
  onDone,
  onError,
}: {
  user: SuperadminUserRow;
  onClose: () => void;
  onDone: () => void;
  onError: (msg: string) => void;
}) {
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);

  async function confirm() {
    setBusy(true);
    try {
      await toggleSuperadminUserActive(user.id, reason);
      onDone();
    } catch (err) {
      onError(err instanceof ApiError ? err.message : "Error al cambiar estado");
    } finally {
      setBusy(false);
    }
  }

  const action = user.is_active ? "Desactivar" : "Activar";

  return (
    <Modal
      open
      onClose={onClose}
      title={`${action} ${user.username}`}
      description="La acción queda registrada en el audit log de plataforma."
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={busy}>
            Cancelar
          </Button>
          <Button
            variant={user.is_active ? "danger" : "primary"}
            onClick={() => void confirm()}
            loading={busy}
            disabled={reason.trim().length < 5}
          >
            {action}
          </Button>
        </>
      }
    >
      <Field label="Motivo (mínimo 5 caracteres)">
        <Input
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Ej. Usuario reportado por el tenant como sospechoso"
        />
      </Field>
    </Modal>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]">
        {label}
      </span>
      {children}
    </label>
  );
}
