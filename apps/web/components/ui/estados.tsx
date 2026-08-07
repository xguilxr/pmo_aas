"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

/**
 * MCS DIS-03 — los cinco estados de una pantalla, en un solo sitio.
 *
 * > «Toda pantalla DEBE definir sus estados: vacío, en carga, con datos, error
 * > y sin permiso.»
 *
 * ## Lo que se midió
 *
 * De las 75 pantallas, **13 tenían señales de los cuatro** estados (el quinto,
 * «con datos», se da por implementado si la pantalla existe). Faltaban: 12 sin
 * carga, 20 sin error, 31 sin vacío y **60 sin «sin permiso»**.
 *
 * ## Por qué no se resuelve pantalla por pantalla
 *
 * El plan de remediación avisó: «hacerlo mecánicamente produciría 70 estados
 * malos». Tenía razón para el vacío —qué dice una lista vacía es una decisión
 * de producto por pantalla— y **no** para los otros tres.
 *
 * Un error de red, un 403 y una espera se ven igual en las 75, y sesenta copias
 * de la misma tarjeta divergen: basta que una aprenda a ofrecer «reintentar» y
 * las otras cincuenta y nueve no. Esos tres se resuelven **en la frontera del
 * segmento** (`app/(app)/error.tsx` y `loading.tsx`, que es la respuesta que el
 * propio framework tiene para esto), y este archivo es su vocabulario.
 *
 * Definir un estado una vez para todo un segmento **es definirlo**, que es lo
 * que el requisito pide. Hacerlo setenta veces es repetirlo.
 */

type EstadoProps = {
  /** Qué pasó, en una línea. Sin valor por defecto: cada estado dice lo suyo. */
  titulo: string;
  /** Qué puede hacer quien lo lee. Sin acción, un estado es un callejón. */
  accion?: ReactNode;
  detalle?: string;
  className?: string;
};

function Caja({
  titulo,
  detalle,
  accion,
  icono,
  className,
}: EstadoProps & { icono: string }) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 rounded-lg border border-[var(--border-default)] px-6 py-12 text-center",
        className,
      )}
      role="status"
    >
      <span aria-hidden="true" className="text-3xl">
        {icono}
      </span>
      <p className="text-sm font-medium text-[var(--text-primary)]">{titulo}</p>
      {detalle ? (
        <p className="max-w-prose text-xs text-[var(--text-tertiary)]">{detalle}</p>
      ) : null}
      {accion}
    </div>
  );
}

/**
 * No hay nada que mostrar **y eso es normal**.
 *
 * `titulo` y `accion` van sin valor por defecto porque el vacío es el único de
 * los cinco que es distinto en cada pantalla: «aún no has creado ningún
 * proyecto» y «ningún riesgo coincide con el filtro» piden cosas opuestas —una
 * invita a crear, la otra a quitar el filtro— y un texto genérico no sirve
 * para ninguna de las dos.
 */
export function Vacio({ titulo, detalle, accion, className }: EstadoProps) {
  return (
    <Caja icono="—" titulo={titulo} detalle={detalle} accion={accion} className={className} />
  );
}

/** Se está esperando. Se distingue del vacío a propósito: aún no se sabe. */
export function Cargando({ que }: { que: string }) {
  return (
    <div
      className="flex items-center justify-center gap-2 px-6 py-12 text-sm text-[var(--text-tertiary)]"
      role="status"
      aria-live="polite"
    >
      <span
        aria-hidden="true"
        className="h-3 w-3 animate-pulse rounded-full bg-[var(--color-primary)]"
      />
      Cargando {que}…
    </div>
  );
}

/**
 * Algo falló al traer los datos.
 *
 * Lleva `reintentar` porque un error sin salida obliga a recargar el navegador,
 * y quien lo haga perderá lo que tuviera a medias en otra pestaña del flujo.
 */
export function ErrorDeCarga({
  titulo,
  detalle,
  reintentar,
  className,
}: {
  titulo: string;
  detalle?: string;
  reintentar?: () => void;
  className?: string;
}) {
  return (
    <Caja
      icono="⚠"
      titulo={titulo}
      detalle={detalle}
      className={className}
      accion={
        reintentar ? (
          <button
            type="button"
            onClick={reintentar}
            className="rounded-md border border-[var(--border-default)] px-3 py-1.5 text-xs font-medium text-[var(--text-primary)] hover:bg-[var(--color-bg-muted)]"
          >
            Reintentar
          </button>
        ) : undefined
      }
    />
  );
}

/**
 * La sesión es válida y esto no le corresponde.
 *
 * **No es lo mismo que «no autenticado»**, y confundirlos es el fallo que
 * manda a alguien a iniciar sesión otra vez con la sesión ya iniciada. El
 * 401 lo trata `RequireAuth`; esto es el 403.
 *
 * Dice a quién pedirlo porque, si no, el estado informa y no resuelve: quien
 * lo ve sabe que no puede y no sabe qué hacer al respecto.
 */
export function SinPermiso({ detalle }: { detalle?: string }) {
  return (
    <Caja
      icono="🔒"
      titulo="No tienes permiso para ver esto"
      detalle={
        detalle ??
        "Tu cuenta existe y la sesión es válida; lo que falta es el permiso. " +
          "Pídeselo a quien administre tu organización."
      }
      accion={
        <Link
          href="/dashboard"
          className="rounded-md border border-[var(--border-default)] px-3 py-1.5 text-xs font-medium text-[var(--text-primary)] hover:bg-[var(--color-bg-muted)]"
        >
          Volver al tablero
        </Link>
      }
    />
  );
}
