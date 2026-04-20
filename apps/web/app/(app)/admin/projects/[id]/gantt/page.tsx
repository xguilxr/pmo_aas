"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { BarChart3 } from "lucide-react";

import { Banner } from "@/components/ui/banner";
import { Skeleton } from "@/components/ui/skeleton";
import { GanttView } from "@/components/gantt-view";
import { ApiError } from "@/lib/api";
import { getGantt, type GanttData } from "@/lib/api/tasks";

export default function GanttPage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<GanttData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    getGantt(id)
      .then(setData)
      .catch((err) => {
        setError(err instanceof ApiError ? err.message : "No se pudo cargar el Gantt");
      })
      .finally(() => setLoading(false));
  }, [id]);

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <header>
        <nav className="text-[11px] text-[var(--text-tertiary)]">
          <Link href="/admin/projects" className="hover:underline">
            Proyectos
          </Link>
          <span className="mx-1">/</span>
          <Link href={`/admin/projects/${id}`} className="hover:underline">
            Detalle
          </Link>
          <span className="mx-1">/</span>
          <Link href={`/admin/projects/${id}/tasks`} className="hover:underline">
            Tareas
          </Link>
          <span className="mx-1">/</span>
          <span>Gantt</span>
        </nav>
        <h1 className="mt-1 flex items-center gap-2 text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
          <BarChart3 className="h-6 w-6" aria-hidden /> Gantt
        </h1>
        <p className="mt-1 text-[13px] text-[var(--text-tertiary)]">
          Timeline interactivo con dependencias, hitos y línea "hoy". Zoom por día, semana, mes o
          trimestre.
        </p>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      {loading ? (
        <Skeleton className="h-[480px] w-full" />
      ) : data ? (
        <GanttView data={data} />
      ) : null}
    </div>
  );
}
