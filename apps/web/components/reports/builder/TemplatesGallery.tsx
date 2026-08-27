"use client";

import { Icono } from "@/components/ui/icono";
import type { ReportBuilderTemplate } from "@/lib/api/report-builder";

type Props = {
  templates: ReportBuilderTemplate[];
  currentUserId: string | null;
  projectId: string;
  onLoad: (tpl: ReportBuilderTemplate) => void;
  onTogglePublish: (tpl: ReportBuilderTemplate) => void;
  onDelete: (tpl: ReportBuilderTemplate) => void;
};

/** US-126 — galería "Mis plantillas" + "Plantillas del proyecto". */
export function TemplatesGallery({
  templates,
  currentUserId,
  projectId,
  onLoad,
  onTogglePublish,
  onDelete,
}: Props) {
  const mine = templates.filter((t) => t.owner_id === currentUserId);
  const projectShared = templates.filter(
    (t) =>
      t.visibility === "project" &&
      t.project_id === projectId &&
      t.owner_id !== currentUserId
  );
  const seeds = templates.filter((t) => t.is_seed);

  if (!mine.length && !projectShared.length && !seeds.length) {
    return null;
  }

  return (
    <div className="space-y-3 border-b border-[var(--border-default)] bg-[var(--color-surface)] p-3.5 text-[12px]">
      {seeds.length > 0 && (
        <Section title="Plantillas seed">
          {seeds.map((t) => (
            <TemplateChip key={t.id} tpl={t} onLoad={() => onLoad(t)} />
          ))}
        </Section>
      )}
      {mine.length > 0 && (
        <Section title="Mis plantillas">
          {mine.map((t) => (
            <TemplateChip
              key={t.id}
              tpl={t}
              onLoad={() => onLoad(t)}
              onTogglePublish={() => onTogglePublish(t)}
              onDelete={() => onDelete(t)}
              owned
            />
          ))}
        </Section>
      )}
      {projectShared.length > 0 && (
        <Section title="Plantillas del proyecto">
          {projectShared.map((t) => (
            <TemplateChip key={t.id} tpl={t} onLoad={() => onLoad(t)} />
          ))}
        </Section>
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">
        {title}
      </h3>
      <div className="flex flex-wrap gap-1.5">{children}</div>
    </div>
  );
}

type ChipProps = {
  tpl: ReportBuilderTemplate;
  owned?: boolean;
  onLoad: () => void;
  onTogglePublish?: () => void;
  onDelete?: () => void;
};

function TemplateChip({ tpl, owned, onLoad, onTogglePublish, onDelete }: ChipProps) {
  return (
    <div className="flex items-center gap-1 rounded-full border border-[var(--border-default)] bg-[var(--color-subtle)] py-0.5 pl-3 pr-1.5 shadow-[var(--relieve-control)]">
      <button
        type="button"
        onClick={onLoad}
        className="text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
        title={tpl.description ?? tpl.name}
      >
        {tpl.name}
      </button>
      {owned && onTogglePublish && (
        <button
          type="button"
          onClick={onTogglePublish}
          className="rounded-[var(--radius-sm)] p-0.5 text-[var(--text-tertiary)] hover:bg-[var(--color-muted)] hover:text-[var(--text-secondary)]"
          title={tpl.visibility === "project" ? "Despublicar" : "Publicar al proyecto"}
        >
          <Icono nombre={tpl.visibility === "project" ? "eye-off" : "eye"} size={13} />
        </button>
      )}
      {owned && onDelete && (
        <button
          type="button"
          onClick={onDelete}
          className="rounded-[var(--radius-sm)] p-0.5 text-[var(--color-danger-fg)] hover:bg-[var(--color-danger-bg)]"
          title="Borrar"
        >
          <Icono nombre="bin" size={13} />
        </button>
      )}
    </div>
  );
}
