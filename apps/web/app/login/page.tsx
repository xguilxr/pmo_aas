"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Icono } from "@/components/ui/icono";
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
  const [diasRecordado, setDiasRecordado] = useState(30);
  const [codigo, setCodigo] = useState("");
  // ADR-035 §Ventana — marcado por defecto: es lo que evita que el segundo
  // factor se vuelva insoportable y acabe desactivado. Se desmarca en un equipo
  // prestado, donde recordar sería peor que la molestia que ahorra.
  const [recordarEquipo, setRecordarEquipo] = useState(true);

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
        setDiasRecordado(res.dias_recordado);
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
      const res = await verificarCodigo(desafio, codigo.trim(), recordarEquipo);
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
      <main className="flex min-h-screen items-center justify-center bg-[var(--color-subtle)] px-4 py-12">
        <div className="flex w-full max-w-[480px] flex-col gap-6">
          <div className="flex flex-col items-center gap-2.5 text-center">
            <div className="inline-flex h-11 w-11 items-center justify-center rounded-[var(--radius-xl)] bg-[var(--color-primary)] text-[var(--color-inverse)]">
              <Icono nombre="bell" size={20} />
            </div>
            <h1 className="text-[22px] font-semibold tracking-[-0.01em] text-[var(--text-primary)]">
              Revisa tu correo
            </h1>
            <p className="text-[13px] leading-[1.5] text-[var(--text-tertiary)]">
              Tu cuenta administra la organización, así que te enviamos un código
              de 6 dígitos. Caduca en 10 minutos.
            </p>
          </div>

          <form
            onSubmit={enviarCodigo}
            noValidate
            className="flex flex-col gap-4 rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5.5 shadow-[var(--relieve-isla)]"
          >
            <div>
              <label
                htmlFor="codigo"
                className="mb-1.5 block text-[12.5px] font-medium text-[var(--text-secondary)]"
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
                className="h-10.5 text-center font-mono text-[17px] tracking-[0.4em]"
              />
            </div>

            <label className="flex items-start gap-2.25 text-[12.5px] text-[var(--text-secondary)]">
              <Checkbox
                checked={recordarEquipo}
                disabled={submitting}
                onChange={(e) => setRecordarEquipo(e.target.checked)}
                className="mt-0.25"
              />
              <span>
                No volver a pedirme el código en este equipo
                <span className="block text-[11px] text-[var(--text-faint)]">
                  Durante {diasRecordado} días. Desmárcalo si el equipo no es
                  tuyo.
                </span>
              </span>
            </label>

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
                className="text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:underline"
              >
                Volver
              </button>
            </div>
          </form>
        </div>
      </main>
    );
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-[var(--color-subtle)] px-4 py-12">
      <div className="flex w-full max-w-[480px] flex-col gap-6">
        <div className="flex flex-col items-center gap-2.5 text-center">
          <div className="inline-flex h-11 w-11 items-center justify-center rounded-[var(--radius-xl)] bg-[var(--color-primary)] text-[var(--color-inverse)]">
            <Icono nombre="lock" size={20} />
          </div>
          <h1 className="text-[22px] font-semibold tracking-[-0.01em] text-[var(--text-primary)]">
            PMO-aaS
          </h1>
          <p className="text-[13px] text-[var(--text-tertiary)]">
            Ingresa a tu espacio de trabajo
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          noValidate
          className="flex flex-col gap-3.5 rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5.5 shadow-[var(--relieve-isla)]"
        >
          <div>
            <label
              htmlFor="identifier"
              className="mb-1.5 block text-[12.5px] font-medium text-[var(--text-secondary)]"
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
              className="mb-1.5 block text-[12.5px] font-medium text-[var(--text-secondary)]"
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
              className="text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:underline"
            >
              ¿Olvidaste tu contraseña?
            </Link>
          </div>
        </form>

        <p className="text-center text-[11.5px] text-[var(--text-faint)]">
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
        <main className="flex min-h-screen items-center justify-center bg-[var(--color-subtle)]">
          <div className="text-sm text-[var(--text-tertiary)]">Cargando…</div>
        </main>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
