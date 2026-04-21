"use client";

import { useEffect, useRef, useState } from "react";

import { getAIJob, type AIJobRead, type AIJobStatus } from "@/lib/api/ai";

type UseAIJobPollingInput = {
  jobId: string | null;
  enabled?: boolean;
  onSuccess?: (job: AIJobRead) => void;
  onError?: (job: AIJobRead) => void;
};

type UseAIJobPollingResult = {
  job: AIJobRead | null;
  status: AIJobStatus | null;
  isPolling: boolean;
  error: string | null;
};

const TERMINAL: AIJobStatus[] = ["succeeded", "failed"];
const BACKOFF_MS = [1000, 2000, 3000, 5000, 8000];
const MAX_POLL_MS = 10 * 60 * 1000;

/**
 * US-051: polling de AIJob con backoff exponencial.
 *
 * Consume `GET /api/v1/ai/jobs/{id}` hasta que el estado sea terminal
 * (`succeeded`/`failed`) o hasta el timeout total. Backoff: 1s, 2s, 3s,
 * 5s, 8s (cap a 10s). Timeout total 10 min — si el job sigue en
 * `queued` más tiempo, hay probablemente un problema en el worker.
 */
export function useAIJobPolling(
  input: UseAIJobPollingInput,
): UseAIJobPollingResult {
  const { jobId, enabled = true, onSuccess, onError } = input;
  const [job, setJob] = useState<AIJobRead | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(false);

  const onSuccessRef = useRef(onSuccess);
  const onErrorRef = useRef(onError);
  onSuccessRef.current = onSuccess;
  onErrorRef.current = onError;

  useEffect(() => {
    if (!jobId || !enabled) {
      return;
    }
    let cancelled = false;
    let attempt = 0;
    let timer: ReturnType<typeof setTimeout> | null = null;
    const startedAt = Date.now();

    setIsPolling(true);
    setError(null);
    setJob(null);

    async function tick() {
      if (cancelled || !jobId) return;
      if (Date.now() - startedAt > MAX_POLL_MS) {
        if (!cancelled) {
          setError("El job no terminó en 10 minutos.");
          setIsPolling(false);
        }
        return;
      }
      try {
        const j = await getAIJob(jobId);
        if (cancelled) return;
        setJob(j);
        if (TERMINAL.includes(j.status)) {
          setIsPolling(false);
          if (j.status === "succeeded") {
            onSuccessRef.current?.(j);
          } else {
            onErrorRef.current?.(j);
          }
          return;
        }
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Error consultando el job");
        setIsPolling(false);
        return;
      }
      const delay = BACKOFF_MS[Math.min(attempt, BACKOFF_MS.length - 1)];
      attempt += 1;
      timer = setTimeout(tick, delay);
    }

    tick();

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [jobId, enabled]);

  return {
    job,
    status: job?.status ?? null,
    isPolling,
    error,
  };
}
