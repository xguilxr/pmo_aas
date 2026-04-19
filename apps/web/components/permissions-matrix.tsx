"use client";

import { Checkbox } from "@/components/ui/checkbox";
import {
  ACTION_LABELS,
  MODULE_LABELS,
  VALID_ACTIONS,
  VALID_MODULES,
} from "@/lib/api/admin";

type Props = {
  value: Record<string, string[]>;
  onChange: (next: Record<string, string[]>) => void;
  disabled?: boolean;
};

export function PermissionsMatrix({ value, onChange, disabled }: Props) {
  function toggle(module: string, action: string, checked: boolean) {
    const current = value[module] ?? [];
    const next = checked
      ? Array.from(new Set([...current, action]))
      : current.filter((a) => a !== action);
    const out = { ...value };
    if (next.length === 0) {
      delete out[module];
    } else {
      out[module] = next;
    }
    onChange(out);
  }

  function toggleRow(module: string, checked: boolean) {
    const out = { ...value };
    if (checked) {
      out[module] = [...VALID_ACTIONS];
    } else {
      delete out[module];
    }
    onChange(out);
  }

  return (
    <div className="overflow-x-auto rounded-[var(--radius-md)] border border-[var(--border-default)]">
      <table className="w-full text-sm">
        <thead className="border-b border-[var(--border-default)] bg-[var(--color-subtle)] text-left text-xs uppercase tracking-wide text-[var(--color-tertiary)]">
          <tr>
            <th className="sticky left-0 z-10 bg-[var(--color-subtle)] px-3 py-2 font-medium">
              Módulo
            </th>
            {VALID_ACTIONS.map((a) => (
              <th key={a} className="px-3 py-2 text-center font-medium">
                {ACTION_LABELS[a]}
              </th>
            ))}
            <th className="px-3 py-2 text-center font-medium">Todo</th>
          </tr>
        </thead>
        <tbody>
          {VALID_MODULES.map((m) => {
            const actions = value[m] ?? [];
            const allChecked = VALID_ACTIONS.every((a) => actions.includes(a));
            return (
              <tr
                key={m}
                className="border-b border-[var(--border-subtle)] last:border-b-0 hover:bg-[var(--color-subtle)]"
              >
                <td className="sticky left-0 z-10 bg-[var(--color-surface)] px-3 py-2 font-medium text-[var(--color-primary)]">
                  {MODULE_LABELS[m]}
                </td>
                {VALID_ACTIONS.map((a) => (
                  <td key={a} className="px-3 py-2 text-center">
                    <Checkbox
                      checked={actions.includes(a)}
                      onChange={(e) => toggle(m, a, e.target.checked)}
                      disabled={disabled}
                      aria-label={`${MODULE_LABELS[m]} · ${ACTION_LABELS[a]}`}
                    />
                  </td>
                ))}
                <td className="px-3 py-2 text-center">
                  <Checkbox
                    checked={allChecked}
                    onChange={(e) => toggleRow(m, e.target.checked)}
                    disabled={disabled}
                    aria-label={`${MODULE_LABELS[m]} · todas`}
                  />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
