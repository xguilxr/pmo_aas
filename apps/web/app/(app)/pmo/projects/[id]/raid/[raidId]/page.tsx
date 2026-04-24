"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { Suspense } from "react";

import {
  BackLink,
  RaidDetailPage,
  type RaidDetailType,
} from "@/components/raid-detail-page";

function parseType(v: string | null): RaidDetailType {
  if (v === "action" || v === "incident" || v === "decision") return v;
  if (v === "actions") return "action";
  if (v === "incidents") return "incident";
  if (v === "decisions") return "decision";
  return "risk";
}

function Inner() {
  const { id, raidId } = useParams<{ id: string; raidId: string }>();
  const search = useSearchParams();
  const type = parseType(search.get("type"));
  return (
    <RaidDetailPage
      raidType={type}
      itemId={raidId}
      breadcrumb={
        <nav className="text-[11px] text-[var(--text-tertiary)]">
          <Link href="/pmo/projects" className="hover:underline">
            Proyectos
          </Link>
          <span className="mx-1">/</span>
          <Link
            href={`/pmo/projects/${id}`}
            className="hover:underline"
          >
            Detalle
          </Link>
          <span className="mx-1">/</span>
          <Link
            href={`/pmo/projects/${id}/raid`}
            className="hover:underline"
          >
            RAID
          </Link>
          <span className="mx-1">/</span>
          <span>Ítem</span>
          <div className="mt-1">
            <BackLink href={`/pmo/projects/${id}/raid`} label="Volver al RAID" />
          </div>
        </nav>
      }
    />
  );
}

export default function ProjectRaidItemPage() {
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
