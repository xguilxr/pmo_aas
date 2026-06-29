"use client";

// ENH-083 — picker reusable de Área asignada al proyecto. Inline-create
// crea área tenant + auto-assign al proyecto (setAreaAssignments).

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { listAreasByProject, type Area } from "@/lib/api/areas";
import { createOrAdoptAreaForProject } from "@/lib/api/area-helpers";

type Props = {
  projectId: string;
  value: string | null | undefined;
  onChange: (areaId: string | null) => void;
  disabled?: boolean;
  placeholder?: string;
  className?: string;
};

export function ProjectAreaPicker({
  projectId,
  value,
  onChange,
  disabled,
  placeholder = "Sin asignar",
  className,
}: Props) {
  const [areas, setAreas] = useState<Area[]>([]);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const rows = await listAreasByProject(projectId);
      setAreas(rows);
    } catch {
      setAreas([]);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function submitCreate() {
    if (!newName.trim()) return;
    setBusy(true);
    setErr(null);
    try {
      // BUG-085: createOrAdoptAreaForProject deriva el org del proyecto,
      // crea (o adopta si ya existe) el área y la asigna al proyecto.
      const { id } = await createOrAdoptAreaForProject(
        newName.trim(),
        projectId,
      );
      await refresh();
      onChange(id);
      setCreating(false);
      setNewName("");
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
            {areas.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </Select>
          <Button
            type="button"
            size="sm"
            variant="ghost"
            onClick={() => setCreating(true)}
            disabled={disabled}
            title="Crear área y asignar al proyecto"
          >
            + Nueva
          </Button>
        </div>
      ) : (
        <div className="space-y-1 rounded border border-[var(--border-default)] p-2">
          <div className="text-xs font-medium text-[var(--text-secondary)]">
            Nueva área — se agrega al proyecto automáticamente
          </div>
          <Input
            placeholder="Nombre del área *"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
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
