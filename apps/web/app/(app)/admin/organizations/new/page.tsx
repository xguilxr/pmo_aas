"use client";

import { Breadcrumb } from "@/components/ui/breadcrumb";
import { OrganizationForm } from "@/components/organization-form";

export default function NewOrganizationPage() {
  // ENH-190: label configurable por tenant para "Organización(es)".
  const newLabel =
    "Nueva organización";

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <Breadcrumb
        items={[
          { href: "/admin/organizations", label: "Organizaciones" },
          { label: "Nueva" },
        ]}
      />
      <div>
        <h1 className="text-[22px] font-semibold tracking-[-0.02em] text-[var(--text-primary)]">{newLabel}</h1>
        <p className="mt-1 text-[13px] text-[var(--text-tertiary)]">
          Crea un nuevo cliente dentro de tu tenant.
        </p>
      </div>
      <OrganizationForm mode="create" />
    </div>
  );
}
