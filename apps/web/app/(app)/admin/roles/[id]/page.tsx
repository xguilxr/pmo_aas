"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { RoleEditor } from "@/components/role-editor";
import { Banner } from "@/components/ui/banner";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import { getRole, type AdminRole } from "@/lib/api/admin";

export default function RoleDetailPage() {
  const params = useParams<{ id: string }>();
  const [role, setRole] = useState<AdminRole | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getRole(params.id)
      .then((r) => {
        if (!cancelled) setRole(r);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "No se pudo cargar el rol");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [params.id]);

  if (error) {
    return (
      <div className="mx-auto max-w-2xl">
        <Banner variant="danger">{error}</Banner>
      </div>
    );
  }

  if (loading || !role) {
    return (
      <div className="mx-auto max-w-3xl space-y-4">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  return <RoleEditor mode="edit" initial={role} />;
}
