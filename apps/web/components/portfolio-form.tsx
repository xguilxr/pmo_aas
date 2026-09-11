"use client";

/**
 * FASE-4 (revamp v2, US-E) — alta y edición de portafolios, para
 * `/pmo/config`. Equivalente a `program-modal.tsx` pero para portafolios,
 * que hasta ahora no tenían UI (`createPortfolio`/`updatePortfolio` sin
 * consumidor).
 */
import { useEffect, useState } from "react";

import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { Modal } from "@/components/ui/modal";
import { listActors, type Actor } from "@/lib/api/areas";
import { ApiError } from "@/lib/api";
import {
  createPortfolio,
  updatePortfolio,
  type Portfolio,
} from "@/lib/api/organizations";

export function PortfolioForm({
  open,
  organizationId,
  portafolio,
  onClose,
  onSaved,
}: {
  open: boolean;
  organizationId: string;
  /** Sin ella, el formulario crea; con ella, edita. */
  portafolio?: Portfolio | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [description, setDescription] = useState("");
  const [ownerActorId, setOwnerActorId] = useState("");
  const [isActive, setIsActive] = useState(true);
  const [actores, setActores] = useState<Actor[]>([]);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setName(portafolio?.name ?? "");
    setCode(portafolio?.code ?? "");
    setDescription(portafolio?.description ?? "");
    setOwnerActorId(portafolio?.owner_actor_id ?? "");
    setIsActive(portafolio?.is_active ?? true);
    setError(null);
  }, [open, portafolio]);

  useEffect(() => {
    if (!open) return;
    listActors({ organization_id: organizationId, is_active: true })
      .then(setActores)
      .catch(() => setActores([]));
  }, [open, organizationId]);

  async function guardar() {
    if (!name.trim()) return;
    setGuardando(true);
    setError(null);
    try {
      const body = {
        name: name.trim(),
        code: code.trim() || null,
        description: description.trim() || null,
        owner_actor_id: ownerActorId || null,
        is_active: isActive,
      };
      if (portafolio) {
        await updatePortfolio(portafolio.id, body);
      } else {
        await createPortfolio(organizationId, body);
      }
      onSaved();
    } catch (e) {
      setError(
        e instanceof ApiError ? e.message : "No se pudo guardar el portafolio.",
      );
    } finally {
      setGuardando(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={portafolio ? "Editar portafolio" : "Nuevo portafolio"}
      size="lg"
    >
      <div className="space-y-4">
        {error ? <Banner variant="danger">{error}</Banner> : null}
        <div>
          <label
            htmlFor="pf_name"
            className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
          >
            Nombre
          </label>
          <Input
            id="pf_name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            minLength={2}
            autoFocus
          />
        </div>
        <div>
          <label
            htmlFor="pf_code"
            className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
          >
            Código
          </label>
          <Input
            id="pf_code"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="Ej. TRX-26"
          />
        </div>
        <div>
          <label
            htmlFor="pf_desc"
            className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
          >
            Descripción
          </label>
          <Textarea
            id="pf_desc"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
          />
        </div>
        <div>
          <label
            htmlFor="pf_owner"
            className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
          >
            Dueño (sponsor ejecutivo)
          </label>
          <Select
            id="pf_owner"
            value={ownerActorId}
            onChange={(e) => setOwnerActorId(e.target.value)}
          >
            <option value="">Sin asignar</option>
            {actores.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </Select>
        </div>
        <div className="flex items-center justify-between rounded-[var(--radius-md)] border border-[var(--border-default)] px-4 py-3">
          <span className="text-sm font-medium text-[var(--color-primary)]">Activo</span>
          <Switch checked={isActive} onChange={setIsActive} />
        </div>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose} disabled={guardando}>
            Cancelar
          </Button>
          <Button
            type="button"
            onClick={guardar}
            disabled={guardando || !name.trim()}
            loading={guardando}
          >
            Guardar
          </Button>
        </div>
      </div>
    </Modal>
  );
}
