import { apiFetch } from "@/lib/api";

// ============================================================================
// Selector de modo IA por tenant (disabled / platform / byo). El único flujo
// de alta de proveedor es el wizard BYO de /admin/ai (BUG-053).
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

/** Proveedores expuestos en el catálogo público de /admin/ai. */
export type BYOProvider =
  | "openai"
  | "claude"
  | "perplexity"
  | "gemini"
  | "custom"
  | "azure";

export type BYOConfigRead = {
  provider: BYOProvider;
  api_key_mask: string | null;
  has_api_key: boolean;
  model: string | null;
  base_url: string | null;
  deployment_name: string | null;
  api_version: string | null;
  rate_limit_rpm: number | null;
  daily_token_limit: number | null;
  acknowledge_security: boolean | null;
  last_test_at: string | null;
  last_test_status: "ok" | "fail" | null;
  last_test_error: string | null;
};

export type BYOConfigIn = {
  provider: BYOProvider;
  api_key?: string | null;
  model?: string | null;
  base_url?: string | null;
  deployment_name?: string | null;
  api_version?: string | null;
  rate_limit_rpm?: number | null;
  daily_token_limit?: number | null;
  acknowledge_security?: boolean | null;
};

export type BYOProviderInfo = {
  key: BYOProvider;
  label: string;
  description: string;
  api_keys_url: string;
  docs_url: string;
  suggested_models: string[];
  requires_base_url: boolean;
  requires_azure_fields?: boolean;
  requires_security_ack?: boolean;
  security_warning?: string;
  base_url_hint?: string;
};

export type TenantAIProviderRead = {
  mode: TenantAIMode;
  byo: BYOConfigRead | null;
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
  opts?: { force?: boolean },
): Promise<TenantAIProviderRead> {
  const qs = opts?.force ? "?force=true" : "";
  return apiFetch<TenantAIProviderRead>(`/api/v1/admin/ai/provider${qs}`, {
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
  custom: "Otro proveedor (compatible OpenAI)",
  azure: "Microsoft Copilot M365 (Azure OpenAI)",
};

// Fallback de modelos si el catálogo del backend no se pudo cargar.
export const BYO_PROVIDER_MODELS: Record<BYOProvider, string[]> = {
  openai: ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"],
  claude: ["claude-3-5-haiku-20241022", "claude-sonnet-4-6"],
  perplexity: ["sonar", "sonar-pro"],
  gemini: ["gemini-1.5-flash", "gemini-1.5-pro"],
  custom: [],
  azure: ["gpt-4o", "gpt-4", "gpt-35-turbo"],
};
