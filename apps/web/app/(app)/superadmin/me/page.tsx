"use client";

import { useEffect, useState } from "react";

import { Banner } from "@/components/ui/banner";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import { getStoredUser } from "@/lib/auth-storage";
import {
  getSuperadminMe,
  updateSuperadminMe,
  type SuperadminMe,
} from "@/lib/api/superadmin";

export default function SuperadminMePage() {
  const me = getStoredUser();
  const [profile, setProfile] = useState<SuperadminMe | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

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

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (saving) return;
    setError(null);
    setNotice(null);

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

      // Si nada cambió, no llamamos.
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
        body.email
          ? "Perfil actualizado. La próxima vez logueate con el email nuevo."
          : "Perfil actualizado.",
      );
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "No se pudo actualizar el perfil",
      );
    } finally {
      setSaving(false);
    }
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
        <h1 className="text-2xl font-semibold text-[var(--color-primary)]">
          Mi cuenta — Superadmin
        </h1>
        <p className="mt-1 text-sm text-[var(--color-tertiary)]">
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
          className="space-y-4 rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--color-surface)] p-6"
        >
          <div>
            <label className="block text-xs font-semibold uppercase text-[var(--color-tertiary)]">
              Username (no editable)
            </label>
            <Input value={profile.username} disabled className="mt-1" />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase text-[var(--color-tertiary)]">
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
            <label className="block text-xs font-semibold uppercase text-[var(--color-tertiary)]">
              Nombre completo
            </label>
            <Input
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="mt-1"
            />
          </div>

          <fieldset className="space-y-3 rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-subtle)] p-4">
            <legend className="px-1 text-xs font-semibold uppercase text-[var(--color-tertiary)]">
              Cambiar contraseña (opcional)
            </legend>
            <Input
              type="password"
              placeholder="Nueva contraseña"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              autoComplete="new-password"
            />
            <Input
              type="password"
              placeholder="Confirmar nueva contraseña"
              value={newPasswordConfirm}
              onChange={(e) => setNewPasswordConfirm(e.target.value)}
              autoComplete="new-password"
              disabled={!newPassword}
            />
          </fieldset>

          <div>
            <label className="block text-xs font-semibold uppercase text-[var(--color-tertiary)]">
              Contraseña actual (obligatoria para guardar)
            </label>
            <Input
              type="password"
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
        </form>
      )}
    </div>
  );
}
