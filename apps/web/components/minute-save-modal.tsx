"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";

/**
 * ENH-104 — Modal "Confirma el título" obligatorio al guardar una
 * minuta cuyo título quedó vacío. Bloquea hasta que el usuario
 * complete un título de al menos 2 chars o cancele.
 */
export function MinuteSaveModal({
  open,
  initial,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  initial?: string;
  onConfirm: (title: string) => void;
  onCancel: () => void;
}) {
  const [value, setValue] = useState(initial ?? "");

  useEffect(() => {
    if (open) {
      setValue(initial ?? "");
    }
  }, [open, initial]);

  const trimmed = value.trim();
  const valid = trimmed.length >= 2;

  return (
    <Modal
      open={open}
      onClose={onCancel}
      title="Confirma el título de la minuta"
      size="sm"
    >
      <p className="text-[13px] text-[var(--text-secondary)]">
        La minuta no tiene título. Ingresa uno antes de guardar.
      </p>
      <Input
        autoFocus
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Ej.: Reunión semanal de avance"
        className="mt-3"
        onKeyDown={(e) => {
          if (e.key === "Enter" && valid) {
            onConfirm(trimmed);
          }
        }}
      />
      <div className="mt-4 flex justify-end gap-2">
        <Button variant="secondary" onClick={onCancel}>
          Cancelar
        </Button>
        <Button onClick={() => valid && onConfirm(trimmed)} disabled={!valid}>
          Guardar minuta
        </Button>
      </div>
    </Modal>
  );
}
