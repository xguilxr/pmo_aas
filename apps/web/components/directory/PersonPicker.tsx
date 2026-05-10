"use client";

// US-117 — dropdown reusable de assignee/owner filtrado por participations
// activas del proyecto. Pensado para reemplazar dropdowns globales en
// plan, RAID, cambios, lecciones, minutas.
//
// Uso:
//   <PersonPicker
//     projectId={projectId}
//     value={task.assignee_actor_id}
//     onChange={(id) => updateTask({ assignee_actor_id: id })}
//   />

import { useEffect, useState } from "react";
import { Plus } from "lucide-react";

import { Select } from "@/components/ui/select";
import {
  listEligibleActors,
  type ActorMini,
} from "@/lib/api/project-directory";

type Props = {
  projectId: string;
  value: string | null | undefined;
  onChange: (actorId: string | null) => void;
  onAddPerson?: () => void;
  disabled?: boolean;
  placeholder?: string;
  className?: string;
};

export function PersonPicker({
  projectId,
  value,
  onChange,
  onAddPerson,
  disabled,
  placeholder = "Sin asignar",
  className,
}: Props) {
  const [actors, setActors] = useState<ActorMini[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let active = true;
    setLoading(true);
    listEligibleActors(projectId)
      .then((rows) => {
        if (active) setActors(rows);
      })
      .catch(() => {
        if (active) setActors([]);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [projectId]);

  return (
    <div className={`flex items-center gap-1 ${className ?? ""}`}>
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
      {onAddPerson && (
        <button
          type="button"
          onClick={onAddPerson}
          aria-label="Agregar persona al proyecto"
          className="rounded p-1 text-[var(--color-tertiary)] hover:bg-[var(--color-subtle)] hover:text-[var(--color-primary)]"
          disabled={disabled}
        >
          <Plus className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}
