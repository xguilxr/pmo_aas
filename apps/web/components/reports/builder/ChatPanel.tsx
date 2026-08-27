"use client";

import { useState } from "react";

import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Icono } from "@/components/ui/icono";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/cn";
import {
  chatWithBuilder,
  type ChatAction,
  type ChatResponse,
} from "@/lib/api/report-builder";

type Transcript = {
  id: string;
  role: "user" | "assistant";
  text: string;
  actions?: ChatAction[];
};

type Props = {
  open: boolean;
  onClose: () => void;
  canvasCodes: string[];
  compositionMode: "A" | "B";
  /** Aplica las acciones devueltas por la IA al canvas. Devuelve un
   *  "undo handle" que ChatPanel guarda en el transcript. */
  onApplyActions: (actions: ChatAction[]) => () => void;
};

/**
 * US-127 — Panel chat lateral con tool-calls JSON-action.
 *
 * El modo del LLM (Groq plataforma o BYO del tenant) lo resuelve el
 * backend con `load_tenant_ai`. Si el tenant está disabled, el panel
 * muestra el 409 y permite al PM ir a /admin/ai.
 */
export function ChatPanel({
  open,
  onClose,
  canvasCodes,
  compositionMode,
  onApplyActions,
}: Props) {
  const [transcript, setTranscript] = useState<Transcript[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [undoStack, setUndoStack] = useState<Record<string, () => void>>({});

  if (!open) return null;

  async function send() {
    if (!input.trim() || sending) return;
    const userText = input.trim();
    const userId = `u-${Date.now()}`;
    setTranscript((t) => [...t, { id: userId, role: "user", text: userText }]);
    setInput("");
    setSending(true);
    setError(null);

    try {
      const res: ChatResponse = await chatWithBuilder({
        user_message: userText,
        canvas_codes: canvasCodes,
        composition_mode: compositionMode,
        history: transcript.slice(-10).map((m) => ({
          role: m.role,
          content: m.text,
        })),
      });
      const assistantId = `a-${Date.now()}`;
      let undoFn: (() => void) | null = null;
      if (res.actions.length > 0) {
        undoFn = onApplyActions(res.actions);
      }
      setTranscript((t) => [
        ...t,
        { id: assistantId, role: "assistant", text: res.message, actions: res.actions },
      ]);
      if (undoFn) {
        setUndoStack((s) => ({ ...s, [assistantId]: undoFn! }));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error en chat IA");
    } finally {
      setSending(false);
    }
  }

  function undo(transcriptId: string) {
    const fn = undoStack[transcriptId];
    if (!fn) return;
    fn();
    setUndoStack(({ [transcriptId]: _drop, ...rest }) => rest);
    setTranscript((t) =>
      t.map((m) =>
        m.id === transcriptId
          ? { ...m, text: m.text + "  (revertido)", actions: [] }
          : m
      )
    );
  }

  return (
    <aside className="fixed right-0 top-0 z-40 flex h-screen w-96 flex-col border-l border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-lg)]">
      <header className="flex items-center justify-between border-b border-[var(--border-default)] px-3.5 py-2.5">
        <div className="flex items-center gap-2 text-[13px] font-semibold text-[var(--text-primary)]">
          <Icono nombre="star" size={15} className="text-[var(--color-accent)]" /> Asistente IA
        </div>
        <button
          type="button"
          onClick={onClose}
          className="inline-flex h-7 w-7 items-center justify-center rounded-[var(--radius-sm)] text-[var(--text-tertiary)] hover:bg-[var(--color-subtle)] hover:text-[var(--text-primary)]"
          title="Cerrar"
        >
          <Icono nombre="x" size={15} />
        </button>
      </header>

      <div className="flex-1 space-y-2.5 overflow-y-auto p-3.5 text-[13px]">
        {transcript.length === 0 && (
          <div className="rounded-[var(--radius-md)] border border-dashed border-[var(--border-default)] p-3 text-[12px] text-[var(--text-tertiary)]">
            Pídeme cosas como “agrega los hitos próximos” o “quita la sección de KPIs”.
          </div>
        )}
        {transcript.map((m) => (
          <div
            key={m.id}
            className={cn(
              "rounded-[var(--radius-md)] p-2.5",
              m.role === "user" ? "bg-[var(--color-muted)]" : "bg-[var(--color-info-bg)]",
            )}
          >
            <div className="mb-1 flex items-center justify-between">
              <span className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">
                {m.role === "user" ? (
                  "Tú"
                ) : (
                  <>
                    <Icono nombre="info" size={12} /> IA
                  </>
                )}
              </span>
              {m.role === "assistant" && undoStack[m.id] && (
                <button
                  type="button"
                  onClick={() => undo(m.id)}
                  className="flex items-center gap-1 text-[10.5px] text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                  title="Revertir acciones"
                >
                  <Icono nombre="rotate-ccw" size={12} /> Revertir
                </button>
              )}
            </div>
            <p className="whitespace-pre-wrap text-[13px] text-[var(--text-primary)]">{m.text}</p>
            {m.actions && m.actions.length > 0 && (
              <ul className="mt-1.5 list-disc pl-4 text-[11px] text-[var(--text-tertiary)]">
                {m.actions.map((a, idx) => (
                  <li key={idx}>
                    {a.type}
                    {a.code ? ` · ${a.code}` : ""}
                    {a.index !== null && a.index !== undefined ? ` · idx=${a.index}` : ""}
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>

      {error && (
        <div className="px-3.5 pb-2.5">
          <Banner variant="danger">{error}</Banner>
        </div>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          void send();
        }}
        className="flex items-center gap-2 border-t border-[var(--border-default)] p-2.5"
      >
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Pídele algo al asistente…"
          disabled={sending}
          className="flex-1"
        />
        <Button type="submit" disabled={sending || !input.trim()} loading={sending} size="sm">
          <Icono nombre="arrow-up-right" size={15} />
        </Button>
      </form>
    </aside>
  );
}
