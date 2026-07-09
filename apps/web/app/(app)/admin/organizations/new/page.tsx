"use client";

import { Breadcrumb } from "@/components/ui/breadcrumb";
import { OrganizationForm } from "@/components/organization-form";
import { useOrgLabel } from "@/lib/org-label";

export default function NewOrganizationPage() {
  // ENH-190: label configurable por tenant para "Organización(es)".
  const orgLabel = useOrgLabel();
  const newLabel =
    orgLabel.singular === "Portafolio" ? "Nuevo portafolio" : "Nueva organización";

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <Breadcrumb
        items={[
          { href: "/admin/organizations", label: orgLabel.plural },
          { label: "Nueva" },
        ]}
      />
      <div>
        <h1 className="text-2xl font-semibold text-[var(--color-primary)]">{newLabel}</h1>
        <p className="mt-1 text-sm text-[var(--color-tertiary)]">
          Crea un nuevo cliente dentro de tu tenant.
        </p>
      </div>
      <OrganizationForm mode="create" />
    </div>
  );
}
