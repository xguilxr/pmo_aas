"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { Icono } from "@/components/ui/icono";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import { confirmarDestructivo } from "@/lib/confirmar";
import { SIN_DATO } from "@/lib/sin-dato";
import { MarcaDeDatos, useLectura } from "@/components/ui/marca-de-datos";
import {
  getTenantDetail,
  hardDeleteTenant,
  joinAsAdmin,
  softDeleteTenant,
  updateUserRoleType,
  type TenantDetail,
} from "@/lib/api/superadmin";
import {
  freezeTenant,
  getTenantFullDetail,
  unfreezeTenant,
  type TenantFullDetail,
} from "@/lib/api/superadmin-panel";
import {
  setActiveTenantId,
  getStoredUser,
  setStoredUser,
} from "@/lib/auth-storage";

export default function TenantDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [data, setData] = useState<TenantDetail | null>(null);
  // DAT-11: cuándo cambió lo que se está mostrando.
  const leido = useLectura(data);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [confirmSoft, setConfirmSoft] = useState(false);
  const [confirmHard, setConfirmHard] = useState(false);
  const [hardSlug, setHardSlug] = useState("");
  const [busy, setBusy] = useState(false);
  const [joining, setJoining] = useState(false);

  type FullTab = "projects" | "logs" | "ai";
  const [fullTab, setFullTab] = useState<FullTab>("projects");
  const [fullData, setFullData] = useState<TenantFullDetail | null>(null);
  const [fullLoading, setFullLoading] = useState(false);
  const [frozen, setFrozen] = useState<boolean | null>(null);

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

  useEffect(() => {
    setFullLoading(true);
    getTenantFullDetail(params.id, "projects,logs,ai")
      .then((d) => {
        setFullData(d);
        const settings = d.tenant.settings as Record<string, unknown>;
        setFrozen(Boolean(settings?.frozen));
      })
      .catch(() => setFullData(null))
      .finally(() => setFullLoading(false));
  }, [params.id]);

  async function toggleFreeze() {
    if (!data) return;
    setBusy(true);
    try {
      if (frozen) {
        await unfreezeTenant(data.tenant.id);
        setFrozen(false);
        setNotice("Tenant descongelado");
      } else {
        await freezeTenant(data.tenant.id);
        setFrozen(true);
        setNotice("Tenant congelado (modo solo lectura)");
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cambiar el estado");
    } finally {
      setBusy(false);
    }
  }

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
      // ASVS 3.2.3 — el token nuevo llega en la cookie que `switch-tenant`
      // acaba de emitir; el navegador ya no guarda ninguna copia.
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
      <div>
        <Banner variant="danger">{error}</Banner>
      </div>
    );
  }

  if (loading || !data) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-72 w-full" />
      </div>
    );
  }

  const { tenant, users, organizations, programs } = data;

  return (
    <div className="space-y-6">
      <Breadcrumb
        items={[
          { href: "/superadmin/tenants", label: "Tenants" },
          { label: tenant.name },
        ]}
      />

      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center gap-2.5">
            <Icono nombre="server" size={22} className="text-[var(--text-tertiary)]" />
            <h1 className="text-2xl font-semibold tracking-[-0.02em] text-[var(--text-primary)]">
              {tenant.name}
            </h1>
            <span
              aria-label={tenant.is_active ? "Activo" : "Inactivo"}
              title={tenant.is_active ? "Activo" : "Inactivo"}
              className={`inline-block h-2.25 w-2.25 rounded-full ${
                tenant.is_active ? "bg-[var(--color-success-fg)]" : "bg-[var(--color-danger-fg)]"
              }`}
            />
            {!tenant.is_active ? <Badge variant="danger">Inactivo</Badge> : null}
          </div>
          {leido && <MarcaDeDatos periodo="vivo" actualizado={leido} />}
          <span className="font-mono text-[12px] tracking-[0.01em] text-[var(--text-faint)]">
            {tenant.slug}
          </span>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="secondary" onClick={handleJoin} loading={joining}>
            <Icono nombre="arrow-right" size={15} />
            Unirme como admin
          </Button>
          <Button variant="secondary" onClick={toggleFreeze} disabled={busy || frozen === null}>
            <Icono nombre={frozen ? "unlock" : "lock"} size={15} />
            {frozen ? "Descongelar" : "Congelar"}
          </Button>
          {tenant.is_active ? (
            <Button variant="danger" onClick={() => setConfirmSoft(true)}>
              <Icono nombre="circle-alert" size={15} />
              Desactivar
            </Button>
          ) : null}
          <Button variant="danger" onClick={() => setConfirmHard(true)}>
            <Icono nombre="triangle-alert" size={15} />
            Borrar permanente
          </Button>
        </div>
      </header>

      {notice ? <Banner variant="success">{notice}</Banner> : null}
      {error ? <Banner variant="danger">{error}</Banner> : null}

      <HierarchyOverview detail={data} />

      <section className="grid gap-3.5 lg:grid-cols-2">
        <UsersInlineSection
          tenantId={tenant.id}
          users={users}
          onChanged={refresh}
        />
        <div className="flex flex-col gap-3.5">
          <BillingCard />
          <FeatureFlagsCard />
        </div>
      </section>

      <section className="grid gap-3.5 lg:grid-cols-2">
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

      <section className="space-y-3">
        <nav role="tablist" className="flex items-center gap-1 border-b border-[var(--border-subtle)]">
          {(
            [
              { id: "projects" as const, label: "Proyectos" },
              { id: "logs" as const, label: "Logs" },
              { id: "ai" as const, label: "Jobs IA" },
            ]
          ).map((t) => (
            <button
              key={t.id}
              role="tab"
              type="button"
              aria-selected={fullTab === t.id}
              onClick={() => setFullTab(t.id)}
              className={`-mb-px h-9 border-b-2 px-3 text-[13px] font-medium ${
                fullTab === t.id
                  ? "border-[var(--text-primary)] text-[var(--text-primary)]"
                  : "border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>

        <div className="rounded-[var(--radius-window)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--relieve-isla)]">
          {fullLoading ? (
            <div className="space-y-2 p-5">
              <Skeleton className="h-4 w-48" />
              <Skeleton className="h-4 w-64" />
              <Skeleton className="h-4 w-40" />
            </div>
          ) : fullTab === "projects" ? (
            <FullTable
              head={["Folio", "Nombre", "Fase", "Salud"]}
              rows={(fullData?.projects ?? []).map((p) => [
                <span key={p.id} className="text-[12px] tracking-[0.01em]">
                  {p.folio}
                </span>,
                p.name,
                <Badge key={`${p.id}-phase`}>{p.phase}</Badge>,
                // ENH-110: salud = solo el color (círculo), sin la palabra.
                <span
                  key={`${p.id}-h`}
                  title={p.health_status ?? "—"}
                  aria-label={p.health_status ?? "—"}
                  role="img"
                  className={`inline-block h-2.5 w-2.5 rounded-full ${
                    p.health_status === "green"
                      ? "bg-[var(--color-success-fg)]"
                      : p.health_status === "yellow"
                        ? "bg-[var(--color-warning-fg)]"
                        : p.health_status === "red"
                          ? "bg-[var(--color-danger-fg)]"
                          : "bg-[var(--color-tertiary)]"
                  }`}
                />,
              ])}
              empty="Sin proyectos."
            />
          ) : fullTab === "logs" ? (
            <FullTable
              head={["Cuándo", "Acción", "Módulo", "Entidad"]}
              rows={(fullData?.logs ?? []).map((l) => [
                <span key={l.id} className="font-mono text-[11px]">
                  {l.occurred_at ? new Date(l.occurred_at).toLocaleString("es-MX") : "—"}
                </span>,
                <Badge key={`${l.id}-a`}>{l.action}</Badge>,
                <span key={`${l.id}-m`} className="text-[12px]">
                  {l.module ?? "—"}
                </span>,
                <span key={`${l.id}-e`} className="text-[12px] tracking-[0.01em]">
                  {l.entity_type ?? "—"}
                  {l.entity_id ? ` · ${l.entity_id.slice(0, 8)}` : ""}
                </span>,
              ])}
              empty="Sin logs registrados."
            />
          ) : (
            <FullTable
              head={["Cuándo", "Tipo", "Status", "Modelo", "Tokens"]}
              rows={(fullData?.ai_jobs ?? []).map((j) => [
                <span key={j.id} className="font-mono text-[11px]">
                  {j.created_at ? new Date(j.created_at).toLocaleString("es-MX") : "—"}
                </span>,
                <Badge key={`${j.id}-k`}>{j.kind}</Badge>,
                <Badge
                  key={`${j.id}-s`}
                  variant={
                    j.status === "succeeded" ? "success" : j.status === "failed" ? "danger" : "info"
                  }
                >
                  {j.status}
                </Badge>,
                <span key={`${j.id}-m`} className="text-[12px]">
                  {j.model_used ?? "—"}
                </span>,
                <span key={`${j.id}-t`} className="pr-3.5 text-right tabular-nums text-[12px]">
                  {(j.tokens_in ?? 0) + (j.tokens_out ?? 0)}
                </span>,
              ])}
              empty="Sin jobs de IA."
            />
          )}
        </div>
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

function FullTable({
  head,
  rows,
  empty,
}: {
  head: string[];
  rows: React.ReactNode[][];
  empty: string;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-[13px]">
        <thead className="border-b border-[var(--border-default)] bg-[var(--color-subtle)] text-left text-[11px] uppercase tracking-[0.01em] text-[var(--text-secondary)] shadow-[var(--linea-surco)]">
          <tr>
            {head.map((h) => (
              <th key={h} className="h-8.5 px-4 font-medium">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td
                colSpan={head.length}
                className="px-4 py-10 text-center text-[var(--text-tertiary)]"
              >
                {empty}
              </td>
            </tr>
          ) : (
            rows.map((cells, i) => (
              <tr key={i} className="border-b border-[var(--border-subtle)] shadow-[var(--linea-surco)]">
                {cells.map((c, j) => (
                  <td key={j} className="h-11 px-4 py-2">
                    {c}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
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
    <div className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--relieve-isla)]">
      <div className="border-b border-[var(--border-default)] px-4 py-3 text-sm font-medium text-[var(--text-primary)] shadow-[var(--linea-surco)]">
        {title}
      </div>
      <div className="max-h-72 divide-y divide-[var(--border-subtle)] overflow-y-auto">
        {items.length === 0 ? (
          <div className="px-4 py-6 text-center text-sm text-[var(--text-tertiary)]">
            {emptyLabel}
          </div>
        ) : (
          items.map((it) => (
            <div key={it.key} className="flex items-center justify-between gap-2 px-4 py-3">
              <div className="min-w-0">
                <p className="truncate text-sm text-[var(--text-primary)]">{it.primary}</p>
                {it.secondary ? (
                  <p className="truncate text-xs text-[var(--text-tertiary)]">{it.secondary}</p>
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


type RoleType = "admin" | "user" | "viewer";

/**
 * BUG-033 — sección "Usuarios" inline con dropdown de role_type
 * editable directamente en la página detalle del tenant. Antes el
 * `<DetailList>` plain no exponía la opción y el owner reportó "no
 * me da la opción de modificar el rol". El deep-link a la página
 * /users dedicada se mantiene en el link superior de la tarjeta.
 *
 * 6d (Revamp v2) — la tarjeta también expone, al pie, el resumen de
 * "Seguridad" (último login / intentos fallidos / sesiones activas):
 * ninguno de esos tres campos tiene endpoint todavía, así que se
 * marcan `SIN_DATO` + «pendiente de backend» en vez de inventarlos.
 */
function UsersInlineSection({
  tenantId,
  users,
  onChanged,
}: {
  tenantId: string;
  users: TenantDetail["users"];
  onChanged: () => void;
}) {
  const router = useRouter();
  const [savingId, setSavingId] = useState<string | null>(null);
  const [pending, setPending] = useState<Record<string, RoleType>>({});

  async function save(uid: string, next: RoleType, label: string) {
    if (savingId) return;
    if (
      !confirmarDestructivo({
        objeto: `el rol de ${label} (→ ${next})`,
        consecuencia: "Cambia lo que puede ver y hacer en toda la plataforma, de inmediato.",
        reversibilidad: "definitiva",
      })
    )
      return;
    setSavingId(uid);
    try {
      await updateUserRoleType(uid, next);
      setPending((m) => {
        const { [uid]: _, ...rest } = m;
        return rest;
      });
      onChanged();
    } catch (err) {
      alert(
        err instanceof ApiError
          ? err.message
          : "No se pudo actualizar el role_type",
      );
    } finally {
      setSavingId(null);
    }
  }

  return (
    <div className="flex flex-col rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--relieve-isla)]">
      <div className="flex h-9.5 items-center justify-between gap-2 border-b border-[var(--border-default)] px-3.5 shadow-[var(--linea-surco)]">
        <span className="text-[13px] font-semibold text-[var(--text-primary)]">
          Usuarios · {users.length}
        </span>
        <button
          type="button"
          className="text-[11.5px] text-[var(--color-accent)] hover:underline"
          onClick={() => router.push(`/superadmin/tenants/${tenantId}/users`)}
        >
          Ver tabla expandida →
        </button>
      </div>
      <div className="max-h-[380px] divide-y divide-[var(--border-subtle)] overflow-y-auto">
        {users.length === 0 ? (
          <div className="px-4 py-6 text-center text-sm text-[var(--text-tertiary)]">
            Sin usuarios
          </div>
        ) : (
          users.map((u) => {
            const current = (u.role_type ?? "user") as RoleType;
            const next = pending[u.id] ?? current;
            const dirty = pending[u.id] !== undefined && pending[u.id] !== current;
            return (
              <div
                key={u.id}
                className="flex min-h-11 items-center justify-between gap-2 px-3.5 py-1.5"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p className="truncate text-[12.5px] font-medium text-[var(--text-primary)]">
                      {u.username}
                    </p>
                    {u.is_superadmin ? (
                      <Badge variant="warning">superadmin</Badge>
                    ) : null}
                    {!u.is_active ? (
                      <Badge variant="danger">Inactivo</Badge>
                    ) : null}
                  </div>
                  <p className="truncate text-[11px] text-[var(--text-tertiary)]">
                    {u.email}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Select
                    value={next}
                    disabled={u.is_superadmin || savingId === u.id}
                    onChange={(e) =>
                      setPending((m) => ({
                        ...m,
                        [u.id]: e.target.value as RoleType,
                      }))
                    }
                    className="h-8 w-28 text-xs"
                  >
                    <option value="admin">Admin</option>
                    <option value="user">User</option>
                    <option value="viewer">Viewer</option>
                  </Select>
                  <Button
                    type="button"
                    size="sm"
                    disabled={!dirty || u.is_superadmin}
                    loading={savingId === u.id}
                    onClick={() => save(u.id, next, u.email)}
                  >
                    Guardar
                  </Button>
                </div>
              </div>
            );
          })
        )}
      </div>

      <div className="mt-auto flex flex-col gap-2 border-t border-[var(--border-default)] px-3.5 py-3 shadow-[var(--linea-surco-arriba)]">
        <div className="flex items-center justify-between">
          <span className="text-[11.5px] font-semibold text-[var(--text-primary)]">Seguridad</span>
          <span className="text-[10px] italic text-[var(--text-faint)]">pendiente de backend</span>
        </div>
        <SecurityRow label="Último login" />
        <SecurityRow label="Intentos fallidos (24h)" />
        <SecurityRow label="Sesiones activas" />
      </div>
    </div>
  );
}

function SecurityRow({ label }: { label: string }) {
  return (
    <span className="flex items-center justify-between text-[12px] text-[var(--text-secondary)]">
      {label}
      <span className="font-mono text-[var(--text-faint)]">{SIN_DATO}</span>
    </span>
  );
}

/** 6d (Revamp v2) — plan/facturación del tenant: sin endpoint todavía. */
function BillingCard() {
  return (
    <div className="flex flex-col gap-2.5 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] px-4 py-3.5 shadow-[var(--relieve-isla)]">
      <div className="flex items-center justify-between">
        <span className="text-[13px] font-semibold text-[var(--text-primary)]">Facturación</span>
        <span className="text-[10px] italic text-[var(--text-faint)]">pendiente de backend</span>
      </div>
      <div className="grid grid-cols-3 gap-2.5">
        <BillingField label="MRR" />
        <BillingField label="Próxima renovación" />
        <BillingField label="Método de pago" />
      </div>
    </div>
  );
}

function BillingField({ label }: { label: string }) {
  return (
    <span className="flex flex-col gap-0.5">
      <span className="text-[10.5px] text-[var(--text-tertiary)]">{label}</span>
      <span className="font-mono text-[13px] text-[var(--text-faint)]">{SIN_DATO}</span>
    </span>
  );
}

/** 6d (Revamp v2) — feature flags por tenant: sin endpoint todavía. */
function FeatureFlagsCard() {
  return (
    <div className="flex flex-col gap-2.5 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] px-4 py-3.5 shadow-[var(--relieve-isla)]">
      <div className="flex items-center justify-between">
        <span className="text-[13px] font-semibold text-[var(--text-primary)]">Feature flags</span>
        <span className="text-[10px] italic text-[var(--text-faint)]">pendiente de backend</span>
      </div>
      <p className="text-[12.5px] text-[var(--text-tertiary)]">
        La gestión de flags por tenant todavía no tiene endpoint. Se habilitará en una fase futura.
      </p>
    </div>
  );
}

function HierarchyOverview({ detail }: { detail: TenantDetail }) {
  const h = detail.hierarchy;
  const nodes = [
    { icon: "building", label: "Orgs", value: h.organization_count },
    { icon: "folders", label: "Portafolios", value: h.portfolio_count },
    { icon: "git-branch", label: "Programas", value: h.program_count },
    { icon: "folder", label: "Proyectos", value: h.project_count },
  ];
  return (
    <section
      aria-label="Jerarquía del tenant"
      className="flex flex-wrap items-center gap-2 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] px-3.5 py-3 shadow-[var(--relieve-isla)]"
    >
      {nodes.map((n, i) => (
        <div key={n.label} className="flex items-center gap-2">
          <span className="flex items-center gap-1.75 text-[13px] text-[var(--text-primary)]">
            <Icono nombre={n.icon} size={14} className="text-[var(--text-tertiary)]" />
            {n.label}
            <span className="font-mono font-semibold tabular-nums">{n.value}</span>
          </span>
          {i < nodes.length - 1 ? (
            <Icono nombre="chevron-right" size={14} className="text-[var(--border-strong)]" />
          ) : null}
        </div>
      ))}
    </section>
  );
}
