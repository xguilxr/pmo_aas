"use client";

/**
 * US-205 — La organización activa, una sola vez y en el header.
 *
 * ## Qué problema resuelve
 *
 * Antes de esto el contexto estaba **disperso**: siete pantallas cargaban su
 * propia lista de organizaciones y su propio `<Select>`, cada una con su estado
 * y su clave en la URL. Elegir «Constructora Delta» en el tablero y pasar a la
 * lista de proyectos volvía a «todas»: el filtro no viajaba, así que la persona
 * lo volvía a poner en cada pantalla, o —peor— leía la pantalla siguiente
 * creyendo que seguía filtrada.
 *
 * El mockup del header lo concentra arriba: se elige una vez y **todo** opera
 * dentro de esa organización.
 *
 * ## Qué NO es esto
 *
 * **No es una frontera de seguridad.** El identificador viaja como
 * `organization_id` en la consulta, igual que cuando lo mandaba cada página. Lo
 * que impide ver la organización de otro no es este contexto: es el filtrado
 * por `tenant_id` y por visibilidad que hace la API (`scoped_project_ids`,
 * `UserScopeAssignment`). Cambiar este valor a mano en el navegador no abre
 * nada que la API no fuera a devolver igual.
 *
 * El claim `active_organization_id` **en el JWT** —que sí convierte esto en una
 * frontera— es de la oleada W2, en `US-214`. Hasta entonces el contexto vive en
 * el cliente y se persiste por inquilino en `localStorage`.
 *
 * ## Por qué la clave de `localStorage` lleva el inquilino
 *
 * Porque un identificador de organización de otro inquilino no solo es
 * inservible: produce consultas que devuelven vacío y se leen como «no hay
 * datos». Al cambiar de inquilino la selección tiene que empezar de cero, y la
 * única forma de que eso pase sola es que la clave no sea la misma.
 */
import { usePathname } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { listOrganizations, type Organization } from "@/lib/api/organizations";
import { getActiveTenantId, getStoredUser } from "@/lib/auth-storage";

/** «Todas las organizaciones»: el valor agregado, solo válido donde agrega. */
export const TODAS = "";

/**
 * Las rutas que muestran más de una organización a la vez.
 *
 * `reestructura-navegacion.md` §1: «Todas» está disponible **únicamente** en las
 * vistas que agregan. Se declara como lista y no como una comparación suelta
 * porque una lista se amplía y una comparación se duplica. US-207 le suma la
 * vista maestra.
 *
 * Hay dos formas de agregar y las dos cuentan:
 *
 * - **Por filtro** — `/dashboard` manda `organization_id` y sin él suma todo.
 * - **Por construcción** — `/admin/organizations` lista las organizaciones, y
 *   `/pmo` lleva en su tabla una columna de organización justamente para poder
 *   mostrar varias a la vez (US-207). Ninguna de las dos tiene un filtro de
 *   organización que aplicar.
 *
 * Las de construcción están aquí porque el switcher **se ve** en ellas. Si no
 * estuvieran, alguien que eligió «Todas» en el tablero llegaría a `/pmo` y
 * leería «Constructora Delta» en el header sobre una pantalla que enumera las
 * cuatro organizaciones: el desajuste al revés, y igual de malo.
 */
export const RUTAS_QUE_AGREGAN: readonly string[] = [
  "/dashboard",
  "/pmo",
  "/admin/organizations",
];

type Contexto = {
  /** Las organizaciones que el usuario ve en el inquilino activo. */
  organizaciones: Organization[];
  /**
   * Lo **elegido**, que puede ser `TODAS`. Se persiste tal cual: la elección
   * del usuario no se pierde por pasar por una pantalla que no sabe agregar.
   */
  activa: string;
  /**
   * Lo que va **a la consulta** en la ruta actual. Coincide con `activa` salvo
   * en un caso: `activa === TODAS` en una ruta que no agrega, donde vale la
   * primera organización.
   *
   * Los dos valores existen separados porque colapsarlos rompe una de las dos
   * mitades. Si se guardara solo lo efectivo, visitar la lista de proyectos
   * destruiría el «todas» del tablero. Si se usara solo lo elegido, la lista
   * consultaría «todas» mientras el control del header muestra una
   * organización concreta — el desajuste que hace que alguien lea una pantalla
   * creyendo que está filtrada.
   */
  efectiva: string;
  /** El objeto de la efectiva, o `null` si es «todas» o si aún no cargó. */
  activaObj: Organization | null;
  /** `true` si la ruta actual sabe agregar varias organizaciones. */
  agrega: boolean;
  elegir: (id: string) => void;
  cargando: boolean;
  /** `true` cuando el inquilino no tiene ninguna organización todavía. */
  vacio: boolean;
};

const Ctx = createContext<Contexto | null>(null);

