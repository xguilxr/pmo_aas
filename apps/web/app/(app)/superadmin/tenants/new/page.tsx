"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState, type FormEvent } from "react";
import { ArrowLeft, Copy, KeyRound, RefreshCw } from "lucide-react";
import Link from "next/link";

import { Banner } from "@/components/ui/banner";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api";
import { provisionTenant, type TenantProvisionResponse } from "@/lib/api/superadmin";
import { generatePassword } from "@/lib/password";

function slugify(raw: string): string {
  return raw
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 64);
}

const SLUG_RX = /^[a-z0-9\-]+$/;

export default function NewTenantPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [slugTouched, setSlugTouched] = useState(false);
  const [adminFullName, setAdminFullName] = useState("");
  const [adminEmail, setAdminEmail] = useState("");
  const [adminUsername, setAdminUsername] = useState("");
  const [adminPassword, setAdminPassword] = useState("");
  const [usePassword, setUsePassword] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TenantProvisionResponse | null>(null);
  const [copied, setCopied] = useState(false);

  const effectiveSlug = slugTouched ? slug : slugify(name);
  const slugValid = effectiveSlug.length >= 2 && SLUG_RX.test(effectiveSlug);
  const emailValid = /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(adminEmail);

  const canSubmit = useMemo(
    () =>
      name.trim().length >= 2 &&
      slugValid &&
      adminFullName.trim().length >= 2 &&
      emailValid,
    [name, slugValid, adminFullName, emailValid],
  );

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!canSubmit) return;
    setSaving(true);
    setError(null);
    try {
      const res = await provisionTenant({
        name: name.trim(),
        slug: effectiveSlug,
        admin_full_name: adminFullName.trim(),
        admin_email: adminEmail.trim().toLowerCase(),
        admin_username: adminUsername.trim() || null,
        admin_password: usePassword && adminPassword ? adminPassword : null,
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo provisionar el tenant");
    } finally {
      setSaving(false);
    }
  }

  async function copyPassword() {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(result.admin_password);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore
    }
  }

  if (result) {
    return (
      <div className="mx-auto max-w-2xl space-y-6">
        <Breadcrumb
          items={[
            { href: "/superadmin/tenants", label: "Tenants" },
            { label: "Provisionado" },
          ]}
        />
        <div className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-sm)]">
          <Banner variant="success">Tenant provisionado correctamente.</Banner>
          <dl className="mt-5 grid gap-3 text-sm">
            <div className="flex justify-between gap-2">
              <dt className="text-[var(--color-tertiary)]">Nombre</dt>
              <dd className="font-medium text-[var(--color-primary)]">{name}</dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt className="text-[var(--color-tertiary)]">Slug</dt>
              <dd className="font-mono text-[var(--color-primary)]">{result.slug}</dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt className="text-[var(--color-tertiary)]">Admin email</dt>
              <dd className="text-[var(--color-primary)]">{adminEmail}</dd>
            </div>
          </dl>

          <div className="mt-5 rounded-[var(--radius-md)] border border-[var(--color-warning-border)] bg-[var(--color-warning-bg)] p-4">
            <p className="text-xs font-medium text-[var(--color-warning-fg)]">
              Guarda esta contraseña temporal. No se volverá a mostrar.
            </p>
            <div className="mt-2 flex items-center gap-2">
              <code className="flex-1 truncate rounded-[var(--radius-sm)] bg-[var(--color-surface)] px-2 py-1 font-mono text-sm text-[var(--color-primary)]">
                {result.admin_password}
              </code>
              <Button type="button" size="sm" variant="secondary" onClick={copyPassword}>
                <Copy className="h-4 w-4" aria-hidden />
                {copied ? "Copiada" : "Copiar"}
              </Button>
            </div>
          </div>

          <div className="mt-6 flex justify-end gap-2">
            <Link href="/superadmin/tenants">
              <Button variant="secondary">Volver</Button>
            </Link>
            <Link href={`/superadmin/tenants/${result.tenant_id}`}>
              <Button>Ver tenant</Button>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <Breadcrumb
        items={[
          { href: "/superadmin/tenants", label: "Tenants" },
          { label: "Provisionar" },
        ]}
      />
      <div>
        <Link
          href="/superadmin/tenants"
          className="inline-flex items-center gap-1 text-sm text-[var(--color-tertiary)] hover:text-[var(--color-primary)]"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden />
          Volver
        </Link>
        <h1 className="mt-2 text-2xl font-semibold text-[var(--color-primary)]">
          Provisionar tenant
        </h1>
        <p className="mt-1 text-sm text-[var(--color-tertiary)]">
          Crea un nuevo tenant y su usuario Administrador inicial. Se generará una contraseña
          temporal si no la defines.
        </p>
      </div>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      <form
        onSubmit={handleSubmit}
        noValidate
        className="space-y-5 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-sm)]"
      >
        <div>
          <label htmlFor="t_name" className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]">
            Nombre del tenant
          </label>
          <Input
            id="t_name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Acme Corp"
            required
            minLength={2}
            disabled={saving}
          />
        </div>
        <div>
          <label htmlFor="t_slug" className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]">
            Slug
          </label>
          <Input
            id="t_slug"
            value={effectiveSlug}
            onChange={(e) => {
              setSlugTouched(true);
              setSlug(e.target.value.toLowerCase());
            }}
            onBlur={() => setSlugTouched(true)}
            invalid={effectiveSlug.length > 0 && !slugValid}
            pattern="^[a-z0-9\-]+$"
            placeholder="acme"
            disabled={saving}
          />
          <p className="mt-1 text-xs text-[var(--color-tertiary)]">
            Se usa en URLs y cabeceras. Solo minúsculas, dígitos y guiones.
          </p>
        </div>

        <div className="border-t border-[var(--border-default)] pt-5">
          <p className="mb-3 text-sm font-medium text-[var(--color-secondary)]">
            Usuario Administrador inicial
          </p>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <label
                htmlFor="t_admin_name"
                className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
              >
                Nombre completo
              </label>
              <Input
                id="t_admin_name"
                value={adminFullName}
                onChange={(e) => setAdminFullName(e.target.value)}
                required
                minLength={2}
                disabled={saving}
              />
            </div>
            <div>
              <label
                htmlFor="t_admin_email"
                className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
              >
                Email
              </label>
              <Input
                id="t_admin_email"
                type="email"
                value={adminEmail}
                onChange={(e) => setAdminEmail(e.target.value)}
                invalid={adminEmail.length > 0 && !emailValid}
                required
                disabled={saving}
              />
            </div>
            <div>
              <label
                htmlFor="t_admin_user"
                className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
              >
                Usuario (opcional)
              </label>
              <Input
                id="t_admin_user"
                value={adminUsername}
                onChange={(e) => setAdminUsername(e.target.value)}
                placeholder="se infiere del email"
                disabled={saving}
              />
            </div>
          </div>

          <div className="mt-4 rounded-[var(--radius-md)] border border-[var(--border-default)] p-4">
            <label className="flex items-center gap-2 text-sm text-[var(--color-secondary)]">
              <input
                type="checkbox"
                checked={usePassword}
                onChange={(e) => setUsePassword(e.target.checked)}
                disabled={saving}
              />
              Definir contraseña manualmente (si no, se genera una segura)
            </label>
            {usePassword ? (
              <div className="mt-3 flex items-center gap-2">
                <Input
                  type="text"
                  value={adminPassword}
                  onChange={(e) => setAdminPassword(e.target.value)}
                  placeholder="min. 12 caracteres, mayúscula, dígito, símbolo"
                  disabled={saving}
                />
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => setAdminPassword(generatePassword(16))}
                  disabled={saving}
                  aria-label="Generar contraseña"
                >
                  <RefreshCw className="h-4 w-4" aria-hidden />
                </Button>
              </div>
            ) : (
              <p className="mt-2 inline-flex items-center gap-1 text-xs text-[var(--color-tertiary)]">
                <KeyRound className="h-3 w-3" aria-hidden />
                Se generará una contraseña temporal y se mostrará una sola vez tras provisionar.
              </p>
            )}
          </div>
        </div>

        <div className="flex justify-end gap-2 border-t border-[var(--border-default)] pt-4">
          <Button
            type="button"
            variant="secondary"
            onClick={() => router.push("/superadmin/tenants")}
            disabled={saving}
          >
            Cancelar
          </Button>
          <Button type="submit" loading={saving} disabled={!canSubmit}>
            Provisionar
          </Button>
        </div>
      </form>
    </div>
  );
}
