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

// ============================================================================
// US-057 — Selector de modo IA por tenant (disabled / platform / byo)
// ============================================================================

export type TenantAIMode = "disabled" | "platform" | "byo";

export type BYOProvider =
  | "openai"
  | "claude"
  | "perplexity"
  | "gemini"
  | "ollama";

export type BYOConfigRead = {
  provider: BYOProvider;
  api_key_mask: string | null;
  has_api_key: boolean;
  model: string | null;
  base_url: string | null;
  last_test_at: string | null;
  last_test_status: "ok" | "fail" | null;
  last_test_error: string | null;
};

export type BYOConfigIn = {
  provider: BYOProvider;
  api_key?: string | null;
  model?: string | null;
  base_url?: string | null;
};

export type TenantAIProviderRead = {
  mode: TenantAIMode;
  byo: BYOConfigRead | null;
};

export type TenantAIProviderPatch = {
  mode: TenantAIMode;
  byo?: BYOConfigIn | null;
};

export function getTenantAIProvider(): Promise<TenantAIProviderRead> {
  return apiFetch<TenantAIProviderRead>("/api/v1/admin/ai/provider");
}

export function updateTenantAIProvider(
  body: TenantAIProviderPatch,
): Promise<TenantAIProviderRead> {
  return apiFetch<TenantAIProviderRead>("/api/v1/admin/ai/provider", {
    method: "PATCH",
    body,
  });
}

export function testTenantAIProvider(
  body: { byo?: BYOConfigIn } = {},
): Promise<TestConnectionResult> {
  return apiFetch<TestConnectionResult>("/api/v1/admin/ai/provider/test", {
    method: "POST",
    body,
  });
}

export const BYO_PROVIDER_LABEL: Record<BYOProvider, string> = {
  openai: "OpenAI",
  claude: "Anthropic (Claude)",
  perplexity: "Perplexity",
  gemini: "Google Gemini",
  ollama: "Ollama (tailnet privado)",
};

export const BYO_PROVIDER_MODELS: Record<BYOProvider, string[]> = {
  openai: ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"],
  claude: ["claude-3-5-haiku-20241022", "claude-3-5-sonnet-20241022"],
  perplexity: ["sonar", "sonar-pro"],
  gemini: ["gemini-1.5-flash", "gemini-1.5-pro"],
  ollama: ["qwen2.5:7b-instruct-q4_K_M", "llama3.1:8b"],
};
