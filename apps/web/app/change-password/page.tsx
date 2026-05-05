"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState, type FormEvent } from "react";
import { Check, KeyRound, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { RequireAuth } from "@/components/require-auth";
import { ApiError } from "@/lib/api";
import { clearSession, getStoredUser } from "@/lib/auth-storage";
import { changePassword } from "@/lib/auth";
import { checkPasswordPolicy } from "@/lib/password";

const POLICY_ERRORS: Record<string, string> = {
  password_too_short: "Debe tener al menos 8 caracteres",
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
    <main className="flex min-h-screen items-center justify-center bg-[var(--color-app)] px-4 py-12">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="mb-3 inline-flex h-12 w-12 items-center justify-center rounded-[var(--radius-lg)] bg-[var(--color-primary)] text-[var(--color-inverse)]">
            <KeyRound className="h-6 w-6" aria-hidden />
          </div>
          <h1 className="text-2xl font-semibold text-[var(--color-primary)]">Cambia tu contraseña</h1>
          <p className="mt-1 text-sm text-[var(--color-tertiary)]">
            {user?.must_change_password
              ? "Define una contraseña nueva antes de continuar."
              : "Actualiza tu contraseña."}
          </p>
        </div>

        <div className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-sm)]">
          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            <div>
              <label htmlFor="current" className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]">
                Contraseña actual
              </label>
              <Input
                id="current"
                type="password"
                autoComplete="current-password"
                required
                disabled={submitting}
                value={current}
                onChange={(e) => setCurrent(e.target.value)}
              />
            </div>

            <div>
              <label htmlFor="next" className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]">
                Nueva contraseña
              </label>
              <Input
                id="next"
                type="password"
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
              <label htmlFor="confirm" className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]">
                Confirmar nueva contraseña
              </label>
              <Input
                id="confirm"
                type="password"
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
