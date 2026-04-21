"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect } from "react";

import { Skeleton } from "@/components/ui/skeleton";

/**
 * US-016: la pestaña Gantt se unificó con Plan.
 * Esta ruta queda como redirect permanente a `/plan?view=gantt`
 * para no romper enlaces/bookmarks existentes.
 */
export default function GanttLegacyRedirect() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  useEffect(() => {
    router.replace(`/admin/projects/${id}/plan?view=gantt`);
  }, [id, router]);
  return (
    <div className="p-8">
      <Skeleton className="h-10 w-48" />
    </div>
  );
}
