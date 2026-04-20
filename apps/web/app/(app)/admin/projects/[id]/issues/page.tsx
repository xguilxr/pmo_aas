"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Shield } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { ModuleShell } from "@/components/module-shell";
import { ApiError } from "@/lib/api";
import {
  ISSUE_STATUS_LABEL,
  ISSUE_TYPE_LABEL,
  createIssue,
  listIssues,
  type Issue,
  type IssueStatus,
  type IssueType,
} from "@/lib/api/modules";

function isOverdue(i: Issue): boolean {
  if (!i.committed_date) return false;
  if (i.status === "resolved" || i.status === "closed") return false;
  return new Date(i.committed_date).getTime() < new Date().setHours(0, 0, 0, 0);
}

export default function IssuesPage() {
  const { id } = useParams<{ id: string }>();
  const [rows, setRows] = useState<Issue[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState<{
    title: string;
    description: string;
    type: IssueType;
    priority: number;
    committed_date: string;
  }>({
    title: "",
    description: "",
    type: "issue",
    priority: 3,
    committed_date: "",
  });

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const r = await listIssues(id);
      setRows(r);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron cargar los AIDs");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function submit() {
    setSubmitting(true);
    try {
      await createIssue(id, {
        title: form.title,
        description: form.description || null,
        type: form.type,
        priority: form.priority,
        committed_date: form.committed_date || null,
      });
      setForm({ title: "", description: "", type: "issue", priority: 3, committed_date: "" });
      setOpen(false);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <ModuleShell<Issue>
      projectId={id}
      title="AIDs"
      subtitle="Acciones, incidencias y decisiones del proyecto."
      icon={<Shield className="h-5 w-5" aria-hidden />}
      records={rows}
      loading={loading}
      error={error}
      newButtonLabel="Nuevo AID"
      newModalTitle="Registrar AID"
      newModalOpen={open}
      setNewModalOpen={setOpen}
      newModalForm={() => (
        <div className="space-y-3">
          <Field label="Título">
            <Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          </Field>
          <Field label="Descripción">
            <Textarea
              rows={3}
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </Field>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Tipo">
              <Select
                value={form.type}
                onChange={(e) => setForm({ ...form, type: e.target.value as IssueType })}
              >
                {(Object.keys(ISSUE_TYPE_LABEL) as IssueType[]).map((t) => (
                  <option key={t} value={t}>
                    {ISSUE_TYPE_LABEL[t]}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Prioridad (1-5)">
              <Select
                value={String(form.priority)}
                onChange={(e) => setForm({ ...form, priority: Number(e.target.value) })}
              >
                {[1, 2, 3, 4, 5].map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </Select>
            </Field>
          </div>
          <Field label="Fecha compromiso">
            <Input
              type="date"
              value={form.committed_date}
              onChange={(e) => setForm({ ...form, committed_date: e.target.value })}
            />
          </Field>
        </div>
      )}
      newModalFooter={(close) => (
        <>
          <Button variant="secondary" onClick={close} disabled={submitting}>
            Cancelar
          </Button>
          <Button onClick={submit} loading={submitting} disabled={!form.title.trim()}>
            Crear
          </Button>
        </>
      )}
      columns={[
        {
          key: "title",
          label: "Título",
          render: (r) => (
            <div className="flex items-center gap-2">
              <span className="font-medium">{r.title}</span>
              {isOverdue(r) ? <Badge variant="danger">Vencido</Badge> : null}
            </div>
          ),
        },
        {
          key: "type",
          label: "Tipo",
          render: (r) => <Badge>{ISSUE_TYPE_LABEL[r.type]}</Badge>,
        },
        {
          key: "priority",
          label: "Prioridad",
          render: (r) => <span className="tabular-nums">{r.priority ?? "—"}</span>,
        },
        {
          key: "status",
          label: "Estado",
          render: (r) => (
            <Badge
              variant={
                r.status === "resolved" || r.status === "closed"
                  ? "success"
                  : r.status === "in_progress"
                    ? "warning"
                    : "info"
              }
            >
              {ISSUE_STATUS_LABEL[r.status as IssueStatus]}
            </Badge>
          ),
        },
        {
          key: "committed_date",
          label: "Compromiso",
          render: (r) => r.committed_date ?? "—",
        },
      ]}
    />
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-[12px] font-medium text-[var(--text-secondary)]">{label}</span>
      {children}
    </label>
  );
}
