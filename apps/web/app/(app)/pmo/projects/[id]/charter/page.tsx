"use client";

import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { ArrowLeft, Download, FileText, Save } from "lucide-react";

import { BackLink } from "@/components/back-link";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api";
import {
  CHARTER_FIELD_LABEL,
  downloadCharter,
  getProjectCharter,
  updateProjectCharter,
  type ProjectCharter,
  type ProjectCharterUpdate,
} from "@/lib/api/project-charters";

const PROJECT_TYPES = [
  { value: "innovation", label: "Innovación" },
  { value: "transformation", label: "Transformación" },
  { value: "operation", label: "Operación" },
  { value: "bau", label: "BAU" },
] as const;

type Notice = { kind: "success" | "danger"; message: string } | null;

export default function ProjectCharterEditPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const search = useSearchParams();
  const justCreated = search.get("created") === "1";

  const [charter, setCharter] = useState<ProjectCharter | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<Notice>(
    justCreated
      ? {
          kind: "success",
          message:
            "Proyecto creado. Complementa el Project Charter antes de arrancar.",
        }
      : null,
  );

  const [form, setForm] = useState<ProjectCharterUpdate>({});

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getProjectCharter(params.id)
      .then((r) => {
        if (cancelled) return;
        setCharter(r);
        setForm({
          project_name: r.project_name,
          description: r.description ?? "",
          sponsor: r.sponsor ?? "",
          sponsor_email: r.sponsor_email ?? "",
          business_leader: r.business_leader ?? "",
          business_leader_email: r.business_leader_email ?? "",
          tech_leader: r.tech_leader ?? "",
          tech_leader_email: r.tech_leader_email ?? "",
          project_type: r.project_type ?? "",
          priority: r.priority ?? null,
          objective: r.objective ?? "",
          restrictions: r.restrictions ?? "",
          risks_summary: r.risks_summary ?? "",
          scope: r.scope ?? "",
          key_people: r.key_people ?? "",
          benefits: r.benefits ?? "",
        });
      })
      .catch((err) => {
        if (cancelled) return;
        setError(
          err instanceof ApiError ? err.message : "No se pudo cargar el charter",
        );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [params.id]);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!charter) return;
    setSaving(true);
    setNotice(null);
    try {
      // Normaliza empty strings → null para respetar el schema.
      const payload: ProjectCharterUpdate = {};
      for (const [k, v] of Object.entries(form)) {
        if (typeof v === "string") {
          payload[k as keyof ProjectCharterUpdate] = (v.trim() || null) as never;
        } else {
          payload[k as keyof ProjectCharterUpdate] = v as never;
        }
      }
      const updated = await updateProjectCharter(charter.project_id, payload);
      setCharter(updated);
      setNotice({ kind: "success", message: "Charter actualizado." });
    } catch (err) {
      setNotice({
        kind: "danger",
        message:
          err instanceof ApiError ? err.message : "No se pudo guardar el charter.",
      });
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-4xl space-y-4">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-10 w-72" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (error || !charter) {
    return (
      <div className="mx-auto max-w-3xl">
        <Banner variant="danger">{error ?? "Charter no encontrado."}</Banner>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="flex items-center gap-2">
        <BackLink fallbackHref={`/pmo/projects/${charter.project_id}`} />
        <nav className="text-xs text-[var(--color-tertiary)]">
          <Link href="/pmo/projects" className="hover:underline">
            Proyectos
          </Link>
          <span className="mx-1">/</span>
          <Link
            href={`/pmo/projects/${charter.project_id}`}
            className="hover:underline"
          >
            {charter.project_name}
          </Link>
          <span className="mx-1">/</span>
          <span>Project Charter</span>
        </nav>
      </div>

      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <span className="inline-flex h-9 w-9 items-center justify-center rounded-[var(--radius-md)] bg-[var(--color-subtle)] text-[var(--color-secondary)]">
            <FileText className="h-5 w-5" aria-hidden />
          </span>
          <div>
            <h1 className="text-2xl font-semibold text-[var(--color-primary)]">
              Project Charter
            </h1>
            <p className="mt-1 text-sm text-[var(--color-tertiary)]">
              Secciones 1–3 editables. Sección 4 (datos de gestión) se sincroniza
              automáticamente desde el proyecto.
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {/* US-083: descarga directa del charter (genera on-demand). */}
          <Button
            type="button"
            variant="secondary"
            onClick={() =>
              downloadCharter(charter.project_id, "docx").catch((err) =>
                window.alert(
                  err instanceof Error ? err.message : "No se pudo descargar",
                ),
              )
            }
          >
            <Download className="h-4 w-4" aria-hidden />
            Descargar DOCX
          </Button>
          <Button
            type="button"
            variant="secondary"
            onClick={() =>
              downloadCharter(charter.project_id, "pdf").catch((err) =>
                window.alert(
                  err instanceof Error ? err.message : "No se pudo descargar",
                ),
              )
            }
          >
            <Download className="h-4 w-4" aria-hidden />
            Descargar PDF
          </Button>
          <Link href={`/pmo/projects/${charter.project_id}`}>
            <Button variant="ghost">
              <ArrowLeft className="h-4 w-4" aria-hidden />
              Volver al proyecto
            </Button>
          </Link>
        </div>
      </header>

      {notice ? <Banner variant={notice.kind}>{notice.message}</Banner> : null}

      {charter?.completeness && !charter.completeness.is_complete ? (
        <Banner variant="warning" title="Charter incompleto">
          Faltan campos requeridos:{" "}
          <span className="font-medium">
            {charter.completeness.missing_fields
              .map((f) => CHARTER_FIELD_LABEL[f] ?? f)
              .join(", ")}
          </span>
          .
        </Banner>
      ) : null}

      <form onSubmit={handleSubmit} className="space-y-6">
        <Section title="1. Información general">
          <Field label="Nombre del proyecto" required>
            <Input
              value={form.project_name ?? ""}
              onChange={(e) =>
                setForm({ ...form, project_name: e.target.value })
              }
              required
            />
          </Field>
          <Field label="Descripción">
            <Textarea
              rows={3}
              value={form.description ?? ""}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </Field>
        </Section>

        <Section title="2. Stakeholders">
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Sponsor">
              <Input
                value={form.sponsor ?? ""}
                onChange={(e) => setForm({ ...form, sponsor: e.target.value })}
              />
            </Field>
            <Field label="Correo del sponsor">
              <Input
                type="email"
                value={form.sponsor_email ?? ""}
                onChange={(e) =>
                  setForm({ ...form, sponsor_email: e.target.value })
                }
              />
            </Field>
            <Field label="Líder de negocio">
              <Input
                value={form.business_leader ?? ""}
                onChange={(e) =>
                  setForm({ ...form, business_leader: e.target.value })
                }
              />
            </Field>
            <Field label="Correo líder de negocio">
              <Input
                type="email"
                value={form.business_leader_email ?? ""}
                onChange={(e) =>
                  setForm({ ...form, business_leader_email: e.target.value })
                }
              />
            </Field>
            <Field label="Líder técnico">
              <Input
                value={form.tech_leader ?? ""}
                onChange={(e) =>
                  setForm({ ...form, tech_leader: e.target.value })
                }
              />
            </Field>
            <Field label="Correo líder técnico">
              <Input
                type="email"
                value={form.tech_leader_email ?? ""}
                onChange={(e) =>
                  setForm({ ...form, tech_leader_email: e.target.value })
                }
              />
            </Field>
          </div>
        </Section>

        <Section title="3. Clasificación y alcance">
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Tipo de proyecto">
              <Select
                value={form.project_type ?? ""}
                onChange={(e) =>
                  setForm({ ...form, project_type: e.target.value })
                }
              >
                <option value="">—</option>
                {PROJECT_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Prioridad (1–5)">
              <Input
                type="number"
                min={1}
                max={5}
                value={form.priority ?? ""}
                onChange={(e) =>
                  setForm({
                    ...form,
                    priority: e.target.value
                      ? Math.max(1, Math.min(5, Number(e.target.value)))
                      : null,
                  })
                }
              />
            </Field>
          </div>
          <Field label="Objetivo">
            <Textarea
              rows={3}
              value={form.objective ?? ""}
              onChange={(e) => setForm({ ...form, objective: e.target.value })}
            />
          </Field>
          <Field label="Alcance">
            <Textarea
              rows={3}
              value={form.scope ?? ""}
              onChange={(e) => setForm({ ...form, scope: e.target.value })}
            />
          </Field>
          <Field label="Beneficios">
            <Textarea
              rows={2}
              value={form.benefits ?? ""}
              onChange={(e) => setForm({ ...form, benefits: e.target.value })}
            />
          </Field>
          <Field label="Restricciones">
            <Textarea
              rows={2}
              value={form.restrictions ?? ""}
              onChange={(e) =>
                setForm({ ...form, restrictions: e.target.value })
              }
            />
          </Field>
          <Field label="Resumen de riesgos">
            <Textarea
              rows={2}
              value={form.risks_summary ?? ""}
              onChange={(e) =>
                setForm({ ...form, risks_summary: e.target.value })
              }
            />
          </Field>
          <Field label="Personas clave">
            <Textarea
              rows={2}
              value={form.key_people ?? ""}
              onChange={(e) => setForm({ ...form, key_people: e.target.value })}
            />
          </Field>
        </Section>

        <div className="flex items-center justify-end gap-2 border-t border-[var(--border-default)] pt-4">
          <Button
            type="button"
            variant="secondary"
            onClick={() => router.push(`/pmo/projects/${charter.project_id}`)}
            disabled={saving}
          >
            Cancelar
          </Button>
          <Button type="submit" loading={saving}>
            <Save className="h-4 w-4" aria-hidden />
            Guardar charter
          </Button>
        </div>
      </form>
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-sm)]">
      <h2 className="mb-4 text-sm font-semibold text-[var(--color-primary)]">
        {title}
      </h2>
      <div className="space-y-4">{children}</div>
    </section>
  );
}

function Field({
  label,
  required,
  children,
}: {
  label: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]">
        {label}
        {required ? <span className="text-[var(--color-danger-fg)]"> *</span> : null}
      </span>
      {children}
    </label>
  );
}
