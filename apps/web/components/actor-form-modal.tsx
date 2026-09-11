"use client";

/**
 * FASE-6 (revamp v2, US-B) — alta de recursos desde `/pmo/resources`.
 * Wireframe W4. `organization_id` es fijo (la organización activa, no
 * editable): DEC-038 hace la unicidad del correo por organización, así que
 * el alta tiene que decir en cuál se está creando.
 */
import { useEffect, useState } from "react";

import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { ApiError } from "@/lib/api";
import { createActor, listAreas, listTeams, type Area, type Team } from "@/lib/api/areas";

export function ActorFormModal({
  open,
  organizationId,
  organizationName,
  onClose,
  onSaved,
}: {
  open: boolean;
  organizationId: string;
  organizationName: string;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [company, setCompany] = useState("");
  const [areaId, setAreaId] = useState("");
  const [teamId, setTeamId] = useState("");
  const [areas, setAreas] = useState<Area[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setName("");
    setEmail("");
    setCompany("");
    setAreaId("");
    setTeamId("");
    setError(null);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    listAreas({ organization_id: organizationId, is_active: true, include_global: true })
      .then(setAreas)
      .catch(() => setAreas([]));
  }, [open, organizationId]);

  useEffect(() => {
    if (!areaId) {
      setTeams([]);
      setTeamId("");
      return;
    }
    listTeams({ area_id: areaId, is_active: true })
      .then(setTeams)
      .catch(() => setTeams([]));
  }, [areaId]);

  async function guardar() {
    if (!name.trim()) return;
    setGuardando(true);
    setError(null);
    try {
      await createActor({
        name: name.trim(),
        email: email.trim() || null,
        company: company.trim() || null,
        area_id: areaId || null,
        team_id: teamId || null,
        organization_id: organizationId,
        is_active: true,
      });
      onSaved();
    } catch (e) {
      if (e instanceof ApiError && e.code === "ACTOR_EMAIL_DUPLICATE") {
        setError(`Ya existe un recurso con ese correo en ${organizationName}.`);
      } else {
        setError(e instanceof ApiError ? e.message : "No se pudo crear el recurso.");
      }
    } finally {
      setGuardando(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Nuevo recurso" size="lg">
      <div className="space-y-4">
        {error ? <Banner variant="danger">{error}</Banner> : null}
        <div>
          <label
            htmlFor="actor_org"
            className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
          >
            Organización
          </label>
          <Input id="actor_org" value={organizationName} disabled />
        </div>
        <div>
          <label
            htmlFor="actor_name"
            className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
          >
            Nombre
          </label>
          <Input
            id="actor_name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            minLength={2}
            autoFocus
          />
        </div>
        <div>
          <label
            htmlFor="actor_email"
            className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
          >
            Correo
          </label>
          <Input
            id="actor_email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <p className="mt-1 text-xs text-[var(--color-tertiary)]">
            Es la clave de unicidad dentro de esta organización.
          </p>
        </div>
        <div>
          <label
            htmlFor="actor_company"
            className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
          >
            Empresa / proveedor
          </label>
          <Input
            id="actor_company"
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            placeholder="Vacío = interno"
          />
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <label
              htmlFor="actor_area"
              className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
            >
              Área
            </label>
            <Select id="actor_area" value={areaId} onChange={(e) => setAreaId(e.target.value)}>
              <option value="">Sin asignar</option>
              {areas.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </Select>
          </div>
          <div>
            <label
              htmlFor="actor_team"
              className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
            >
              Equipo
            </label>
            <Select
              id="actor_team"
              value={teamId}
              onChange={(e) => setTeamId(e.target.value)}
              disabled={!areaId}
            >
              <option value="">Sin asignar</option>
              {teams.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </Select>
          </div>
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
            Crear
          </Button>
        </div>
      </div>
    </Modal>
  );
}
