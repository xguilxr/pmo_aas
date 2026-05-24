// US-142: ruta deprecada. Redirige a `minutes/new` (generador unificado
// con 3 modos: transcript / minuta / manual). Bookmarks viejos siguen
// funcionando. Se borrará en el próximo cleanup pasado un sprint de
// gracia.
import { redirect } from "next/navigation";

export default async function DeprecatedAiMinutesNewPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  redirect(`/pmo/projects/${id}/minutes/new`);
}
