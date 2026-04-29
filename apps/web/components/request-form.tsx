"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { CheckCircle2, FileText, Plus, Trash2 } from "lucide-react";

import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api";
import { listOrganizations, type Organization } from "@/lib/api/organizations";
import {
  createRequest,
  type ProjectRequest,
  type ProjectRequestCreateBody,
  type RequestAttachment,
} from "@/lib/api/requests";
import { cn } from "@/lib/cn";

type Draft = {
  title: string;
  description: string;
  objective: string;
  organization_id: string;
  business_unit: string;
  department: string;
  sponsor: string;
  sponsor_email: string;
  benefits: string;
  budget: string;
  scope: string;
  entregables: string;
  key_people: string;
  if_not_done: string;
  observations: string;
  requester_name: string;
  requester_email: string;
  delivery_constraint_date: string;
  attachments: RequestAttachment[];
};

const EMPTY: Draft = {
  title: "",
  description: "",
  objective: "",
  organization_id: "",
  business_unit: "",
  department: "",
  sponsor: "",
  sponsor_email: "",
  benefits: "",
  budget: "",
  scope: "",
  entregables: "",
  key_people: "",
  if_not_done: "",
  observations: "",
  requester_name: "",
  requester_email: "",
  delivery_constraint_date: "",
  attachments: [],
};

const DRAFT_KEY = "pmoaas.requests.draft";
const AUTOSAVE_MS = 30_000;

const STEPS = [
  { id: "basics", label: "Básicos" },
  { id: "scope", label: "Alcance" },
  { id: "attachments", label: "Adjuntos" },
  { id: "review", label: "Revisar" },
] as const;

type StepId = (typeof STEPS)[number]["id"];

function currency(v: string): string {
  const n = Number(v);
  if (!Number.isFinite(n)) return "—";
  return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(n);
}

function loadDraft(): Draft | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(DRAFT_KEY);
  if (!raw) return null;
  try {
    return { ...EMPTY, ...(JSON.parse(raw) as Draft) };
  } catch {
    return null;
  }
}

function saveDraft(d: Draft) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(DRAFT_KEY, JSON.stringify(d));
}

function clearDraft() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(DRAFT_KEY);
}

