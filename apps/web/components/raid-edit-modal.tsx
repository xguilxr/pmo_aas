"use client";

// US-178 — modal de edición de un ítem RAID desde la lista. Reusa
// RaidEditFields en modo edición; al guardar/cancelar cierra y vuelve a la
// vista de lista completa (no navega a la página de detalle).

import { Modal } from "@/components/ui/modal";
import { RaidEditFields } from "@/components/raid-edit-fields";
import type { Issue, Risk } from "@/lib/api/modules";

type Props =
  | {
      kind: "risk";
      item: Risk;
      onClose: () => void;
      onSaved: (next: Risk) => void;
    }
  | {
      kind: "issue";
      item: Issue;
      onClose: () => void;
      onSaved: (next: Issue) => void;
    };

export function RaidEditModal(props: Props) {
  const { kind, item, onClose } = props;
  return (
    <Modal open title={`Editar ${item.folio}`} onClose={onClose} size="xl">
      {kind === "risk" ? (
        <RaidEditFields
          kind="risk"
          item={item}
          defaultEditing
          onClose={onClose}
          onSaved={props.onSaved}
        />
      ) : (
        <RaidEditFields
          kind="issue"
          item={item}
          defaultEditing
          onClose={onClose}
          onSaved={props.onSaved}
        />
      )}
    </Modal>
  );
}
