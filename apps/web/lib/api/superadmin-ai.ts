import { apiFetch } from "@/lib/api";

export type EnvSnapshot = {
  ai_mode: string;
  ollama_base_url: string;
  ollama_model: string;
  ai_timeout_sec: number;
  gemini_configured: boolean;
  claude_configured: boolean;
};

export type PlatformAIDefaultsRead = {
  ai_mode: string | null;
  ollama_base_url: string | null;
  ollama_model: string | null;
  ai_timeout_sec: number | null;
  env: EnvSnapshot;
};

export type PlatformAIDefaultsPatch = {
  ai_mode?: "ollama" | "gemini" | "claude" | "disabled" | null;
  ollama_base_url?: string | null;
  ollama_model?: string | null;
  ai_timeout_sec?: number | null;
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
