"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { CheckCircle2, Sparkles, XCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";

/**
 * US-113 — landing pública para que un aprobador externo registre su
 * decisión sobre un Change Request, sin auth (token JWT en URL).
 *
 * GET  /api/v1/public/approve/{token}  → info para mostrar.
 * POST /api/v1/public/approve/{token}  → registrar decisión.
 *
 * No usa `apiFetch` porque queremos sin Bearer token; llamamos directo
 * a la API base con fetch nativo.
 */

type ApprovalInfo = {
  change_id: string;
  folio: string;
  title: string;
  description: string | null;
  type: string;
  impact: string | null;
  project_name: string;
  actor_name: string | null;
  expires_at: string;
  consumed_at: string | null;
  action_taken: string | null;
};

function apiBase(): string {
  return (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/+$/, "");
}

export default function PublicApprovePage() {
  const { token } = useParams<{ token: string }>();
  const [info, setInfo] = useState<ApprovalInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState<"approve" | "reject" | null>(
    null,
  );
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState<{ action: string; status: string } | null>(
    null,
  );
  const [note, setNote] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetch(`${apiBase()}/api/v1/public/approve/${token}`, { method: "GET" })
      .then(async (res) => {
        if (cancelled) return;
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          const detail = data?.detail?.detail || data?.detail || `Error ${res.status}`;
          throw new Error(detail);
        }
        const data = (await res.json()) as ApprovalInfo;
        if (!cancelled) setInfo(data);
      })
      .catch((err) => {
        if (!cancelled)
          setError(err instanceof Error ? err.message : "No se pudo cargar la solicitud");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  async function submitDecision() {
    if (!pendingAction) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch(`${apiBase()}/api/v1/public/approve/${token}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: pendingAction,
          note: note.trim() || null,
        }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        const detail = data?.detail?.detail || data?.detail || `Error ${res.status}`;
        throw new Error(detail);
      }
      const data = (await res.json()) as { action: string; change_status: string };
      setDone({ action: data.action, status: data.change_status });
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo registrar la decisión");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-2xl space-y-3 p-8">
        <Skeleton className="h-8 w-1/2" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-12 w-full" />
      </div>
    );
  }

  if (error && !info) {
    // CA10: tokens expirados/consumidos/inválidos.
    return (
      <div className="mx-auto max-w-2xl p-8">
        <h1 className="mb-3 flex items-center gap-2 text-xl font-semibold">
          <XCircle className="h-6 w-6 text-[var(--color-danger-fg)]" aria-hidden />
          Enlace no válido
        </h1>
        <Banner variant="danger">{error}</Banner>
        <p className="mt-4 text-[13px] text-[var(--text-tertiary)]">
          Si tu enlace ya expiró o fue revocado, contacta al PM del proyecto
          para que te envíe uno nuevo.
        </p>
      </div>
    );
  }
  if (!info) return null;

  // CA9 — confirmación tras action exitosa.
  if (done) {
    const isApprove = done.action === "approve";
    return (
      <div className="mx-auto max-w-2xl p-8">
        <h1 className="mb-3 flex items-center gap-2 text-xl font-semibold">
          {isApprove ? (
            <CheckCircle2 className="h-6 w-6 text-[var(--color-success-fg)]" aria-hidden />
          ) : (
            <XCircle className="h-6 w-6 text-[var(--color-danger-fg)]" aria-hidden />
          )}
          Gracias, su decisión ha sido registrada
        </h1>
        <p className="mt-2 text-[14px]">
          Tu decisión fue: <strong>{isApprove ? "Aprobado" : "Rechazado"}</strong>.
        </p>
        <p className="mt-1 text-[13px] text-[var(--text-tertiary)]">
          Estado del Cambio: <Badge variant={
            done.status === "approved"
              ? "success"
              : done.status === "rejected"
                ? "danger"
                : "info"
          }>{done.status}</Badge>
        </p>
      </div>
    );
  }

  // CA10: token ya fue consumido (info.consumed_at != null).
  if (info.consumed_at) {
    return (
      <div className="mx-auto max-w-2xl p-8">
        <h1 className="mb-3 flex items-center gap-2 text-xl font-semibold">
          <Sparkles className="h-6 w-6 text-[var(--color-tertiary)]" aria-hidden />
          Ya respondiste a esta solicitud
        </h1>
        <p className="text-[13px] text-[var(--text-tertiary)]">
          Tu decisión fue: <strong>{info.action_taken ?? "—"}</strong>.
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl p-8">
      <header className="mb-5">
        <p className="text-[11px] uppercase tracking-wide text-[var(--text-tertiary)]">
          Solicitud de aprobación
        </p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
          {info.title}
        </h1>
        <p className="mt-1 text-[13px] text-[var(--text-tertiary)]">
          Proyecto: <strong>{info.project_name}</strong> ·{" "}
          <span className="font-mono">{info.folio}</span>
        </p>
        {info.actor_name ? (
          <p className="mt-1 text-[12px] text-[var(--text-tertiary)]">
            Para: {info.actor_name}
          </p>
        ) : null}
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      <section className="space-y-3 rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-sm)]">
        <Field label="Tipo">{info.type}</Field>
        {info.description ? (
          <Field label="Descripción">
            <p className="whitespace-pre-wrap">{info.description}</p>
          </Field>
        ) : null}
        {info.impact ? (
          <Field label="Impacto esperado">
            <p className="whitespace-pre-wrap">{info.impact}</p>
          </Field>
        ) : null}
        <Field label="Vence">
          {new Date(info.expires_at).toLocaleString("es-MX", {
            dateStyle: "medium",
            timeStyle: "short",
          })}
        </Field>
      </section>

      <section className="mt-6 space-y-3">
        <p className="text-[13px] text-[var(--text-secondary)]">
          ¿Qué decisión registras para este Cambio?
        </p>
        <div className="flex flex-wrap gap-2">
          <Button
            variant={pendingAction === "approve" ? "primary" : "secondary"}
            onClick={() => setPendingAction("approve")}
          >
            <CheckCircle2 className="h-4 w-4" aria-hidden /> Aprobar
          </Button>
          <Button
            variant={pendingAction === "reject" ? "danger" : "secondary"}
            onClick={() => setPendingAction("reject")}
          >
            <XCircle className="h-4 w-4" aria-hidden /> Rechazar
          </Button>
        </div>
        {pendingAction ? (
          <div className="space-y-2 rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--color-subtle)] p-3">
            <label className="block">
              <span className="mb-1 block text-[12px] font-medium text-[var(--text-secondary)]">
                Nota (opcional)
              </span>
              <Textarea
                rows={3}
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder={
                  pendingAction === "approve"
                    ? "Comentario opcional…"
                    : "Razón del rechazo…"
                }
              />
            </label>
            <div className="flex flex-wrap items-center justify-end gap-2">
              <Button
                variant="ghost"
                onClick={() => {
                  setPendingAction(null);
                  setNote("");
                }}
                disabled={submitting}
              >
                Cancelar
              </Button>
              <Button onClick={submitDecision} loading={submitting}>
                Confirmar {pendingAction === "approve" ? "aprobación" : "rechazo"}
              </Button>
            </div>
          </div>
        ) : null}
      </section>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--color-tertiary)]">
        {label}
      </p>
      <div className="mt-0.5 text-[13px] text-[var(--color-primary)]">{children}</div>
    </div>
  );
}
