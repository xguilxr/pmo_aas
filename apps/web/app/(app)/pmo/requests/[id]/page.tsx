"use client";

import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  CheckCircle2,
  ExternalLink,
  FileText,
  Info,
  RotateCcw,
  XCircle,
} from "lucide-react";

import { BackLink } from "@/components/back-link";
import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api";
import { listUsers, type AdminUser } from "@/lib/api/admin";
import { getOrganization, type Organization } from "@/lib/api/organizations";
import {
  createProjectFromRequest,
  getRequest,
  reopenRequest,
  resubmitRequest,
  reviewRequest,
  REQUEST_STATUS_LABEL,
  type ProjectRequest,
  type RequestStatus,
  type ReviewDecision,
} from "@/lib/api/requests";

type Notice = { kind: "success" | "danger" | "info"; message: string } | null;

function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("es-MX", { dateStyle: "medium", timeStyle: "short" });
  } catch {
    return iso;
  }
}

function formatDateOnly(iso: string | null | undefined): string {
  if (!iso) return "—";
  // Acepta "YYYY-MM-DD" o ISO completo. Forzamos parseo local para evitar shift de TZ.
  const ymd = iso.length >= 10 ? iso.slice(0, 10) : iso;
  const [y, m, d] = ymd.split("-").map((s) => Number(s));
  if (!y || !m || !d) return iso;
  const dt = new Date(y, m - 1, d);
  return dt.toLocaleDateString("es-MX", { dateStyle: "long" });
}

function formatMxn(n: string | number): string {
  const v = typeof n === "string" ? Number(n) : n;
  if (!Number.isFinite(v)) return "—";
  return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(v);
}

