"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState, type FormEvent } from "react";
import { LogIn, MailCheck } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";
import { ApiError } from "@/lib/api";
import { esDesafio, login, verificarCodigo } from "@/lib/auth";
import { hasSession } from "@/lib/auth-storage";

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
  // Si el user ya tiene un ?redirect=... respeta ese valor. Si no, la
  // landing por default se decide post-login según is_superadmin
  // (BUG-021): superadmin → /superadmin; resto → /dashboard.
  const explicitRedirect = searchParams.get("redirect");

  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // ASVS 4.3.1 — segundo paso. `null` = todavía estamos en el primero.
  const [desafio, setDesafio] = useState<string | null>(null);
  const [codigo, setCodigo] = useState("");

  useEffect(() => {
    if (hasSession()) {
      router.replace(explicitRedirect || "/dashboard");
    }
  }, [router, explicitRedirect]);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!identifier.trim() || !password) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await login(identifier.trim(), password);
      // La contraseña era correcta pero la cuenta llega a administración: falta
      // el código del correo antes de que haya sesión.
      if (esDesafio(res)) {
        setDesafio(res.desafio);
        setSubmitting(false);
        return;
      }
      if (res.user.must_change_password) {
        router.replace("/change-password");
        return;
      }
      const landing =
        explicitRedirect ||
        (res.user.is_superadmin ? "/superadmin" : "/dashboard");
      router.replace(landing);
    } catch (err) {
      setError(resolveErrorMessage(err));
      setSubmitting(false);
    }
  }

  async function enviarCodigo(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!desafio || !codigo.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await verificarCodigo(desafio, codigo.trim());
      const landing = res.user.must_change_password
        ? "/change-password"
        : explicitRedirect || (res.user.is_superadmin ? "/superadmin" : "/dashboard");
      router.replace(landing);
    } catch {
      // El servidor responde igual a todos los fallos —código erróneo,
      // caducado, agotado— para no decirle a quien prueba si va bien.
      setError("El código no es válido o caducó. Vuelve a iniciar sesión.");
      setSubmitting(false);
    }
  }

  if (desafio) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[var(--color-app)] px-4 py-12">
        <div className="w-full max-w-md">
          <div className="mb-8 text-center">
            <div className="mb-3 inline-flex h-12 w-12 items-center justify-center rounded-[var(--radius-lg)] bg-[var(--color-primary)] text-[var(--color-inverse)]">
              <MailCheck className="h-6 w-6" aria-hidden />
            </div>
            <h1 className="text-2xl font-semibold text-[var(--color-primary)]">
              Revisa tu correo
            </h1>
            <p className="mt-1 text-sm text-[var(--color-tertiary)]">
              Tu cuenta administra la organización, así que te enviamos un código
              de 6 dígitos. Caduca en 10 minutos.
            </p>
          </div>

          <div className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-sm)]">
            <form onSubmit={enviarCodigo} noValidate className="space-y-4">
              <div>
                <label
                  htmlFor="codigo"
                  className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
                >
                  Código
                </label>
                <Input
                  id="codigo"
                  name="codigo"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  autoFocus
                  required
                  maxLength={6}
                  disabled={submitting}
                  value={codigo}
                  onChange={(e) => setCodigo(e.target.value.replace(/\D/g, ""))}
                  placeholder="000000"
                  className="text-center text-lg tracking-[0.4em]"
                />
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
                disabled={codigo.length < 6}
              >
                Entrar
              </Button>

              <div className="text-center text-xs">
                <button
                  type="button"
                  onClick={() => {
                    setDesafio(null);
                    setCodigo("");
                    setError(null);
                  }}
                  className="text-[var(--color-tertiary)] hover:text-[var(--color-primary)] hover:underline"
                >
                  Volver
                </button>
              </div>
            </form>
          </div>
        </div>
      </main>
    );
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
              <PasswordInput
                id="password"
                name="password"
                autoComplete="current-password"
                required
                disabled={submitting}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
              />
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

            <div className="text-center text-xs">
              <Link
                href="/forgot-password"
                className="text-[var(--color-tertiary)] hover:text-[var(--color-primary)] hover:underline"
              >
                ¿Olvidaste tu contraseña?
              </Link>
            </div>
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
