"use client";

/**
 * US-221 — Admin › Plan: los límites del inquilino y su consumo.
 *
 * Del artboard «Admin — Plan (suscripción)», con la línea que manda sobre todo
 * lo demás: **«Solo lectura — sin paywall ni billing en esta fase»**.
 *
 * ## La pantalla lo dice, no solo el código
 *
 * Un usuario que ve «3/1 proyectos» y una barra roja asume que algo está
 * bloqueado y va a buscar a quién pedirle permiso. La nota de que no se hace
 * cumplir no es un detalle legal: es lo que evita una llamada de soporte por algo
 * que no está pasando.
 *
 * ## «Sin límite declarado» es una respuesta, no un hueco
 *
 * Los tres nombres de tier salen del artboard aprobado; los **números** de cada
 * uno no están en ningún documento de este repositorio. Así que el tope se
 * captura por inquilino, y donde no se capturó la pantalla lo dice — en vez de
 * pintar un cero, que diría «no puedes crear ninguna».
 */
import { useEffect, useState } from "react";

import { Banner } from "@/components/ui/banner";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Icono } from "@/components/ui/icono";
import { Skeleton } from "@/components/ui/skeleton";
import { MarcaDeDatos, useLectura } from "@/components/ui/marca-de-datos";
import { ApiError } from "@/lib/api";
import { getPlan, type EstadoDeUso, type EstadoDelPlan } from "@/lib/api/plan";

const CLASE_BARRA: Record<EstadoDeUso, string> = {
  sin_limite: "bg-[var(--color-muted)]",
  dentro: "bg-[var(--color-success-fg)]",
  al_limite: "bg-[var(--color-warning-fg)]",
  excedido: "bg-[var(--color-danger-fg)]",
};

const CLASE_TEXTO: Record<EstadoDeUso, string> = {
  sin_limite: "text-[var(--text-tertiary)]",
  dentro: "text-[var(--color-success-fg)]",
  al_limite: "text-[var(--color-warning-fg)]",
  excedido: "text-[var(--color-danger-fg)]",
};

export default function PlanPage() {
  const [plan, setPlan] = useState<EstadoDelPlan | null>(null);
  const [error, setError] = useState<string | null>(null);
  const leido = useLectura(plan);

  useEffect(() => {
    getPlan()
      .then(setPlan)
      .catch((e) =>
        setError(
          e instanceof ApiError
            ? e.message
            : "No se pudo cargar el plan del inquilino.",
        ),
      );
  }, []);

  return (
    <div className="space-y-4">
      <Breadcrumb
        items={[
          { href: "/admin", label: "Admin" },
          { label: "Plan" },
        ]}
      />
      <header className="flex flex-col gap-2">
        <div className="flex items-center gap-2.25">
          <Icono nombre="credit-card" size={20} className="text-[var(--text-primary)]" />
          <h1 className="text-2xl font-semibold tracking-[-0.02em] text-[var(--text-primary)]">
            Plan de suscripción
          </h1>
        </div>
        {leido && plan ? (
          <MarcaDeDatos
            periodo="vivo"
            detalle={`plan ${plan.tier_label}`}
            actualizado={leido}
          />
        ) : null}
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      {plan === null ? (
        error ? null : <Skeleton className="h-40 w-full" />
      ) : (
        <>
          <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--relieve-isla)]">
            <div className="flex flex-wrap items-baseline gap-3">
              <span className="text-[10.5px] font-semibold uppercase tracking-[0.07em] text-[var(--text-tertiary)]">
                Plan actual
              </span>
              <span className="text-2xl font-semibold capitalize tracking-[-0.02em] text-[var(--text-primary)]">
                {plan.tier_label}
              </span>
            </div>
            {/* La nota que evita la llamada de soporte por algo que no pasa. */}
            <p className="mt-2 flex items-start gap-1.5 text-[13px] text-[var(--text-secondary)]">
              <Icono nombre="info" size={14} className="mt-0.5 shrink-0 text-[var(--text-tertiary)]" />
              {plan.note}
            </p>
            {plan.over_limit ? (
              <Banner variant="warning" className="mt-3">
                Hay recursos por encima del plan. Nada se ha bloqueado; para
                ampliar los topes, habla con quien administra la plataforma.
              </Banner>
            ) : null}
            {plan.undeclared_limits > 0 ? (
              <p className="mt-2 text-[11px] text-[var(--text-tertiary)]">
                {plan.undeclared_limits} de {plan.usage.length} recursos no tienen
                tope declarado. Sin tope no hay nada que comparar — no es que sea
                cero.
              </p>
            ) : null}
          </section>

          <section className="space-y-3 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--relieve-isla)]">
            <h2 className="text-sm font-semibold text-[var(--text-primary)]">
              Límites y consumo
            </h2>
            <ul className="space-y-3">
              {plan.usage.map((u) => (
                <li key={u.key}>
                  <div className="flex flex-wrap items-baseline justify-between gap-2 text-[13px]">
                    <span className="font-medium text-[var(--text-primary)]">{u.label}</span>
                    <span className={`font-mono ${CLASE_TEXTO[u.state]}`}>
                      {u.limit === null
                        ? `${u.used} · ${plan.state_labels[u.state]}`
                        : `${u.used} / ${u.limit} · ${plan.state_labels[u.state]}`}
                    </span>
                  </div>
                  {/* Sin tope no se pinta barra: una barra necesita un
                      denominador, y dibujarla contra uno inventado convertiría
                      «no se sabe» en «vas bien». */}
                  {u.percent !== null ? (
                    <div
                      className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-[var(--color-muted)] shadow-[var(--hundido)]"
                      role="presentation"
                    >
                      <div
                        className={`h-full rounded-full ${CLASE_BARRA[u.state]}`}
                        style={{ width: `${Math.min(u.percent, 100)}%` }}
                      />
                    </div>
                  ) : null}
                  <p className="mt-1 text-[11px] text-[var(--text-tertiary)]">
                    {plan.consequences[u.key]}
                  </p>
                </li>
              ))}
            </ul>
          </section>
        </>
      )}
    </div>
  );
}