export default function RequestDetailPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const search = useSearchParams();
  const id = params.id;

  const [request, setRequest] = useState<ProjectRequest | null>(null);
  const [org, setOrg] = useState<Organization | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<Notice>(
    search.get("created") === "1"
      ? { kind: "success", message: "Solicitud enviada. Está en revisión." }
      : null,
  );

  const [reviewModal, setReviewModal] = useState<ReviewDecision | null>(null);
  const [reviewComment, setReviewComment] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const [createModal, setCreateModal] = useState(false);
  const [pms, setPms] = useState<AdminUser[]>([]);
  const [pmId, setPmId] = useState("");
  const [creating, setCreating] = useState(false);

  async function reload() {
    setLoading(true);
    setError(null);
    try {
      const r = await getRequest(id);
      setRequest(r);
      if (r.organization_id) {
        try {
          const o = await getOrganization(r.organization_id);
          setOrg(o);
        } catch {
          setOrg(null);
        }
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar la solicitud");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const canReview = useMemo(() => {
    if (!request) return false;
    return request.status === "in_review" || request.status === "needs_info";
  }, [request]);

  const canCreateProject = useMemo(() => {
    if (!request) return false;
    return request.status === "approved" && !request.project_id;
  }, [request]);

  // ENH-016: reabrir solo si está aprobada y aún no hay proyecto.
  const canReopen = useMemo(() => {
    if (!request) return false;
    return request.status === "approved" && !request.project_id;
  }, [request]);

  async function submitReview() {
    if (!reviewModal || !request) return;
    const needsComment = reviewModal === "reject" || reviewModal === "needs_info";
    if (needsComment && !reviewComment.trim()) {
      setNotice({ kind: "danger", message: "El comentario es obligatorio." });
      return;
    }
    setSubmitting(true);
    setNotice(null);
    try {
      await reviewRequest(request.id, {
        decision: reviewModal,
        comment: reviewComment.trim() || null,
      });
      setReviewModal(null);
      setReviewComment("");
      await reload();
      setNotice({
        kind: "success",
        message:
          reviewModal === "approve"
            ? "Solicitud aprobada."
            : reviewModal === "reject"
              ? "Solicitud rechazada."
              : "Solicitud marcada como pendiente de información.",
      });
    } catch (err) {
      setNotice({
        kind: "danger",
        message: err instanceof ApiError ? err.message : "No se pudo registrar la revisión.",
      });
    } finally {
      setSubmitting(false);
    }
  }

  async function handleResubmit() {
    if (!request) return;
    setSubmitting(true);
    setNotice(null);
    try {
      await resubmitRequest(request.id);
      await reload();
      setNotice({ kind: "success", message: "Solicitud re-sometida a revisión." });
    } catch (err) {
      setNotice({
        kind: "danger",
        message: err instanceof ApiError ? err.message : "No se pudo re-someter la solicitud.",
      });
    } finally {
      setSubmitting(false);
    }
  }

  async function handleReopen() {
    if (!request) return;
    if (
      !window.confirm(
        "¿Reabrir esta solicitud? Volverá a 'En revisión' y perderá el comentario del revisor.",
      )
    ) {
      return;
    }
    setSubmitting(true);
    setNotice(null);
    try {
      await reopenRequest(request.id);
      await reload();
      setNotice({ kind: "success", message: "Solicitud reabierta." });
    } catch (err) {
      setNotice({
        kind: "danger",
        message:
          err instanceof ApiError ? err.message : "No se pudo reabrir la solicitud.",
      });
    } finally {
      setSubmitting(false);
    }
  }

  async function openCreateProject() {
    setCreateModal(true);
    if (pms.length === 0) {
      try {
        const res = await listUsers({ is_active: true, limit: 100 });
        setPms(res.items);
      } catch {
        // fallback vacío
      }
    }
  }

  async function submitCreateProject() {
    if (!request || !pmId) return;
    setCreating(true);
    setNotice(null);
    try {
      const out = await createProjectFromRequest(request.id, { pm_id: pmId });
      setCreateModal(false);
      // BUG-017: tras aprobar + crear proyecto, abrir el charter para
      // complementar información que la solicitud no captura
      // (stakeholders extra, prioridad, riesgos, etc.). Si el proyecto
      // ya existía (idempotent), aún así es útil abrir el charter.
      router.push(`/pmo/projects/${out.project_id}/charter?created=1`);
    } catch (err) {
      setNotice({
        kind: "danger",
        message: err instanceof ApiError ? err.message : "No se pudo crear el proyecto.",
      });
    } finally {
      setCreating(false);
    }
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-4xl space-y-4">
        <Skeleton className="h-6 w-40" />
        <Skeleton className="h-10 w-72" />
        <div className="space-y-3 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-6">
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
        </div>
      </div>
    );
  }

  if (error || !request) {
    return (
      <div className="mx-auto max-w-3xl">
        <Banner variant="danger">{error ?? "Solicitud no encontrada."}</Banner>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <header className="space-y-2">
        <div className="flex items-center gap-2">
          <BackLink fallbackHref="/pmo/requests" />
          <nav className="text-xs text-[var(--color-tertiary)]">
            <Link href="/pmo/requests" className="hover:underline">
              Solicitudes
            </Link>
            <span className="mx-1">/</span>
            <span>{request.folio}</span>
          </nav>
        </div>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-semibold text-[var(--color-primary)]">
                {request.title}
              </h1>
              <StatusBadge status={request.status} />
            </div>
            <p className="mt-1 font-mono text-xs text-[var(--color-tertiary)]">{request.folio}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {canReview ? (
              <>
                <Button onClick={() => setReviewModal("approve")} disabled={submitting}>
                  <CheckCircle2 className="h-4 w-4" aria-hidden />
                  Aprobar
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => setReviewModal("needs_info")}
                  disabled={submitting}
                >
                  <Info className="h-4 w-4" aria-hidden />
                  Pedir info
                </Button>
                <Button
                  variant="danger"
                  onClick={() => setReviewModal("reject")}
                  disabled={submitting}
                >
                  <XCircle className="h-4 w-4" aria-hidden />
                  Rechazar
                </Button>
              </>
            ) : null}
            {request.status === "needs_info" ? (
              <Button variant="secondary" onClick={handleResubmit} loading={submitting}>
                Re-someter
              </Button>
            ) : null}
            {canCreateProject ? (
              <Button onClick={openCreateProject}>
                <ArrowRight className="h-4 w-4" aria-hidden />
                Crear proyecto
              </Button>
            ) : null}
            {canReopen ? (
              <Button
                variant="secondary"
                onClick={handleReopen}
                loading={submitting}
                title="Regresa la solicitud a 'En revisión' (sólo si aún no hay proyecto creado)"
              >
                <RotateCcw className="h-4 w-4" aria-hidden />
                Reabrir
              </Button>
            ) : null}
            {request.project_id ? (
              <>
                <Link
                  href={`/pmo/projects/${request.project_id}/charter`}
                  className="inline-flex items-center gap-1 text-sm font-medium text-[var(--color-accent)] hover:underline"
                >
                  Editar charter
                  <FileText className="h-4 w-4" aria-hidden />
                </Link>
                <Link
                  href={`/pmo/projects/${request.project_id}`}
                  className="inline-flex items-center gap-1 text-sm font-medium text-[var(--color-accent)] hover:underline"
                >
                  Ver proyecto
                  <ExternalLink className="h-4 w-4" aria-hidden />
                </Link>
              </>
            ) : null}
          </div>
        </div>
      </header>

      {notice ? <Banner variant={notice.kind}>{notice.message}</Banner> : null}

      {request.review_comment ? (
        <Banner variant={request.status === "rejected" ? "danger" : "info"} title="Comentario del revisor">
          {request.review_comment}
        </Banner>
      ) : null}

      <section className="grid gap-4 sm:grid-cols-2">
        <Card title="Datos de negocio">
          <Row k="Sponsor" v={request.sponsor} />
          <Row k="Organización" v={org?.name ?? "—"} />
          <Row k="Unidad de negocio" v={request.business_unit} />
          <Row k="Departamento" v={request.department} />
          <Row k="Presupuesto" v={formatMxn(request.budget)} />
        </Card>
        <Card title="Seguimiento">
          <Row k="Fecha de solicitud" v={formatDate(request.requested_at)} />
          <Row k="Revisada" v={formatDate(request.reviewed_at)} />
          {request.delivery_constraint_date ? (
            <Row
              k="Fecha de restricción de entrega"
              v={formatDateOnly(request.delivery_constraint_date)}
            />
          ) : null}
          <Row k="Estado" v={REQUEST_STATUS_LABEL[request.status]} />
          {request.project_id ? <Row k="Proyecto" v={request.project_id} /> : null}
        </Card>
        <Card title="Descripción" full>
          <p className="whitespace-pre-wrap text-sm text-[var(--color-primary)]">
            {request.description}
          </p>
        </Card>
        <Card title="Objetivo" full>
          <p className="whitespace-pre-wrap text-sm text-[var(--color-primary)]">
            {request.objective}
          </p>
        </Card>
        <Card title="Alcance" full>
          <p className="whitespace-pre-wrap text-sm text-[var(--color-primary)]">{request.scope}</p>
        </Card>
        <Card title="Beneficios" full>
          <p className="whitespace-pre-wrap text-sm text-[var(--color-primary)]">
            {request.benefits}
          </p>
        </Card>
        <Card title="Adjuntos" full>
          {request.attachments.length ? (
            <ul className="divide-y divide-[var(--border-subtle)] rounded-[var(--radius-md)] border border-[var(--border-default)]">
              {request.attachments.map((a, i) => (
                <li key={i} className="flex items-center justify-between gap-3 px-3 py-2 text-sm">
                  <span className="truncate font-medium text-[var(--color-primary)]">
                    {a.filename}
                  </span>
                  <a
                    href={a.url}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="inline-flex items-center gap-1 text-xs text-[var(--color-accent)] hover:underline"
                  >
                    Abrir
                    <ExternalLink className="h-3.5 w-3.5" aria-hidden />
                  </a>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-[var(--color-tertiary)]">Sin adjuntos.</p>
          )}
        </Card>
      </section>

      <Modal
        open={reviewModal !== null}
        onClose={() => {
          if (!submitting) setReviewModal(null);
        }}
        title={
          reviewModal === "approve"
            ? "Aprobar solicitud"
            : reviewModal === "reject"
              ? "Rechazar solicitud"
              : "Solicitar información"
        }
        description={
          reviewModal === "approve"
            ? "Una vez aprobada podrás convertirla en proyecto."
            : "El solicitante será notificado de la decisión."
        }
        footer={
          <>
            <Button variant="secondary" onClick={() => setReviewModal(null)} disabled={submitting}>
              Cancelar
            </Button>
            <Button onClick={submitReview} loading={submitting}>
              Confirmar
            </Button>
          </>
        }
      >
        <label htmlFor="review-comment" className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]">
          Comentario{" "}
          {reviewModal && reviewModal !== "approve" ? (
            <span className="text-[var(--color-danger-fg)]">*</span>
          ) : (
            <span className="text-[var(--color-tertiary)]">(opcional)</span>
          )}
        </label>
        <Textarea
          id="review-comment"
          rows={4}
          value={reviewComment}
          onChange={(e) => setReviewComment(e.target.value)}
          placeholder="Notas para el solicitante"
        />
      </Modal>

      <Modal
        open={createModal}
        onClose={() => {
          if (!creating) setCreateModal(false);
        }}
        title="Crear proyecto desde solicitud"
        description="Selecciona al Project Manager asignado."
        footer={
          <>
            <Button variant="secondary" onClick={() => setCreateModal(false)} disabled={creating}>
              Cancelar
            </Button>
            <Button onClick={submitCreateProject} loading={creating} disabled={!pmId}>
              Crear proyecto
            </Button>
          </>
        }
      >
        <label htmlFor="pm" className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]">
          Project Manager
        </label>
        <Select id="pm" value={pmId} onChange={(e) => setPmId(e.target.value)}>
          <option value="">Selecciona…</option>
          {pms.map((u) => (
            <option key={u.id} value={u.id}>
              {u.full_name} ({u.email})
            </option>
          ))}
        </Select>
      </Modal>
    </div>
  );
}

function StatusBadge({ status }: { status: RequestStatus }) {
  const variant =
    status === "approved"
      ? "success"
      : status === "rejected"
        ? "danger"
        : status === "needs_info"
          ? "warning"
          : "info";
  return <Badge variant={variant}>{REQUEST_STATUS_LABEL[status]}</Badge>;
}

function Card({
  title,
  children,
  full,
}: {
  title: string;
  children: React.ReactNode;
  full?: boolean;
}) {
  return (
    <article
      className={`rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-sm)] ${
        full ? "sm:col-span-2" : ""
      }`}
    >
      <h2 className="mb-3 text-xs font-medium uppercase tracking-wide text-[var(--color-tertiary)]">
        {title}
      </h2>
      <div className="space-y-2">{children}</div>
    </article>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="grid gap-0.5 sm:grid-cols-[160px_1fr]">
      <span className="text-xs uppercase tracking-wide text-[var(--color-tertiary)]">{k}</span>
      <span className="text-sm text-[var(--color-primary)]">{v || "—"}</span>
    </div>
  );
}
