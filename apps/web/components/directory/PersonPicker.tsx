"use client";

// US-117 / BUG-056 — picker reusable de persona del proyecto, alimentado
// por eligible-actors (participations activas). Soporta inline-create
// que (a) crea actor en el catálogo tenant, (b) crea participation
// activa en el proyecto, (c) autoselecciona el nuevo actor.

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { createActor } from "@/lib/api/areas";
import { getProject } from "@/lib/api/projects";
import {
  createParticipation,
  listEligibleActors,
  type ActorMini,
} from "@/lib/api/project-directory";

type Props = {
  projectId: string;
  value: string | null | undefined;
  onChange: (actorId: string | null) => void;
  disabled?: boolean;
  placeholder?: string;
  className?: string;
  /** Si true, oculta el botón "+ Crear y agregar al proyecto" inline. */
  hideCreate?: boolean;
};

export function PersonPicker({
  projectId,
  value,
  onChange,
  disabled,
  placeholder = "Sin asignar",
  className,
  hideCreate,
}: Props) {
  const [actors, setActors] = useState<ActorMini[]>([]);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  // BUG-107 — la organización del proyecto, para que el alta en línea no
  // fabrique un recurso global. `eligible-actors` ya filtra la lista desde
  // BUG-103; lo que faltaba era no crear recursos que sirven a todas las
  // organizaciones cada vez que alguien usa este atajo.
  const [organizationId, setOrganizationId] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const rows = await listEligibleActors(projectId);
      setActors(rows);
    } catch {
      setActors([]);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    let vigente = true;
    getProject(projectId)
      .then((p) => {
        if (vigente) setOrganizationId((p as any)?.organization_id ?? null);
      })
      .catch(() => {
        if (vigente) setOrganizationId(null);
      });
    return () => {
      vigente = false;
    };
  }, [projectId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function submitCreate() {
    if (!newName.trim()) return;
    setBusy(true);
    setErr(null);
    try {
      const actor = await createActor({
        name: newName.trim(),
        email: newEmail.trim() || undefined,
        // BUG-107: nace en la organización del proyecto desde el que se crea.
        organization_id: organizationId || undefined,
      } as any);
      await createParticipation(projectId, {
        actor_id: actor.id,
        is_active: true,
        is_primary: true,
      });
      await refresh();
      onChange(actor.id);
      setCreating(false);
      setNewName("");
      setNewEmail("");
    } catch (e: any) {
      setErr(e?.message ?? "Error al crear");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={`space-y-1 ${className ?? ""}`}>
      {!creating ? (
        <div className="flex items-center gap-1">
          <Select
            value={value ?? ""}
            disabled={disabled || loading}
            onChange={(e) => onChange(e.target.value || null)}
          >
            <option value="">{placeholder}</option>
            {actors.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
                {a.email ? ` — ${a.email}` : ""}
              </option>
            ))}
          </Select>
          {!hideCreate && (
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={() => setCreating(true)}
              disabled={disabled}
              title="Crear y agregar al proyecto"
            >
              + Nueva
            </Button>
          )}
        </div>
      ) : (
        <div className="space-y-1 rounded border border-[var(--border-default)] p-2">
          <div className="text-xs font-medium text-[var(--text-secondary)]">
            Nueva persona — se agrega al proyecto automáticamente
          </div>
          <Input
            placeholder="Nombre completo *"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
          />
          <Input
            placeholder="Email (opcional)"
            value={newEmail}
            onChange={(e) => setNewEmail(e.target.value)}
          />
          {err ? <p className="text-xs text-red-600">{err}</p> : null}
          <div className="flex justify-end gap-1">
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={() => {
                setCreating(false);
                setNewName("");
                setNewEmail("");
                setErr(null);
              }}
              disabled={busy}
            >
              Cancelar
            </Button>
            <Button
              type="button"
              size="sm"
              onClick={submitCreate}
              disabled={busy || !newName.trim()}
            >
              {busy ? "Creando…" : "Crear"}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
