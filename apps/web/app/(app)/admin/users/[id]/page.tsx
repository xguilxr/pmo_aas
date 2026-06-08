"use client";

import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState, type FormEvent } from "react";
import {
  Copy,
  KeyRound,
  Lock,
  PowerOff,
  ShieldOff,
} from "lucide-react";

import { BackLink } from "@/components/back-link";
import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { ApiError } from "@/lib/api";
import {
  deleteUser,
  forcePasswordChange,
  getExcludedOrganizations,
  getUser,
  hardDeleteUser,
  listRoles,
  previewHardDeleteUser,
  resetUserPassword,
  setExcludedOrganizations,
  unlockUser,
  updateUser,
  type AdminRole,
  type AdminUser,
  type RoleType,
} from "@/lib/api/admin";
import { HardDeleteButton } from "@/components/hard-delete-button";
import { listOrganizations, type Organization } from "@/lib/api/organizations";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  createPermissionRequest,
  type CreatePermissionRequestBody,
} from "@/lib/api/permission-requests";

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

type Notice =
  | { kind: "success"; message: string }
  | { kind: "danger"; message: string }
  | null;

function UserDetail() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const searchParams = useSearchParams();
  const userId = params.id;

  const [user, setUser] = useState<AdminUser | null>(null);
  const [roles, setRoles] = useState<AdminRole[]>([]);
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [excludedOrgIds, setExcludedOrgIds] = useState<string[]>([]);
  const [originalExcludedOrgIds, setOriginalExcludedOrgIds] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [isActive, setIsActive] = useState(true);
  const [roleIds, setRoleIds] = useState<string[]>([]);
  const [roleType, setRoleType] = useState<RoleType>("user");

  const [saving, setSaving] = useState(false);
  // US-082 — modal de solicitar cambio de permiso al SuperAdmin.
  const [showPermRequestModal, setShowPermRequestModal] = useState(false);
  const [notice, setNotice] = useState<Notice>(
    searchParams.get("created") === "1"
      ? { kind: "success", message: "Usuario creado correctamente" }
      : null,
  );

  const [resetOpen, setResetOpen] = useState(false);
  const [resetTemp, setResetTemp] = useState<string | null>(null);
  const [resetting, setResetting] = useState(false);
  const [unlocking, setUnlocking] = useState(false);
  const [forcing, setForcing] = useState(false);
  const [deactivating, setDeactivating] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setLoadError(null);
    Promise.all([
      getUser(userId),
      listRoles(),
      listOrganizations({ is_active: true }),
      getExcludedOrganizations(userId).catch(() => ({ organization_ids: [] as string[] })),
    ])
      .then(([u, r, orgList, excl]) => {
        if (cancelled) return;
        setUser(u);
        setRoles(r);
        setOrgs(orgList);
        setExcludedOrgIds(excl.organization_ids);
        setOriginalExcludedOrgIds(excl.organization_ids);
        setFullName(u.full_name);
        setEmail(u.email);
        setIsActive(u.is_active);
        setRoleType((u.role_type as RoleType) ?? "user");
        const ids = r.filter((role) => u.roles.includes(role.name)).map((role) => role.id);
        setRoleIds(ids);
      })
      .catch((err) => {
        if (cancelled) return;
        setLoadError(err instanceof ApiError ? err.message : "No se pudo cargar el usuario");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [userId]);

  const emailValid = useMemo(() => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email), [email]);
  const dirty = useMemo(() => {
    if (!user) return false;
    if (fullName.trim() !== user.full_name) return true;
    if (email.trim().toLowerCase() !== user.email.toLowerCase()) return true;
    if (isActive !== user.is_active) return true;
    if (roleType !== ((user.role_type as RoleType) ?? "user")) return true;
    const currentRoleIds = roles
      .filter((r) => user.roles.includes(r.name))
      .map((r) => r.id)
      .sort();
    const nextRoleIds = [...roleIds].sort();
    if (currentRoleIds.length !== nextRoleIds.length) return true;
    if (currentRoleIds.some((id, i) => id !== nextRoleIds[i])) return true;
    const a = [...originalExcludedOrgIds].sort();
    const b = [...excludedOrgIds].sort();
    if (a.length !== b.length) return true;
    return a.some((id, i) => id !== b[i]);
  }, [
    user,
    roles,
    fullName,
    email,
    isActive,
    roleIds,
    roleType,
    originalExcludedOrgIds,
    excludedOrgIds,
  ]);

  function toggleRole(id: string, checked: boolean) {
    setRoleIds((prev) => (checked ? [...prev, id] : prev.filter((r) => r !== id)));
  }

  async function handleSave(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!user || !dirty || !emailValid || fullName.trim().length < 2) return;
    setSaving(true);
    setNotice(null);
    try {
      const updated = await updateUser(user.id, {
        full_name: fullName.trim(),
        email: email.trim().toLowerCase(),
        is_active: isActive,
        role_ids: roleIds,
        role_type: roleType,
      });
      // Persistir exclusions si cambiaron.
      const a = [...originalExcludedOrgIds].sort();
      const b = [...excludedOrgIds].sort();
      const exclusionsChanged =
        a.length !== b.length || a.some((id, i) => id !== b[i]);
      if (exclusionsChanged) {
        await setExcludedOrganizations(user.id, excludedOrgIds);
        setOriginalExcludedOrgIds(excludedOrgIds);
      }
      setUser(updated);
      setIsActive(updated.is_active);
      setNotice({ kind: "success", message: "Cambios guardados" });
    } catch (err) {
      setNotice({
        kind: "danger",
        message: err instanceof ApiError ? err.message : "No se pudieron guardar los cambios",
      });
    } finally {
      setSaving(false);
    }
  }

  async function handleForcePasswordChange() {
    if (!user) return;
    setForcing(true);
    setNotice(null);
    try {
      await forcePasswordChange(user.id);
      setUser({ ...user, must_change_password: true });
      setNotice({
        kind: "success",
        message: "El usuario deberá cambiar su contraseña en el próximo ingreso.",
      });
    } catch (err) {
      setNotice({
        kind: "danger",
        message:
          err instanceof ApiError
            ? err.message
            : "No se pudo forzar el cambio de contraseña",
      });
    } finally {
      setForcing(false);
    }
  }

  function toggleExcludeOrg(orgId: string, included: boolean) {
    // Checkbox marcado = INCLUIDA → quitar de exclusiones.
    setExcludedOrgIds((prev) =>
      included ? prev.filter((id) => id !== orgId) : Array.from(new Set([...prev, orgId]))
    );
  }

  async function handleResetPassword() {
    if (!user) return;
    setResetting(true);
    try {
      const res = await resetUserPassword(user.id);
      setResetTemp(res.temp_password);
      setUser({ ...user, must_change_password: true });
    } catch (err) {
      setResetOpen(false);
      setNotice({
        kind: "danger",
        message:
          err instanceof ApiError ? err.message : "No se pudo resetear la contraseña",
      });
    } finally {
      setResetting(false);
    }
  }

  async function handleUnlock() {
    if (!user) return;
    setUnlocking(true);
    setNotice(null);
    try {
      await unlockUser(user.id);
      setNotice({ kind: "success", message: "Cuenta desbloqueada" });
    } catch (err) {
      setNotice({
        kind: "danger",
        message: err instanceof ApiError ? err.message : "No se pudo desbloquear la cuenta",
      });
    } finally {
      setUnlocking(false);
    }
  }

  async function handleDeactivate() {
    if (!user) return;
    setDeactivating(true);
    setNotice(null);
    try {
      await deleteUser(user.id);
      router.replace("/admin/users");
    } catch (err) {
      setConfirmDelete(false);
      setNotice({
        kind: "danger",
        message: err instanceof ApiError ? err.message : "No se pudo desactivar el usuario",
      });
      setDeactivating(false);
    }
  }

  function copyTempPassword() {
    if (!resetTemp) return;
    void navigator.clipboard?.writeText(resetTemp);
  }

  if (loadError) {
    return (
      <div className="mx-auto max-w-2xl space-y-4">
        <BackLink fallbackHref="/admin/users" />
        <Banner variant="danger">{loadError}</Banner>
      </div>
    );
  }

  if (loading || !user) {
    return (
      <div className="mx-auto max-w-2xl space-y-4">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <BackLink fallbackHref="/admin/users" />
        <div className="mt-2 flex flex-wrap items-end justify-between gap-2">
          <div>
            <h1 className="text-2xl font-semibold text-[var(--color-primary)]">{user.full_name}</h1>
            <p className="text-sm text-[var(--color-tertiary)]">
              {user.username} · {user.email}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-1.5">
            {user.is_active ? (
              <Badge variant="success">Activo</Badge>
            ) : (
              <Badge variant="danger">Inactivo</Badge>
            )}
            {user.must_change_password ? <Badge variant="warning">Cambio pendiente</Badge> : null}
            <Badge>Último ingreso: {formatDate(user.last_login)}</Badge>
            {/* US-082 — solicitar cambio de permiso al SuperAdmin. */}
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setShowPermRequestModal(true)}
            >
              Solicitar cambio de permiso
            </Button>
          </div>
        </div>
      </div>

      {/* US-082 — modal para crear ticket. */}
      <PermissionRequestModal
        open={showPermRequestModal}
        onClose={() => setShowPermRequestModal(false)}
        targetUserId={user.id}
        targetUserLabel={user.full_name || user.email}
      />

      {notice ? (
        <Banner variant={notice.kind === "success" ? "success" : "danger"}>
          {notice.message}
        </Banner>
      ) : null}

      <form
        onSubmit={handleSave}
        noValidate
        className="space-y-5 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-sm)]"
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="full_name" className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]">
              Nombre completo
            </label>
            <Input
              id="full_name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              disabled={saving}
              required
            />
          </div>
          <div>
            <label htmlFor="email" className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]">
              Correo
            </label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={saving}
              invalid={email.length > 0 && !emailValid}
              required
            />
          </div>
        </div>

        <div>
          <p className="mb-2 text-sm font-medium text-[var(--color-secondary)]">Roles</p>
          {roles.length === 0 ? (
            <p className="text-xs text-[var(--color-tertiary)]">
              Los permisos se gestionan por <Link href="/admin/permissions" className="underline">capability del rol</Link>{" "}
              (admin/user). La asignación se hará desde esta página en US-078.
            </p>
          ) : (
            <div className="grid gap-2 sm:grid-cols-2">
              {roles.map((r) => {
                const checked = roleIds.includes(r.id);
                return (
                  <label
                    key={r.id}
                    className="flex cursor-pointer items-start gap-2 rounded-[var(--radius-md)] border border-[var(--border-default)] p-3 hover:bg-[var(--color-subtle)]"
                  >
                    <Checkbox
                      checked={checked}
                      onChange={(e) => toggleRole(r.id, e.target.checked)}
                      disabled={saving}
                    />
                    <div className="flex-1">
                      <div className="text-sm font-medium text-[var(--color-primary)]">
                        {r.name}
                      </div>
                      {r.description ? (
                        <div className="text-xs text-[var(--color-tertiary)]">{r.description}</div>
                      ) : null}
                    </div>
                  </label>
                );
              })}
            </div>
          )}
        </div>

        <div>
          <label htmlFor="role_type" className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]">
            Rol del tenant
          </label>
          <select
            id="role_type"
            value={roleType}
            onChange={(e) => setRoleType(e.target.value as RoleType)}
            disabled={saving}
            className="w-full rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-surface)] px-3 py-2 text-sm"
          >
            <option value="user">PM — operador del tenant (visibilidad por asignación)</option>
            <option value="pm_sr">PM Sr — acceso admin completo al tenant</option>
            <option value="admin">Admin — metaconfig + acceso admin completo</option>
          </select>
          <p className="mt-1 text-xs text-[var(--color-tertiary)]">
            <Link href="/admin/permissions" className="underline">
              Ver qué hace cada rol
            </Link>
          </p>
        </div>

        <div>
          <p className="mb-2 text-sm font-medium text-[var(--color-secondary)]">
            Acceso a organizaciones
          </p>
          <p className="mb-2 text-xs text-[var(--color-tertiary)]">
            Por defecto el usuario tiene acceso a todas las organizaciones del
            tenant. Desmarca para excluirlo de orgs específicas.
          </p>
          {orgs.length === 0 ? (
            <p className="text-xs text-[var(--color-tertiary)]">
              Sin organizaciones activas en el tenant.
            </p>
          ) : (
            <div className="grid gap-1.5 sm:grid-cols-2">
              {orgs.map((o) => {
                const included = !excludedOrgIds.includes(o.id);
                return (
                  <label
                    key={o.id}
                    className="flex cursor-pointer items-center gap-2 rounded-[var(--radius-md)] border border-[var(--border-default)] px-3 py-2 hover:bg-[var(--color-subtle)]"
                  >
                    <Checkbox
                      checked={included}
                      onChange={(e) => toggleExcludeOrg(o.id, e.target.checked)}
                      disabled={saving}
                    />
                    <span className="text-sm text-[var(--color-primary)]">
                      {o.name}
                    </span>
                  </label>
                );
              })}
            </div>
          )}
        </div>

        <Switch
          id="is_active"
          checked={isActive}
          onChange={setIsActive}
          disabled={saving}
          label="Cuenta activa"
        />

        <div className="flex justify-end gap-2 border-t border-[var(--border-default)] pt-4">
          <Button
            type="button"
            variant="secondary"
            disabled={saving || !dirty}
            onClick={() => {
              setFullName(user.full_name);
              setEmail(user.email);
              setIsActive(user.is_active);
              setRoleIds(roles.filter((r) => user.roles.includes(r.name)).map((r) => r.id));
              setRoleType((user.role_type as RoleType) ?? "user");
              setExcludedOrgIds(originalExcludedOrgIds);
            }}
          >
            Descartar
          </Button>
          <Button type="submit" loading={saving} disabled={!dirty || !emailValid}>
            Guardar cambios
          </Button>
        </div>
      </form>

      <section className="space-y-3 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-sm)]">
        <header>
          <h2 className="text-base font-semibold text-[var(--color-primary)]">Acciones</h2>
          <p className="text-xs text-[var(--color-tertiary)]">
            Resetear, desbloquear o desactivar esta cuenta.
          </p>
        </header>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          <Button
            type="button"
            variant="secondary"
            onClick={() => {
              setResetTemp(null);
              setResetOpen(true);
            }}
          >
            <KeyRound className="h-4 w-4" aria-hidden />
            Resetear contraseña
          </Button>
          <Button
            type="button"
            variant="secondary"
            onClick={handleForcePasswordChange}
            loading={forcing}
            disabled={user.must_change_password}
            title={
              user.must_change_password
                ? "El usuario ya tiene un cambio pendiente"
                : "Marca al usuario para que cambie su contraseña en el próximo ingreso (sin tocar la actual)."
            }
          >
            <KeyRound className="h-4 w-4" aria-hidden />
            Forzar cambio próximo login
          </Button>
          <Button
            type="button"
            variant="secondary"
            onClick={handleUnlock}
            loading={unlocking}
          >
            <Lock className="h-4 w-4" aria-hidden />
            Desbloquear
          </Button>
          <Button
            type="button"
            variant="danger"
            onClick={() => setConfirmDelete(true)}
            disabled={!user.is_active}
          >
            {user.is_active ? (
              <>
                <PowerOff className="h-4 w-4" aria-hidden />
                Desactivar
              </>
            ) : (
              <>
                <ShieldOff className="h-4 w-4" aria-hidden />
                Inactivo
              </>
            )}
          </Button>
          {!user.is_active ? (
            <HardDeleteButton
              preview={() => previewHardDeleteUser(user.id)}
              hardDelete={(slug) => hardDeleteUser(user.id, slug)}
              onDeleted={() => {
                window.location.assign("/admin/users");
              }}
              entityLabel="Usuario"
            />
          ) : null}
        </div>
      </section>

      <Modal
        open={resetOpen}
        onClose={() => setResetOpen(false)}
        title={resetTemp ? "Contraseña temporal" : "Resetear contraseña"}
        description={
          resetTemp
            ? "Cópiala ahora. No se volverá a mostrar."
            : "Se generará una contraseña temporal y se forzará el cambio en el próximo ingreso."
        }
        footer={
          resetTemp ? (
            <Button onClick={() => setResetOpen(false)}>Cerrar</Button>
          ) : (
            <>
              <Button variant="secondary" onClick={() => setResetOpen(false)} disabled={resetting}>
                Cancelar
              </Button>
              <Button onClick={handleResetPassword} loading={resetting}>
                Generar
              </Button>
            </>
          )
        }
      >
        {resetTemp ? (
          <div className="flex items-center gap-2 rounded-[var(--radius-md)] border border-[var(--border-strong)] bg-[var(--color-subtle)] p-3">
            <code className="flex-1 break-all font-mono text-sm">{resetTemp}</code>
            <button
              type="button"
              onClick={copyTempPassword}
              aria-label="Copiar"
              className="inline-flex h-8 w-8 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-secondary)] hover:bg-[var(--color-muted)]"
            >
              <Copy className="h-4 w-4" aria-hidden />
            </button>
          </div>
        ) : (
          <p className="text-sm text-[var(--color-secondary)]">
            ¿Confirmas resetear la contraseña de <strong>{user.full_name}</strong>?
          </p>
        )}
      </Modal>

      <Modal
        open={confirmDelete}
        onClose={() => setConfirmDelete(false)}
        title="Desactivar usuario"
        description="La cuenta queda inactiva (soft delete). Se puede reactivar editando el switch."
        footer={
          <>
            <Button
              variant="secondary"
              onClick={() => setConfirmDelete(false)}
              disabled={deactivating}
            >
              Cancelar
            </Button>
            <Button variant="danger" onClick={handleDeactivate} loading={deactivating}>
              Desactivar
            </Button>
          </>
        }
      >
        <p className="text-sm text-[var(--color-secondary)]">
          ¿Confirmas desactivar a <strong>{user.full_name}</strong>?
        </p>
      </Modal>
    </div>
  );
}

