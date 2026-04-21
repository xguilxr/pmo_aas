import { redirect } from "next/navigation";

// ENH-006: /tasks ya no existe como editor separado — se consolidó en
// /plan (lista + gantt + editor inline). Redirect permanente para
// links viejos.
export default async function LegacyTasksRedirect({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  redirect(`/admin/projects/${id}/plan?view=list`);
}
