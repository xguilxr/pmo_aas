"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { Skeleton } from "@/components/ui/skeleton";

/**
 * US-NEW-026: Health se consolidó en /superadmin (Visión general).
 * Esta ruta queda como redirect permanente para no romper bookmarks.
 */
export default function HealthLegacyRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/superadmin");
  }, [router]);
  return (
    <div className="p-8">
      <Skeleton className="h-10 w-48" />
    </div>
  );
}
