"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Icono } from "@/components/ui/icono";
import { PasswordInput } from "@/components/ui/password-input";
import { RequireAuth } from "@/components/require-auth";
import { ApiError } from "@/lib/api";
import { clearSession, getStoredUser } from "@/lib/auth-storage";
import { changePassword } from "@/lib/auth";
import { checkPasswordPolicy } from "@/lib/password";

const POLICY_ERRORS: Record<string, string> = {
  password_too_short: "Debe tener al menos 8 caracteres",
  password_too_long: "No puede pasar de 128 caracteres",
  password_missing_uppercase: "Debe incluir al menos una letra mayúscula",
  password_missing_digit: "Debe incluir al menos un dígito",
  password_missing_symbol: "Debe incluir al menos un símbolo",
};

function ChangePasswordForm() {
  const router = useRouter();
  const user = getStoredUser();

  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const checks = useMemo(() => checkPasswordPolicy(next), [next]);
  const policyOk = checks.every((c) => c.ok);
  const matches = next.length > 0 && next === confirm;
  const canSubmit = current.length > 0 && policyOk && matches && next !== current;

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      await changePassword(current, next);
      // cambio exitoso invalida refresh tokens → forzar relogin limpio
      clearSession();
      router.replace("/login");
    } catch (err) {
      if (err instanceof ApiError) {
        const fieldCode =
          err.fields && typeof err.fields === "object" && "code" in err.fields
            ? String((err.fields as { code?: unknown }).code ?? "")
            : "";
        if (fieldCode && POLICY_ERRORS[fieldCode]) {
          setError(POLICY_ERRORS[fieldCode]);
        } else if (err.code === "UNAUTHENTICATED") {
          setError("Contraseña actual incorrecta");
        } else {
          setError(err.message);
        }
      } else {
        setError("No se pudo cambiar la contraseña");
      }
      setSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-[var(--color-subtle)] px-4 py-12">
      <div className="flex w-full max-w-[480px] flex-col gap-6">
        <div className="flex flex-col items-center gap-2.5 text-center">
          <div className="inline-flex h-11 w-11 items-center justify-center rounded-[var(--radius-xl)] bg-[var(--color-primary)] text-[var(--color-inverse)]">
            <Icono nombre="lock" size={20} />
          </div>
          <h1 className="text-[22px] font-semibold tracking-[-0.01em] text-[var(--text-primary)]">
            Cambia tu contraseña
          </h1>
          <p className="text-[13px] text-[var(--text-tertiary)]">
            {user?.must_change_password
              ? "Define una contraseña nueva antes de continuar."
              : "Actualiza tu contraseña."}
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          noValidate
          className="flex flex-col gap-3.5 rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5.5 shadow-[var(--relieve-isla)]"
        >
          <div>
            <label htmlFor="current" className="mb-1.5 block text-[12.5px] font-medium text-[var(--text-secondary)]">
              Contraseña actual
            </label>
            <PasswordInput
              id="current"
              autoComplete="current-password"
              required
              disabled={submitting}
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
            />
          </div>

          <div>
            <label htmlFor="next" className="mb-1.5 block text-[12.5px] font-medium text-[var(--text-secondary)]">
              Nueva contraseña
            </label>
            <PasswordInput
              id="next"
              autoComplete="new-password"
              required
              disabled={submitting}
              value={next}
              onChange={(e) => setNext(e.target.value)}
            />
            <ul className="mt-2 space-y-1 text-xs">
              {checks.map((c) => (
                <li
                  key={c.label}
                  className={
                    c.ok
                      ? "flex items-center gap-1.5 text-[var(--color-success-fg)]"
                      : "flex items-center gap-1.5 text-[var(--text-tertiary)]"
                  }
                >
                  <Icono nombre={c.ok ? "check" : "x"} size={13} />
                  {c.label}
                </li>
              ))}
            </ul>
          </div>

          <div>
            <label htmlFor="confirm" className="mb-1.5 block text-[12.5px] font-medium text-[var(--text-secondary)]">
              Confirmar nueva contraseña
            </label>
            <PasswordInput
              id="confirm"
              autoComplete="new-password"
              required
              disabled={submitting}
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              invalid={confirm.length > 0 && !matches}
            />
            {confirm.length > 0 && !matches ? (
              <p className="mt-1 text-xs text-[var(--color-danger-fg)]">Las contraseñas no coinciden</p>
            ) : null}
          </div>

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
            {submitting ? "Guardando…" : "Guardar contraseña"}
          </Button>
        </form>
      </div>
    </main>
  );
}

export default function ChangePasswordPage() {
  return (
    <RequireAuth allowMustChangePassword>
      <ChangePasswordForm />
    </RequireAuth>
  );
}
