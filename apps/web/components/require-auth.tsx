"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { getAccessToken, getStoredUser } from "@/lib/auth-storage";

type Props = {
  children: ReactNode;
  /** Si la cuenta debe cambiar contraseña, redirige a /change-password (excepto en esa ruta). */
  allowMustChangePassword?: boolean;
};

export function RequireAuth({ children, allowMustChangePassword = false }: Props) {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      router.replace("/login");
      return;
    }
    const user = getStoredUser();
    if (user?.must_change_password && !allowMustChangePassword) {
      router.replace("/change-password");
      return;
    }
    setReady(true);
  }, [router, allowMustChangePassword]);

  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-sm text-[var(--color-tertiary)]">Cargando…</div>
      </div>
    );
  }

  return <>{children}</>;
}
