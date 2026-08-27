"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Icono } from "@/components/ui/icono";
import { MarcaDeDatos, useLectura } from "@/components/ui/marca-de-datos";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api";
import { getStoredUser } from "@/lib/auth-storage";
import { confirmarDestructivo } from "@/lib/confirmar";
import {
  approvePermissionRequest,
  listPermissionRequests,
  rejectPermissionRequest,
  type PermissionRequest,
  type PermissionRequestStatus,
} from "@/lib/api/permission-requests";

/**
 * US-082 — vista superadmin de tickets de permisos.
 *
 * Lista todos los tickets (filtrable por status), permite aprobar
 * (auto-crea override en tenant_role_permission_overrides US-073)
 * o rechazar con decision_note obligatorio.
 */
export default function SuperadminPermissionRequestsPage() {
  const me = getStoredUser();
  const [rows, setRows] = useState<PermissionRequest[]>([]);
  // DAT-11: cuándo cambió lo que se está mostrando.
  const leido = useLectura(rows);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<PermissionRequestStatus | "">(
    "pending",
  );
  const [busyId, setBusyId] = useState<string | null>(null);
  const [rejectingFor, setRejectingFor] = useState<PermissionRequest | null>(
    null,
  );
  const [rejectNote, setRejectNote] = useState("");

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const data = await listPermissionRequests(
        filterStatus ? { status: filterStatus } : {},
      );
      setRows(data);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "No se pudieron cargar los tickets",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterStatus]);

  if (me && !me.is_superadmin) {
    return (
      <div>
        <Banner variant="danger">Solo superadmin puede ver esta página.</Banner>
      </div>
    );
  }

  async function approve(req: PermissionRequest) {
    if (
      !confirmarDestructivo({
        objeto: `el permiso ${req.module}.${req.action} de ${req.target_user?.email}`,
        consecuencia: req.requested_grant
          ? "Se le otorga: pasa a poder ejecutar esa acción."
          : "Se le revoca: deja de poder ejecutar esa acción de inmediato.",
        reversibilidad: "definitiva",
      })
    ) {
      return;
    }
    setBusyId(req.id);
    try {
      await approvePermissionRequest(req.id);
      await refresh();
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Error al aprobar");
    } finally {
      setBusyId(null);
    }
  }

  async function submitReject() {
    if (!rejectingFor) return;
    if (rejectNote.trim().length < 1) {
      alert("Necesitas escribir un motivo para rechazar.");
      return;
    }
    setBusyId(rejectingFor.id);
    try {
      await rejectPermissionRequest(rejectingFor.id, rejectNote.trim());
      setRejectingFor(null);
      setRejectNote("");
      await refresh();
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Error al rechazar");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-col gap-1">
          <h1 className="text-[24px] font-semibold tracking-[-0.02em] text-[var(--text-primary)]">
            Tickets de cambio de permisos
          </h1>
          {leido && <MarcaDeDatos periodo="vivo" actualizado={leido} />}
          <p className="max-w-[620px] text-[13px] text-[var(--text-tertiary)]">
            Solicitudes de los administradores de tenants para cambios
            puntuales en permisos por usuario. Al aprobar, se crea/actualiza
            el override correspondiente en{" "}
            <code className="font-mono">tenant_role_permission_overrides</code> (DEC-021).
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select
            value={filterStatus}
            onChange={(e) =>
              setFilterStatus(e.target.value as PermissionRequestStatus | "")
            }
            className="w-40"
          >
            <option value="">Todos</option>
            <option value="pending">Pendientes</option>
            <option value="approved">Aprobados</option>
            <option value="rejected">Rechazados</option>
            <option value="cancelled">Cancelados</option>
          </Select>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => void refresh()}
            aria-label="Refrescar"
          >
            <Icono nombre="refresh-cw" size={15} />
          </Button>
        </div>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </div>
      ) : rows.length === 0 ? (
        <p className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-8 text-center text-[13px] text-[var(--text-tertiary)] shadow-[var(--relieve-isla)]">
          Sin tickets para los filtros aplicados.
        </p>
      ) : (
        <ul className="space-y-3">
          {rows.map((r) => (
            <li
              key={r.id}
              className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--relieve-isla)]"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2 text-[13px]">
                    <Badge variant={statusVariant(r.status)}>
                      {STATUS_LABEL[r.status]}
                    </Badge>
                    <span className="font-medium text-[var(--text-primary)]">
                      {r.requested_grant ? "Otorgar" : "Revocar"}{" "}
                      <code className="font-mono text-[12px] tracking-[0.01em]">
                        {r.module}.{r.action}
                      </code>
                    </span>
                    <span className="text-[11.5px] text-[var(--text-tertiary)]">
                      a{" "}
                      <strong className="text-[var(--text-secondary)]">
                        {r.target_user?.full_name || r.target_user?.email}
                      </strong>
                    </span>
                  </div>
                  <div className="mt-1 text-[11.5px] text-[var(--text-tertiary)]">
                    Solicitado por{" "}
                    <strong className="text-[var(--text-secondary)]">
                      {r.requested_by?.full_name || r.requested_by?.email}
                    </strong>{" "}
                    · tenant{" "}
                    <span className="font-mono text-[11px] tracking-[0.01em]">{r.tenant_id}</span>
                  </div>
                  <div className="mt-2 rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--color-subtle)] p-2 text-[12.5px] text-[var(--text-secondary)]">
                    <span className="text-[10px] font-semibold uppercase tracking-[0.07em] text-[var(--text-tertiary)]">
                      Motivo:
                    </span>{" "}
                    {r.reason}
                  </div>
                  {r.decision_note ? (
                    <div className="mt-2 rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--color-subtle)] p-2 text-[12.5px] text-[var(--text-secondary)]">
                      <span className="text-[10px] font-semibold uppercase tracking-[0.07em] text-[var(--text-tertiary)]">
                        Decisión ({r.decided_by?.email}):
                      </span>{" "}
                      {r.decision_note}
                    </div>
                  ) : null}
                </div>
                {r.status === "pending" ? (
                  <div className="flex items-center gap-2">
                    <Button
                      type="button"
                      variant="primary"
                      size="sm"
                      onClick={() => approve(r)}
                      disabled={busyId === r.id}
                      loading={busyId === r.id}
                    >
                      <Icono nombre="check" size={14} />
                      Aprobar
                    </Button>
                    <Button
                      type="button"
                      variant="danger"
                      size="sm"
                      onClick={() => {
                        setRejectingFor(r);
                        setRejectNote("");
                      }}
                      disabled={busyId === r.id}
                    >
                      <Icono nombre="x" size={14} />
                      Rechazar
                    </Button>
                  </div>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      )}

      <Modal
        open={rejectingFor !== null}
        onClose={() => setRejectingFor(null)}
        title="Rechazar ticket"
      >
        {rejectingFor ? (
          <div className="space-y-3">
            <p className="text-sm text-[var(--color-secondary)]">
              Vas a rechazar la solicitud de{" "}
              <strong>{rejectingFor.requested_by?.email}</strong> para{" "}
              <code className="font-mono text-[12px] tracking-[0.01em]">
                {rejectingFor.module}.{rejectingFor.action}
              </code>
              . Escribe un motivo claro — el solicitante recibirá la nota por
              email + notificación in-app.
            </p>
            <Textarea
              value={rejectNote}
              onChange={(e) => setRejectNote(e.target.value)}
              rows={4}
              placeholder="Ej. No procede porque viola el modelo de roles. Sugerencia: ..."
              required
            />
            <div className="flex justify-end gap-2">
              <Button
                type="button"
                variant="secondary"
                onClick={() => setRejectingFor(null)}
                disabled={busyId === rejectingFor.id}
              >
                Cancelar
              </Button>
              <Button
                type="button"
                variant="danger"
                onClick={submitReject}
                loading={busyId === rejectingFor.id}
                disabled={rejectNote.trim().length < 1}
              >
                Confirmar rechazo
              </Button>
            </div>
          </div>
        ) : null}
      </Modal>
    </div>
  );
}

const STATUS_LABEL: Record<PermissionRequestStatus, string> = {
  pending: "Pendiente",
  approved: "Aprobado",
  rejected: "Rechazado",
  cancelled: "Cancelado",
};

function statusVariant(
  s: PermissionRequestStatus,
): "neutral" | "success" | "danger" | "warning" {
  if (s === "pending") return "warning";
  if (s === "approved") return "success";
  if (s === "rejected") return "danger";
  return "neutral";
}
