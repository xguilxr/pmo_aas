"use client";

/**
 * US-214 — El selector de inquilino del header.
 *
 * Del artboard «Header — contexto tenant/org»: «Switcher de tenant — **visible
 * solo con más de una membresía**. Cambiar re-emite la sesión y recarga la
 * aplicación en el tenant elegido.»
 *
 * ## Por qué no se muestra con una sola membresía
 *
 * Un desplegable de un elemento es un control que no hace nada, y ocupa el sitio
 * más caro de la pantalla. La mayoría de los usuarios pertenecen a un inquilino;
 * para ellos este control es ruido. Con dos o más, es la única forma de llegar
 * al otro.
 *
 * ## Por qué recarga la aplicación entera
 *
 * A diferencia del selector de organización —que solo cambia un filtro y
 * re-consulta—, cambiar de inquilino cambia **todo**: las organizaciones, los
 * proyectos, el catálogo de personas, la marca, la moneda preferida, los
 * permisos. Re-consultar pantalla por pantalla dejaría media interfaz con datos
 * del inquilino anterior durante el tiempo que tarde cada consulta, y esa mezcla
 * es peor que una recarga: alguien tomaría una decisión mirando el proyecto de un
 * cliente con el nombre de otro en el encabezado.
 *
 * ## De dónde sale la lista
 *
 * De `GET /auth/my-tenants`, que la lee de la **tabla** de membresías y no del
 * token. Un claim puede llevar una membresía ya revocada; seleccionarla fallaría
 * (AM-16), y ofrecerla es prometer algo que no se va a poder hacer.
 */
import { useEffect, useState } from "react";

import { Select } from "@/components/ui/select";
import { ApiError, apiFetch } from "@/lib/api";

type Inquilino = {
  id: string;
  name: string;
  slug: string | null;
  organizations: number;
};

type MisInquilinos = {
  active_tenant_id: string | null;
  tenants: Inquilino[];
};

export function SwitcherDeInquilino() {
  const [datos, setDatos] = useState<MisInquilinos | null>(null);
  const [cambiando, setCambiando] = useState(false);

  useEffect(() => {
    let vivo = true;
    apiFetch<MisInquilinos>("/api/v1/auth/my-tenants")
      .then((d) => {
        if (vivo) setDatos(d);
      })
      // El fallo se traga a propósito: sin este control la aplicación funciona
      // igual en el inquilino activo. Un banner de error aquí ocuparía el header
      // para contar un problema que no impide trabajar.
      .catch(() => {
        if (vivo) setDatos(null);
      });
    return () => {
      vivo = false;
    };
  }, []);

  async function cambiar(id: string) {
    if (!datos || id === datos.active_tenant_id) return;
    setCambiando(true);
    try {
      await apiFetch("/api/v1/auth/switch-tenant", {
        method: "POST",
        body: { tenant_id: id },
      });
      // La recarga es el punto: ver el comentario de arriba. Va a la raíz y no a
      // la ruta actual porque la ruta actual puede ser el detalle de un proyecto
      // que en el inquilino nuevo no existe, y aterrizar en un 404 tras cambiar
      // de cliente se lee como que el cambio falló.
      window.location.assign("/dashboard");
    } catch (e) {
      setCambiando(false);
      // Aquí sí se avisa: el usuario pidió algo explícito y no ocurrió. El caso
      // real es una membresía revocada mientras la sesión seguía abierta.
      alert(
        e instanceof ApiError
          ? e.message
          : "No se pudo cambiar de organización.",
      );
    }
  }

  // Con una sola membresía —o ninguna, o si la lista no cargó— no hay nada que
  // elegir y el control no se pinta.
  if (!datos || datos.tenants.length < 2) return null;

  return (
    <Select
      aria-label="Inquilino activo"
      title="Cambiar de inquilino recarga la aplicación"
      value={datos.active_tenant_id ?? ""}
      disabled={cambiando}
      onChange={(e) => void cambiar(e.target.value)}
      className="hidden h-[30px] max-w-[220px] border-[var(--border-default)] bg-[var(--color-surface)] py-0 text-[13px] lg:block"
    >
      {datos.tenants.map((t) => (
        <option key={t.id} value={t.id}>
          {t.name}
          {/* El conteo del artboard. Con `<select>` no cabe una segunda línea,
              así que va entre paréntesis: es el dato que distingue dos
              inquilinos de nombre parecido. */}
          {` (${t.organizations} organizacion${t.organizations === 1 ? "" : "es"})`}
        </option>
      ))}
    </Select>
  );
}