export default function UserDetailPage() {
  return (
    <Suspense
      fallback={
        <div className="mx-auto max-w-2xl space-y-4">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-64 w-full" />
        </div>
      }
    >
      <UserDetail />
    </Suspense>
  );
}

/**
 * US-082 — modal "Solicitar cambio de permiso" al SuperAdmin.
 * Inputs: módulo, acción, otorgar/revocar, motivo (≥10 chars). Al
 * guardar hace POST a /api/v1/permission-requests y notifica
 * automáticamente al superadmin (in-app + email vía Resend).
 */
function PermissionRequestModal({
  open,
  onClose,
  targetUserId,
  targetUserLabel,
}: {
  open: boolean;
  onClose: () => void;
  targetUserId: string;
  targetUserLabel: string;
}) {
  const [moduleName, setModuleName] = useState("tasks");
  const [action, setAction] = useState("delete");
  const [grant, setGrant] = useState(true);
  const [reason, setReason] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (reason.trim().length < 10) {
      setError("El motivo debe tener al menos 10 caracteres.");
      return;
    }
    setSaving(true);
    try {
      const body: CreatePermissionRequestBody = {
        target_user_id: targetUserId,
        module: moduleName.trim().toLowerCase(),
        action: action.trim().toLowerCase(),
        requested_grant: grant,
        reason: reason.trim(),
      };
      await createPermissionRequest(body);
      setSuccess(true);
      setReason("");
      setTimeout(() => {
        setSuccess(false);
        onClose();
      }, 2_000);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "No se pudo crear el ticket",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Solicitar cambio de permiso">
      <form onSubmit={submit} className="space-y-4">
        <p className="text-sm text-[var(--color-secondary)]">
          Estás pidiendo al SuperAdmin un cambio de permiso para{" "}
          <strong>{targetUserLabel}</strong>. Recibirás respuesta por email +
          notificación in-app.
        </p>

        {success ? (
          <Banner variant="success">
            Ticket creado. El SuperAdmin recibirá notificación por email.
          </Banner>
        ) : null}
        {error ? <Banner variant="danger">{error}</Banner> : null}

        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-xs font-medium uppercase text-[var(--color-tertiary)]">
              Módulo
            </label>
            <Input
              value={moduleName}
              onChange={(e) => setModuleName(e.target.value)}
              placeholder="ej. tasks"
              required
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium uppercase text-[var(--color-tertiary)]">
              Acción
            </label>
            <Input
              value={action}
              onChange={(e) => setAction(e.target.value)}
              placeholder="ej. delete"
              required
            />
          </div>
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium uppercase text-[var(--color-tertiary)]">
            Tipo de cambio
          </label>
          <Select
            value={grant ? "grant" : "revoke"}
            onChange={(e) => setGrant(e.target.value === "grant")}
          >
            <option value="grant">Otorgar el permiso</option>
            <option value="revoke">Revocar el permiso</option>
          </Select>
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium uppercase text-[var(--color-tertiary)]">
            Motivo (mínimo 10 caracteres)
          </label>
          <Textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={3}
            placeholder="Explica por qué este usuario necesita este permiso puntual..."
            required
          />
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <Button
            type="button"
            variant="secondary"
            onClick={onClose}
            disabled={saving}
          >
            Cancelar
          </Button>
          <Button type="submit" loading={saving} disabled={saving || success}>
            Enviar solicitud
          </Button>
        </div>
      </form>
    </Modal>
  );
}
