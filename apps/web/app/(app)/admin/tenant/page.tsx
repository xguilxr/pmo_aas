"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState, type FormEvent } from "react";
import {
  BarChart3,
  Building2,
  Cog,
  FolderKanban,
  HardDrive,
  LifeBuoy,
  Palette,
  Pencil,
  Trash2,
  Upload,
  Users,
} from "lucide-react";

import { OllamaLocalAiForm } from "@/components/ollama-local-ai-form";
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

type TenantTab = "info" | "branding" | "config" | "stats";
const TAB_KEYS: TenantTab[] = ["info", "branding", "config", "stats"];
const TAB_LABELS: Record<TenantTab, { label: string; icon: React.ReactNode }> = {
  info: { label: "Información", icon: <Building2 className="h-4 w-4" aria-hidden /> },
  branding: { label: "Branding", icon: <Palette className="h-4 w-4" aria-hidden /> },
  config: { label: "Configuración", icon: <Cog className="h-4 w-4" aria-hidden /> },
  stats: { label: "Uso & Stats", icon: <BarChart3 className="h-4 w-4" aria-hidden /> },
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

function StatCard({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string | number;
}) {
  return (
    <div className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--shadow-sm)]">
      <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-[var(--color-tertiary)]">
        {icon}
        {label}
      </div>
      <div className="mt-2 text-2xl font-semibold tabular-nums text-[var(--color-primary)]">
        {value}
      </div>
    </div>
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

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-[var(--color-primary)]">
          Gestión de Tenant
        </h1>
        <p className="mt-1 text-sm text-[var(--color-tertiary)]">
          Información, branding, configuración y uso del tenant en una sola vista.
        </p>
      </header>

      <nav
        aria-label="Secciones del tenant"
        className="-mx-4 border-b border-[var(--border-default)] px-4 lg:-mx-8 lg:px-8"
      >
        <ul className="flex gap-1 overflow-x-auto">
          {TAB_KEYS.map((k) => {
            const active = activeTab === k;
            return (
              <li key={k}>
                <button
                  type="button"
                  onClick={() => setActiveTab(k)}
                  className={cn(
                    "inline-flex h-10 items-center gap-1.5 border-b-2 px-4 text-sm transition-colors",
                    active
                      ? "border-[var(--color-accent)] font-semibold text-[var(--color-primary)]"
                      : "border-transparent text-[var(--color-tertiary)] hover:text-[var(--color-primary)]",
                  )}
                  aria-current={active ? "page" : undefined}
                >
                  {TAB_LABELS[k].icon}
                  {TAB_LABELS[k].label}
                </button>
              </li>
            );
          })}
        </ul>
      </nav>

      {error ? <Banner variant="danger">{error}</Banner> : null}
      {notice ? <Banner variant="success">{notice}</Banner> : null}

      {loading || !info ? (
        <Skeleton className="h-48 w-full" />
      ) : activeTab === "info" ? (
        <>
          <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-sm)]">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="flex items-center gap-4">
                <div className="flex h-16 w-16 flex-none items-center justify-center overflow-hidden rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--color-subtle)] text-[var(--color-tertiary)]">
                  {info.logo_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={resolveLogoUrl(info.logo_url) ?? ""}
                      alt=""
                      className="h-full w-full object-contain"
                    />
                  ) : (
                    <Building2 className="h-8 w-8" aria-hidden />
                  )}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-xl font-semibold text-[var(--color-primary)]">
                      {info.name}
                    </h2>
                    {!info.is_active ? (
                      <Badge variant="danger">Inactivo</Badge>
                    ) : null}
                  </div>
                  <div className="mt-1 text-xs font-mono text-[var(--color-tertiary)]">
                    slug: {info.slug}
                  </div>
                </div>
              </div>
              {!editing ? (
                <Button variant="secondary" onClick={() => setEditing(true)}>
                  <Pencil className="h-4 w-4" aria-hidden /> Editar nombre
                </Button>
              ) : null}
            </div>

            {editing ? (
              <form onSubmit={save} className="mt-5 space-y-3">
                <div>
                  <label
                    htmlFor="name"
                    className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
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
                  <p className="mt-1 text-xs text-[var(--color-tertiary)]">
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

          <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-sm)]">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-sm font-semibold uppercase tracking-wide text-[var(--color-tertiary)]">
                  Plan actual
                </h2>
                <p className="mt-1 text-2xl font-semibold capitalize text-[var(--color-primary)]">
                  {info.plan}
                </p>
              </div>
              <a
                href="mailto:soporte@pmoaas.example.com?subject=Soporte PMO-aaS"
                className="inline-flex items-center gap-1.5 text-sm text-[var(--color-accent)] hover:underline"
              >
                <LifeBuoy className="h-4 w-4" aria-hidden />
                Contactar soporte
              </a>
            </div>
          </section>
        </>
      ) : activeTab === "branding" ? (
        <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-sm)] space-y-4">
          <div className="flex items-center gap-4">
            <div className="flex h-20 w-20 flex-none items-center justify-center overflow-hidden rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--color-subtle)] text-[var(--color-tertiary)]">
              {info.logo_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={resolveLogoUrl(info.logo_url) ?? ""}
                  alt=""
                  className="h-full w-full object-contain"
                />
              ) : (
                <Building2 className="h-10 w-10" aria-hidden />
              )}
            </div>
            <div>
              <h2 className="text-sm font-semibold text-[var(--color-primary)]">
                Logo del tenant
              </h2>
              <p className="mt-1 text-xs text-[var(--color-tertiary)]">
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
              <Upload className="h-4 w-4" aria-hidden />
              Subir archivo
            </Button>
            {info.logo_url ? (
              <Button
                type="button"
                variant="ghost"
                onClick={onRemoveLogo}
                disabled={uploadingLogo}
              >
                <Trash2 className="h-4 w-4" aria-hidden />
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
              className="block text-xs font-medium text-[var(--color-secondary)]"
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
        <>
          <TenantSettingsForm />
          <OllamaLocalAiForm />
        </>
      ) : (
        <>
          <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-sm)]">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-sm font-semibold uppercase tracking-wide text-[var(--color-tertiary)]">
                  Plan actual
                </h2>
                <p className="mt-1 text-2xl font-semibold capitalize text-[var(--color-primary)]">
                  {info.plan}
                </p>
              </div>
            </div>
          </section>
          <section className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatCard
              icon={<Users className="h-4 w-4" aria-hidden />}
              label="Usuarios activos"
              value={`${info.stats.active_users} / ${info.stats.total_users}`}
            />
            <StatCard
              icon={<Building2 className="h-4 w-4" aria-hidden />}
              label="Organizaciones"
              value={info.stats.total_organizations}
            />
            <StatCard
              icon={<FolderKanban className="h-4 w-4" aria-hidden />}
              label="Proyectos"
              value={info.stats.total_projects}
            />
            <StatCard
              icon={<HardDrive className="h-4 w-4" aria-hidden />}
              label="Storage"
              value={bytesToHuman(info.stats.storage_bytes)}
            />
          </section>
        </>
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
