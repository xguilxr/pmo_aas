import { redirect } from "next/navigation";

// BUG-019: /panel ahora es alias legacy. El resumen de la organización
// vive en /admin/organizations/[id] (la home de la organización); la
// edición en /admin/organizations/[id]/edit. Cualquier link viejo a
// /panel hace redirect permanente.
export default async function LegacyOrganizationPanelRedirect({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  redirect(`/admin/organizations/${id}`);
}
