"use client";

/**
 * FASE-7 (revamp v2, US-A) — `/admin/hierarchy`: árbol
 * organización → portafolio → programa → proyecto, con mover, crear y
 * borrar, para todo el tenant. Wireframe W7. Punto 10 de
 * `../REVAMP-V2-FEEDBACK.md`.
 *
 * El árbol de portafolios/programas (crear, editar, archivar, borrado
 * permanente) y el mover-proyecto ya existían en `OrgHierarchySection`
 * (usado hasta ahora dentro de la ficha de una organización); esta página
 * es la vista de nivel tenant: elige la organización arriba y reusa esa
 * misma sección, sin duplicar la lógica.
 */
import Link from "next/link";
import { useEffect, useState } from "react";

import { HardDeleteButton } from "@/components/hard-delete-button";
import { OrgHierarchySection } from "@/components/org-hierarchy-section";
import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { Icono } from "@/components/ui/icono";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import {
  deleteOrganization,
  hardDeleteOrganization,
  listOrganizations,
  previewHardDeleteOrganization,
  type Organization,
} from "@/lib/api/organizations";

export default function AdminHierarchyPage() {
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [orgId, setOrgId] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  async function cargarOrgs(seleccionar?: string) {
    setLoading(true);
    setError(null);
    try {
      const filas = await listOrganizations();
      setOrgs(filas);
      if (seleccionar && filas.some((o) => o.id === seleccionar)) {
        setOrgId(seleccionar);
      } else if (!filas.some((o) => o.id === orgId)) {
        setOrgId(filas[0]?.id ?? "");
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudieron cargar las organizaciones.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void cargarOrgs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const org = orgs.find((o) => o.id === orgId) ?? null;

  async function desactivarOrganizacion() {
    if (!org) return;
    setDeleting(true);
    try {
      await deleteOrganization(org.id);
      setConfirmDelete(false);
      await cargarOrgs(org.id);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo desactivar la organización.");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="space-y-4 p-4">
      <Breadcrumb items={[{ label: "Admin", href: "/admin" }, { label: "Organizaciones y portafolios" }]} />

      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-[22px] font-semibold tracking-[-0.02em] text-[var(--text-primary)]">
            Organizaciones y portafolios
          </h1>
          <p className="text-[13px] text-[var(--text-tertiary)]">
            Árbol organización → portafolio → programa → proyecto de todo el
            tenant: mover, crear y borrar en un solo lugar.
          </p>
        </div>
        <div className="flex gap-2">
          <Link href="/admin/organizations">
            <Button variant="secondary" size="sm">
              <Icono nombre="building" size={14} />
              Ver todas / editar organización
            </Button>
          </Link>
          <Link href="/admin/organizations/new">
            <Button size="sm">
              <Icono nombre="plus" size={14} />
              Nueva organización
            </Button>
          </Link>
        </div>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      {loading ? (
        <Skeleton className="h-10 w-72" />
      ) : orgs.length === 0 ? (
        <Banner variant="info">
          Este tenant todavía no tiene organizaciones. Crea la primera con
          «Nueva organización».
        </Banner>
      ) : (
        <div className="flex flex-wrap items-center gap-3">
          <Select
            value={orgId}
            onChange={(e) => setOrgId(e.target.value)}
            className="w-72"
            aria-label="Organización"
          >
            {orgs.map((o) => (
              <option key={o.id} value={o.id}>
                {o.name}
                {!o.is_active ? " (inactiva)" : ""}
              </option>
            ))}
          </Select>
          {org && !org.is_active ? <Badge variant="danger">Inactiva</Badge> : null}
          {org ? (
            <div className="ml-auto flex gap-2">
              {org.is_active ? (
                <Button variant="danger" size="sm" onClick={() => setConfirmDelete(true)}>
                  <Icono nombre="circle-alert" size={14} />
                  Desactivar organización
                </Button>
              ) : (
                <HardDeleteButton
                  preview={() => previewHardDeleteOrganization(org.id)}
                  hardDelete={(slug) => hardDeleteOrganization(org.id, slug)}
                  onDeleted={() => void cargarOrgs()}
                  entityLabel="Organización"
                  triggerVariant="danger"
                />
              )}
            </div>
          ) : null}
        </div>
      )}

      {org ? <OrgHierarchySection orgId={org.id} /> : null}

      <Modal
        open={confirmDelete}
        onClose={() => setConfirmDelete(false)}
        title="Desactivar organización"
        description="La organización queda inactiva pero no se borra. Sus portafolios, programas y proyectos permanecen."
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirmDelete(false)} disabled={deleting}>
              Cancelar
            </Button>
            <Button variant="danger" onClick={() => void desactivarOrganizacion()} loading={deleting}>
              Desactivar
            </Button>
          </>
        }
      >
        <p className="text-[13px] text-[var(--text-secondary)]">
          ¿Desactivar <strong>{org?.name}</strong>?
        </p>
      </Modal>
    </div>
  );
}
