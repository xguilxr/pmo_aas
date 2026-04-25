"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  AlertTriangle,
  Building2,
  ChevronRight,
  FolderKanban,
  LogIn,
  Network,
  Pause,
  Play,
  ServerCog,
  Trash2,
  Users,
  Workflow,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
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
          <Button variant="secondary" onClick={toggleFreeze} disabled={busy || frozen === null}>
            {frozen ? <Play className="h-4 w-4" aria-hidden /> : <Pause className="h-4 w-4" aria-hidden />}
            {frozen ? "Descongelar" : "Congelar"}
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

      <div>
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={() => router.push(`/superadmin/tenants/${tenant.id}/users`)}
        >
          Gestionar role_type de usuarios →
        </Button>
      </div>

      <HierarchyOverview detail={data} />

      <section className="grid gap-5 lg:grid-cols-2">
        <UsersInlineSection
          tenantId={tenant.id}
          users={users}
          onChanged={refresh}
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

        <div className="rounded-[var(--radius-window)] border border-[var(--border-subtle)] bg-[var(--color-surface)]">
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
                <span key={p.id} className="font-mono text-[11px]">
                  {p.folio}
                </span>,
                p.name,
                <Badge key={`${p.id}-phase`}>{p.phase}</Badge>,
                <span key={`${p.id}-h`} className="text-[12px]">
                  {p.health_status}
                </span>,
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
                <span key={`${l.id}-e`} className="font-mono text-[11px]">
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
                <span key={`${j.id}-t`} className="tabular-nums text-[12px]">
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
        <thead className="border-b border-[var(--border-subtle)] bg-[var(--color-subtle)] text-left text-[11px] uppercase tracking-[0.01em] text-[var(--text-secondary)]">
          <tr>
            {head.map((h) => (
              <th key={h} className="h-10 px-4 font-medium">
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
              <tr key={i} className="border-b border-[var(--border-subtle)]">
                {cells.map((c, j) => (
                  <td key={j} className="px-4 py-2">
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


type RoleType = "admin" | "user" | "viewer";

/**
 * BUG-033 — sección "Usuarios" inline con dropdown de role_type
 * editable directamente en la página detalle del tenant. Antes el
 * `<DetailList>` plain no exponía la opción y el owner reportó "no
 * me da la opción de modificar el rol". El deep-link a la página
 * /users dedicada se mantiene en el botón superior.
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
    if (!window.confirm(`Cambiar role_type de ${label} → ${next}?`)) return;
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
    <div className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]">
      <div className="flex items-center justify-between gap-2 border-b border-[var(--border-default)] px-4 py-3">
        <span className="text-sm font-medium text-[var(--color-primary)]">
          Usuarios ({users.length})
        </span>
        <button
          type="button"
          className="text-[11px] text-[var(--color-accent)] hover:underline"
          onClick={() => router.push(`/superadmin/tenants/${tenantId}/users`)}
        >
          Ver tabla expandida →
        </button>
      </div>
      <div className="max-h-[380px] divide-y divide-[var(--border-subtle)] overflow-y-auto">
        {users.length === 0 ? (
          <div className="px-4 py-6 text-center text-sm text-[var(--color-tertiary)]">
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
                className="flex items-center justify-between gap-2 px-4 py-2.5"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p className="truncate text-sm font-medium text-[var(--color-primary)]">
                      {u.username}
                    </p>
                    {u.is_superadmin ? (
                      <Badge variant="warning">superadmin</Badge>
                    ) : null}
                    {!u.is_active ? (
                      <Badge variant="danger">Inactivo</Badge>
                    ) : null}
                  </div>
                  <p className="truncate text-xs text-[var(--color-tertiary)]">
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
    </div>
  );
}

function HierarchyOverview({ detail }: { detail: TenantDetail }) {
  const h = detail.hierarchy;
  const nodes = [
    { icon: <Building2 className="h-4 w-4" aria-hidden />, label: "Orgs", value: h.organization_count },
    { icon: <Workflow className="h-4 w-4" aria-hidden />, label: "BUs", value: h.business_unit_count },
    { icon: <Users className="h-4 w-4" aria-hidden />, label: "Deptos", value: h.department_count },
    { icon: <Network className="h-4 w-4" aria-hidden />, label: "Programas", value: h.program_count },
    { icon: <FolderKanban className="h-4 w-4" aria-hidden />, label: "Proyectos", value: h.project_count },
  ];
  return (
    <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--shadow-sm)]">
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-[var(--color-tertiary)]">
        Jerarquía (overview)
      </h2>
      <ol className="flex flex-wrap items-center gap-1.5 text-sm">
        {nodes.map((n, i) => (
          <li key={n.label} className="flex items-center gap-1.5">
            <span className="inline-flex items-center gap-1.5 rounded-[var(--radius-md)] bg-[var(--color-subtle)] px-2.5 py-1.5">
              <span className="text-[var(--color-tertiary)]">{n.icon}</span>
              <span className="text-[var(--color-tertiary)]">{n.label}</span>
              <span className="font-semibold tabular-nums text-[var(--color-primary)]">
                {n.value}
              </span>
            </span>
            {i < nodes.length - 1 ? (
              <ChevronRight
                className="h-3.5 w-3.5 text-[var(--color-tertiary)]"
                aria-hidden
              />
            ) : null}
          </li>
        ))}
      </ol>
    </section>
  );
}