function clave(tenantId: string | null | undefined): string {
  return `pmoaas:org-activa:${tenantId ?? "sin-tenant"}`;
}

export function OrganizacionActivaProvider({ children }: { children: ReactNode }) {
  // El inquilino activo no vive en `StoredUser`: lo guarda aparte
  // `getActiveTenantId()`, que es lo que escribe «Unirme como admin» del
  // superadmin (BUG-056). Se usa el identificador del usuario como respaldo
  // para que dos cuentas en el mismo navegador no compartan la selección.
  //
  // Se lee en un efecto y con los dos oyentes, como `app-shell` (BUG-005 y
  // BUG-009): leerlo en el render no se suscribe a nada, y el superadmin que
  // cambia de inquilino sin recargar se quedaría con las organizaciones del
  // anterior —una lista que ya no le corresponde y consultas que vuelven
  // vacías—.
  const [tenantId, setTenantId] = useState<string | null>(null);
  const pathname = usePathname();

  useEffect(() => {
    function leer() {
      setTenantId(getActiveTenantId() ?? getStoredUser()?.id ?? null);
    }
    leer();
    window.addEventListener("storage", leer);
    window.addEventListener("pmoaas:user-updated", leer);
    return () => {
      window.removeEventListener("storage", leer);
      window.removeEventListener("pmoaas:user-updated", leer);
    };
  }, []);
  const [organizaciones, setOrganizaciones] = useState<Organization[]>([]);
  const [activa, setActiva] = useState<string>(TODAS);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    // `null` significa «todavía no leído», no «sin inquilino»: dentro de
    // `<RequireAuth>` el perfil ya está en memoria, así que siempre acaba
    // habiendo uno. Se espera en vez de cargar con la clave «sin-tenant» y
    // volver a cargar un tick después con la buena.
    if (tenantId === null) return;
    let cancelado = false;
    setCargando(true);
    listOrganizations({ is_active: true })
      .then((r) => {
        if (cancelado) return;
        setOrganizaciones(r);
        // La guardada solo se restaura si **sigue existiendo** y el usuario
        // sigue viéndola: una organización archivada o retirada de su alcance
        // dejaría la aplicación entera filtrando por algo invisible.
        let guardada = TODAS;
        try {
          guardada = window.localStorage.getItem(clave(tenantId)) ?? TODAS;
        } catch {
          // Modo privado o almacenamiento lleno: se arranca en «todas».
        }
        setActiva(r.some((o) => o.id === guardada) ? guardada : TODAS);
      })
      .catch(() => {
        if (!cancelado) setOrganizaciones([]);
      })
      .finally(() => {
        if (!cancelado) setCargando(false);
      });
    return () => {
      cancelado = true;
    };
  }, [tenantId]);

  const elegir = useCallback(
    (id: string) => {
      setActiva(id);
      try {
        if (id) window.localStorage.setItem(clave(tenantId), id);
        else window.localStorage.removeItem(clave(tenantId));
      } catch {
        // Que no se pueda recordar no impide que se pueda elegir.
      }
    },
    [tenantId],
  );

  const valor = useMemo<Contexto>(() => {
    const agrega = RUTAS_QUE_AGREGAN.includes(pathname);
    const efectiva =
      activa || (agrega ? TODAS : (organizaciones[0]?.id ?? TODAS));
    return {
      organizaciones,
      activa,
      efectiva,
      activaObj: organizaciones.find((o) => o.id === efectiva) ?? null,
      agrega,
      elegir,
      cargando,
      vacio: !cargando && organizaciones.length === 0,
    };
  }, [organizaciones, activa, elegir, cargando, pathname]);

  return <Ctx.Provider value={valor}>{children}</Ctx.Provider>;
}

/**
 * El contexto de organización activa.
 *
 * Lanza si se usa fuera del proveedor, y a propósito: devolver un valor por
 * defecto dejaría una pantalla filtrando por «todas» sin que nadie lo note, que
 * es el fallo silencioso que esta US existe para cerrar.
 */
export function useOrganizacionActiva(): Contexto {
  const ctx = useContext(Ctx);
  if (!ctx) {
    throw new Error(
      "useOrganizacionActiva fuera de <OrganizacionActivaProvider>. Vive en " +
        "app/(app)/layout.tsx, así que toda pantalla del segmento lo tiene.",
    );
  }
  return ctx;
}

/**
 * El `organization_id` que va a la consulta, o `undefined` con «todas».
 *
 * Existe para que ninguna pantalla escriba `activa || undefined` a mano: la
 * cadena vacía es un valor válido de `<Select>` y un filtro **roto** en la API,
 * y esa conversión olvidada en un sitio devuelve la cartera completa donde
 * debería devolver una organización.
 */
export function useOrgFiltro(): string | undefined {
  return useOrganizacionActiva().efectiva || undefined;
}
