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
import { GripVertical, Settings, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { ReportSection } from "@/lib/api/report-builder";

type Props = {
  /** Códigos en el orden actual del canvas. */
  codes: string[];
  /** Catálogo para resolver code → name/description. */
  catalog: ReportSection[];
  selectedCode: string | null;
  onReorder: (codes: string[]) => void;
  onSelect: (code: string) => void;
  onRemove: (code: string) => void;
};

/** US-124 — canvas central con drag-and-drop vertical. */
export function SectionCanvas({
  codes,
  catalog,
  selectedCode,
  onReorder,
  onSelect,
  onRemove,
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
        <div className="rounded-lg border-2 border-dashed border-zinc-300 bg-white p-12 text-center text-sm text-zinc-500">
          <p className="mb-1 font-medium text-zinc-700">Canvas vacío</p>
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
                selected={selectedCode === code}
                onSelect={() => onSelect(code)}
                onRemove={() => onRemove(code)}
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
  selected: boolean;
  onSelect: () => void;
  onRemove: () => void;
};

function SortableSectionItem({ code, section, selected, onSelect, onRemove }: ItemProps) {
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
      onClick={onSelect}
      className={`group flex cursor-pointer items-start gap-2 rounded-lg border bg-white p-3 shadow-sm transition ${
        selected ? "border-zinc-900 ring-1 ring-zinc-900" : "border-zinc-200 hover:border-zinc-400"
      }`}
    >
      <button
        type="button"
        {...attributes}
        {...listeners}
        className="flex h-6 w-4 cursor-grab items-center justify-center text-zinc-400 hover:text-zinc-700"
        onClick={(e) => e.stopPropagation()}
        title="Arrastrar"
      >
        <GripVertical className="h-4 w-4" />
      </button>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-zinc-800">
          <span className="text-zinc-400">{code}</span> · {section?.name ?? "(sin catalogar)"}
        </p>
        {section?.description && (
          <p className="line-clamp-1 text-xs text-zinc-500">{section.description}</p>
        )}
      </div>
      <Button
        type="button"
        size="sm"
        variant="ghost"
        onClick={(e) => {
          e.stopPropagation();
          onSelect();
        }}
        title="Parámetros"
      >
        <Settings className="h-3.5 w-3.5" />
      </Button>
      <Button
        type="button"
        size="sm"
        variant="ghost"
        onClick={(e) => {
          e.stopPropagation();
          onRemove();
        }}
        title="Quitar"
      >
        <Trash2 className="h-3.5 w-3.5" />
      </Button>
    </li>
  );
}
