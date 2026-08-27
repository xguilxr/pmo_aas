"use client";

import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import type { DragEndEvent } from "@dnd-kit/core";
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

import { Button } from "@/components/ui/button";
import { Icono } from "@/components/ui/icono";
import {
  SectionParamsForm,
  type SectionParams,
} from "@/components/reports/builder/SectionParamsPanel";
import { cn } from "@/lib/cn";
import type { ReportSection } from "@/lib/api/report-builder";

type Props = {
  /** Códigos en el orden actual del canvas. */
  codes: string[];
  /** Catálogo para resolver code → name/description. */
  catalog: ReportSection[];
  selectedCode: string | null;
  /** BUG-063: params por sección para el panel inline desplegable. */
  paramsByCode: Record<string, SectionParams>;
  onReorder: (codes: string[]) => void;
  onSelect: (code: string) => void;
  onRemove: (code: string) => void;
  onParamsChange: (code: string, next: SectionParams) => void;
};

/** US-124 + BUG-063 — canvas central con drag-and-drop vertical y
 *  parámetros inline desplegables por sección. */
export function SectionCanvas({
  codes,
  catalog,
  selectedCode,
  paramsByCode,
  onReorder,
  onSelect,
  onRemove,
  onParamsChange,
}: Props) {
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const byCode = new Map(catalog.map((s) => [s.code, s]));

  function handleDragEnd(ev: DragEndEvent) {
    const { active, over } = ev;
    if (!over || active.id === over.id) return;
    const oldIdx = codes.indexOf(String(active.id));
    const newIdx = codes.indexOf(String(over.id));
    if (oldIdx < 0 || newIdx < 0) return;
    onReorder(arrayMove(codes, oldIdx, newIdx));
  }

  if (codes.length === 0) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <div className="rounded-[var(--radius-xl)] border-2 border-dashed border-[var(--border-default)] bg-[var(--color-surface)] p-12 text-center text-[13px] text-[var(--text-tertiary)]">
          <p className="mb-1 font-medium text-[var(--text-secondary)]">Canvas vacío</p>
          <p>Arrastra secciones del catálogo para empezar tu reporte.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4">
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext items={codes} strategy={verticalListSortingStrategy}>
          <ul className="space-y-2">
            {codes.map((code) => (
              <SortableSectionItem
                key={code}
                code={code}
                section={byCode.get(code)}
                expanded={selectedCode === code}
                params={paramsByCode[code] ?? {}}
                onToggle={() => onSelect(selectedCode === code ? "" : code)}
                onRemove={() => onRemove(code)}
                onParamsChange={(next) => onParamsChange(code, next)}
              />
            ))}
          </ul>
        </SortableContext>
      </DndContext>
    </div>
  );
}

type ItemProps = {
  code: string;
  section: ReportSection | undefined;
  expanded: boolean;
  params: SectionParams;
  onToggle: () => void;
  onRemove: () => void;
  onParamsChange: (next: SectionParams) => void;
};

function SortableSectionItem({
  code,
  section,
  expanded,
  params,
  onToggle,
  onRemove,
  onParamsChange,
}: ItemProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: code,
  });

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <li
      ref={setNodeRef}
      style={style}
      className={cn(
        "group rounded-[var(--radius-xl)] border bg-[var(--color-surface)] shadow-[var(--relieve-isla)] transition-colors",
        expanded
          ? "border-[var(--color-accent)] ring-1 ring-[var(--color-accent)]"
          : "border-[var(--border-default)] hover:border-[var(--border-strong)]",
      )}
    >
      <div className="flex items-start gap-2.5 p-3">
        <button
          type="button"
          {...attributes}
          {...listeners}
          className="flex h-7 w-5 shrink-0 cursor-grab items-center justify-center text-[var(--text-faint)] hover:text-[var(--text-secondary)] active:cursor-grabbing"
          title="Arrastrar"
        >
          <Icono nombre="more-vertical" size={15} />
        </button>
        <button
          type="button"
          onClick={onToggle}
          className="min-w-0 flex-1 text-left"
        >
          <p className="truncate text-[13px] font-medium text-[var(--text-primary)]">
            <span className="text-[var(--text-faint)]">{code}</span> · {section?.name ?? "(sin catalogar)"}
          </p>
          {section?.description && (
            <p className="line-clamp-1 text-[11.5px] text-[var(--text-tertiary)]">{section.description}</p>
          )}
        </button>
        <Button
          type="button"
          size="sm"
          variant={expanded ? "secondary" : "ghost"}
          onClick={onToggle}
          title="Parámetros de la sección"
        >
          <Icono nombre="settings" size={14} />
        </Button>
        <Button
          type="button"
          size="sm"
          variant="ghost"
          onClick={onRemove}
          title="Quitar sección"
        >
          <Icono nombre="bin" size={14} />
        </Button>
      </div>
      {expanded && (
        <div className="border-t border-[var(--border-subtle)] bg-[var(--color-subtle)] p-3">
          <SectionParamsForm
            section={section ?? null}
            params={params}
            onChange={onParamsChange}
          />
        </div>
      )}
    </li>
  );
}
