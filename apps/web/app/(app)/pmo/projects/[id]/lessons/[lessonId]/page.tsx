"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { Suspense } from "react";

import {
  LessonBackLink,
  LessonDetailPage,
} from "@/components/lesson-detail-page";

function Inner() {
  const { id, lessonId } = useParams<{ id: string; lessonId: string }>();
  const filteredHref = `/pmo/projects/${id}/lessons`;
  return (
    <LessonDetailPage
      lessonId={lessonId}
      breadcrumb={
        <div className="flex flex-col gap-1">
          <nav
            aria-label="Breadcrumb"
            className="text-[11px] text-[var(--color-tertiary)]"
          >
            <Link href={filteredHref} className="hover:underline">
              Lecciones
            </Link>
            <span className="mx-1">/</span>
            <span className="font-mono text-[var(--color-secondary)]">
              {lessonId.slice(0, 8)}
            </span>
          </nav>
          <LessonBackLink href={filteredHref} label="Volver" />
        </div>
      }
    />
  );
}

export default function LessonDetailRoute() {
  return (
    <Suspense
      fallback={
        <div className="p-6 text-sm text-[var(--color-tertiary)]">Cargando…</div>
      }
    >
      <Inner />
    </Suspense>
  );
}
