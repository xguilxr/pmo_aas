"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Check, KeyRound, UserCircle, X } from "lucide-react";

import { MisDatosSection } from "@/components/mis-datos-section";
import { NotificationPreferencesSection } from "@/components/notification-preferences-section";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import { setStoredUser, getStoredUser } from "@/lib/auth-storage";
import { changePassword } from "@/lib/auth";
import {
  getMyProfile,
  updateMyProfile,
  type MyProfile,
} from "@/lib/api/users";
import { checkPasswordPolicy } from "@/lib/password";

function ProfileSection() {
  const [profile, setProfile] = useState<MyProfile | null>(null);
  const [fullName, setFullName] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getMyProfile()
      .then((p) => {
        if (cancelled) return;
        setProfile(p);
        setFullName(p.full_name);
      })
      .catch((err) => {
        if (!cancelled)
          setError(err instanceof ApiError ? err.message : "Error al cargar perfil");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const dirty = profile !== null && fullName.trim() !== profile.full_name;

  async function handleSave(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!dirty || fullName.trim().length < 2) return;
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const updated = await updateMyProfile({ full_name: fullName.trim() });
      setProfile(updated);
      // actualizar storage → topbar muestra nuevo nombre sin reload
      const stored = getStoredUser();
      if (stored) setStoredUser({ ...stored, full_name: updated.full_name });
      setSuccess("Perfil actualizado.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-sm)]">
      <div className="mb-4 flex items-center gap-2">
        <UserCircle className="h-5 w-5 text-[var(--color-tertiary)]" aria-hidden />
        <h2 className="text-lg font-semibold text-[var(--color-primary)]">
          Detalles personales
        </h2>
      </div>

      {loading ? (
        <div className="space-y-3">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      ) : (
        <form onSubmit={handleSave} className="space-y-4">
          <div>
            <label
              htmlFor="full_name"
              className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
            >
              Nombre completo
            </label>
            <Input
              id="full_name"
              value={fullName}
              minLength={2}
              maxLength={200}
              onChange={(e) => setFullName(e.target.value)}
              disabled={saving}
              required
            />
          </div>

          <div>
            <label
              htmlFor="email"
              className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
            >
              Email
            </label>
            <Input
              id="email"
              type="email"
              value={profile?.email ?? ""}
              readOnly
              disabled
            />
            <p className="mt-1 text-xs text-[var(--color-tertiary)]">
              El cambio de email requiere verificación (post-MVP).
            </p>
          </div>

          {error ? <Banner variant="danger">{error}</Banner> : null}
          {success ? <Banner variant="success">{success}</Banner> : null}

          <div className="flex justify-end">
            <Button
              type="submit"
              disabled={!dirty || saving || fullName.trim().length < 2}
              loading={saving}
            >
              Guardar cambios
            </Button>
          </div>
        </form>
      )}
    </section>
  );
}

function PasswordSection() {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const checks = useMemo(() => checkPasswordPolicy(next), [next]);
  const policyOk = checks.every((c) => c.ok);
  const matches = next.length > 0 && next === confirm;
  const canSubmit =
    current.length > 0 && policyOk && matches && next !== current;

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!canSubmit) return;
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      await changePassword(current, next);
      setSuccess(
        "Contraseña actualizada. Por seguridad, vuelve a iniciar sesión cuando expire el token actual.",
      );
      setCurrent("");
      setNext("");
      setConfirm("");
    } catch (err) {
      if (err instanceof ApiError && err.code === "UNAUTHENTICATED") {
        setError("Contraseña actual incorrecta");
      } else {
        setError(err instanceof ApiError ? err.message : "Error al cambiar contraseña");
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-sm)]">
      <div className="mb-4 flex items-center gap-2">
        <KeyRound className="h-5 w-5 text-[var(--color-tertiary)]" aria-hidden />
        <h2 className="text-lg font-semibold text-[var(--color-primary)]">
          Cambiar contraseña
        </h2>
      </div>

      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        <div>
          <label
            htmlFor="current"
            className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
          >
            Contraseña actual
          </label>
          <PasswordInput
            id="current"
            autoComplete="current-password"
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
            disabled={saving}
            required
          />
        </div>

        <div>
          <label
            htmlFor="new"
            className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
          >
            Nueva contraseña
          </label>
          <PasswordInput
            id="new"
            autoComplete="new-password"
            value={next}
            onChange={(e) => setNext(e.target.value)}
            disabled={saving}
            required
          />
          <ul className="mt-2 space-y-1 text-xs">
            {checks.map((c) => (
              <li
                key={c.label}
                className={
                  c.ok
                    ? "flex items-center gap-1.5 text-[var(--color-success-fg)]"
                    : "flex items-center gap-1.5 text-[var(--color-tertiary)]"
                }
              >
                {c.ok ? (
                  <Check className="h-3.5 w-3.5" aria-hidden />
                ) : (
                  <X className="h-3.5 w-3.5" aria-hidden />
                )}
                {c.label}
              </li>
            ))}
          </ul>
        </div>

        <div>
          <label
            htmlFor="confirm"
            className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
          >
            Confirmar nueva contraseña
          </label>
          <PasswordInput
            id="confirm"
            autoComplete="new-password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            disabled={saving}
            invalid={confirm.length > 0 && !matches}
            required
          />
          {confirm.length > 0 && !matches ? (
            <p className="mt-1 text-xs text-[var(--color-danger-fg)]">
              Las contraseñas no coinciden
            </p>
          ) : null}
        </div>

        {error ? <Banner variant="danger">{error}</Banner> : null}
        {success ? <Banner variant="success">{success}</Banner> : null}

        <div className="flex justify-end">
          <Button type="submit" loading={saving} disabled={!canSubmit}>
            Guardar contraseña
          </Button>
        </div>
      </form>
    </section>
  );
}

export default function AccountPage() {
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-[var(--color-primary)]">
          Administrar cuenta
        </h1>
        <p className="mt-1 text-sm text-[var(--color-tertiary)]">
          Actualiza tus datos personales y la contraseña de tu cuenta.
        </p>
      </header>
      <ProfileSection />
      <PasswordSection />
      <NotificationPreferencesSection />
      <MisDatosSection />
    </div>
  );
}
