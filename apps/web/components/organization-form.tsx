"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState, type FormEvent, type ReactNode } from "react";

import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Icono } from "@/components/ui/icono";
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
import { cn } from "@/lib/cn";

// BUG-068: subida directa de logos (PNG/JPG/SVG/WEBP) como data-URL base64.
const MAX_LOGO_BYTES = 2 * 1024 * 1024; // 2 MB
const LOGO_ACCEPT = "image/png,image/jpeg,image/svg+xml,image/webp";

function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = () => reject(reader.error ?? new Error("read error"));
    reader.readAsDataURL(file);
  });
}

/**
 * BUG-068: campo de logo con tres caminos — subir archivo (data-URL),
 * pegar URL externa, o quitar. Muestra preview en vivo; `shape="circle"`
 * replica el circulito con que se muestra la org en /pmo y listados.
 */
function LogoField({
  id,
  label,
  value,
  onChange,
  helper,
  shape,
  disabled,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  helper: ReactNode;
  shape: "circle" | "square";
  disabled?: boolean;
}) {
  const [err, setErr] = useState<string | null>(null);
  const isData = value.startsWith("data:");

  async function onFile(file: File | undefined) {
    setErr(null);
    if (!file) return;
    if (file.size > MAX_LOGO_BYTES) {
      setErr("El logo excede 2 MB. Usa una imagen más liviana.");
      return;
    }
    try {
      onChange(await readFileAsDataUrl(file));
    } catch {
      setErr("No se pudo leer el archivo.");
    }
  }

  return (
    <div>
      <label
        htmlFor={id}
        className="mb-1.5 block text-[12.5px] font-medium text-[var(--text-secondary)]"
      >
        {label}
      </label>
      <div className="flex items-start gap-3">
        <div
          className={cn(
            "flex h-12 w-12 flex-none items-center justify-center overflow-hidden border border-[var(--border-default)] bg-[var(--color-subtle)] text-[10px] text-[var(--text-tertiary)]",
            shape === "circle" ? "rounded-full" : "rounded-[var(--radius-md)]",
          )}
        >
          {value ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={value}
              alt={`Preview ${label}`}
              className={cn(
                "h-full w-full",
                shape === "circle" ? "object-cover" : "object-contain",
              )}
              onError={(e) => {
                (e.target as HTMLImageElement).style.display = "none";
              }}
            />
          ) : shape === "circle" ? (
            <Icono nombre="building" size={20} />
          ) : (
            "logo"
          )}
        </div>
        <div className="min-w-0 flex-1 space-y-2">
          {isData ? (
            <div className="flex items-center gap-2 text-[12px] text-[var(--text-secondary)]">
              <span className="truncate rounded-[var(--radius-sm)] bg-[var(--color-subtle)] px-2 py-1">
                Imagen subida
              </span>
              <button
                type="button"
                onClick={() => onChange("")}
                disabled={disabled}
                className="text-[var(--color-accent)] hover:underline"
              >
                Quitar
              </button>
            </div>
          ) : (
            <Input
              id={id}
              type="text"
              value={value}
              onChange={(e) => onChange(e.target.value)}
              disabled={disabled}
              maxLength={500}
              placeholder="https://cdn.example.com/logo.png"
            />
          )}
          <input
            type="file"
            accept={LOGO_ACCEPT}
            disabled={disabled}
            onChange={(e) => onFile(e.target.files?.[0])}
            aria-label={`Subir ${label}`}
            className="block w-full text-[12px] text-[var(--text-tertiary)] file:mr-3 file:rounded-[var(--radius-sm)] file:border file:border-[var(--border-default)] file:bg-[var(--color-surface)] file:px-3 file:py-1.5 file:text-[12px] file:font-medium file:text-[var(--text-secondary)] hover:file:bg-[var(--color-subtle)]"
          />
          {err ? (
            <p className="text-[12px] text-[var(--color-danger-fg)]">{err}</p>
          ) : null}
        </div>
      </div>
      <p className="mt-1 text-[12px] text-[var(--text-tertiary)]">{helper}</p>
    </div>
  );
}

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
      className="space-y-5 rounded-[var(--radius-window)] border border-[var(--border-subtle)] bg-[var(--color-surface)] p-8"
    >
      {notice ? <Banner variant={notice.kind}>{notice.message}</Banner> : null}

      <div className="grid gap-x-5 gap-y-4 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <label htmlFor="name" className="mb-1.5 block text-[12.5px] font-medium text-[var(--text-secondary)]">
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
            className="mb-1.5 block text-[12.5px] font-medium text-[var(--text-secondary)]"
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
            className="mb-1.5 block text-[12.5px] font-medium text-[var(--text-secondary)]"
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
            className="mb-1.5 block text-[12.5px] font-medium text-[var(--text-secondary)]"
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
            className="mb-1.5 block text-[12.5px] font-medium text-[var(--text-secondary)]"
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
        <LogoField
          id="logo_url"
          label="Logo de la organización"
          value={logoUrl}
          onChange={setLogoUrl}
          shape="circle"
          disabled={saving}
          helper="Marca propia de esta organización (PMO). Sube un PNG/JPG/SVG/WEBP o pega una URL — así se verá en el circulito."
        />
        <LogoField
          id="client_logo_url"
          label="Logo del cliente"
          value={clientLogoUrl}
          onChange={setClientLogoUrl}
          shape="square"
          disabled={saving}
          helper="ENH-100: usado en el header de los reportes generados (EP020, sección S-01). Sube un archivo o pega la URL pública."
        />
      </div>

      <div className="flex items-center justify-between rounded-[var(--radius-md)] border border-[var(--border-default)] px-4 py-3 shadow-[var(--relieve-control)]">
        <div>
          <p className="text-[13px] font-medium text-[var(--text-primary)]">Organización activa</p>
          <p className="text-[12px] text-[var(--text-tertiary)]">
            Al desactivarla, dejará de listarse en los filtros por defecto.
          </p>
        </div>
        <Switch
          checked={isActive}
          onChange={(v) => setIsActive(v)}
          disabled={saving}
        />
      </div>

      <div className="flex flex-wrap items-center justify-end gap-2 border-t border-[var(--border-default)] pt-4 shadow-[var(--linea-surco-arriba)]">
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
