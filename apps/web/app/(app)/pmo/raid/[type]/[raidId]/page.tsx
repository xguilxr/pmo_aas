"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { Suspense } from "react";

import {
  BackLink,
  RaidDetailPage,
  type RaidDetailType,
} from "@/components/raid-detail-page";

function parseType(v: string): RaidDetailType {
  if (v === "action" || v === "incident" || v === "decision") return v;
  return "risk";
}

// BUG-052: tipo localizado para breadcrumb + map al param `kind` del
// listado tenant (`/pmo/raid?kind=...`).
const TYPE_META: Record<
  RaidDetailType,
  { label: string; kindParam: string }
> = {
  risk: { label: "Riesgos", kindParam: "risks" },
  action: { label: "Acciones", kindParam: "actions" },
  incident: { label: "Issues", kindParam: "issues" },
  decision: { label: "Decisiones", kindParam: "decisions" },
};

function Inner() {
  const { type, raidId } = useParams<{ type: string; raidId: string }>();
  const resolved = parseType(type);
  const meta = TYPE_META[resolved];
  const filteredHref = `/pmo/raid?kind=${meta.kindParam}`;
  return (
    <RaidDetailPage
      raidType={resolved}
      itemId={raidId}
      breadcrumb={
        <div className="flex flex-col gap-1">
          {/* BUG-052: breadcrumb canónico RAID / [Tipo] / [ID] */}
          <nav
            aria-label="Breadcrumb"
            className="text-[11px] text-[var(--text-tertiary)]"
          >
            <Link href="/pmo/raid" className="hover:underline">
              RAID
            </Link>
            <span className="mx-1">/</span>
            <Link href={filteredHref} className="hover:underline">
              {meta.label}
            </Link>
            <span className="mx-1">/</span>
            <span className="text-[12px] tracking-[0.01em] text-[var(--text-secondary)]">
              {raidId.slice(0, 8)}
            </span>
          </nav>
          <BackLink href={filteredHref} label="Volver" />
        </div>
      }
    />
  );
}

export default function TenantRaidItemPage() {
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
