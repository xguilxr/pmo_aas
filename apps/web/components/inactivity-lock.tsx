"use client";

import { useState, type FormEvent, type ReactNode } from "react";

import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Icono } from "@/components/ui/icono";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";
import { useInactivityLock } from "@/hooks/use-inactivity-lock";
import { ApiError } from "@/lib/api";
import { esDesafio, login, logout } from "@/lib/auth";
import { getActiveTenantId, getStoredUser, setActiveTenantId } from "@/lib/auth-storage";
import { cn } from "@/lib/cn";

const ERROR_MESSAGES: Record<string, string> = {
  UNAUTHENTICATED: "Credenciales inválidas. Verifica tu contraseña.",
  ACCOUNT_LOCKED: "Cuenta bloqueada temporalmente por intentos fallidos. Intenta más tarde.",
  USER_INACTIVE: "Este usuario está inactivo. Contacta a tu administrador.",
  NETWORK_ERROR: "No pudimos conectar con el servidor. Revisa tu conexión.",
};

function resolveErrorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    return ERROR_MESSAGES[err.code] ?? err.message ?? "No se pudo reanudar la sesión.";
  }
  return "No se pudo reanudar la sesión. Intenta nuevamente.";
}

/**
 * ENH-160 — Guarda de inactividad para áreas autenticadas.
 *
 * Envuelve el contenido de la app. Tras 15 min sin actividad
 * (`useInactivityLock`), aplica blur + bloqueo de interacción al contenido y
 * monta un overlay no descartable que pide re-autenticar. Al volver a iniciar
 * sesión, el contenido se desbloquea en la misma ruta/estado — no hay redirect
 * ni reload, así que no se pierde progreso.
 */
export function InactivityLock({ children }: { children: ReactNode }) {
  const { locked, unlock } = useInactivityLock();

  return (
    <>
      <div
        className={cn(locked && "pointer-events-none select-none blur-sm")}
        aria-hidden={locked || undefined}
        inert={locked}
      >
        {children}
      </div>
      {locked ? <ReauthOverlay onUnlock={unlock} /> : null}
    </>
  );
}

function ReauthOverlay({ onUnlock }: { onUnlock: () => void }) {
  const user = getStoredUser();
  const identifier = user?.email || user?.username || "";

  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!identifier || !password) return;
    setSubmitting(true);
    setError(null);
    // login() reescribe el tenant activo con el default del usuario; si había
    // otro tenant en contexto y sigue siendo válido, lo restauramos para no
    // cambiar de contexto al desbloquear.
    const prevTenant = getActiveTenantId();
    try {
      const res = await login(identifier, password);
      // ASVS 4.3.1 — si la cuenta administra, el desbloqueo también pasa por el
      // segundo factor. Aquí no se puede pedir el código sin convertir el panel
      // de bloqueo en una pantalla de inicio de sesión completa, así que se
      // manda a `/login`, que ya lo sabe hacer.
      //
      // Es más fricción de la que tenía y es lo correcto: si el desbloqueo se
      // saltara el segundo factor, bastaría con esperar a que un administrador
      // dejara la sesión bloqueada para entrar solo con la contraseña.
      if (esDesafio(res)) {
        window.location.href = "/login";
        return;
      }
      if (prevTenant && prevTenant !== res.active_tenant_id && res.tenants.includes(prevTenant)) {
        setActiveTenantId(prevTenant);
      }
      setPassword("");
      onUnlock();
    } catch (err) {
      setError(resolveErrorMessage(err));
      setSubmitting(false);
    }
  }

  async function handleSignOut() {
    await logout();
    window.location.href = "/login";
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Sesión bloqueada por inactividad"
      className="fixed inset-0 z-50 flex items-center justify-center px-4"
    >
      <div className="absolute inset-0 bg-[oklch(0%_0_0_/_0.45)]" />
      <div className="relative z-10 w-full max-w-md rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-lg)]">
        <div className="px-6 pt-6 text-center">
          <div className="mb-3 inline-flex h-12 w-12 items-center justify-center rounded-[var(--radius-lg)] bg-[var(--color-primary)] text-[var(--color-inverse)]">
            <Icono nombre="lock" size={22} />
          </div>
          <h2 className="text-lg font-semibold text-[var(--color-primary)]">
            Sesión bloqueada por inactividad
          </h2>
          <p className="mt-1 text-sm text-[var(--color-tertiary)]">
            Pasaron 15 minutos sin actividad. Vuelve a iniciar sesión para
            continuar; no perderás tu progreso.
          </p>
        </div>

        <form onSubmit={handleSubmit} noValidate className="space-y-4 px-6 py-5">
          <div>
            <label className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]">
              Cuenta
            </label>
            <Input
              type="text"
              value={identifier}
              readOnly
              tabIndex={-1}
              autoComplete="username"
              className="cursor-default bg-[var(--color-subtle)] text-[var(--color-tertiary)]"
            />
          </div>

          <div>
            <label
              htmlFor="reauth-password"
              className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
            >
              Contraseña
            </label>
            <PasswordInput
              id="reauth-password"
              name="password"
              autoComplete="current-password"
              autoFocus
              required
              disabled={submitting}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </div>

          {error ? <Banner variant="danger">{error}</Banner> : null}

          <Button
            type="submit"
            size="lg"
            className="w-full"
            loading={submitting}
            disabled={!identifier || !password}
          >
            {submitting ? "Reanudando…" : "Continuar"}
          </Button>

          <div className="text-center">
            <button
              type="button"
              onClick={handleSignOut}
              disabled={submitting}
              className="text-xs text-[var(--color-tertiary)] hover:text-[var(--color-primary)] hover:underline disabled:cursor-not-allowed"
            >
              Cerrar sesión
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
