"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import { ShieldCheck } from "lucide-react";

import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";
import { fetchMe } from "@/lib/auth";
import { getStoredUser } from "@/lib/auth-storage";

/**
 * MCS SEG-01 · ASVS 8.3.3 — pantalla de bienvenida con el aviso, y aceptación.
 *
 * «Verify that users are provided clear language regarding collection and use
 * of supplied personal information and that users have provided opt-in consent
 * for the use of that data before it is used in any way.»
 *
 * ## Por qué aquí y no en un alta
 *
 * No hay alta por autoservicio: las cuentas las crea un administrador. Así que
 * el consentimiento va en el **primer inicio de sesión** —decisión del owner—,
 * y vuelve a salir **si el aviso cambia**, que es lo que hace que sea un
 * consentimiento vivo y no una casilla que alguien marcó una vez.
 *
 * ## Por qué bloquea
 *
 * El control dice «before it is used in any way». Una pantalla que se puede
 * cerrar con la equis es un aviso, no un consentimiento. Por eso no hay forma
 * de esquivarla salvo cerrar sesión — que es exactamente la alternativa que
 * tiene que existir para que decir que no signifique algo.
 *
 * Quién debe verla lo decide el **servidor** (`debe_aceptar_privacidad`), no
 * este componente: si la web supiera cuál es la versión vigente habría dos
 * sitios que la conocen y acabarían discrepando.
 */
type Apartado = { titulo: string; cuerpo: string };
type Aviso = { version: string; apartados: Apartado[] };

export function AvisoPrivacidadGate({ children }: { children: ReactNode }) {
  const [debeAceptar, setDebeAceptar] = useState<boolean | null>(null);
  const [aviso, setAviso] = useState<Aviso | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sincroniza = useCallback(() => {
    const user = getStoredUser();
    setDebeAceptar(user ? user.debe_aceptar_privacidad === true : null);
  }, []);

  useEffect(() => {
    sincroniza();
    window.addEventListener("pmoaas:user-updated", sincroniza);
    return () => window.removeEventListener("pmoaas:user-updated", sincroniza);
  }, [sincroniza]);

  useEffect(() => {
    if (!debeAceptar || aviso) return;
    let vigente = true;
    apiFetch<Aviso>("/api/v1/auth/aviso-privacidad", { auth: false })
      .then((a) => {
        if (vigente) setAviso(a);
      })
      .catch(() => {
        if (vigente) setError("No se pudo cargar el aviso. Recarga la página.");
      });
    return () => {
      vigente = false;
    };
  }, [debeAceptar, aviso]);

  async function aceptar() {
    setEnviando(true);
    setError(null);
    try {
      await apiFetch("/api/v1/auth/aceptar-privacidad", { method: "POST" });
      // Se relee el perfil en vez de darlo por hecho: quien decide si ya está
      // aceptado sigue siendo el servidor.
      await fetchMe();
      sincroniza();
    } catch {
      setError("No se pudo registrar tu aceptación. Inténtalo de nuevo.");
      setEnviando(false);
    }
  }

  // `null` = todavía no se sabe (no hay perfil cargado). No se pinta nada:
  // enseñar el aviso a quien quizá ya aceptó sería peor que esperar un instante.
  if (debeAceptar === null || debeAceptar === false) return <>{children}</>;

  return (
    <div className="flex min-h-screen items-start justify-center bg-[var(--color-app)] px-4 py-10">
      <div className="w-full max-w-2xl rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-sm)]">
        <div className="mb-5 flex items-start gap-3">
          <div className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-[var(--radius-lg)] bg-[var(--color-primary)] text-[var(--color-inverse)]">
            <ShieldCheck className="h-5 w-5" aria-hidden />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-[var(--color-primary)]">
              Antes de empezar
            </h1>
            <p className="mt-1 text-sm text-[var(--color-tertiary)]">
              Esto es lo que PMO·aaS guarda sobre ti y para qué. Léelo y dinos si
              estás de acuerdo.
            </p>
          </div>
        </div>

        {aviso ? (
          <div className="space-y-4">
            {aviso.apartados.map((a) => (
              <section key={a.titulo}>
                <h2 className="text-sm font-semibold text-[var(--color-primary)]">
                  {a.titulo}
                </h2>
                <p className="mt-1 text-sm leading-relaxed text-[var(--color-secondary)]">
                  {a.cuerpo}
                </p>
              </section>
            ))}
          </div>
        ) : (
          <p className="text-sm text-[var(--color-tertiary)]">Cargando el aviso…</p>
        )}

        {error ? (
          <div
            role="alert"
            className="mt-4 rounded-[var(--radius-md)] border border-[var(--color-danger-border)] bg-[var(--color-danger-bg)] px-3 py-2 text-sm text-[var(--color-danger-fg)]"
          >
            {error}
          </div>
        ) : null}

        <div className="mt-6 flex flex-col gap-3 border-t border-[var(--border-default)] pt-5 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs text-[var(--color-tertiary)]">
            Si no estás de acuerdo, cierra sesión y habla con quien administre tu
            organización.
          </p>
          <Button onClick={aceptar} loading={enviando} disabled={!aviso || enviando}>
            Estoy de acuerdo
          </Button>
        </div>
      </div>
    </div>
  );
}
