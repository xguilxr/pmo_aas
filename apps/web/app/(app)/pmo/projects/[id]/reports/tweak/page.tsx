// ENH-121 / Cleanup: ruta deprecada. El flujo de "Crear reporte
// (IA + plantilla)" se fusionó al Builder unificado (Sprint 32 Bloque 2,
// US-148/ENH-123/124/125). Redirige para preservar bookmarks; se borrará
// completamente en el próximo cleanup.
import { redirect } from "next/navigation";

export default async function DeprecatedTweakPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  redirect(`/pmo/projects/${id}/reports/builder`);
}
