"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AlertTriangle, LogIn, ServerCog, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import {
  getTenantDetail,
  hardDeleteTenant,
  joinAsAdmin,
  softDeleteTenant,
  type TenantDetail,
} from "@/lib/api/superadmin";
import {
  setAccessToken,
  setActiveTenantId,
  getStoredUser,
  setStoredUser,
} from "@/lib/auth-storage";

export default function TenantDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [data, setData] = useState<TenantDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [confirmSoft, setConfirmSoft] = useState(false);
  const [confirmHard, setConfirmHard] = useState(false);
  const [hardSlug, setHardSlug] = useState("");
  const [busy, setBusy] = useState(false);
  const [joining, setJoining] = useState(false);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const d = await getTenantDetail(params.id);
      setData(d);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar el tenant");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.id]);

  async function handleSoftDelete() {
    if (!data) return;
    setBusy(true);
    try {
      await softDeleteTenant(data.tenant.id);
      setConfirmSoft(false);
      setNotice("Tenant desactivado");
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo desactivar el tenant");
    } finally {
      setBusy(false);
    }
  }

  async function handleHardDelete() {
    if (!data) return;
    if (hardSlug !== data.tenant.slug) return;
    setBusy(true);
    try {
      await hardDeleteTenant(data.tenant.id, hardSlug);
      router.replace("/superadmin/tenants");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo borrar el tenant");
      setBusy(false);
    }
  }

  async function handleJoin() {
    if (!data) return;
    setJoining(true);
    try {
      const res = await joinAsAdmin(data.tenant.id);
      setAccessToken(res.access_token);
      setActiveTenantId(res.active_tenant_id);
      const user = getStoredUser();
      if (user && !user.roles.includes("Administrador")) {
        setStoredUser({ ...user, roles: [...user.roles, "Administrador"] });
      }
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo unir como admin");
      setJoining(false);
    }
  }

  if (error && !data) {
    return (
      <div className="mx-auto max-w-3xl">
        <Banner variant="danger">{error}</Banner>
      </div>
    );
  }

  if (loading || !data) {
    return (
      <div className="mx-auto max-w-4xl space-y-4">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-72 w-full" />
      </div>
    );
  }

  const { tenant, users, organizations, programs } = data;

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <Breadcrumb
        items={[
          { href: "/superadmin/tenants", label: "Tenants" },
          { label: tenant.name },
        ]}
      />

      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <ServerCog className="h-8 w-8 text-[var(--color-tertiary)]" aria-hidden />
          <div>
            <h1 className="text-2xl font-semibold text-[var(--color-primary)]">{tenant.name}</h1>
            <div className="mt-0.5 flex items-center gap-2 text-xs">
              <span className="font-mono text-[var(--color-tertiary)]">{tenant.slug}</span>
              {!tenant.is_active ? <Badge variant="danger">Inactivo</Badge> : null}
            </div>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" onClick={handleJoin} loading={joining}>
            <LogIn className="h-4 w-4" aria-hidden />
            Unirme como admin
          </Button>
          {tenant.is_active ? (
            <Button variant="danger" onClick={() => setConfirmSoft(true)}>
              <Trash2 className="h-4 w-4" aria-hidden />
              Desactivar
            </Button>
          ) : null}
          <Button variant="danger" onClick={() => setConfirmHard(true)}>
            <AlertTriangle className="h-4 w-4" aria-hidden />
            Borrar permanente
          </Button>
        </div>
      </header>

      {notice ? <Banner variant="success">{notice}</Banner> : null}
      {error ? <Banner variant="danger">{error}</Banner> : null}

      <section className="grid gap-3 sm:grid-cols-3">
        <StatCard label="Usuarios" value={users.length} />
        <StatCard label="Organizaciones" value={organizations.length} />
        <StatCard label="Programas" value={programs.length} />
      </section>

      <section className="grid gap-5 lg:grid-cols-2">
        <DetailList
          title="Usuarios"
          items={users.map((u) => ({
            key: u.id,
            primary: u.username,
            secondary: u.email,
            badge: u.is_active ? null : "Inactivo",
          }))}
          emptyLabel="Sin usuarios"
        />
        <DetailList
          title="Organizaciones"
          items={organizations.map((o) => ({
            key: o.id,
            primary: o.name,
            secondary: null,
            badge: o.is_active ? null : "Inactiva",
          }))}
          emptyLabel="Sin organizaciones"
        />
        <DetailList
          title="Programas"
          items={programs.map((p) => ({
            key: p.id,
            primary: p.name,
            secondary: null,
            badge: null,
          }))}
          emptyLabel="Sin programas"
        />
      </section>

      <Modal
        open={confirmSoft}
        onClose={() => setConfirmSoft(false)}
        title="Desactivar tenant"
        description="El tenant y sus usuarios dejarán de poder iniciar sesión. Se puede reactivar."
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirmSoft(false)} disabled={busy}>
              Cancelar
            </Button>
            <Button variant="danger" onClick={handleSoftDelete} loading={busy}>
              Desactivar
            </Button>
          </>
        }
      >
        <p className="text-sm text-[var(--color-secondary)]">
          ¿Confirmas desactivar <strong>{tenant.name}</strong>?
        </p>
      </Modal>

      <Modal
        open={confirmHard}
        onClose={() => {
          setConfirmHard(false);
          setHardSlug("");
        }}
        title="Borrado permanente"
        description="Esta acción es irreversible. Se elimina el tenant y TODA su información (usuarios, organizaciones, programas)."
        footer={
          <>
            <Button
              variant="secondary"
              onClick={() => {
                setConfirmHard(false);
                setHardSlug("");
              }}
              disabled={busy}
            >
              Cancelar
            </Button>
            <Button
              variant="danger"
              onClick={handleHardDelete}
              loading={busy}
              disabled={hardSlug !== tenant.slug}
            >
              Borrar permanente
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <p className="text-sm text-[var(--color-secondary)]">
            Para confirmar, escribe el slug exacto: <code className="font-mono">{tenant.slug}</code>
          </p>
          <Input
            value={hardSlug}
            onChange={(e) => setHardSlug(e.target.value)}
            invalid={hardSlug.length > 0 && hardSlug !== tenant.slug}
            placeholder={tenant.slug}
            autoFocus
          />
        </div>
      </Modal>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-sm)]">
      <p className="text-xs text-[var(--color-tertiary)]">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-[var(--color-primary)]">{value}</p>
    </div>
  );
}

type DetailItem = {
  key: string;
  primary: string;
  secondary: string | null;
  badge: string | null;
};

function DetailList({
  title,
  items,
  emptyLabel,
}: {
  title: string;
  items: DetailItem[];
  emptyLabel: string;
}) {
  return (
    <div className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]">
      <div className="border-b border-[var(--border-default)] px-4 py-3 text-sm font-medium text-[var(--color-primary)]">
        {title}
      </div>
      <div className="max-h-72 divide-y divide-[var(--border-subtle)] overflow-y-auto">
        {items.length === 0 ? (
          <div className="px-4 py-6 text-center text-sm text-[var(--color-tertiary)]">
            {emptyLabel}
          </div>
        ) : (
          items.map((it) => (
            <div key={it.key} className="flex items-center justify-between gap-2 px-4 py-3">
              <div className="min-w-0">
                <p className="truncate text-sm text-[var(--color-primary)]">{it.primary}</p>
                {it.secondary ? (
                  <p className="truncate text-xs text-[var(--color-tertiary)]">{it.secondary}</p>
                ) : null}
              </div>
              {it.badge ? <Badge variant="danger">{it.badge}</Badge> : null}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

