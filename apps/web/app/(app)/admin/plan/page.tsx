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
import { AlertTriangle, Info } from "lucide-react";

import { Banner } from "@/components/ui/banner";
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
  sin_limite: "text-[var(--color-tertiary)]",
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
    <div className="space-y-4 p-6">
      <header>
        <nav className="text-[11px] text-[var(--text-tertiary)]">
          <span>Admin</span>
          <span className="mx-1">/</span>
          <span>Plan</span>
        </nav>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
          Plan de suscripción
        </h1>
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
        error ? null : (
          <span
            aria-hidden
            className="block h-40 animate-pulse rounded-[var(--radius-lg)] bg-[var(--color-muted)]"
          />
        )
      ) : (
        <>
          <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--shadow-sm)]">
            <div className="flex flex-wrap items-baseline gap-3">
              <span className="text-[11px] uppercase tracking-wide text-[var(--color-tertiary)]">
                Plan actual
              </span>
              <span className="text-xl font-semibold text-[var(--color-primary)]">
                {plan.tier_label}
              </span>
            </div>
            {/* La nota que evita la llamada de soporte por algo que no pasa. */}
            <p className="mt-2 flex items-start gap-1.5 text-[13px] text-[var(--color-secondary)]">
              <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
              {plan.note}
            </p>
            {plan.over_limit ? (
              <Banner variant="warning" className="mt-3">
                <span className="flex items-start gap-1.5">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
                  Hay recursos por encima del plan. Nada se ha bloqueado; para
                  ampliar los topes, habla con quien administra la plataforma.
                </span>
              </Banner>
            ) : null}
            {plan.undeclared_limits > 0 ? (
              <p className="mt-2 text-[11px] text-[var(--color-tertiary)]">
                {plan.undeclared_limits} de {plan.usage.length} recursos no tienen
                tope declarado. Sin tope no hay nada que comparar — no es que sea
                cero.
              </p>
            ) : null}
          </section>

          <section className="space-y-3 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--shadow-sm)]">
            <h2 className="text-sm font-semibold text-[var(--color-primary)]">
              Límites y consumo
            </h2>
            <ul className="space-y-3">
              {plan.usage.map((u) => (
                <li key={u.key}>
                  <div className="flex flex-wrap items-baseline justify-between gap-2 text-[13px]">
                    <span className="font-medium">{u.label}</span>
                    <span className={CLASE_TEXTO[u.state]}>
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
                      className="mt-1 h-1.5 w-full overflow-hidden rounded bg-[var(--color-muted)]"
                      role="presentation"
                    >
                      <div
                        className={`h-full ${CLASE_BARRA[u.state]}`}
                        style={{ width: `${Math.min(u.percent, 100)}%` }}
                      />
                    </div>
                  ) : null}
                  <p className="mt-1 text-[11px] text-[var(--color-tertiary)]">
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
