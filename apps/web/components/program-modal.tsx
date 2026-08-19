"use client";

import { useEffect, useState, type FormEvent } from "react";

import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api";
import {
  createProgram,
  listOrganizations,
  listPortfolios,
  type Organization,
  type Portfolio,
  type ProgramCreateBody,
} from "@/lib/api/organizations";

type Props = {
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
  initialOrgId?: string;
};

export function ProgramModal({ open, onClose, onSaved, initialOrgId }: Props) {
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [orgId, setOrgId] = useState(initialOrgId ?? "");
  // US-200 — el programa vive dentro de un portafolio. Vacío es válido: cae en
  // el «Portafolio General» de su organización (DEC-030), que es lo que evita
  // obligar a nadie a inventarse una taxonomía para registrar su primer
  // programa.
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [portfolioId, setPortfolioId] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [strategic, setStrategic] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [isActive, setIsActive] = useState(true);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [loadingOrgs, setLoadingOrgs] = useState(true);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setLoadingOrgs(true);
    listOrganizations({ is_active: true })
      .then((rows) => {
        if (!cancelled) {
          setOrgs(rows);
          if (initialOrgId) setOrgId(initialOrgId);
          else if (rows.length > 0) setOrgId(rows[0].id);
        }
      })
      .catch(() => {
        /* non-fatal */
      })
      .finally(() => {
        if (!cancelled) setLoadingOrgs(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, initialOrgId]);

  useEffect(() => {
    if (!open || !orgId) {
      setPortfolios([]);
      return;
    }
    let cancelled = false;
    listPortfolios(orgId, { is_active: true })
      .then((rows) => {
        if (!cancelled) setPortfolios(rows);
      })
      .catch(() => {
        if (!cancelled) setPortfolios([]);
      });
    return () => {
      cancelled = true;
    };
  }, [open, orgId]);

  const canSubmit = name.trim().length >= 2 && orgId;

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!canSubmit) return;
    setSaving(true);
    setErr(null);
    try {
      const body: ProgramCreateBody = {
        name: name.trim(),
        organization_id: orgId,
        portfolio_id: portfolioId || null,
        description: description.trim() || null,
        strategic_alignment: strategic.trim() || null,
        start_date: startDate || null,
        end_date: endDate || null,
        is_active: isActive,
      };
      await createProgram(body);
      setName("");
      setPortfolioId("");
      setDescription("");
      setStrategic("");
      setStartDate("");
      setEndDate("");
      setIsActive(true);
      onSaved();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "No se pudo guardar el programa");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Nuevo programa" size="lg">
      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        {err ? <Banner variant="danger">{err}</Banner> : null}
        {!initialOrgId ? (
          <div>
            <label
              htmlFor="prog_org"
              className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
            >
              Organización
            </label>
            <Select
              id="prog_org"
              value={orgId}
              onChange={(e) => {
                setOrgId(e.target.value);
                // El portafolio pertenece a la organización: al cambiarla, el
                // elegido deja de ser válido.
                setPortfolioId("");
              }}
              disabled={saving || loadingOrgs}
              required
            >
              <option value="">Selecciona una organización</option>
              {orgs.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.name}
                </option>
              ))}
            </Select>
          </div>
        ) : null}
        <div>
          <label
            htmlFor="prog_portfolio"
            className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
          >
            Portafolio
          </label>
          <Select
            id="prog_portfolio"
            value={portfolioId}
            onChange={(e) => setPortfolioId(e.target.value)}
            disabled={saving || !orgId}
          >
            <option value="">Portafolio General (por defecto)</option>
            {portfolios.map((pf) => (
              <option key={pf.id} value={pf.id}>
                {pf.code ? `${pf.code} — ${pf.name}` : pf.name}
              </option>
            ))}
          </Select>
          <p className="mt-1 text-xs text-[var(--color-tertiary)]">
            Sin elegir, el programa cae en el «Portafolio General» de la
            organización. Se puede mover después.
          </p>
        </div>
        <div>
          <label
            htmlFor="prog_name"
            className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
          >
            Nombre
          </label>
          <Input
            id="prog_name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            disabled={saving}
            required
            minLength={2}
          />
        </div>
        <div>
          <label
            htmlFor="prog_desc"
            className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
          >
            Descripción
          </label>
          <Textarea
            id="prog_desc"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            disabled={saving}
            rows={2}
          />
        </div>
        <div>
          <label
            htmlFor="prog_strategic"
            className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
          >
            Alineación estratégica
          </label>
          <Textarea
            id="prog_strategic"
            value={strategic}
            onChange={(e) => setStrategic(e.target.value)}
            disabled={saving}
            rows={2}
          />
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <label
              htmlFor="prog_start"
              className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
            >
              Inicio
            </label>
            <Input
              id="prog_start"
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              disabled={saving}
            />
          </div>
          <div>
            <label
              htmlFor="prog_end"
              className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
            >
              Fin
            </label>
            <Input
              id="prog_end"
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              disabled={saving}
            />
          </div>
        </div>
        <div className="flex items-center justify-between rounded-[var(--radius-md)] border border-[var(--border-default)] px-4 py-3">
          <span className="text-sm font-medium text-[var(--color-primary)]">Activo</span>
          <Switch
            checked={isActive}
            onChange={(v) => setIsActive(v)}
            disabled={saving}
          />
        </div>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose} disabled={saving}>
            Cancelar
          </Button>
          <Button type="submit" loading={saving} disabled={!canSubmit}>
            Crear
          </Button>
        </div>
      </form>
    </Modal>
  );
}
