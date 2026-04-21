import { apiFetch } from "@/lib/api";

export type OllamaConfigRead = {
  base_url: string | null;
  model: string | null;
  timeout_sec: number;
  configured: boolean;
};

export type OllamaConfigPatch = {
  base_url?: string;
  model?: string;
  timeout_sec?: number;
};

export type TestConnectionResult = {
  ok: boolean;
  latency_ms: number | null;
  model_present: boolean | null;
  tags_count: number | null;
  error: string | null;
  code: string | null;
};

export function getOllamaConfig(): Promise<OllamaConfigRead> {
  return apiFetch<OllamaConfigRead>("/api/v1/admin/ai/ollama");
}

export function updateOllamaConfig(body: OllamaConfigPatch): Promise<OllamaConfigRead> {
  return apiFetch<OllamaConfigRead>("/api/v1/admin/ai/ollama", {
    method: "PATCH",
    body,
  });
}

export function testAiConnection(provider: "ollama" = "ollama"): Promise<TestConnectionResult> {
  return apiFetch<TestConnectionResult>("/api/v1/admin/ai/test-connection", {
    method: "POST",
    body: { provider },
  });
}
