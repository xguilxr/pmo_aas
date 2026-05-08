import { apiFetch } from "@/lib/api";

export type EnvSnapshot = {
  ai_mode: string;
  gemini_configured: boolean;
  claude_configured: boolean;
  groq_configured: boolean;
};

export type PlatformAIDefaultsRead = {
  ai_mode: string | null;
  groq_api_key_mask: string | null;
  groq_configured: boolean;
  groq_model: string | null;
  env: EnvSnapshot;
};

export type PlatformAIDefaultsPatch = {
  ai_mode?: "disabled" | "platform" | "byo" | null;
  groq_api_key?: string | null;
  groq_model?: string | null;
};

export function getPlatformAIDefaults(): Promise<PlatformAIDefaultsRead> {
  return apiFetch<PlatformAIDefaultsRead>("/api/v1/superadmin/ai/defaults");
}

export function updatePlatformAIDefaults(
  body: PlatformAIDefaultsPatch,
): Promise<PlatformAIDefaultsRead> {
  return apiFetch<PlatformAIDefaultsRead>("/api/v1/superadmin/ai/defaults", {
    method: "PATCH",
    body,
  });
}

// ============================================================================
// US-057 — Panel de tenants + dashboard de uso Groq
// ============================================================================

export type TenantAIStatusRow = {
  tenant_id: string;
  tenant_name: string;
  tenant_slug: string;
  mode: "disabled" | "platform" | "byo";
  byo_provider: string | null;
  byo_model: string | null;
  byo_api_key_mask: string | null;
  last_test_at: string | null;
  last_test_status: "ok" | "fail" | null;
  last_test_error: string | null;
};

export function listTenantsAIStatus(): Promise<TenantAIStatusRow[]> {
  return apiFetch<TenantAIStatusRow[]>("/api/v1/superadmin/ai/tenants-status");
}

export type GroqUsageDayBucket = {
  date: string;
  requests: number;
  tokens_in: number;
  tokens_out: number;
  failed: number;
};

export type GroqUsageTenantRow = {
  tenant_id: string;
  tenant_name: string;
  requests: number;
  tokens_in: number;
  tokens_out: number;
};

export type GroqUsageSummary = {
  days: number;
  today_requests: number;
  today_tokens: number;
  limit_requests_per_day: number;
  limit_tokens_per_day: number;
  total_requests: number;
  total_tokens: number;
  total_failed: number;
  by_day: GroqUsageDayBucket[];
  top_tenants: GroqUsageTenantRow[];
};

export function getGroqUsage(days = 30): Promise<GroqUsageSummary> {
  return apiFetch<GroqUsageSummary>(`/api/v1/superadmin/ai/groq-usage?days=${days}`);
}

export type GroqPingResult = {
  ok: boolean;
  latency_ms: number | null;
  error: string | null;
  model: string | null;
};

export function pingGroq(): Promise<GroqPingResult> {
  return apiFetch<GroqPingResult>("/api/v1/superadmin/ai/groq/ping", {
    method: "POST",
  });
}
