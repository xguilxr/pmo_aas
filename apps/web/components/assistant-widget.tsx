"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Bot, Loader2, Plus, Send, Sparkles, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import {
  type AssistantAction,
  sendAssistantMessage,
} from "@/lib/api/assistant";
import { cn } from "@/lib/cn";

/**
 * US-165 — Asistente IA flotante (widget global).
 *
 * Botón flotante (abajo-derecha) + panel con transcript. Ctrl/⌘-K abre y
 * cierra. Manda el `pathname` actual como contexto de página para que el
 * modelo responda situado. Ejecuta acciones seguras (navigate) vía router.
 * El historial se persiste server-side (EP008); aquí mantenemos el hilo de
 * la sesión actual en estado.
 */

type ChatTurn = {
  role: "user" | "assistant";
  content: string;
  actions?: AssistantAction[];
};

const WELCOME: ChatTurn = {
  role: "assistant",
  content:
    "Hola 👋 Soy tu copiloto PMO. Preguntame sobre tus proyectos, riesgos, " +
    "reportes o pedime que te lleve a una sección.",
};

export function AssistantWidget() {
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [turns, setTurns] = useState<ChatTurn[]>([WELCOME]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);

  // Ctrl/⌘-K togglea el panel.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      } else if (e.key === "Escape" && open) {
        setOpen(false);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  useEffect(() => {
    if (open) {
      endRef.current?.scrollIntoView({ behavior: "smooth" });
      inputRef.current?.focus();
    }
  }, [open, turns]);

  function resetConversation() {
    setTurns([WELCOME]);
    setConversationId(null);
    setError(null);
  }

  async function send() {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    setError(null);
    setTurns((t) => [...t, { role: "user", content: text }]);
    setLoading(true);
    try {
      const res = await sendAssistantMessage({
        message: text,
        conversation_id: conversationId,
        page_context: `Ruta actual: ${pathname}`,
      });
      setConversationId(res.conversation_id);
      setTurns((t) => [
        ...t,
        { role: "assistant", content: res.message, actions: res.actions },
      ]);
    } catch (err) {
      if (err instanceof ApiError && err.code === "AI_DISABLED") {
        setError("La IA no está habilitada en tu organización. Pedile al admin que la active.");
      } else {
        setError("No pude responder ahora mismo. Intentá de nuevo en un momento.");
      }
    } finally {
      setLoading(false);
    }
  }

  function runAction(a: AssistantAction) {
    if (a.type === "navigate" && a.path) {
      router.push(a.path);
      setOpen(false);
    }
  }

  return (
    <>
      {/* Botón flotante */}
      <button
        type="button"
        aria-label="Asistente IA (Ctrl/⌘-K)"
        title="Asistente IA · Ctrl/⌘-K"
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "fixed bottom-5 right-5 z-50 flex h-12 w-12 items-center justify-center",
          "rounded-full text-white shadow-[var(--shadow-optical-md)] transition-transform hover:scale-105",
          "focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]",
        )}
        style={{ background: "var(--color-accent)" }}
      >
        {open ? <X className="h-5 w-5" /> : <Sparkles className="h-5 w-5" />}
      </button>

      {/* Panel */}
      {open ? (
        <div
          role="dialog"
          aria-label="Asistente IA"
          className={cn(
            "fixed bottom-20 right-5 z-50 flex w-[min(380px,calc(100vw-2.5rem))] flex-col",
            "rounded-[var(--radius-window)] border border-[var(--border-default)]",
            "bg-[var(--color-surface)] shadow-[var(--shadow-optical-md)]",
          )}
          style={{ height: "min(560px, calc(100vh - 7rem))" }}
        >
          {/* Header */}
          <header
            className="flex items-center justify-between gap-2 rounded-t-[var(--radius-window)] px-4 py-3 text-white"
            style={{ background: "var(--color-primary)" }}
          >
            <span className="flex items-center gap-2 text-sm font-semibold">
              <Bot className="h-4 w-4" /> Copiloto PMO
            </span>
            <span className="flex items-center gap-1">
              <button
                type="button"
                onClick={resetConversation}
                title="Nueva conversación"
                className="rounded-md p-1 opacity-80 hover:bg-white/10 hover:opacity-100"
              >
                <Plus className="h-4 w-4" />
              </button>
              <button
                type="button"
                onClick={() => setOpen(false)}
                title="Cerrar"
                className="rounded-md p-1 opacity-80 hover:bg-white/10 hover:opacity-100"
              >
                <X className="h-4 w-4" />
              </button>
            </span>
          </header>

          {/* Transcript */}
          <div className="flex-1 space-y-3 overflow-y-auto px-3 py-3">
            {turns.map((t, i) => (
              <div
                key={i}
                className={cn(
                  "flex",
                  t.role === "user" ? "justify-end" : "justify-start",
                )}
              >
                <div
                  className={cn(
                    "max-w-[85%] whitespace-pre-wrap rounded-2xl px-3 py-2 text-sm",
                    t.role === "user"
                      ? "rounded-br-sm bg-[var(--color-accent)] text-white"
                      : "rounded-bl-sm bg-[var(--color-subtle)] text-[var(--color-primary)]",
                  )}
                >
                  {t.content}
                  {t.actions && t.actions.length > 0 ? (
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {t.actions
                        .filter((a) => a.type === "navigate" && a.path)
                        .map((a, j) => (
                          <button
                            key={j}
                            type="button"
                            onClick={() => runAction(a)}
                            className="rounded-full border border-[var(--color-accent)] px-2.5 py-1 text-xs font-medium text-[var(--color-accent)] hover:bg-[var(--color-accent)] hover:text-white"
                          >
                            {a.label || "Ir"} →
                          </button>
                        ))}
                    </div>
                  ) : null}
                </div>
              </div>
            ))}
            {loading ? (
              <div className="flex justify-start">
                <div className="flex items-center gap-2 rounded-2xl rounded-bl-sm bg-[var(--color-subtle)] px-3 py-2 text-sm text-[var(--color-tertiary)]">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" /> Pensando…
                </div>
              </div>
            ) : null}
            {error ? (
              <p className="px-1 text-xs text-[var(--color-danger-fg)]">{error}</p>
            ) : null}
            <div ref={endRef} />
          </div>

          {/* Input */}
          <div className="border-t border-[var(--border-subtle)] p-2.5">
            <div className="flex items-end gap-2">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    void send();
                  }
                }}
                rows={1}
                placeholder="Escribí tu pregunta…"
                className="max-h-28 min-h-[38px] flex-1 resize-none rounded-lg border border-[var(--border-default)] bg-[var(--color-surface)] px-3 py-2 text-sm text-[var(--color-primary)] focus:border-[var(--color-accent)] focus:outline-none"
              />
              <Button
                type="button"
                size="sm"
                variant="primary"
                onClick={() => void send()}
                disabled={loading || !input.trim()}
                aria-label="Enviar"
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>
            {/*
              MCS IA-04 — ruta de escalada a atención humana. El aviso de que
              esto es IA ya estaba (el botón y el panel lo dicen en su
              `aria-label`); lo que faltaba era la salida. Va a la intención de
              solicitud, que es el circuito humano que ya existe: la atiende la
              PMO de la organización, que es quien conoce el proyecto. No somos
              nosotros: el producto es multiinquilino.
            */}
            <p className="mt-2 px-1 text-[11px] text-[var(--color-tertiary)]">
              Respuestas generadas por IA: pueden equivocarse.{" "}
              <button
                type="button"
                onClick={() => {
                  setOpen(false);
                  router.push("/pmo/requests/new");
                }}
                className="underline underline-offset-2 hover:text-[var(--color-accent)]"
              >
                ¿Necesitás a una persona?
              </button>
            </p>
          </div>
        </div>
      ) : null}
    </>
  );
}
