"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { getStoredUser, hasSession } from "@/lib/auth-storage";

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    if (!hasSession()) {
      router.replace("/login");
      return;
    }
    const user = getStoredUser();
    if (user?.must_change_password) {
      router.replace("/change-password");
    } else {
      router.replace("/dashboard");
    }
  }, [router]);

  return (
    <main className="flex min-h-screen items-center justify-center bg-[var(--color-app)]">
      <div className="text-sm text-[var(--color-tertiary)]">Cargando…</div>
    </main>
  );
}
