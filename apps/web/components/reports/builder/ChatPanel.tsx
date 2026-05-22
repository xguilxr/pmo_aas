"use client";

import { useState } from "react";
import { Bot, Loader2, Send, Sparkles, Undo2, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
    <aside className="fixed right-0 top-0 z-40 flex h-screen w-96 flex-col border-l border-zinc-200 bg-white shadow-xl">
      <header className="flex items-center justify-between border-b border-zinc-200 px-3 py-2">
        <div className="flex items-center gap-2 text-sm font-semibold text-zinc-800">
          <Sparkles className="h-4 w-4 text-violet-500" /> Asistente IA
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded p-1 text-zinc-500 hover:bg-zinc-100"
          title="Cerrar"
        >
          <X className="h-4 w-4" />
        </button>
      </header>

      <div className="flex-1 space-y-2 overflow-y-auto p-3 text-sm">
        {transcript.length === 0 && (
          <div className="rounded border border-dashed border-zinc-300 p-3 text-xs text-zinc-500">
            Pídeme cosas como “agrega los hitos próximos” o “quita la sección de KPIs”.
          </div>
        )}
        {transcript.map((m) => (
          <div
            key={m.id}
            className={`rounded-lg p-2 ${
              m.role === "user" ? "bg-zinc-100" : "bg-violet-50"
            }`}
          >
            <div className="mb-0.5 flex items-center justify-between">
              <span className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide text-zinc-500">
                {m.role === "user" ? "Tú" : <><Bot className="h-3 w-3" /> IA</>}
              </span>
              {m.role === "assistant" && undoStack[m.id] && (
                <button
                  type="button"
                  onClick={() => undo(m.id)}
                  className="flex items-center gap-0.5 text-[10px] text-zinc-600 hover:text-zinc-900"
                  title="Revertir acciones"
                >
                  <Undo2 className="h-3 w-3" /> Revertir
                </button>
              )}
            </div>
            <p className="whitespace-pre-wrap text-sm text-zinc-800">{m.text}</p>
            {m.actions && m.actions.length > 0 && (
              <ul className="mt-1 list-disc pl-4 text-[11px] text-zinc-600">
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
        <div className="bg-red-50 px-3 py-1.5 text-xs text-red-700">{error}</div>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          void send();
        }}
        className="flex items-center gap-2 border-t border-zinc-200 p-2"
      >
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Pídele algo al asistente…"
          disabled={sending}
          className="flex-1 text-sm"
        />
        <Button type="submit" disabled={sending || !input.trim()} size="sm">
          {sending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
        </Button>
      </form>
    </aside>
  );
}
