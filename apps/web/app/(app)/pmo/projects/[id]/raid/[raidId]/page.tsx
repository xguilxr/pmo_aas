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

// BUG-052: mapping al param `tab` del listado proyecto.
const TYPE_META: Record<
  RaidDetailType,
  { label: string; tabParam: string }
> = {
  risk: { label: "Riesgos", tabParam: "risks" },
  action: { label: "Acciones", tabParam: "actions" },
  incident: { label: "Incidentes", tabParam: "incidents" },
  decision: { label: "Decisiones", tabParam: "decisions" },
};

function Inner() {
  const { id, raidId } = useParams<{ id: string; raidId: string }>();
  const search = useSearchParams();
  const type = parseType(search.get("type"));
  const meta = TYPE_META[type];
  const filteredHref = `/pmo/projects/${id}/raid?tab=${meta.tabParam}`;
  return (
    <RaidDetailPage
      raidType={type}
      itemId={raidId}
      breadcrumb={
        <div className="flex flex-col gap-1">
          {/* BUG-052: breadcrumb canónico RAID / [Tipo] / [ID] */}
          <nav
            aria-label="Breadcrumb"
            className="text-[11px] text-[var(--color-tertiary)]"
          >
            <Link
              href={`/pmo/projects/${id}/raid`}
              className="hover:underline"
            >
              RAID
            </Link>
            <span className="mx-1">/</span>
            <Link href={filteredHref} className="hover:underline">
              {meta.label}
            </Link>
            <span className="mx-1">/</span>
            <span className="font-mono text-[var(--color-secondary)]">
              {raidId.slice(0, 8)}
            </span>
          </nav>
          <BackLink href={filteredHref} label="Volver" />
        </div>
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
