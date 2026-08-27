"use client";

/**
 * US-088 — Botón "Eliminar permanentemente" reutilizable.
 *
 * Patrón two-step:
 *   1. Soft delete (botón "Borrar" existente) → entidad pasa a is_active=false.
 *   2. Este botón aparece para entidades inactivas. Click abre modal con:
 *      - cuenta de cascadas (proyectos hijos, BUs hijas, etc.) traída del preview,
 *      - input que el usuario debe re-tipear con el slug confirm exacto,
 *      - botón disabled hasta match.
 *   3. Confirm → DELETE /<entity>/{id}/permanent?confirm=<slug>.
 */
import { useEffect, useMemo, useState } from "react";

import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Icono } from "@/components/ui/icono";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { ApiError } from "@/lib/api";
import type { HardDeletePreview } from "@/lib/api/organizations";

type Props = {
  preview: () => Promise<HardDeletePreview>;
  hardDelete: (confirmSlug: string) => Promise<void>;
  onDeleted: () => void;
  // Texto opcional sobre la entidad para el cuerpo del modal.
  entityLabel?: string;
  // Variante visual del trigger.
  triggerVariant?: "danger" | "ghost";
  triggerLabel?: string;
  // Si es true, no renderiza nada cuando la entidad está activa.
  hideWhenActive?: boolean;
};

const CASCADE_LABELS: Record<string, string> = {
  projects: "proyectos",
  portfolios: "portafolios",
  programs: "programas",
  project_requests: "solicitudes de proyecto",
  projects_in_programs: "proyectos dentro de esos programas",
  projects_direct: "proyectos que cuelgan directo",
  project_links_to_unset: "proyectos quedan sin asignar",
  program_links_to_unset: "programas quedan sin asignar",
  memberships: "membresías de proyecto",
};

function describeCascade(cascades: Record<string, number>): string[] {
  return Object.entries(cascades)
    .filter(([, n]) => n > 0)
    .map(([k, n]) => `${n} ${CASCADE_LABELS[k] ?? k}`);
}

export function HardDeleteButton({
  preview,
  hardDelete,
  onDeleted,
  entityLabel,
  triggerVariant = "danger",
  triggerLabel = "Eliminar permanentemente",
  hideWhenActive = false,
}: Props) {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<HardDeletePreview | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [typed, setTyped] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!open) {
      setTyped("");
      setError(null);
    }
  }, [open]);

  async function loadPreview() {
    setLoading(true);
    setError(null);
    try {
      const p = await preview();
      setData(p);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo cargar el preview");
    } finally {
      setLoading(false);
    }
  }

  async function handleClick() {
    setOpen(true);
    await loadPreview();
  }

  async function handleConfirm() {
    if (!data) return;
    setSubmitting(true);
    setError(null);
    try {
      await hardDelete(data.confirm_slug);
      setOpen(false);
      onDeleted();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo eliminar permanentemente");
    } finally {
      setSubmitting(false);
    }
  }

  const cascadeLines = useMemo(
    () => (data ? describeCascade(data.cascades) : []),
    [data],
  );

  const matches = data && typed === data.confirm_slug;

  // Si la prop hideWhenActive está activa, el botón solo se muestra una vez
  // sabemos que la entidad está inactiva. El check inicial se hace al abrir
  // el modal — así que renderizamos el botón siempre, pero el modal se
  // encarga de bloquear si está activa (backend devuelve 409).
  // Para evitar el extra click, los callsites pueden setear hideWhenActive
  // y filtrar visualmente: este componente no tiene estado pre-load para
  // saber si está activa.
  void hideWhenActive;

  return (
    <>
      <Button
        type="button"
        variant={triggerVariant}
        size="sm"
        onClick={handleClick}
        aria-label={triggerLabel}
      >
        <Icono nombre="bin" size={15} />
        {triggerLabel}
      </Button>

      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title="Eliminar permanentemente"
        description="Esta acción es irreversible. La entidad y sus dependencias serán borradas físicamente de la base de datos."
        size="lg"
        footer={
          <>
            <Button
              type="button"
              variant="secondary"
              onClick={() => setOpen(false)}
              disabled={submitting}
            >
              Cancelar
            </Button>
            <Button
              type="button"
              variant="danger"
              onClick={handleConfirm}
              loading={submitting}
              disabled={!matches || submitting}
            >
              Eliminar para siempre
            </Button>
          </>
        }
      >
        {loading ? (
          <p className="text-sm text-[var(--color-tertiary)]">Cargando preview…</p>
        ) : error && !data ? (
          <Banner variant="danger">{error}</Banner>
        ) : data ? (
          <div className="space-y-4">
            {error ? <Banner variant="danger">{error}</Banner> : null}

            {data.is_active ? (
              <Banner variant="warning">
                Esta entidad sigue activa. Desactívala primero (botón Borrar)
                antes de eliminarla permanentemente.
              </Banner>
            ) : null}

            {data.blockers.length > 0 ? (
              <Banner variant="danger">
                No se puede eliminar todavía: existen referencias bloqueantes:
                {" "}
                {data.blockers.join(", ")}
              </Banner>
            ) : null}

            <div>
              <p className="text-sm font-medium text-[var(--color-primary)]">
                {entityLabel ?? data.entity_type}: <strong>{data.entity_name}</strong>
              </p>
              {cascadeLines.length > 0 ? (
                <div className="mt-2 rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-subtle)] p-3 text-sm text-[var(--color-secondary)]">
                  <p className="font-medium">Esto también borrará en cascada:</p>
                  <ul className="mt-1 list-disc pl-5">
                    {cascadeLines.map((l) => (
                      <li key={l}>{l}</li>
                    ))}
                  </ul>
                </div>
              ) : (
                <p className="mt-2 text-sm text-[var(--color-tertiary)]">
                  No hay dependencias en cascada.
                </p>
              )}
            </div>

            <div>
              <label
                htmlFor="hard-delete-confirm"
                className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
              >
                Para confirmar, escribe exactamente:{" "}
                <code className="rounded bg-[var(--color-subtle)] px-1.5 py-0.5 text-xs">
                  {data.confirm_slug}
                </code>
              </label>
              <Input
                id="hard-delete-confirm"
                value={typed}
                onChange={(e) => setTyped(e.target.value)}
                placeholder={data.confirm_slug}
                disabled={
                  submitting || data.is_active || data.blockers.length > 0
                }
                autoComplete="off"
              />
            </div>
          </div>
        ) : null}
      </Modal>
    </>
  );
}
