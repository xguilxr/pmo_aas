"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  Building2,
  Cog,
  FolderKanban,
  HardDrive,
  LifeBuoy,
  Pencil,
  Trash2,
  Upload,
  Users,
} from "lucide-react";

import { useTenantBranding } from "@/components/tenant-branding-provider";
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

export default function TenantAdminPage() {
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
          Mi tenant
        </h1>
        <p className="mt-1 text-sm text-[var(--color-tertiary)]">
          Información del tenant, plan actual y estadísticas. La configuración
          detallada (idioma, moneda, timezone, IA) está en{" "}
          <Link
            href="/admin/settings"
            className="text-[var(--color-accent)] hover:underline"
          >
            Configuración
          </Link>
          .
        </p>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}
      {notice ? <Banner variant="success">{notice}</Banner> : null}

      {loading ? (
        <Skeleton className="h-48 w-full" />
      ) : info ? (
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
                  <Pencil className="h-4 w-4" aria-hidden /> Editar
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
                </div>
                <div className="space-y-2">
                  <label
                    htmlFor="logo"
                    className="block text-sm font-medium text-[var(--color-secondary)]"
                  >
                    Logo del tenant
                  </label>
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
                  <p className="text-xs text-[var(--color-tertiary)]">
                    PNG, JPG, SVG o WEBP hasta 2 MB. También puedes pegar una URL externa:
                  </p>
                  <Input
                    id="logo"
                    value={logoUrl}
                    onChange={(e) => setLogoUrl(e.target.value)}
                    maxLength={500}
                    placeholder="https://cdn.example.com/logo.png"
                  />
                  <p className="text-xs text-[var(--color-tertiary)]">
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
                      setLogoUrl(info.logo_url ?? "");
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

          <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-sm)]">
            <div className="flex items-center gap-2 text-sm font-semibold text-[var(--color-primary)]">
              <Cog className="h-4 w-4" aria-hidden /> Configuración rápida
            </div>
            <p className="mt-1 text-sm text-[var(--color-tertiary)]">
              Idioma, moneda, timezone, IA y color primario se ajustan en la
              pantalla dedicada.
            </p>
            <div className="mt-3">
              <Link href="/admin/settings">
                <Button variant="secondary">Abrir configuración</Button>
              </Link>
            </div>
          </section>
        </>
      ) : null}
    </div>
  );
}