export function RequestForm() {
  const router = useRouter();
  const [draft, setDraft] = useState<Draft>(EMPTY);
  const [step, setStep] = useState<StepId>("basics");
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [loadingOrgs, setLoadingOrgs] = useState(true);
  const [saving, setSaving] = useState(false);
  const [autosavedAt, setAutosavedAt] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [showSummary, setShowSummary] = useState(false);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const prev = loadDraft();
    if (prev) setDraft(prev);
    setHydrated(true);
  }, []);

  useEffect(() => {
    let cancelled = false;
    listOrganizations({ is_active: true })
      .then((r) => {
        if (!cancelled) setOrgs(r);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoadingOrgs(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    saveDraft(draft);
  }, [draft, hydrated]);

  useEffect(() => {
    if (!hydrated) return;
    const t = setInterval(() => {
      saveDraft(draft);
      setAutosavedAt(new Date());
    }, AUTOSAVE_MS);
    return () => clearInterval(t);
  }, [draft, hydrated]);

  function setField<K extends keyof Draft>(k: K, v: Draft[K]) {
    setDraft((d) => ({ ...d, [k]: v }));
    setFieldErrors((e) => {
      if (!e[k as string]) return e;
      const next = { ...e };
      delete next[k as string];
      return next;
    });
  }

  function focusFirstError(errors: Record<string, string>) {
    if (typeof window === "undefined") return;
    const order = [
      "title",
      "sponsor",
      "sponsor_email",
      "organization_id",
      "business_unit",
      "department",
      "budget",
      "description",
      "objective",
      "scope",
      "benefits",
    ];
    const idMap: Record<string, string> = {
      organization_id: "org",
      business_unit: "bu",
      department: "dept",
      description: "desc",
      objective: "obj",
    };
    const key = order.find((k) => errors[k]);
    if (!key) return;
    const id = idMap[key] ?? key;
    requestAnimationFrame(() => {
      const el = document.getElementById(id);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
        (el as HTMLInputElement).focus({ preventScroll: true });
      }
    });
  }

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const result = validateAll(draft);
    if (!result.ok) {
      setFieldErrors(result.errors);
      setShowSummary(true);
      const firstStep = firstStepWithError(result.errors);
      if (firstStep) setStep(firstStep);
      focusFirstError(result.errors);
      return;
    }
    setShowSummary(false);
    setSaving(true);
    setError(null);
    try {
      const body: ProjectRequestCreateBody = {
        title: draft.title.trim(),
        description: draft.description.trim(),
        objective: draft.objective.trim(),
        organization_id: draft.organization_id,
        business_unit: draft.business_unit.trim(),
        department: draft.department.trim(),
        sponsor: draft.sponsor.trim(),
        sponsor_email: draft.sponsor_email.trim(),
        benefits: draft.benefits.trim(),
        budget: draft.budget.trim() ? Number(draft.budget) : null,
        scope: draft.scope.trim(),
        entregables: draft.entregables.trim() || null,
        key_people: draft.key_people.trim() || null,
        if_not_done: draft.if_not_done.trim() || null,
        observations: draft.observations.trim() || null,
        requester_name: draft.requester_name.trim() || null,
        requester_email: draft.requester_email.trim() || null,
        delivery_constraint_date: draft.delivery_constraint_date.trim() || null,
        attachments: draft.attachments,
      };
      const created: ProjectRequest = await createRequest(body);
      clearDraft();
      router.replace(`/pmo/requests/${created.id}?created=1`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear la solicitud");
    } finally {
      setSaving(false);
    }
  }

  function goNext() {
    const idx = STEPS.findIndex((s) => s.id === step);
    if (idx < STEPS.length - 1) setStep(STEPS[idx + 1].id);
  }

  function goBack() {
    const idx = STEPS.findIndex((s) => s.id === step);
    if (idx > 0) setStep(STEPS[idx - 1].id);
  }

  return (
    <form
      onSubmit={handleSubmit}
      noValidate
      className="space-y-5 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-sm)]"
    >
      <ol className="flex flex-wrap gap-2" aria-label="Pasos del formulario">
        {STEPS.map((s, idx) => {
          const current = s.id === step;
          const done = STEPS.findIndex((x) => x.id === step) > idx;
          return (
            <li key={s.id}>
              <button
                type="button"
                onClick={() => setStep(s.id)}
                aria-current={current ? "step" : undefined}
                className={cn(
                  "inline-flex items-center gap-2 rounded-[var(--radius-md)] border px-3 py-1.5 text-sm transition-colors",
                  current
                    ? "border-[var(--color-primary)] bg-[var(--color-primary)] text-[var(--color-inverse)]"
                    : done
                      ? "border-[var(--color-success-border)] bg-[var(--color-success-bg)] text-[var(--color-success-fg)]"
                      : "border-[var(--border-default)] text-[var(--color-secondary)] hover:bg-[var(--color-subtle)]",
                )}
              >
                <span className="inline-flex h-5 w-5 items-center justify-center rounded-full border border-current text-[11px] font-semibold">
                  {done ? <CheckCircle2 className="h-4 w-4" aria-hidden /> : idx + 1}
                </span>
                {s.label}
              </button>
            </li>
          );
        })}
      </ol>

      {error ? <Banner variant="danger">{error}</Banner> : null}
      {showSummary && Object.keys(fieldErrors).length > 0 ? (
        <Banner variant="danger">
          <div>
            <p className="font-medium">Faltan campos obligatorios:</p>
            <ul className="mt-1 list-disc pl-5 text-sm">
              {fieldsSummary(fieldErrors).map((f) => (
                <li key={f}>{f}</li>
              ))}
            </ul>
          </div>
        </Banner>
      ) : null}
      {autosavedAt ? (
        <p className="text-xs text-[var(--color-tertiary)]">
          Guardado automático · {autosavedAt.toLocaleTimeString("es-MX")}
        </p>
      ) : null}

      {step === "basics" ? (
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Título" htmlFor="title" error={fieldErrors.title} required full>
            <Input
              id="title"
              value={draft.title}
              onChange={(e) => setField("title", e.target.value)}
              maxLength={200}
              required
            />
          </Field>
          <Field label="Sponsor" htmlFor="sponsor" error={fieldErrors.sponsor} required>
            <Input
              id="sponsor"
              value={draft.sponsor}
              onChange={(e) => setField("sponsor", e.target.value)}
              required
            />
          </Field>
          <Field
            label="Email del sponsor"
            htmlFor="sponsor_email"
            error={fieldErrors.sponsor_email}
            required
          >
            <Input
              id="sponsor_email"
              type="email"
              value={draft.sponsor_email}
              onChange={(e) => setField("sponsor_email", e.target.value)}
              required
            />
          </Field>
          <Field
            label="Solicitante (nombre)"
            htmlFor="requester_name"
            error={fieldErrors.requester_name}
            help="Opcional — si se deja vacío se usa tu nombre"
          >
            <Input
              id="requester_name"
              value={draft.requester_name}
              onChange={(e) => setField("requester_name", e.target.value)}
            />
          </Field>
          <Field
            label="Solicitante (email)"
            htmlFor="requester_email"
            error={fieldErrors.requester_email}
            help="Opcional — si se deja vacío se usa tu correo"
          >
            <Input
              id="requester_email"
              type="email"
              value={draft.requester_email}
              onChange={(e) => setField("requester_email", e.target.value)}
            />
          </Field>
          <Field label="Organización" htmlFor="org" error={fieldErrors.organization_id} required>
            <Select
              id="org"
              value={draft.organization_id}
              onChange={(e) => setField("organization_id", e.target.value)}
              disabled={loadingOrgs}
              required
            >
              <option value="">Selecciona…</option>
              {orgs.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Unidad de negocio" htmlFor="bu" error={fieldErrors.business_unit} required>
            <Input
              id="bu"
              value={draft.business_unit}
              onChange={(e) => setField("business_unit", e.target.value)}
              required
            />
          </Field>
          <Field label="Departamento" htmlFor="dept" error={fieldErrors.department} required>
            <Input
              id="dept"
              value={draft.department}
              onChange={(e) => setField("department", e.target.value)}
              required
            />
          </Field>
          <Field
            label="Presupuesto (MXN)"
            htmlFor="budget"
            error={fieldErrors.budget}
            help={
              draft.budget
                ? currency(draft.budget)
                : "Opcional — si tienes estimado grueso (ej: 1250000.00)"
            }
          >
            <Input
              id="budget"
              type="number"
              min={0}
              step="0.01"
              inputMode="decimal"
              value={draft.budget}
              onChange={(e) => setField("budget", e.target.value)}
            />
          </Field>
          <Field
            label="Fecha de restricción de entrega"
            htmlFor="delivery_constraint_date"
            error={fieldErrors.delivery_constraint_date}
            help="Opcional — si la entrega debe ocurrir en/antes de una fecha"
          >
            <Input
              id="delivery_constraint_date"
              type="date"
              value={draft.delivery_constraint_date}
              onChange={(e) => setField("delivery_constraint_date", e.target.value)}
            />
          </Field>
          <Field
            label="Descripción"
            htmlFor="desc"
            error={fieldErrors.description}
            required
            full
          >
            <Textarea
              id="desc"
              rows={3}
              value={draft.description}
              onChange={(e) => setField("description", e.target.value)}
              required
            />
          </Field>
          <Field
            label="Objetivo"
            htmlFor="obj"
            error={fieldErrors.objective}
            required
            full
          >
            <Textarea
              id="obj"
              rows={3}
              value={draft.objective}
              onChange={(e) => setField("objective", e.target.value)}
              required
            />
          </Field>
        </div>
      ) : null}

      {step === "scope" ? (
        <div className="grid gap-4">
          <Field label="Alcance" htmlFor="scope" error={fieldErrors.scope} required>
            <Textarea
              id="scope"
              rows={5}
              value={draft.scope}
              onChange={(e) => setField("scope", e.target.value)}
              required
            />
          </Field>
          <Field
            label="Entregables"
            htmlFor="entregables"
            error={fieldErrors.entregables}
            help="Qué productos concretos se entregan (opcional, complementa Alcance)"
          >
            <Textarea
              id="entregables"
              rows={3}
              value={draft.entregables}
              onChange={(e) => setField("entregables", e.target.value)}
            />
          </Field>
          <Field
            label="Beneficios esperados"
            htmlFor="benefits"
            error={fieldErrors.benefits}
            required
          >
            <Textarea
              id="benefits"
              rows={4}
              value={draft.benefits}
              onChange={(e) => setField("benefits", e.target.value)}
              required
            />
          </Field>
          <Field
            label="Personas clave"
            htmlFor="key_people"
            help="Stakeholders relevantes (opcional)"
          >
            <Textarea
              id="key_people"
              rows={2}
              value={draft.key_people}
              onChange={(e) => setField("key_people", e.target.value)}
            />
          </Field>
          <Field
            label="¿Qué pasa si no se hace?"
            htmlFor="if_not_done"
            help="Impacto de no ejecutar el proyecto (opcional)"
          >
            <Textarea
              id="if_not_done"
              rows={3}
              value={draft.if_not_done}
              onChange={(e) => setField("if_not_done", e.target.value)}
            />
          </Field>
          <Field
            label="Observaciones"
            htmlFor="observations"
            help="Notas adicionales para el revisor (opcional)"
          >
            <Textarea
              id="observations"
              rows={2}
              value={draft.observations}
              onChange={(e) => setField("observations", e.target.value)}
            />
          </Field>
        </div>
      ) : null}

      {step === "attachments" ? (
        <AttachmentsEditor
          value={draft.attachments}
          onChange={(next) => setField("attachments", next)}
        />
      ) : null}

      {step === "review" ? (
        <ReviewPane draft={draft} orgs={orgs} onEdit={(id) => setStep(id)} />
      ) : null}

      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-[var(--border-default)] pt-4">
        <Button type="button" variant="danger" onClick={() => router.push("/pmo/requests")}>
          Cancelar
        </Button>
        <div className="flex gap-2">
          <Button
            type="button"
            variant="secondary"
            disabled={step === "basics"}
            onClick={goBack}
          >
            Atrás
          </Button>
          {step !== "review" ? (
            <Button type="button" onClick={goNext}>
              Siguiente
            </Button>
          ) : (
            <Button type="submit" loading={saving}>
              Enviar solicitud
            </Button>
          )}
        </div>
      </div>
    </form>
  );
}

type FieldProps = {
  label: string;
  htmlFor: string;
  error?: string;
  children: React.ReactNode;
  required?: boolean;
  full?: boolean;
  help?: string;
};

function Field({ label, htmlFor, error, children, required, full, help }: FieldProps) {
  const errorId = error ? `${htmlFor}-error` : undefined;
  return (
    <div className={cn(full ? "sm:col-span-2" : undefined)}>
      <label
        htmlFor={htmlFor}
        className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
      >
        {label} {required ? <span className="text-[var(--color-danger-fg)]">*</span> : null}
      </label>
      <div
        className={cn(
          error
            ? "rounded-[var(--radius-md)] ring-2 ring-[var(--color-danger-fg)]/40"
            : undefined,
        )}
        aria-describedby={errorId}
      >
        {children}
      </div>
      {error ? (
        <p id={errorId} className="mt-1 text-xs text-[var(--color-danger-fg)]" role="alert">
          {error}
        </p>
      ) : help ? (
        <p className="mt-1 text-xs text-[var(--color-tertiary)]">{help}</p>
      ) : null}
    </div>
  );
}

function fieldsSummary(errors: Record<string, string>): string[] {
  const labels: Record<string, string> = {
    title: "Título",
    description: "Descripción",
    objective: "Objetivo",
    organization_id: "Organización",
    business_unit: "Unidad de negocio",
    department: "Departamento",
    sponsor: "Sponsor",
    sponsor_email: "Email del sponsor",
    benefits: "Beneficios esperados",
    budget: "Presupuesto",
    scope: "Alcance",
    requester_email: "Email del solicitante",
  };
  return Object.keys(errors).map((k) => labels[k] ?? k);
}

function AttachmentsEditor({
  value,
  onChange,
}: {
  value: RequestAttachment[];
  onChange: (next: RequestAttachment[]) => void;
}) {
  const [filename, setFilename] = useState("");
  const [url, setUrl] = useState("");

  function add() {
    const trimmedName = filename.trim();
    const trimmedUrl = url.trim();
    if (!trimmedName || !trimmedUrl) return;
    onChange([
      ...value,
      { filename: trimmedName, url: trimmedUrl, size: 0, mime: guessMime(trimmedName) },
    ]);
    setFilename("");
    setUrl("");
  }

  function remove(idx: number) {
    onChange(value.filter((_, i) => i !== idx));
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-[var(--color-tertiary)]">
        Agrega enlaces a documentos de soporte (cotización, one-pager, etc.). Opcional.
      </p>

      {value.length > 0 ? (
        <ul className="divide-y divide-[var(--border-subtle)] rounded-[var(--radius-md)] border border-[var(--border-default)]">
          {value.map((a, i) => (
            <li key={`${a.filename}-${i}`} className="flex items-center gap-3 px-3 py-2">
              <FileText className="h-4 w-4 text-[var(--color-tertiary)]" aria-hidden />
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-medium text-[var(--color-primary)]">
                  {a.filename}
                </div>
                <a
                  href={a.url}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="truncate text-xs text-[var(--color-tertiary)] hover:underline"
                >
                  {a.url}
                </a>
              </div>
              <Button type="button" variant="ghost" size="sm" onClick={() => remove(i)}>
                <Trash2 className="h-4 w-4" aria-hidden />
                Quitar
              </Button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="rounded-[var(--radius-md)] border border-dashed border-[var(--border-default)] px-4 py-6 text-center text-sm text-[var(--color-tertiary)]">
          Sin adjuntos.
        </p>
      )}

      <div className="grid gap-3 sm:grid-cols-[1fr_2fr_auto]">
        <Input
          placeholder="Nombre de archivo"
          value={filename}
          onChange={(e) => setFilename(e.target.value)}
        />
        <Input
          placeholder="https://…"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
        />
        <Button
          type="button"
          variant="secondary"
          onClick={add}
          disabled={!filename.trim() || !url.trim()}
        >
          <Plus className="h-4 w-4" aria-hidden />
          Agregar
        </Button>
      </div>
    </div>
  );
}

function ReviewPane({
  draft,
  orgs,
  onEdit,
}: {
  draft: Draft;
  orgs: Organization[];
  onEdit: (step: StepId) => void;
}) {
  const orgName = orgs.find((o) => o.id === draft.organization_id)?.name ?? "—";
  return (
    <div className="space-y-4">
      <Section title="Básicos" onEdit={() => onEdit("basics")}>
        <Row k="Título" v={draft.title} />
        <Row k="Sponsor" v={draft.sponsor} />
        <Row k="Email sponsor" v={draft.sponsor_email} />
        <Row k="Solicitante" v={draft.requester_name || "(tu usuario)"} />
        <Row k="Email solicitante" v={draft.requester_email || "(tu correo)"} />
        <Row k="Organización" v={orgName} />
        <Row k="Unidad de negocio" v={draft.business_unit} />
        <Row k="Departamento" v={draft.department} />
        <Row k="Presupuesto" v={draft.budget ? currency(draft.budget) : "—"} />
        <Row k="Descripción" v={draft.description} multiline />
        <Row k="Objetivo" v={draft.objective} multiline />
      </Section>
      <Section title="Alcance" onEdit={() => onEdit("scope")}>
        <Row k="Alcance" v={draft.scope} multiline />
        <Row k="Entregables" v={draft.entregables} multiline />
        <Row k="Beneficios" v={draft.benefits} multiline />
        <Row k="Personas clave" v={draft.key_people} multiline />
        <Row k="Si no se hace" v={draft.if_not_done} multiline />
        <Row k="Observaciones" v={draft.observations} multiline />
      </Section>
      <Section title="Adjuntos" onEdit={() => onEdit("attachments")}>
        {draft.attachments.length ? (
          <ul className="list-disc pl-4 text-sm text-[var(--color-secondary)]">
            {draft.attachments.map((a, i) => (
              <li key={i}>
                {a.filename} —{" "}
                <a href={a.url} className="hover:underline" target="_blank" rel="noreferrer noopener">
                  {a.url}
                </a>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-[var(--color-tertiary)]">Sin adjuntos.</p>
        )}
      </Section>
    </div>
  );
}

function Section({
  title,
  children,
  onEdit,
}: {
  title: string;
  children: React.ReactNode;
  onEdit: () => void;
}) {
  return (
    <section className="rounded-[var(--radius-md)] border border-[var(--border-default)]">
      <header className="flex items-center justify-between border-b border-[var(--border-default)] px-4 py-2">
        <h3 className="text-sm font-semibold text-[var(--color-primary)]">{title}</h3>
        <button
          type="button"
          onClick={onEdit}
          className="text-xs font-medium text-[var(--color-accent)] hover:underline"
        >
          Editar
        </button>
      </header>
      <div className="space-y-2 px-4 py-3 text-sm">{children}</div>
    </section>
  );
}

function Row({ k, v, multiline }: { k: string; v: string; multiline?: boolean }) {
  return (
    <div className={cn("grid gap-1", multiline ? "" : "sm:grid-cols-[180px_1fr]")}>
      <span className="text-xs uppercase tracking-wide text-[var(--color-tertiary)]">{k}</span>
      <span
        className={cn(
          "text-[var(--color-primary)]",
          multiline ? "whitespace-pre-wrap" : "truncate",
        )}
      >
        {v || "—"}
      </span>
    </div>
  );
}

function guessMime(name: string): string {
  const ext = name.split(".").pop()?.toLowerCase() ?? "";
  const map: Record<string, string> = {
    pdf: "application/pdf",
    docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    pptx: "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    png: "image/png",
    jpg: "image/jpeg",
    jpeg: "image/jpeg",
  };
  return map[ext] ?? "application/octet-stream";
}

function validateAll(d: Draft): { ok: boolean; errors: Record<string, string> } {
  const e: Record<string, string> = {};
  const required: (keyof Draft)[] = [
    "title",
    "description",
    "objective",
    "organization_id",
    "business_unit",
    "department",
    "sponsor",
    "benefits",
    "scope",
  ];
  for (const k of required) {
    const v = d[k];
    if (typeof v !== "string" || v.trim().length < 3) {
      if (k === "organization_id") e[k] = "Selecciona una organización";
      else e[k] = "Obligatorio (mínimo 3 caracteres)";
    }
  }
  // ENH-040: presupuesto opcional. Sólo validar formato si el usuario
  // llenó algo.
  if (d.budget.trim()) {
    const budget = Number(d.budget);
    if (!Number.isFinite(budget) || budget < 0) {
      e.budget = "Presupuesto no válido (debe ser >= 0)";
    }
  }
  const emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!d.sponsor_email.trim() || !emailRe.test(d.sponsor_email.trim())) {
    e.sponsor_email = "Email del sponsor no es válido";
  }
  if (d.requester_email.trim() && !emailRe.test(d.requester_email.trim())) {
    e.requester_email = "Email no válido";
  }
  return { ok: Object.keys(e).length === 0, errors: e };
}

function firstStepWithError(errs: Record<string, string>): StepId | null {
  const byStep: Record<StepId, (keyof Draft)[]> = {
    basics: [
      "title",
      "description",
      "objective",
      "organization_id",
      "business_unit",
      "department",
      "sponsor",
      "sponsor_email",
      "requester_name",
      "requester_email",
      "budget",
      "delivery_constraint_date",
    ],
    scope: [
      "scope",
      "benefits",
      "entregables",
      "key_people",
      "if_not_done",
      "observations",
    ],
    attachments: [],
    review: [],
  };
  for (const s of STEPS) {
    if (byStep[s.id].some((k) => errs[k as string])) return s.id;
  }
  return null;
}
