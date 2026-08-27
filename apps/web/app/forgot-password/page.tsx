"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Icono } from "@/components/ui/icono";
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
    <main className="flex min-h-screen items-center justify-center bg-[var(--color-subtle)] px-4 py-12">
      <div className="flex w-full max-w-[480px] flex-col gap-6">
        <div className="flex flex-col items-center gap-2.5 text-center">
          <div className="inline-flex h-11 w-11 items-center justify-center rounded-[var(--radius-xl)] bg-[var(--color-primary)] text-[var(--color-inverse)]">
            <Icono nombre="mail" size={20} />
          </div>
          <h1 className="text-[22px] font-semibold tracking-[-0.01em] text-[var(--text-primary)]">
            Restablecer contraseña
          </h1>
          <p className="text-[13px] text-[var(--text-tertiary)]">
            Te enviaremos un link por correo.
          </p>
        </div>

        <div className="rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5.5 shadow-[var(--relieve-isla)]">
          {submitted ? (
            <div className="space-y-4">
              <p className="text-[13px] text-[var(--text-secondary)]">
                Si <strong className="text-[var(--text-primary)]">{email}</strong>{" "}
                corresponde a un usuario registrado, enviamos un link para
                restablecer tu contraseña. El link expira en <strong>30
                minutos</strong>.
              </p>
              <p className="text-xs text-[var(--text-faint)]">
                No recibirás más emails si el correo no está registrado —
                por seguridad no confirmamos si un email existe o no.
              </p>
              <div className="flex justify-center pt-2">
                <Link
                  href="/login"
                  className="inline-flex items-center gap-1 text-[13px] text-[var(--color-accent)] hover:underline"
                >
                  <Icono nombre="arrow-left" size={13} />
                  Volver a iniciar sesión
                </Link>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-3.5">
              <div>
                <label
                  htmlFor="email"
                  className="mb-1.5 block text-[12.5px] font-medium text-[var(--text-secondary)]"
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
                  className="text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:underline"
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
