"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { Suspense } from "react";

import {
  ChangeBackLink,
  ChangeDetailPage,
} from "@/components/change-detail-page";

function Inner() {
  const { id, changeId } = useParams<{ id: string; changeId: string }>();
  const filteredHref = `/pmo/projects/${id}/changes`;
  return (
    <ChangeDetailPage
      changeId={changeId}
      breadcrumb={
        <div className="flex flex-col gap-1">
          <nav
            aria-label="Breadcrumb"
            className="text-[11px] text-[var(--color-tertiary)]"
          >
            <Link href={filteredHref} className="hover:underline">
              Cambios
            </Link>
            <span className="mx-1">/</span>
            <span className="font-mono text-[var(--color-secondary)]">
              {changeId.slice(0, 8)}
            </span>
          </nav>
          <ChangeBackLink href={filteredHref} label="Volver" />
        </div>
      }
    />
  );
}

export default function ChangeDetailRoute() {
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
