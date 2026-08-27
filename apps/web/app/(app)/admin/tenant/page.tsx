"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState, type FormEvent } from "react";

import { Icono } from "@/components/ui/icono";
import { useTenantBranding } from "@/components/tenant-branding-provider";
import { TenantSettingsForm } from "@/components/tenant-settings-form";
import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import {
  getTenantInfo,
  updateTenantInfo,
  type TenantInfo,
} from "@/lib/api/admin-panel";
import {
  deleteTenantLogo,
  resolveLogoUrl,
  uploadTenantLogo,
} from "@/lib/api/branding";
import { cn } from "@/lib/cn";
import { MarcaDeDatos, useLectura } from "@/components/ui/marca-de-datos";

type TenantTab = "info" | "branding" | "config" | "stats";
const TAB_KEYS: TenantTab[] = ["info", "branding", "config", "stats"];
const TAB_LABELS: Record<TenantTab, { label: string; icon: string }> = {
  info: { label: "Información", icon: "building" },
  branding: { label: "Branding", icon: "grid-2x2" },
  config: { label: "Configuración", icon: "settings" },
  stats: { label: "Uso & Stats", icon: "trending-up" },
};

function bytesToHuman(bytes: number): string {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let i = 0;
  let v = bytes;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i += 1;
  }
  return `${v.toFixed(v < 10 && i > 0 ? 1 : 0)} ${units[i]}`;
}

function UsoRow({
  icon,
  label,
  value,
}: {
  icon: string;
  label: string;
  value: string | number;
}) {
  return (
    <span className="flex items-center justify-between text-[12.5px] text-[var(--text-secondary)]">
      <span className="flex items-center gap-1.5">
        <Icono nombre={icon} size={13} className="text-[var(--text-tertiary)]" />
        {label}
      </span>
      <span className="font-mono text-[var(--text-primary)]">{value}</span>
    </span>
  );
}

function TenantAdminPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const rawTab = searchParams.get("tab");
  const activeTab: TenantTab = TAB_KEYS.includes(rawTab as TenantTab)
    ? (rawTab as TenantTab)
    : "info";
  const setActiveTab = (t: TenantTab) => {
    router.replace(`/admin/tenant?tab=${t}`);
  };

  const [info, setInfo] = useState<TenantInfo | null>(null);
  // DAT-11: cuándo cambió lo que se está mostrando.
  const leido = useLectura(info);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [logoUrl, setLogoUrl] = useState("");
  const [uploadingLogo, setUploadingLogo] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const { refresh: refreshBranding } = useTenantBranding();

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const data = await getTenantInfo();
      setInfo(data);
      setName(data.name);
      setLogoUrl(data.logo_url ?? "");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar tenant");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function onLogoFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || !info) return;
    setUploadingLogo(true);
    setError(null);
    setNotice(null);
    try {
      const r = await uploadTenantLogo(file);
      setInfo({ ...info, logo_url: r.logo_url });
      setLogoUrl(r.logo_url);
      await refreshBranding();
      setNotice("Logo actualizado.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al subir logo");
    } finally {
      setUploadingLogo(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function onRemoveLogo() {
    if (!info) return;
    setUploadingLogo(true);
    setError(null);
    setNotice(null);
    try {
      const r = await deleteTenantLogo();
      setInfo({ ...info, logo_url: r.logo_url });
      setLogoUrl(r.logo_url ?? "");
      await refreshBranding();
      setNotice("Logo eliminado.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al eliminar logo");
    } finally {
      setUploadingLogo(false);
    }
  }

  async function save(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!info) return;
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const updated = await updateTenantInfo({
        name: name.trim() !== info.name ? name.trim() : undefined,
        logo_url:
          (logoUrl.trim() || null) !== (info.logo_url ?? null)
            ? logoUrl.trim() || null
            : undefined,
      });
      setInfo({ ...info, ...updated });
      setEditing(false);
      await refreshBranding();
      setNotice("Tenant actualizado.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al guardar");
    } finally {
      setSaving(false);
    }
  }

  const usuariosPct =
    info && info.stats.total_users > 0
      ? Math.min(100, Math.round((info.stats.active_users / info.stats.total_users) * 100))
      : 0;

  return (
    <div className="mx-auto max-w-5xl flex flex-col gap-4">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-[-0.02em] text-[var(--text-primary)]">
          Tenant
        </h1>
        {leido && <MarcaDeDatos periodo="vivo" actualizado={leido} />}
        <p className="text-[13px] text-[var(--text-tertiary)]">
          Información, branding, configuración y uso del tenant en una sola vista.
        </p>
      </header>

      <div
        role="tablist"
        aria-label="Secciones del tenant"
        className="flex items-center gap-1 overflow-x-auto border-b border-[var(--border-default)] shadow-[var(--linea-surco)]"
      >
        {TAB_KEYS.map((k) => {
          const active = activeTab === k;
          return (
            <button
              key={k}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => setActiveTab(k)}
              className={cn(
                "-mb-px inline-flex h-9 items-center gap-1.75 border-b-2 px-2.5 text-[13px] whitespace-nowrap transition-colors",
                active
                  ? "border-[var(--text-primary)] font-semibold text-[var(--text-primary)]"
                  : "border-transparent text-[var(--text-tertiary)] hover:text-[var(--text-primary)]",
              )}
            >
              <Icono nombre={TAB_LABELS[k].icon} size={15} />
              {TAB_LABELS[k].label}
            </button>
          );
        })}
      </div>

      {error ? <Banner variant="danger">{error}</Banner> : null}
      {notice ? <Banner variant="success">{notice}</Banner> : null}

      {loading || !info ? (
        <Skeleton className="h-48 w-full" />
      ) : activeTab === "info" ? (
        <>
          <section className="flex flex-wrap items-center justify-between gap-4 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--relieve-isla)]">
            <div className="flex items-center gap-4">
              <div className="flex h-16 w-16 flex-none items-center justify-center overflow-hidden rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-subtle)] text-[var(--text-faint)]">
                {info.logo_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={resolveLogoUrl(info.logo_url) ?? ""}
                    alt=""
                    className="h-full w-full object-contain"
                  />
                ) : (
                  <Icono nombre="building" size={30} />
                )}
              </div>
              <div className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <h2 className="text-[19px] font-semibold tracking-[-0.01em] text-[var(--text-primary)]">
                    {info.name}
                  </h2>
                  {!info.is_active ? (
                    <Badge variant="danger">Inactivo</Badge>
                  ) : null}
                </div>
                <div className="text-[12px] tracking-[0.01em] text-[var(--text-tertiary)]">
                  slug: {info.slug}
                </div>
              </div>
            </div>
            {!editing ? (
              <Button variant="secondary" onClick={() => setEditing(true)}>
                <Icono nombre="pen" size={15} /> Editar nombre
              </Button>
            ) : null}

            {editing ? (
              <form onSubmit={save} className="w-full space-y-3 pt-1">
                <div>
                  <label
                    htmlFor="name"
                    className="mb-1.5 block text-[13px] font-medium text-[var(--text-secondary)]"
                  >
                    Nombre del tenant
                  </label>
                  <Input
                    id="name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    minLength={2}
                    maxLength={200}
                    required
                  />
                  <p className="mt-1 text-[12px] text-[var(--text-tertiary)]">
                    El slug no puede modificarse desde aquí (solo super admin).
                  </p>
                </div>
                <div className="flex justify-end gap-2">
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => {
                      setEditing(false);
                      setName(info.name);
                    }}
                  >
                    Cancelar
                  </Button>
                  <Button type="submit" loading={saving}>
                    Guardar
                  </Button>
                </div>
              </form>
            ) : null}
          </section>

          <section className="flex flex-wrap items-center justify-between gap-4 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4.5 shadow-[var(--relieve-isla)]">
            <div className="flex flex-col gap-1">
              <span className="text-[10.5px] font-semibold uppercase tracking-[0.07em] text-[var(--text-tertiary)]">
                Plan actual
              </span>
              <span className="text-2xl font-semibold capitalize tracking-[-0.02em] text-[var(--text-primary)]">
                {info.plan}
              </span>
            </div>
            <a
              href="mailto:soporte@pmoaas.example.com?subject=Soporte PMO-aaS"
              className="inline-flex items-center gap-1.75 text-[13px] font-medium text-[var(--color-accent)] hover:underline"
            >
              <Icono nombre="info" size={15} />
              Contactar soporte
            </a>
          </section>
        </>
      ) : activeTab === "branding" ? (
        <section className="flex flex-col gap-4 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4.5 shadow-[var(--relieve-isla)]">
          <div className="flex items-center gap-4">
            <div className="flex h-20 w-20 flex-none items-center justify-center overflow-hidden rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-subtle)] text-[var(--text-faint)]">
              {info.logo_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={resolveLogoUrl(info.logo_url) ?? ""}
                  alt=""
                  className="h-full w-full object-contain"
                />
              ) : (
                <Icono nombre="building" size={32} />
              )}
            </div>
            <div>
              <h2 className="text-[13px] font-semibold text-[var(--text-primary)]">
                Logo del tenant
              </h2>
              <p className="mt-1 text-[12px] text-[var(--text-tertiary)]">
                PNG, JPG, SVG o WEBP hasta 2 MB. También puedes pegar una URL externa.
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <input
              ref={fileInputRef}
              type="file"
              id="logo-file"
              accept="image/png,image/jpeg,image/svg+xml,image/webp"
              onChange={onLogoFileChange}
              className="hidden"
            />
            <Button
              type="button"
              variant="secondary"
              onClick={() => fileInputRef.current?.click()}
              loading={uploadingLogo}
            >
              <Icono nombre="upload" size={15} />
              Subir archivo
            </Button>
            {info.logo_url ? (
              <Button
                type="button"
                variant="ghost"
                onClick={onRemoveLogo}
                disabled={uploadingLogo}
              >
                <Icono nombre="bin" size={15} />
                Quitar
              </Button>
            ) : null}
          </div>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void save(e);
            }}
            className="space-y-2"
          >
            <label
              htmlFor="logo"
              className="block text-[12px] font-medium text-[var(--text-secondary)]"
            >
              URL externa del logo
            </label>
            <Input
              id="logo"
              value={logoUrl}
              onChange={(e) => setLogoUrl(e.target.value)}
              maxLength={500}
              placeholder="https://cdn.example.com/logo.png"
            />
            <div className="flex justify-end">
              <Button type="submit" loading={saving} disabled={(logoUrl || null) === (info.logo_url ?? null)}>
                Guardar URL
              </Button>
            </div>
          </form>
        </section>
      ) : activeTab === "config" ? (
        <div className="flex flex-col gap-4">
          <TenantSettingsForm />
          <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4.5 shadow-[var(--relieve-isla)]">
            <div className="flex items-center gap-2">
              <Icono nombre="info" size={15} className="text-[var(--color-accent)]" />
              <h2 className="text-[13px] font-semibold text-[var(--text-primary)]">
                Configuración de IA
              </h2>
            </div>
            <p className="mt-2 text-[13px] text-[var(--text-secondary)]">
              La configuración de IA del tenant vive en{" "}
              <Link
                href="/admin/ai"
                className="font-medium text-[var(--color-accent)] hover:underline"
              >
                Admin → IA
              </Link>
              . Ahí eliges entre <strong>Sin IA</strong>,{" "}
              <strong>IA de la plataforma (Groq)</strong> o conectar tu
              propio proveedor (BYO).
            </p>
          </section>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3.5 lg:grid-cols-[1.6fr_1fr]">
          <section className="flex flex-col gap-4 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4.5 shadow-[var(--relieve-isla)]">
            <div className="flex flex-col gap-1">
              <span className="text-[10.5px] font-semibold uppercase tracking-[0.07em] text-[var(--text-tertiary)]">
                Plan actual
              </span>
              <span className="text-2xl font-semibold capitalize tracking-[-0.02em] text-[var(--text-primary)]">
                {info.plan}
              </span>
            </div>
          </section>

          <section className="flex flex-col rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4.5 shadow-[var(--relieve-isla)]">
            <span className="text-[10.5px] font-semibold uppercase tracking-[0.07em] text-[var(--text-tertiary)]">
              Uso vs. plan
            </span>
            <div className="mt-3.5 flex flex-col gap-3.5">
              <div className="flex flex-col gap-1.25">
                <span className="flex items-baseline justify-between text-[12px] text-[var(--text-secondary)]">
                  <span className="flex items-center gap-1.5">
                    <Icono nombre="users" size={13} />
                    Usuarios activos
                  </span>
                  <span className="font-mono text-[var(--text-primary)]">
                    {info.stats.active_users} / {info.stats.total_users}
                  </span>
                </span>
                <span className="h-1.5 overflow-hidden rounded-full bg-[var(--color-muted)] shadow-[var(--hundido)]">
                  <span
                    className="block h-full rounded-full bg-[var(--text-primary)]"
                    style={{ width: `${usuariosPct}%` }}
                  />
                </span>
              </div>
              <div className="h-px bg-[var(--border-default)] shadow-[var(--linea-surco)]" />
              <UsoRow icon="upload" label="Storage" value={bytesToHuman(info.stats.storage_bytes)} />
              <UsoRow icon="building" label="Organizaciones" value={info.stats.total_organizations} />
              <UsoRow icon="folder" label="Proyectos" value={info.stats.total_projects} />
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

export default function TenantAdminPage() {
  return (
    <Suspense fallback={<div className="h-96" />}>
      <TenantAdminPageInner />
    </Suspense>
  );
}
