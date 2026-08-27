"use client";

import { useEffect, useState } from "react";

import { Banner } from "@/components/ui/banner";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import { getStoredUser } from "@/lib/auth-storage";
import { confirmarDestructivo } from "@/lib/confirmar";
import {
  getSuperadminMe,
  updateSuperadminMe,
  type SuperadminMe,
} from "@/lib/api/superadmin";

type EmailClashInfo = {
  user_id: string;
  email: string;
  username: string;
  tenant_id: string | null;
};

export default function SuperadminMePage() {
  const me = getStoredUser();
  const [profile, setProfile] = useState<SuperadminMe | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  // BUG-032: cuando el backend devuelve 409 con code=EMAIL_TAKEN_OFFER_TAKEOVER,
  // guardamos el clash + ofrecemos botón para reintentar con
  // force_takeover_email=true.
  const [emailClash, setEmailClash] = useState<EmailClashInfo | null>(null);

  // Editable fields.
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newPasswordConfirm, setNewPasswordConfirm] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getSuperadminMe()
      .then((p) => {
        if (cancelled) return;
        setProfile(p);
        setEmail(p.email);
        setFullName(p.full_name ?? "");
      })
      .catch((err) => {
        if (!cancelled) {
          setError(
            err instanceof ApiError
              ? err.message
              : "No se pudo cargar el perfil",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function submit(forceTakeoverEmail = false) {
    setError(null);
    setNotice(null);
    setEmailClash(null);

    if (newPassword && newPassword !== newPasswordConfirm) {
      setError("La nueva contraseña y su confirmación no coinciden.");
      return;
    }
    if (!currentPassword) {
      setError("Ingresa tu contraseña actual para confirmar el cambio.");
      return;
    }

    setSaving(true);
    try {
      const body: Parameters<typeof updateSuperadminMe>[0] = {
        current_password: currentPassword,
      };
      if (profile && email !== profile.email) body.email = email.trim();
      if (profile && fullName !== (profile.full_name ?? ""))
        body.full_name = fullName.trim();
      if (newPassword) body.new_password = newPassword;
      if (forceTakeoverEmail) body.force_takeover_email = true;

      if (
        body.email === undefined &&
        body.full_name === undefined &&
        body.new_password === undefined
      ) {
        setNotice("No hay cambios para guardar.");
        return;
      }

      const updated = await updateSuperadminMe(body);
      setProfile(updated);
      setEmail(updated.email);
      setFullName(updated.full_name ?? "");
      setCurrentPassword("");
      setNewPassword("");
      setNewPasswordConfirm("");
      setNotice(
        forceTakeoverEmail
          ? "Email tomado. El user en conflicto fue renombrado a `released.<ts>.<old>` para liberarlo. Logueate con el email nuevo."
          : body.email
            ? "Perfil actualizado. La próxima vez logueate con el email nuevo."
            : "Perfil actualizado.",
      );
    } catch (err) {
      if (err instanceof ApiError && err.code === "EMAIL_TAKEN_OFFER_TAKEOVER") {
        const f = err.fields;
        setEmailClash({
          user_id: String(f.clashing_user_id ?? ""),
          email: String(f.clashing_user_email ?? ""),
          username: String(f.clashing_user_username ?? ""),
          tenant_id: f.clashing_user_tenant_id
            ? String(f.clashing_user_tenant_id)
            : null,
        });
        setError(
          "Ese email ya está en uso por otro usuario. Si reconoces el conflicto, puedes liberarlo abajo.",
        );
      } else {
        setError(
          err instanceof ApiError ? err.message : "No se pudo actualizar el perfil",
        );
      }
    } finally {
      setSaving(false);
    }
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (saving) return;
    await submit(false);
  }

  async function handleTakeoverEmail() {
    if (saving) return;
    if (
      !confirmarDestructivo({
        objeto: `el correo de ${emailClash?.username} (${emailClash?.email})`,
        consecuencia:
          'Se le renombra a "released.<ts>.<email>" para liberar la dirección. No se borra al usuario, pero no podrá iniciar sesión hasta que actualice su correo.',
        reversibilidad: "definitiva",
      })
    ) {
      return;
    }
    await submit(true);
  }

  if (me && !me.is_superadmin) {
    return (
      <div className="mx-auto max-w-2xl p-6">
        <Banner variant="danger">
          Solo los super administradores pueden ver esta página.
        </Banner>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <Breadcrumb
        items={[
          { label: "Superadmin", href: "/superadmin" },
          { label: "Mi cuenta" },
        ]}
      />

      <header>
        <h1 className="text-[22px] font-semibold tracking-[-0.02em] text-[var(--text-primary)]">
          Mi cuenta — Superadmin
        </h1>
        <p className="mt-1 text-[13px] text-[var(--text-tertiary)]">
          Actualiza el email y la contraseña de la cuenta superadmin.
          Cambios sensibles requieren confirmar la contraseña actual.
        </p>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}
      {notice ? <Banner variant="success">{notice}</Banner> : null}

      {loading || !profile ? (
        <div className="space-y-3">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      ) : (
        <form
          onSubmit={handleSave}
          className="space-y-4 rounded-[var(--radius-window)] border border-[var(--border-default)] bg-[var(--color-surface)] p-6 shadow-[var(--relieve-isla)]"
        >
          <div>
            <label className="block text-[10.5px] font-semibold uppercase tracking-[0.07em] text-[var(--text-tertiary)]">
              Username (no editable)
            </label>
            <Input value={profile.username} disabled className="mt-1" />
          </div>

          <div>
            <label className="block text-[10.5px] font-semibold uppercase tracking-[0.07em] text-[var(--text-tertiary)]">
              Email
            </label>
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="mt-1"
            />
          </div>

          <div>
            <label className="block text-[10.5px] font-semibold uppercase tracking-[0.07em] text-[var(--text-tertiary)]">
              Nombre completo
            </label>
            <Input
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="mt-1"
            />
          </div>

          <fieldset className="space-y-3 rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-subtle)] p-4">
            <legend className="px-1 text-[10.5px] font-semibold uppercase tracking-[0.07em] text-[var(--text-tertiary)]">
              Cambiar contraseña (opcional)
            </legend>
            <PasswordInput
              placeholder="Nueva contraseña"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              autoComplete="new-password"
            />
            <PasswordInput
              placeholder="Confirmar nueva contraseña"
              value={newPasswordConfirm}
              onChange={(e) => setNewPasswordConfirm(e.target.value)}
              autoComplete="new-password"
              disabled={!newPassword}
            />
          </fieldset>

          <div>
            <label className="block text-[10.5px] font-semibold uppercase tracking-[0.07em] text-[var(--text-tertiary)]">
              Contraseña actual (obligatoria para guardar)
            </label>
            <PasswordInput
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              autoComplete="current-password"
              required
              className="mt-1"
            />
          </div>

          <Button type="submit" loading={saving} disabled={saving}>
            Guardar cambios
          </Button>

          {emailClash ? (
            <div className="rounded-[var(--radius-md)] border border-[var(--color-warning-border)] bg-[var(--color-warning-bg)] p-4">
              <p className="text-sm font-medium text-[var(--color-warning-fg)]">
                Conflicto de email detectado
              </p>
              <p className="mt-1 text-xs text-[var(--text-secondary)]">
                El email <code>{email}</code> ya está en uso por el usuario{" "}
                <strong>{emailClash.username}</strong> (
                <code>{emailClash.email}</code>
                {emailClash.tenant_id ? (
                  <>
                    {" "}
                    · tenant <code>{emailClash.tenant_id}</code>
                  </>
                ) : (
                  " · sin tenant"
                )}
                ).
              </p>
              <p className="mt-2 text-xs text-[var(--text-secondary)]">
                Si reconoces el conflicto y quieres tomar el email, podemos
                renombrar al user en conflicto a{" "}
                <code>released.{"<timestamp>"}.{emailClash.email}</code> para
                liberarlo. El user no se borra; sólo deberá actualizar su email
                para volver a iniciar sesión.
              </p>
              <div className="mt-3 flex gap-2">
                <Button
                  type="button"
                  variant="danger"
                  size="sm"
                  loading={saving}
                  onClick={handleTakeoverEmail}
                >
                  Liberar email y reintentar
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => setEmailClash(null)}
                >
                  Cancelar
                </Button>
              </div>
            </div>
          ) : null}
        </form>
      )}
    </div>
  );
}
