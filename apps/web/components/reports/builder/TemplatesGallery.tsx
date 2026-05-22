"use client";

import { Eye, EyeOff, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
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
    <div className="space-y-3 border-b border-zinc-200 bg-white p-3 text-xs">
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
      <h3 className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-zinc-500">
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
    <div className="flex items-center gap-1 rounded-full border border-zinc-200 bg-zinc-50 pl-3 pr-1.5 py-0.5">
      <button
        type="button"
        onClick={onLoad}
        className="text-zinc-800 hover:text-zinc-900"
        title={tpl.description ?? tpl.name}
      >
        {tpl.name}
      </button>
      {owned && onTogglePublish && (
        <button
          type="button"
          onClick={onTogglePublish}
          className="rounded p-0.5 text-zinc-500 hover:bg-zinc-200 hover:text-zinc-700"
          title={tpl.visibility === "project" ? "Despublicar" : "Publicar al proyecto"}
        >
          {tpl.visibility === "project" ? (
            <EyeOff className="h-3 w-3" />
          ) : (
            <Eye className="h-3 w-3" />
          )}
        </button>
      )}
      {owned && onDelete && (
        <button
          type="button"
          onClick={onDelete}
          className="rounded p-0.5 text-red-500 hover:bg-red-50 hover:text-red-700"
          title="Borrar"
        >
          <Trash2 className="h-3 w-3" />
        </button>
      )}
    </div>
  );
}
