"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { ArrowLeft, Mail } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { forgotPassword } from "@/lib/auth";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!email.trim()) return;
    setSubmitting(true);
    try {
      await forgotPassword(email.trim());
    } catch {
      // Silenciamos errores: el backend responde 204 igual, pero si
      // hay problema de red mostramos igual la confirmación para no
      // revelar nada (mismo tratamiento que el backend).
    }
    setSubmitted(true);
    setSubmitting(false);
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-[var(--color-app)] px-4 py-12">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="mb-3 inline-flex h-12 w-12 items-center justify-center rounded-[var(--radius-lg)] bg-[var(--color-primary)] text-[var(--color-inverse)]">
            <Mail className="h-6 w-6" aria-hidden />
          </div>
          <h1 className="text-2xl font-semibold text-[var(--color-primary)]">
            Restablecer contraseña
          </h1>
          <p className="mt-1 text-sm text-[var(--color-tertiary)]">
            Te enviaremos un link por correo.
          </p>
        </div>

        <div className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-sm)]">
          {submitted ? (
            <div className="space-y-4">
              <p className="text-sm text-[var(--color-secondary)]">
                Si <strong className="text-[var(--color-primary)]">{email}</strong>{" "}
                corresponde a un usuario registrado, enviamos un link para
                restablecer tu contraseña. El link expira en <strong>30
                minutos</strong>.
              </p>
              <p className="text-xs text-[var(--color-tertiary)]">
                No recibirás más emails si el correo no está registrado —
                por seguridad no confirmamos si un email existe o no.
              </p>
              <div className="flex justify-center pt-2">
                <Link
                  href="/login"
                  className="inline-flex items-center gap-1 text-sm text-[var(--color-accent)] hover:underline"
                >
                  <ArrowLeft className="h-3.5 w-3.5" aria-hidden />
                  Volver a iniciar sesión
                </Link>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} noValidate className="space-y-4">
              <div>
                <label
                  htmlFor="email"
                  className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
                >
                  Correo electrónico
                </label>
                <Input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  autoFocus
                  required
                  disabled={submitting}
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="tu@email.com"
                />
              </div>
              <Button
                type="submit"
                size="lg"
                className="w-full"
                loading={submitting}
                disabled={!email.trim()}
              >
                Enviar link de restablecimiento
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
          )}
        </div>
      </div>
    </main>
  );
}
