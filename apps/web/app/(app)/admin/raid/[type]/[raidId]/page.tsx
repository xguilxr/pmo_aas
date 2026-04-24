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

function Inner() {
  const { type, raidId } = useParams<{ type: string; raidId: string }>();
  const resolved = parseType(type);
  return (
    <RaidDetailPage
      raidType={resolved}
      itemId={raidId}
      breadcrumb={
        <nav className="text-[11px] text-[var(--text-tertiary)]">
          <Link href="/admin/raid" className="hover:underline">
            RAID · Tenant
          </Link>
          <span className="mx-1">/</span>
          <span>Ítem</span>
          <div className="mt-1">
            <BackLink href="/admin/raid" label="Volver al RAID" />
          </div>
        </nav>
      }
    />
  );
}

export default function TenantRaidItemPage() {
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
