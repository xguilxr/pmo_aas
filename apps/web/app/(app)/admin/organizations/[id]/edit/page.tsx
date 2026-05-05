"use client";

import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { Building2, PowerOff } from "lucide-react";

import { OrganizationForm } from "@/components/organization-form";
import { OrgHierarchySection } from "@/components/org-hierarchy-section";
import { ProgramsSection } from "@/components/programs-section";
import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import {
  deleteOrganization,
  getOrganization,
  hardDeleteOrganization,
  previewHardDeleteOrganization,
  type Organization,
} from "@/lib/api/organizations";
import { HardDeleteButton } from "@/components/hard-delete-button";

function OrganizationDetailInner() {
  const params = useParams<{ id: string }>();
  const search = useSearchParams();
  const router = useRouter();
  const [org, setOrg] = useState<Organization | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [notice, setNotice] = useState<string | null>(
    search.get("created") === "1" ? "Organización creada" : null,
  );

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getOrganization(params.id)
      .then((r) => {
        if (!cancelled) setOrg(r);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(
            err instanceof ApiError ? err.message : "No se pudo cargar la organización",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [params.id]);

  async function handleDelete() {
    if (!org) return;
    setDeleting(true);
    try {
      await deleteOrganization(org.id);
      router.replace("/admin/organizations");
    } catch (err) {
      setConfirmDelete(false);
      setDeleting(false);
      setError(
        err instanceof ApiError ? err.message : "No se pudo desactivar la organización",
      );
    }
  }

  if (error && !org) {
    return (
      <div className="mx-auto max-w-3xl">
        <Banner variant="danger">{error}</Banner>
      </div>
    );
  }

  if (loading || !org) {
    return (
      <div className="mx-auto max-w-3xl space-y-4">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <Breadcrumb
        items={[
          { href: "/admin/organizations", label: "Organizaciones" },
          { href: `/admin/organizations/${org.id}`, label: org.name },
          { label: "Editar" },
        ]}
      />

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 flex-none items-center justify-center overflow-hidden rounded-full border border-[var(--border-default)] bg-[var(--color-subtle)] text-[var(--color-tertiary)]">
            {org.logo_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={org.logo_url} alt="" className="h-full w-full object-cover" />
            ) : (
              <Building2 className="h-6 w-6" aria-hidden />
            )}
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-[var(--color-primary)]">{org.name}</h1>
            <div className="mt-1 flex items-center gap-2 text-xs text-[var(--color-tertiary)]">
              {[org.industry, org.country].filter(Boolean).join(" · ") || "Sin datos"}
              {!org.is_active ? <Badge variant="danger">Inactiva</Badge> : null}
            </div>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="danger" onClick={() => setConfirmDelete(true)}>
            <PowerOff className="h-4 w-4" aria-hidden />
            Desactivar
          </Button>
          {!org.is_active ? (
            <HardDeleteButton
              preview={() => previewHardDeleteOrganization(org.id)}
              hardDelete={(slug) => hardDeleteOrganization(org.id, slug)}
              onDeleted={() => router.replace("/admin/organizations")}
              entityLabel="Organización"
            />
          ) : null}
        </div>
      </div>

      {notice ? <Banner variant="success">{notice}</Banner> : null}
      {error ? <Banner variant="danger">{error}</Banner> : null}

      <OrganizationForm
        mode="edit"
        initial={org}
        onSaved={(updated) => {
          setOrg(updated);
          setNotice(null);
        }}
      />

      <OrgHierarchySection orgId={org.id} />

      <ProgramsSection organizationId={org.id} />

      <Modal
        open={confirmDelete}
        onClose={() => setConfirmDelete(false)}
        title="Desactivar organización"
        description="La organización quedará inactiva pero no se borra. Sus programas y proyectos permanecen."
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirmDelete(false)} disabled={deleting}>
              Cancelar
            </Button>
            <Button variant="danger" onClick={handleDelete} loading={deleting}>
              Desactivar
            </Button>
          </>
        }
      >
        <p className="text-sm text-[var(--color-secondary)]">
          ¿Confirmas desactivar <strong>{org.name}</strong>?
        </p>
      </Modal>
    </div>
  );
}

export default function OrganizationDetailPage() {
  return (
    <Suspense fallback={<div className="h-96" />}>
      <OrganizationDetailInner />
    </Suspense>
  );
}
