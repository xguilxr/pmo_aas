"use client";

/**
 * US-222 / EP021 — El consumo de IA del inquilino.
 *
 * Del artboard «Admin — IA», fila «Consumo / alertas». Es la única de las cinco
 * filas de ese artboard que no dependía de una decisión pendiente: `AIJob` ya
 * guardaba tokens, modelo y proveedor desde US-057. Las otras cuatro —skills,
 * tools, prompts, workflows y roles de agente— están en `EP021-catalogo-de-ia.md`
 * con las preguntas que las bloquean.
 *
 * ## Por qué no hay una cifra en pesos
 *
 * La tarifa de cada modelo la fija su proveedor, cambia cuando él la cambia y no
 * vive en esta plataforma. Un importe calculado con una tarifa de hace seis meses
 * se leería como el gasto y no lo sería — y nadie volvería a comprobarlo. Se
 * cuentan tokens, que es el dato que sí es nuestro, y la pantalla dice por qué.
 *
 * ## Los fallidos van con el total
 *
 * «120 trabajos este mes» con treinta fallidos se lee como éxito. Es la misma
 * pareja que el costo con «sin tarifa» (US-215) y la importación con «quedaron
 * fuera» (US-216): un total sin su hueco miente por omisión.
 */
import { useEffect, useState } from "react";

import { Banner } from "@/components/ui/banner";
import { Icono } from "@/components/ui/icono";
import { MarcaDeDatos, useLectura } from "@/components/ui/marca-de-datos";
import { ApiError } from "@/lib/api";
import { getAIUsage, type ConsumoDeIA } from "@/lib/api/admin-ai";

const NUMERO = new Intl.NumberFormat("es-MX");

/** `2026-08` → `ago 26`. Corto, porque son seis columnas. */
function mes(clave: string): string {
  const [anio, m] = clave.split("-");
  const nombres = [
    "ene", "feb", "mar", "abr", "may", "jun",
    "jul", "ago", "sep", "oct", "nov", "dic",
  ];
  return `${nombres[Number(m) - 1] ?? m} ${anio.slice(2)}`;
}

export function ConsumoDeIAPanel() {
  const [datos, setDatos] = useState<ConsumoDeIA | null>(null);
  const [error, setError] = useState<string | null>(null);
  const leido = useLectura(datos);

  useEffect(() => {
    getAIUsage()
      .then(setDatos)
      .catch((e) =>
        setError(
          e instanceof ApiError
            ? e.message
            : "No se pudo cargar el consumo de IA.",
        ),
      );
  }, []);

  if (error) return <Banner variant="danger">{error}</Banner>;
  if (datos === null) {
    return (
      <span
        aria-hidden
        className="block h-32 animate-pulse rounded-[var(--radius-lg)] bg-[var(--color-muted)]"
      />
    );
  }

  // El pico de la serie da la escala de las barras. Con todo en cero no hay
  // escala, y se dice en vez de pintar seis barras vacías.
  const pico = Math.max(...datos.by_month.map((m) => m.tokens_total), 0);
  const sinNada = datos.by_month.every((m) => m.jobs === 0);

  return (
    <section
      aria-label="Consumo de IA"
      className="space-y-3 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--shadow-sm)]"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Icono nombre="activity" size={15} className="text-[var(--color-tertiary)]" />
            <h2 className="text-sm font-semibold text-[var(--color-primary)]">
              Consumo
            </h2>
          </div>
          {leido ? (
            <MarcaDeDatos
              periodo="acumulado"
              detalle="por mes calendario, seis meses"
              actualizado={leido}
            />
          ) : null}
        </div>
        <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 text-xs">
          <span>
            <span className="text-[var(--color-tertiary)]">Este mes</span>{" "}
            <span className="font-semibold">
              {NUMERO.format(datos.jobs_this_month)}
            </span>{" "}
            trabajos
          </span>
          <span>
            <span className="font-semibold">
              {NUMERO.format(datos.tokens_this_month)}
            </span>{" "}
            tokens
          </span>
          {datos.failed_this_month > 0 ? (
            <span className="flex items-center gap-1 text-[var(--color-danger-fg)]">
              <Icono nombre="triangle-alert" size={13} />
              {datos.failed_this_month} fallidos
            </span>
          ) : null}
        </div>
      </div>

      {sinNada ? (
        <p className="text-[13px] text-[var(--color-secondary)]">
          Este inquilino no ha usado la IA en los últimos seis meses. Con la IA
          desactivada es lo esperable; con un proveedor conectado, quiere decir
          que nadie ha generado una minuta ni un reporte todavía.
        </p>
      ) : (
        <>
          <div className="flex items-end gap-2">
            {datos.by_month.map((m) => (
              <div key={m.month} className="flex flex-1 flex-col items-center gap-1">
                <div
                  className="flex h-16 w-full items-end"
                  title={`${NUMERO.format(m.tokens_total)} tokens · ${m.jobs} trabajos`}
                >
                  {/* Un mes en cero deja la columna vacía a propósito: es el dato,
                      no un fallo de carga. */}
                  <div
                    className="w-full rounded-t bg-[var(--color-primary)]"
                    style={{
                      height: pico > 0 ? `${(m.tokens_total * 100) / pico}%` : "0%",
                    }}
                  />
                </div>
                <span className="text-[10px] text-[var(--color-tertiary)]">
                  {mes(m.month)}
                </span>
              </div>
            ))}
          </div>

          {datos.by_model.length > 0 ? (
            <div>
              <h3 className="text-[11px] font-medium uppercase tracking-wide text-[var(--color-tertiary)]">
                Por modelo, este mes
              </h3>
              <ul className="mt-1 divide-y divide-[var(--border-subtle)] text-[13px]">
                {datos.by_model.map((m) => (
                  <li
                    key={`${m.model ?? "sin"}-${m.provider ?? "sin"}`}
                    className="flex items-center justify-between gap-2 py-1"
                  >
                    <span>
                      {/* `null` cuando el trabajo falló antes de saber qué modelo
                          lo iba a atender. Se nombra en vez de descartarse. */}
                      {m.model ?? "Sin modelo (falló antes de elegirlo)"}
                      {m.provider ? (
                        <span className="ml-1.5 text-[11px] text-[var(--color-tertiary)]">
                          {m.provider}
                        </span>
                      ) : null}
                    </span>
                    <span className="tabular-nums text-[var(--color-secondary)]">
                      {NUMERO.format(m.tokens_total)} tokens · {m.jobs}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </>
      )}

      <p className="flex items-start gap-1.5 text-[11px] text-[var(--color-tertiary)]">
        <Icono nombre="info" size={14} className="mt-0.5 shrink-0" />
        {datos.note}
      </p>
    </section>
  );
}
