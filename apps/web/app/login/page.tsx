"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState, type FormEvent } from "react";
import { Eye, EyeOff, LogIn } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api";
import { login } from "@/lib/auth";
import { getAccessToken } from "@/lib/auth-storage";

const ERROR_MESSAGES: Record<string, string> = {
  UNAUTHENTICATED: "Credenciales inválidas. Verifica tu usuario y contraseña.",
  ACCOUNT_LOCKED: "Cuenta bloqueada temporalmente por intentos fallidos. Intenta más tarde.",
  USER_INACTIVE: "Este usuario está inactivo. Contacta a tu administrador.",
  NETWORK_ERROR: "No pudimos conectar con el servidor. Revisa tu conexión.",
};

function resolveErrorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    return ERROR_MESSAGES[err.code] ?? err.message ?? "No se pudo iniciar sesión.";
  }
  return "No se pudo iniciar sesión. Intenta nuevamente.";
}

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectTo = searchParams.get("redirect") || "/dashboard";

  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (getAccessToken()) {
      router.replace(redirectTo);
    }
  }, [router, redirectTo]);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!identifier.trim() || !password) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await login(identifier.trim(), password);
      if (res.user.must_change_password) {
        router.replace("/change-password");
      } else {
        router.replace(redirectTo);
      }
    } catch (err) {
      setError(resolveErrorMessage(err));
      setSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-[var(--color-app)] px-4 py-12">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="mb-3 inline-flex h-12 w-12 items-center justify-center rounded-[var(--radius-lg)] bg-[var(--color-primary)] text-[var(--color-inverse)]">
            <LogIn className="h-6 w-6" aria-hidden />
          </div>
          <h1 className="text-2xl font-semibold text-[var(--color-primary)]">PMO-aaS</h1>
          <p className="mt-1 text-sm text-[var(--color-tertiary)]">
            Ingresa a tu espacio de trabajo
          </p>
        </div>

        <div className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-sm)]">
          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            <div>
              <label
                htmlFor="identifier"
                className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
              >
                Usuario o correo
              </label>
              <Input
                id="identifier"
                name="identifier"
                type="text"
                autoComplete="username"
                autoFocus
                required
                disabled={submitting}
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                placeholder="admin@acme.pmoaas.local"
              />
            </div>

            <div>
              <label
                htmlFor="password"
                className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
              >
                Contraseña
              </label>
              <div className="relative">
                <Input
                  id="password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  required
                  disabled={submitting}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  disabled={submitting}
                  aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
                  className="absolute right-2 top-1/2 inline-flex h-6 w-6 -translate-y-1/2 items-center justify-center rounded-[var(--radius-xs)] text-[var(--color-tertiary)] hover:text-[var(--color-primary)]"
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" aria-hidden />
                  ) : (
                    <Eye className="h-4 w-4" aria-hidden />
                  )}
                </button>
              </div>
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
              disabled={!identifier.trim() || !password}
            >
              {submitting ? "Ingresando…" : "Iniciar sesión"}
            </Button>
          </form>
        </div>

        <p className="mt-6 text-center text-xs text-[var(--color-tertiary)]">
          PMO-aaS · Project Management Office as a Service
        </p>
      </div>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <main className="flex min-h-screen items-center justify-center bg-[var(--color-app)]">
          <div className="text-sm text-[var(--color-tertiary)]">Cargando…</div>
        </main>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
