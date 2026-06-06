"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Textarea } from "@/components/ui/textarea";
import {
  createBuilderTemplate,
  type CreateBuilderTemplateBody,
} from "@/lib/api/report-builder";

type Props = {
  open: boolean;
  onClose: () => void;
  defaults: Omit<CreateBuilderTemplateBody, "code" | "name" | "visibility">;
  onSaved: (newTemplateId: string) => void;
};

/** US-126 — modal "Guardar como plantilla" con visibility (private/project). */
export function SaveTemplateModal({ open, onClose, defaults, onSaved }: Props) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [visibility, setVisibility] = useState<"private" | "project">("private");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function buildCode(n: string) {
    return n
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "")
      .slice(0, 50) || `tpl-${Date.now()}`;
  }

  async function handleSave() {
    if (!name.trim()) {
      setError("El nombre es obligatorio");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const created = await createBuilderTemplate({
        ...defaults,
        code: buildCode(name),
        name: name.trim(),
        description: description.trim() || null,
        visibility,
        project_id:
          visibility === "project" ? (defaults.project_id ?? null) : null,
      });
      onSaved(created.id);
      onClose();
      setName("");
      setDescription("");
      setVisibility("private");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo guardar");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Guardar como plantilla"
      description="Las plantillas privadas sólo las ves tú. Publicar al proyecto las vuelve visibles para los miembros."
      footer={
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose} disabled={saving}>
            Cancelar
          </Button>
          <Button onClick={handleSave} loading={saving}>
            Guardar
          </Button>
        </div>
      }
    >
      <div className="space-y-3">
        {error && (
          <div className="rounded bg-red-50 px-3 py-2 text-xs text-red-700">
            {error}
          </div>
        )}
        <label className="block text-sm">
          <span className="mb-1 block text-zinc-700">Nombre</span>
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Mi reporte semanal"
            disabled={saving}
          />
        </label>
        <label className="block text-sm">
          <span className="mb-1 block text-zinc-700">Descripción (opcional)</span>
          <Textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
            disabled={saving}
          />
        </label>
        <fieldset className="space-y-1.5 text-sm">
          <legend className="mb-1 text-zinc-700">Visibilidad</legend>
          <label className="flex items-start gap-2">
            <input
              type="radio"
              checked={visibility === "private"}
              onChange={() => setVisibility("private")}
              disabled={saving}
              className="mt-0.5"
            />
            <span>
              <strong>Privada</strong>
              <span className="block text-xs text-zinc-500">
                Solo tú la ves.
              </span>
            </span>
          </label>
          <label className="flex items-start gap-2">
            <input
              type="radio"
              checked={visibility === "project"}
              onChange={() => setVisibility("project")}
              disabled={saving || !defaults.project_id}
              className="mt-0.5"
            />
            <span>
              <strong>Publicar al proyecto</strong>
              <span className="block text-xs text-zinc-500">
                Todos los miembros del proyecto la pueden usar.
              </span>
            </span>
          </label>
        </fieldset>
      </div>
    </Modal>
  );
}
