"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState, type FormEvent } from "react";

import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api";
import {
  createOrganization,
  updateOrganization,
  type Organization,
  type OrganizationCreateBody,
  type OrganizationUpdateBody,
} from "@/lib/api/organizations";

type Props = {
  mode: "create" | "edit";
  initial?: Organization;
  onSaved?: (org: Organization) => void;
};

type Notice = { kind: "success" | "danger"; message: string } | null;

const INDUSTRIES = [
  "Banca y Finanzas",
  "Energía",
  "Gobierno",
  "Logística",
  "Manufactura",
  "Retail",
  "Salud",
  "Seguros",
  "Servicios",
  "Tecnología",
  "Telecomunicaciones",
  "Otro",
];

export function OrganizationForm({ mode, initial, onSaved }: Props) {
  const router = useRouter();
  const [name, setName] = useState(initial?.name ?? "");
  const [reasonSocial, setReasonSocial] = useState(initial?.reason_social ?? "");
  const [industry, setIndustry] = useState(initial?.industry ?? "");
  const [country, setCountry] = useState(initial?.country ?? "");
  const [contactEmail, setContactEmail] = useState(initial?.contact_email ?? "");
  const [logoUrl, setLogoUrl] = useState(initial?.logo_url ?? "");
  // ENH-100: logo del cliente (consumido por el header de reportes EP020).
  const [clientLogoUrl, setClientLogoUrl] = useState(initial?.client_logo_url ?? "");
  const [isActive, setIsActive] = useState(initial?.is_active ?? true);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<Notice>(null);

  const dirty = useMemo(() => {
    if (mode === "create") return true;
    if (!initial) return false;
    return (
      name.trim() !== initial.name ||
      (reasonSocial ?? "").trim() !== (initial.reason_social ?? "").trim() ||
      (industry ?? "") !== (initial.industry ?? "") ||
      (country ?? "").trim() !== (initial.country ?? "").trim() ||
      (contactEmail ?? "").trim() !== (initial.contact_email ?? "").trim() ||
      (logoUrl ?? "").trim() !== (initial.logo_url ?? "").trim() ||
      (clientLogoUrl ?? "").trim() !== (initial.client_logo_url ?? "").trim() ||
      isActive !== initial.is_active
    );
  }, [
    mode,
    initial,
    name,
    reasonSocial,
    industry,
    country,
    contactEmail,
    logoUrl,
    clientLogoUrl,
    isActive,
  ]);

  const canSubmit = name.trim().length >= 2;

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!canSubmit) return;
    setSaving(true);
    setNotice(null);
    try {
      const payload: OrganizationCreateBody & OrganizationUpdateBody = {
        name: name.trim(),
        reason_social: reasonSocial.trim() || null,
        industry: industry || null,
        country: country.trim() || null,
        contact_email: contactEmail.trim() || null,
        logo_url: logoUrl.trim() || null,
        // ENH-100
        client_logo_url: clientLogoUrl.trim() || null,
        is_active: isActive,
      };
      if (mode === "create") {
        const created = await createOrganization(payload);
        // BUG-019: tras crear, lleva al resumen con flag ?created=1.
        // La edición vive ahora en /admin/organizations/[id]/edit.
        router.replace(`/admin/organizations/${created.id}?created=1`);
      } else if (initial) {
        const updated = await updateOrganization(initial.id, payload);
        setNotice({ kind: "success", message: "Organización actualizada" });
        onSaved?.(updated);
      }
    } catch (err) {
      setNotice({
        kind: "danger",
        message: err instanceof ApiError ? err.message : "No se pudo guardar la organización",
      });
    } finally {
      setSaving(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      noValidate
      className="space-y-5 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-sm)]"
    >
      {notice ? <Banner variant={notice.kind}>{notice.message}</Banner> : null}

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <label htmlFor="name" className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]">
            Nombre
          </label>
          <Input
            id="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            disabled={saving}
            required
            minLength={2}
          />
        </div>
        <div className="sm:col-span-2">
          <label
            htmlFor="reason_social"
            className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
          >
            Razón social
          </label>
          <Textarea
            id="reason_social"
            value={reasonSocial}
            onChange={(e) => setReasonSocial(e.target.value)}
            disabled={saving}
            rows={2}
          />
        </div>
        <div>
          <label
            htmlFor="industry"
            className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
          >
            Industria
          </label>
          <Select
            id="industry"
            value={industry}
            onChange={(e) => setIndustry(e.target.value)}
            disabled={saving}
          >
            <option value="">Sin especificar</option>
            {INDUSTRIES.map((x) => (
              <option key={x} value={x}>
                {x}
              </option>
            ))}
          </Select>
        </div>
        <div>
          <label
            htmlFor="country"
            className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
          >
            País
          </label>
          <Input
            id="country"
            value={country}
            onChange={(e) => setCountry(e.target.value)}
            disabled={saving}
          />
        </div>
        <div className="sm:col-span-2">
          <label
            htmlFor="contact_email"
            className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
          >
            Email de contacto
          </label>
          <Input
            id="contact_email"
            type="email"
            value={contactEmail}
            onChange={(e) => setContactEmail(e.target.value)}
            disabled={saving}
          />
        </div>
        <div>
          <label
            htmlFor="logo_url"
            className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
          >
            Logo de la organización (URL)
          </label>
          <Input
            id="logo_url"
            type="url"
            value={logoUrl}
            onChange={(e) => setLogoUrl(e.target.value)}
            disabled={saving}
            maxLength={500}
            placeholder="https://cdn.example.com/org-logo.png"
          />
          <p className="mt-1 text-xs text-[var(--color-tertiary)]">
            Marca propia de esta organización (PMO).
          </p>
        </div>
        <div>
          <label
            htmlFor="client_logo_url"
            className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
          >
            Logo del cliente (URL)
          </label>
          <div className="flex items-center gap-3">
            <Input
              id="client_logo_url"
              type="url"
              value={clientLogoUrl}
              onChange={(e) => setClientLogoUrl(e.target.value)}
              disabled={saving}
              maxLength={500}
              placeholder="https://cdn.example.com/cliente-logo.png"
              className="flex-1"
            />
            {/* ENH-113: preview en vivo cuando hay URL. */}
            {clientLogoUrl ? (
              <div className="flex h-12 w-12 flex-none items-center justify-center overflow-hidden rounded border border-[var(--border-default)] bg-[var(--color-subtle)]">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={clientLogoUrl}
                  alt="Preview logo cliente"
                  className="h-full w-full object-contain"
                  onError={(e) => {
                    (e.target as HTMLImageElement).style.display = "none";
                  }}
                />
              </div>
            ) : (
              <div className="flex h-12 w-12 flex-none items-center justify-center rounded border border-dashed border-[var(--border-default)] bg-[var(--color-subtle)] text-[10px] text-[var(--color-tertiary)]">
                logo
              </div>
            )}
          </div>
          <p className="mt-1 text-xs text-[var(--color-tertiary)]">
            ENH-100/113: usado en el header de reportes generados (EP020,
            sección S-01). v1.0: pega la URL pública del logo (CDN, R2,
            S3); el upload directo desde aquí llega en v1.1.
          </p>
        </div>
      </div>

      <div className="flex items-center justify-between rounded-[var(--radius-md)] border border-[var(--border-default)] px-4 py-3">
        <div>
          <p className="text-sm font-medium text-[var(--color-primary)]">Organización activa</p>
          <p className="text-xs text-[var(--color-tertiary)]">
            Al desactivarla, dejará de listarse en los filtros por defecto.
          </p>
        </div>
        <Switch
          checked={isActive}
          onChange={(v) => setIsActive(v)}
          disabled={saving}
        />
      </div>

      <div className="flex flex-wrap items-center justify-end gap-2 border-t border-[var(--border-default)] pt-4">
        <Button
          type="button"
          variant="secondary"
          onClick={() => router.push("/admin/organizations")}
          disabled={saving}
        >
          Cancelar
        </Button>
        <Button type="submit" loading={saving} disabled={!dirty || !canSubmit}>
          {mode === "create" ? "Crear organización" : "Guardar cambios"}
        </Button>
      </div>
    </form>
  );
}
