"use client";

import { Breadcrumb } from "@/components/ui/breadcrumb";
import { OrganizationForm } from "@/components/organization-form";

export default function NewOrganizationPage() {
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <Breadcrumb
        items={[
          { href: "/admin/organizations", label: "Organizaciones" },
          { label: "Nueva" },
        ]}
      />
      <div>
        <h1 className="text-2xl font-semibold text-[var(--color-primary)]">Nueva organización</h1>
        <p className="mt-1 text-sm text-[var(--color-tertiary)]">
          Crea un nuevo cliente dentro de tu tenant.
        </p>
      </div>
      <OrganizationForm mode="create" />
    </div>
  );
}
