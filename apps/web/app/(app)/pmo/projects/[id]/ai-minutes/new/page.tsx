// US-142: ruta deprecada. Redirige a `minutes/new` (generador unificado
// con 3 modos: transcript / minuta / manual). Bookmarks viejos siguen
// funcionando. Se borrará en el próximo cleanup pasado un sprint de
// gracia.
import { redirect } from "next/navigation";

export default function DeprecatedAiMinutesNewPage({
  params,
}: {
  params: { id: string };
}) {
  redirect(`/pmo/projects/${params.id}/minutes/new`);
}
