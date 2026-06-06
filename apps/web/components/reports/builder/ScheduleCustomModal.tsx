"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import {
  createCustomSchedule,
  type ScheduleCustomBody,
} from "@/lib/api/report-builder";

type Props = {
  open: boolean;
  onClose: () => void;
  projectId: string;
  templateId: string | null;
};

/** US-131 — modal "Programar suscripción" para reportes custom. */
export function ScheduleCustomModal({
  open,
  onClose,
  projectId,
  templateId,
}: Props) {
  const [cadence, setCadence] = useState<"daily" | "weekly" | "monthly" | "once">(
    "weekly"
  );
  const [dayOfWeek, setDayOfWeek] = useState(0); // lunes
  const [hourOfDay, setHourOfDay] = useState(9);
  const [dayOfMonth, setDayOfMonth] = useState(1);
  const [runAt, setRunAt] = useState("");
  const [recipients, setRecipients] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function parseEmails(): string[] {
    return recipients
      .split(/[,;\s]+/)
      .map((s) => s.trim())
      .filter(Boolean);
  }

  async function save() {
    if (!templateId) {
      setError("Guarda primero la plantilla.");
      return;
    }
    const emails = parseEmails();
    if (emails.length === 0) {
      setError("Agrega al menos un destinatario.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const body: ScheduleCustomBody = {
        cadence,
        recipients: emails,
        report_builder_template_id: templateId,
      };
      if (cadence === "daily") {
        body.hour_of_day = hourOfDay;
      } else if (cadence === "weekly") {
        body.day_of_week = dayOfWeek;
        body.hour_of_day = hourOfDay;
      } else if (cadence === "monthly") {
        body.day_of_month = dayOfMonth;
        body.hour_of_day = hourOfDay;
      } else if (cadence === "once") {
        if (!runAt) {
          setError("Define fecha y hora para la ejecución única.");
          setSaving(false);
          return;
        }
        body.run_at = new Date(runAt).toISOString();
      }
      await createCustomSchedule(projectId, body);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo programar");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Programar reporte"
      description="El reporte se generará y enviará automáticamente según la cadencia configurada."
      footer={
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose} disabled={saving}>
            Cancelar
          </Button>
          <Button onClick={save} loading={saving} disabled={!templateId}>
            Programar
          </Button>
        </div>
      }
    >
      <div className="space-y-3">
        {!templateId && (
          <div className="rounded bg-yellow-50 px-3 py-2 text-xs text-yellow-800">
            Necesitas guardar la plantilla antes de programar.
          </div>
        )}
        {error && (
          <div className="rounded bg-red-50 px-3 py-2 text-xs text-red-700">
            {error}
          </div>
        )}
        <label className="block text-sm">
          <span className="mb-1 block text-zinc-700">Cadencia</span>
          <Select
            value={cadence}
            onChange={(e) => setCadence(e.target.value as typeof cadence)}
          >
            <option value="daily">Diaria</option>
            <option value="weekly">Semanal</option>
            <option value="monthly">Mensual</option>
            <option value="once">Una sola vez</option>
          </Select>
        </label>

        {cadence === "weekly" && (
          <label className="block text-sm">
            <span className="mb-1 block text-zinc-700">Día de la semana</span>
            <Select
              value={String(dayOfWeek)}
              onChange={(e) => setDayOfWeek(Number(e.target.value))}
            >
              <option value="0">Lunes</option>
              <option value="1">Martes</option>
              <option value="2">Miércoles</option>
              <option value="3">Jueves</option>
              <option value="4">Viernes</option>
              <option value="5">Sábado</option>
              <option value="6">Domingo</option>
            </Select>
          </label>
        )}

        {cadence === "monthly" && (
          <label className="block text-sm">
            <span className="mb-1 block text-zinc-700">Día del mes (1-31)</span>
            <Input
              type="number"
              min={1}
              max={31}
              value={dayOfMonth}
              onChange={(e) => setDayOfMonth(Number(e.target.value) || 1)}
            />
          </label>
        )}

        {cadence !== "once" && (
          <label className="block text-sm">
            <span className="mb-1 block text-zinc-700">Hora (UTC, 0-23)</span>
            <Input
              type="number"
              min={0}
              max={23}
              value={hourOfDay}
              onChange={(e) => setHourOfDay(Number(e.target.value) || 0)}
            />
          </label>
        )}

        {cadence === "once" && (
          <label className="block text-sm">
            <span className="mb-1 block text-zinc-700">Fecha y hora</span>
            <Input
              type="datetime-local"
              value={runAt}
              onChange={(e) => setRunAt(e.target.value)}
            />
          </label>
        )}

        <label className="block text-sm">
          <span className="mb-1 block text-zinc-700">
            Destinatarios (separa por coma)
          </span>
          <Input
            placeholder="pm@empresa.com, cliente@otra.com"
            value={recipients}
            onChange={(e) => setRecipients(e.target.value)}
          />
        </label>
      </div>
    </Modal>
  );
}
