// ENH-121 / Cleanup: ruta deprecada. El flujo de "Crear reporte
// (IA + plantilla)" se fusionó al Builder unificado (Sprint 32 Bloque 2,
// US-148/ENH-123/124/125). Redirige para preservar bookmarks; se borrará
// completamente en el próximo cleanup.
import { redirect } from "next/navigation";

export default function DeprecatedTweakPage({
  params,
}: {
  params: { id: string };
}) {
  redirect(`/pmo/projects/${params.id}/reports/builder`);
}
