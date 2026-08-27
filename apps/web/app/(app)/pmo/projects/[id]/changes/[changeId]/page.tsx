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
            className="text-[11px] text-[var(--text-tertiary)]"
          >
            <Link href={filteredHref} className="hover:underline">
              Cambios
            </Link>
            <span className="mx-1">/</span>
            <span className="text-[12px] tracking-[0.01em] text-[var(--text-secondary)]">
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
        <div className="p-6 text-[13px] text-[var(--text-tertiary)]">Cargando…</div>
      }
    >
      <Inner />
    </Suspense>
  );
}
