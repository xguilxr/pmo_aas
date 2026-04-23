import { apiFetch } from "@/lib/api";

// ============================================================================
// US-057 + DEC-017/019 — Selector de modo IA por tenant (disabled / platform / byo).
// Los helpers legacy de Ollama/Tailscale (US-045, US-047, US-048) se retiraron
// en BUG-027: el cascade IA vive en `settings.ai.{mode,byo,...}` y el único
// flujo de alta de proveedor es el wizard BYO de /admin/ai.
// ============================================================================

export type TestConnectionResult = {
  ok: boolean;
  latency_ms: number | null;
  model_present: boolean | null;
  tags_count: number | null;
  error: string | null;
  code: string | null;
};

export type TenantAIMode = "disabled" | "platform" | "byo";

/** Proveedores expuestos en el catálogo público de /admin/ai. Ollama
 *  quedó fuera (follow-up US-063): tenants legacy US-048 siguen
 *  funcionando en el worker pero la UI ya no ofrece su alta.
 */
export type BYOProvider = "openai" | "claude" | "perplexity" | "gemini";

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

export type BYOProviderInfo = {
  key: BYOProvider;
  label: string;
  description: string;
  api_keys_url: string;
  docs_url: string;
  suggested_models: string[];
  requires_base_url: boolean;
};

export type TenantAIProviderRead = {
  mode: TenantAIMode;
  byo: BYOConfigRead | null;
  byo_enabled: boolean;
  byo_catalog: BYOProviderInfo[];
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
};

// Fallback de modelos si el catálogo del backend no se pudo cargar.
export const BYO_PROVIDER_MODELS: Record<BYOProvider, string[]> = {
  openai: ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"],
  claude: ["claude-3-5-haiku-20241022", "claude-sonnet-4-6"],
  perplexity: ["sonar", "sonar-pro"],
  gemini: ["gemini-1.5-flash", "gemini-1.5-pro"],
};
