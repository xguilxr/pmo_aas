"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useMemo, useState, type FormEvent } from "react";
import { CheckCircle2, KeyRound, XCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { PasswordInput } from "@/components/ui/password-input";
import { ApiError } from "@/lib/api";
import { resetPassword } from "@/lib/auth";
import { checkPasswordPolicy, passwordPolicyOk } from "@/lib/password";

function ResetInner() {
  const router = useRouter();
  const search = useSearchParams();
  const token = search.get("token") ?? "";

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const checks = useMemo(() => checkPasswordPolicy(password), [password]);
  const matches = password.length > 0 && password === confirm;
  const canSubmit =
    Boolean(token) && passwordPolicyOk(password) && matches && !submitting;

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      await resetPassword(token, password);
      router.replace("/login?reset=1");
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.code === "TOKEN_INVALID") {
          setError(
            "El link ya no es válido o expiró. Solicita uno nuevo desde 'Olvidé mi contraseña'.",
          );
        } else if (err.code === "RATE_LIMITED") {
          setError(
            "Demasiados intentos. Espera una hora e intenta de nuevo.",
          );
        } else {
          setError(err.message || "No se pudo restablecer la contraseña.");
        }
      } else {
        setError("No se pudo conectar con el servidor. Intenta de nuevo.");
      }
      setSubmitting(false);
    }
  }

  if (!token) {
    return (
      <div className="w-full max-w-md">
        <div className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-sm)]">
          <p className="text-sm text-[var(--color-secondary)]">
            Este link no incluye un token de restablecimiento. Solicita uno
            nuevo desde <Link href="/forgot-password" className="text-[var(--color-accent)] hover:underline">"Olvidé mi contraseña"</Link>.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-md">
      <div className="mb-8 text-center">
        <div className="mb-3 inline-flex h-12 w-12 items-center justify-center rounded-[var(--radius-lg)] bg-[var(--color-primary)] text-[var(--color-inverse)]">
          <KeyRound className="h-6 w-6" aria-hidden />
        </div>
        <h1 className="text-2xl font-semibold text-[var(--color-primary)]">
          Nueva contraseña
        </h1>
        <p className="mt-1 text-sm text-[var(--color-tertiary)]">
          Elige una contraseña nueva para tu cuenta.
        </p>
      </div>

      <div className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-sm)]">
        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          <div>
            <label
              htmlFor="password"
              className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
            >
              Nueva contraseña
            </label>
            <PasswordInput
              id="password"
              name="password"
              autoComplete="new-password"
              required
              autoFocus
              disabled={submitting}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          <div>
            <label
              htmlFor="confirm"
              className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
            >
              Confirmar contraseña
            </label>
            <PasswordInput
              id="confirm"
              name="confirm"
              autoComplete="new-password"
              required
              disabled={submitting}
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
            />
          </div>

          <ul className="space-y-1 text-[12px]">
            {checks.map((c) => (
              <li
                key={c.label}
                className={
                  c.ok
                    ? "inline-flex w-full items-center gap-1.5 text-[var(--color-success-fg)]"
                    : "inline-flex w-full items-center gap-1.5 text-[var(--color-tertiary)]"
                }
              >
                {c.ok ? (
                  <CheckCircle2 className="h-3.5 w-3.5" aria-hidden />
                ) : (
                  <XCircle className="h-3.5 w-3.5" aria-hidden />
                )}
                {c.label}
              </li>
            ))}
            <li
              className={
                matches
                  ? "inline-flex w-full items-center gap-1.5 text-[var(--color-success-fg)]"
                  : "inline-flex w-full items-center gap-1.5 text-[var(--color-tertiary)]"
              }
            >
              {matches ? (
                <CheckCircle2 className="h-3.5 w-3.5" aria-hidden />
              ) : (
                <XCircle className="h-3.5 w-3.5" aria-hidden />
              )}
              Las contraseñas coinciden
            </li>
          </ul>

          {error ? (
            <div
              role="alert"
              className="rounded-[var(--radius-md)] border border-[var(--color-danger-border)] bg-[var(--color-danger-bg)] px-3 py-2 text-sm text-[var(--color-danger-fg)]"
            >
              {error}
            </div>
          ) : null}

          <Button
            type="submit"
            size="lg"
            className="w-full"
            loading={submitting}
            disabled={!canSubmit}
          >
            Restablecer contraseña
          </Button>

          <div className="text-center text-xs">
            <Link
              href="/login"
              className="text-[var(--color-tertiary)] hover:text-[var(--color-primary)] hover:underline"
            >
              Volver a iniciar sesión
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function ResetPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[var(--color-app)] px-4 py-12">
      <Suspense
        fallback={<div className="text-sm text-[var(--color-tertiary)]">Cargando…</div>}
      >
        <ResetInner />
      </Suspense>
    </main>
  );
}
