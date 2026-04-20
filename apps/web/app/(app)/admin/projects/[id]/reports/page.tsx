"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { Mail, Send, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api";
import {
  draftReport,
  sendReport,
  type ReportSections,
} from "@/lib/api/ai";

export default function ReportsPage() {
  const { id } = useParams<{ id: string }>();
  const [loading, setLoading] = useState(false);
  const [reportId, setReportId] = useState<string | null>(null);
  const [model, setModel] = useState<string | null>(null);
  const [sections, setSections] = useState<ReportSections | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [subject, setSubject] = useState("");
  const [recipientsText, setRecipientsText] = useState("");
  const [includePdf, setIncludePdf] = useState(false);
  const [sending, setSending] = useState(false);

  async function generate() {
    setLoading(true);
    setError(null);
    setNotice(null);
    try {
      const r = await draftReport(id, {});
      setReportId(r.report_id);
      setSections(r.sections);
      setModel(r.model);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo generar el reporte");
    } finally {
      setLoading(false);
    }
  }

  async function handleSend() {
    if (!reportId) return;
    const recipients = recipientsText
      .split(/[,\s;]+/)
      .map((s) => s.trim())
      .filter(Boolean);
    if (recipients.length === 0) {
      setError("Agrega al menos un destinatario");
      return;
    }
    setSending(true);
    setError(null);
    try {
      const res = await sendReport(reportId, {
        recipients,
        include_pdf: includePdf,
        subject: subject.trim() || undefined,
      });
      setNotice(`Reporte enviado a ${res.recipients.length} destinatarios.`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo enviar el reporte");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-5">
      <header>
        <nav className="text-[11px] text-[var(--text-tertiary)]">
          <Link href="/admin/projects" className="hover:underline">
            Proyectos
          </Link>
          <span className="mx-1">/</span>
          <Link href={`/admin/projects/${id}`} className="hover:underline">
            Detalle
          </Link>
          <span className="mx-1">/</span>
          <span>Reportes IA</span>
        </nav>
        <h1 className="mt-1 flex items-center gap-2 text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
          <Sparkles className="h-6 w-6 text-[var(--color-accent)]" aria-hidden />
          Reporte de avance
        </h1>
        <p className="mt-1 text-[13px] text-[var(--text-tertiary)]">
          Genera un draft con IA a partir del estado del proyecto, revísalo y envíalo por correo.
        </p>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}
      {notice ? <Banner variant="success">{notice}</Banner> : null}

      {!sections ? (
        <section className="flex flex-col items-center gap-3 rounded-[var(--radius-window)] border border-dashed border-[var(--border-default)] bg-[var(--color-surface)] p-12 text-center">
          <p className="text-[14px] text-[var(--text-primary)]">
            Todavía no hay draft. Genera uno con el contexto actual.
          </p>
          <p className="max-w-md text-[12px] text-[var(--text-tertiary)]">
            La IA incluye avance, presupuesto plan vs real, top 5 riesgos, cambios en revisión y
            últimas minutas. Tú decides qué editar antes de enviar.
          </p>
          <Button onClick={generate} loading={loading}>
            <Sparkles className="h-4 w-4" aria-hidden /> Generar draft
          </Button>
        </section>
      ) : (
        <>
          <section className="rounded-[var(--radius-window)] border border-[var(--border-subtle)] bg-[var(--color-surface)] p-6 space-y-5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-[16px] font-semibold text-[var(--text-primary)]">
                Draft generado
              </h2>
              {model ? <Badge>{model}</Badge> : null}
            </div>

            <Field label="Resumen ejecutivo">
              <Textarea
                rows={6}
                value={typeof sections.executive_summary === "string" ? sections.executive_summary : ""}
                onChange={(e) =>
                  setSections({ ...sections, executive_summary: e.target.value })
                }
              />
            </Field>

            <Field label="Logros">
              <Textarea
                rows={4}
                value={stringify(sections.achievements)}
                onChange={(e) =>
                  setSections({ ...sections, achievements: parseLines(e.target.value) })
                }
              />
            </Field>

            <Field label="Próximas actividades">
              <Textarea
                rows={4}
                value={stringify(sections.next_activities)}
                onChange={(e) =>
                  setSections({ ...sections, next_activities: parseLines(e.target.value) })
                }
              />
            </Field>

            {sections.top_risks?.length ? (
              <section>
                <h3 className="mb-2 text-[12px] font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">
                  Top riesgos
                </h3>
                <ul className="space-y-1 text-[13px] text-[var(--text-primary)]">
                  {sections.top_risks.map((r, i) => (
                    <li key={i}>
                      · {r.title}
                      {r.severity !== undefined ? (
                        <span className="ml-2 text-[var(--text-tertiary)]">sev {r.severity}</span>
                      ) : null}
                      {r.status ? (
                        <span className="ml-2 text-[var(--text-tertiary)]">({r.status})</span>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}
          </section>

          <section className="rounded-[var(--radius-window)] border border-[var(--border-subtle)] bg-[var(--color-surface)] p-6 space-y-3">
            <h2 className="text-[14px] font-semibold text-[var(--text-primary)]">
              Enviar por correo
            </h2>
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Asunto (opcional)">
                <Input value={subject} onChange={(e) => setSubject(e.target.value)} />
              </Field>
              <Field label="Destinatarios (separados por coma)">
                <Input
                  type="email"
                  multiple
                  value={recipientsText}
                  onChange={(e) => setRecipientsText(e.target.value)}
                  placeholder="sponsor@empresa.com, pm@empresa.com"
                />
              </Field>
            </div>
            <label className="inline-flex items-center gap-2 text-[12px] text-[var(--text-secondary)]">
              <input
                type="checkbox"
                checked={includePdf}
                onChange={(e) => setIncludePdf(e.target.checked)}
              />
              Adjuntar PDF (post-MVP)
            </label>
            <div className="flex justify-end">
              <Button onClick={handleSend} loading={sending}>
                <Send className="h-4 w-4" aria-hidden /> Enviar reporte
              </Button>
            </div>
          </section>

          <Banner variant="info">
            <Mail className="mr-1 inline h-4 w-4" aria-hidden />
            En dev/test el envío queda registrado pero no despacha correos reales.
          </Banner>
        </>
      )}
    </div>
  );
}

function stringify(v: unknown): string {
  if (Array.isArray(v)) return v.map((x) => String(x)).join("\n");
  if (typeof v === "string") return v;
  return "";
}

function parseLines(s: string): string[] {
  return s.split("\n").map((l) => l.trim()).filter(Boolean);
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-[12px] font-medium text-[var(--text-secondary)]">{label}</span>
      {children}
    </label>
  );
}
