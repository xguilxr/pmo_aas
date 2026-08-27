"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState, type FormEvent, type ReactNode } from "react";

import { BackLink } from "@/components/back-link";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Icono } from "@/components/ui/icono";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api";
import {
  getProjectAIContext,
  updateProjectAIContext,
  type ProjectAIContext,
} from "@/lib/api/projects";

const MAX_LEN = 20000;

type Notice = { kind: "success" | "danger"; message: string } | null;

type FormState = {
  context_md: string;
  instructions_md: string;
  auto_summary_md: string;
};

export default function ProjectAIContextPage() {
  const params = useParams<{ id: string }>();

  const [ctx, setCtx] = useState<ProjectAIContext | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<Notice>(null);

  const [form, setForm] = useState<FormState>({
    context_md: "",
    instructions_md: "",
    auto_summary_md: "",
  });

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getProjectAIContext(params.id)
      .then((r) => {
        if (cancelled) return;
        setCtx(r);
        setForm({
          context_md: r.context_md ?? "",
          instructions_md: r.instructions_md ?? "",
          auto_summary_md: r.auto_summary_md ?? "",
        });
      })
      .catch((err) => {
        if (cancelled) return;
        setError(
          err instanceof ApiError ? err.message : "No se pudo cargar la memoria IA",
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
    setSaving(true);
    setNotice(null);
    try {
      const updated = await updateProjectAIContext(params.id, {
        context_md: form.context_md.trim() || null,
        instructions_md: form.instructions_md.trim() || null,
        auto_summary_md: form.auto_summary_md.trim() || null,
      });
      setCtx(updated);
      setForm({
        context_md: updated.context_md ?? "",
        instructions_md: updated.instructions_md ?? "",
        auto_summary_md: updated.auto_summary_md ?? "",
      });
      setNotice({ kind: "success", message: "Memoria IA actualizada." });
    } catch (err) {
      setNotice({
        kind: "danger",
        message:
          err instanceof ApiError ? err.message : "No se pudo guardar la memoria IA.",
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
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (error || !ctx) {
    return (
      <div className="mx-auto max-w-3xl">
        <Banner variant="danger">{error ?? "Memoria IA no encontrada."}</Banner>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <header className="space-y-3">
        <div className="flex items-center gap-2">
          <BackLink fallbackHref={`/pmo/projects/${ctx.project_id}`} />
          <nav className="text-[11px] text-[var(--text-tertiary)]">
            <Link href="/pmo/projects" className="hover:underline">
              Proyectos
            </Link>
            <span className="mx-1">/</span>
            <Link href={`/pmo/projects/${ctx.project_id}`} className="hover:underline">
              Detalle
            </Link>
            <span className="mx-1">/</span>
            <span>Memoria IA</span>
          </nav>
        </div>
        <div className="flex items-start gap-3">
          <span className="inline-flex h-9 w-9 items-center justify-center rounded-[var(--radius-md)] bg-[var(--color-subtle)] text-[var(--text-secondary)]">
            <Icono nombre="info" size={18} />
          </span>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
              Memoria IA
            </h1>
            <p className="mt-1 text-sm text-[var(--text-tertiary)]">
              Contexto persistente que la IA usa al generar minutas y reportes de
              este proyecto.
            </p>
          </div>
        </div>
      </header>

      {notice ? <Banner variant={notice.kind}>{notice.message}</Banner> : null}

      <form onSubmit={handleSubmit} className="space-y-6">
        <Section
          title="Contexto y reglas de negocio"
          description="Objetivo, glosario/siglas, reglas, actores clave. Curado por el PM."
        >
          <Textarea
            rows={8}
            maxLength={MAX_LEN}
            value={form.context_md}
            onChange={(e) => setForm({ ...form, context_md: e.target.value })}
          />
          <CharCount value={form.context_md} />
        </Section>

        <Section
          title="Instrucciones permanentes de generación"
          description="Formato, idioma, qué destacar. Se aplican a toda generación de IA."
        >
          <Textarea
            rows={6}
            maxLength={MAX_LEN}
            value={form.instructions_md}
            onChange={(e) => setForm({ ...form, instructions_md: e.target.value })}
          />
          <CharCount value={form.instructions_md} />
        </Section>

        <Section
          title="Resumen acumulado (mantenido por IA)"
          description={
            <>
              La IA actualiza este resumen automáticamente al guardar minutas.
              Puedes editarlo o podarlo aquí.
              {ctx.auto_summary_updated_at ? (
                <span className="mt-1 block text-[var(--text-tertiary)]">
                  Actualizado por IA el {formatDateTime(ctx.auto_summary_updated_at)}.
                </span>
              ) : null}
            </>
          }
        >
          <Textarea
            rows={8}
            maxLength={MAX_LEN}
            value={form.auto_summary_md}
            onChange={(e) => setForm({ ...form, auto_summary_md: e.target.value })}
          />
          <CharCount value={form.auto_summary_md} />
        </Section>

        <div className="flex items-center justify-end gap-2 border-t border-[var(--border-default)] pt-4 shadow-[var(--linea-surco-arriba)]">
          <Link href={`/pmo/projects/${ctx.project_id}`}>
            <Button type="button" variant="secondary" disabled={saving}>
              Cancelar
            </Button>
          </Link>
          <Button type="submit" loading={saving}>
            <Icono nombre="check" size={15} />
            Guardar
          </Button>
        </div>
      </form>
    </div>
  );
}

function Section({
  title,
  description,
  children,
}: {
  title: string;
  description?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--relieve-isla)]">
      <h2 className="text-sm font-semibold text-[var(--text-primary)]">{title}</h2>
      {description ? (
        <p className="mb-3 mt-1 text-[12px] text-[var(--text-tertiary)]">
          {description}
        </p>
      ) : (
        <div className="mb-3" />
      )}
      <div className="space-y-1.5">{children}</div>
    </section>
  );
}

function CharCount({ value }: { value: string }) {
  return (
    <p className="text-right text-[11px] text-[var(--text-tertiary)]">
      {value.length.toLocaleString("es-MX")} / {MAX_LEN.toLocaleString("es-MX")}
    </p>
  );
}

function formatDateTime(s: string): string {
  try {
    return new Date(s).toLocaleString("es-MX", {
      day: "2-digit",
      month: "long",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return s;
  }
}
