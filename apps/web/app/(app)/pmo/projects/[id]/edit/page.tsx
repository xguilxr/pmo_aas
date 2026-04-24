"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { Banner } from "@/components/ui/banner";
import { Skeleton } from "@/components/ui/skeleton";
import { ProjectForm } from "@/components/project-form";
import { ApiError } from "@/lib/api";
import { getProject, type ProjectDetail } from "@/lib/api/projects";

export default function EditProjectPage() {
  const { id } = useParams<{ id: string }>();
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getProject(id)
      .then(setProject)
      .catch((err) => {
        setError(err instanceof ApiError ? err.message : "No se pudo cargar el proyecto");
      });
  }, [id]);

  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <header>
        <nav className="text-[11px] text-[var(--text-tertiary)]">
          <Link href="/pmo/projects" className="hover:underline">
            Proyectos
          </Link>
          <span className="mx-1">/</span>
          <Link href={`/pmo/projects/${id}`} className="hover:underline">
            {project?.folio ?? id}
          </Link>
          <span className="mx-1">/</span>
          <span>Editar</span>
        </nav>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
          Editar proyecto
        </h1>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}
      {!project && !error ? (
        <Skeleton className="h-[480px] w-full" />
      ) : project ? (
        <ProjectForm mode="edit" initial={project} />
      ) : null}
    </div>
  );
}
