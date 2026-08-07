"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { getStoredUser, hasSession } from "@/lib/auth-storage";
import { fetchMe } from "@/lib/auth";
import { InactivityLock } from "@/components/inactivity-lock";
import { AvisoPrivacidadGate } from "@/components/aviso-privacidad-gate";

type Props = {
  children: ReactNode;
  /** Si la cuenta debe cambiar contraseña, redirige a /change-password (excepto en esa ruta). */
  allowMustChangePassword?: boolean;
};

export function RequireAuth({ children, allowMustChangePassword = false }: Props) {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let vigente = true;

    // ASVS 8.2.2 (ADR-033) — el perfil dejó de persistirse en `localStorage` y
    // vive en memoria, así que **una recarga lo vacía**. Aquí se repone desde
    // `/auth/me`, que es de donde tenía que haber salido siempre: el perfil
    // guardado podía llevar días de retraso, con los roles de antes de que un
    // administrador los cambiara.
    //
    // `hasSession()` no es una credencial y puede mentir —el token caduca y el
    // indicador sigue puesto—. Quien decide es el servidor: si la cookie ya no
    // vale, `/auth/me` responde 401 y `apiFetch` limpia y dispara
    // `pmoaas:unauthorized`, que es el otro efecto de este componente.
    async function comprueba() {
      if (!hasSession()) {
        router.replace("/login");
        return;
      }
      let user = getStoredUser();
      if (!user) {
        try {
          user = await fetchMe();
        } catch {
          // El 401 ya lo gestionó `apiFetch`; cualquier otro fallo deja la
          // sesión sin comprobar, y sin comprobar no se entra.
          if (vigente) router.replace("/login");
          return;
        }
      }
      if (!vigente) return;
      if (user?.must_change_password && !allowMustChangePassword) {
        router.replace("/change-password");
        return;
      }
      setReady(true);
    }

    void comprueba();
    return () => {
      vigente = false;
    };
  }, [router, allowMustChangePassword]);

  useEffect(() => {
    function handleUnauthorized() {
      router.replace("/login");
    }
    window.addEventListener("pmoaas:unauthorized", handleUnauthorized);
    return () => window.removeEventListener("pmoaas:unauthorized", handleUnauthorized);
  }, [router]);

  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-sm text-[var(--color-tertiary)]">Cargando…</div>
      </div>
    );
  }

  return (
    <AvisoPrivacidadGate>
      <InactivityLock>{children}</InactivityLock>
    </AvisoPrivacidadGate>
  );
}
