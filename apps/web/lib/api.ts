import { getAccessToken, clearAccessToken } from "./auth-storage";

export type ApiErrorCode =
  | "UNAUTHENTICATED"
  | "ACCOUNT_LOCKED"
  | "USER_INACTIVE"
  | "FORBIDDEN"
  | "NOT_FOUND"
  | "CONFLICT"
  | "VALIDATION_ERROR"
  | "BUSINESS_RULE"
  | "NETWORK_ERROR"
  | "UNKNOWN";

export class ApiError extends Error {
  readonly status: number;
  readonly code: ApiErrorCode | string;
  readonly fields: Record<string, unknown>;

  constructor(status: number, code: string, message: string, fields: Record<string, unknown> = {}) {
    super(message);
    this.status = status;
    this.code = code;
    this.fields = fields;
  }
}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

export function apiBase(): string {
  if (!API_URL) {
    throw new ApiError(0, "NETWORK_ERROR", "NEXT_PUBLIC_API_URL no está configurada");
  }
  return API_URL.replace(/\/+$/, "");
}

type RequestOptions = {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  headers?: Record<string, string>;
  auth?: boolean;
  signal?: AbortSignal;
};

export async function apiFetch<T = unknown>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, headers = {}, auth = true, signal } = opts;
  const url = `${apiBase()}${path.startsWith("/") ? path : `/${path}`}`;

  const finalHeaders: Record<string, string> = {
    Accept: "application/json",
    ...headers,
  };
  if (body !== undefined) finalHeaders["Content-Type"] = "application/json";
  if (auth) {
    const token = getAccessToken();
    if (token) finalHeaders["Authorization"] = `Bearer ${token}`;
  }

  let res: Response;
  try {
    res = await fetch(url, {
      method,
      headers: finalHeaders,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      credentials: "include",
      // BUG-fix US-095 rework: evita que GETs idempotentes (ej. /tasks)
      // se sirvan desde el HTTP cache del navegador tras un PATCH.
      cache: "no-store",
      signal,
    });
  } catch (err) {
    throw new ApiError(0, "NETWORK_ERROR", "No se pudo conectar con el servidor");
  }

  if (res.status === 204) {
    return undefined as T;
  }

  const text = await res.text();
  const data = text ? safeJsonParse(text) : null;

  if (!res.ok) {
    if (res.status === 401 && auth) {
      clearAccessToken();
      if (typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent("pmoaas:unauthorized"));
      }
    }
    const envelope = extractErrorEnvelope(data, res.status);
    throw new ApiError(res.status, envelope.code, envelope.detail, envelope.fields);
  }

  return data as T;
}

function safeJsonParse(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

type ErrorEnvelope = {
  detail: string;
  code: string;
  fields: Record<string, unknown>;
};

function extractErrorEnvelope(data: unknown, status: number): ErrorEnvelope {
  const fallback: ErrorEnvelope = {
    detail: `Error ${status}`,
    code: "UNKNOWN",
    fields: {},
  };
  if (!data || typeof data !== "object") return fallback;
  const outer = (data as { detail?: unknown }).detail;
  if (outer && typeof outer === "object") {
    const inner = outer as { detail?: unknown; code?: unknown; fields?: unknown };
    return {
      detail: typeof inner.detail === "string" ? inner.detail : fallback.detail,
      code: typeof inner.code === "string" ? inner.code : fallback.code,
      fields: (inner.fields && typeof inner.fields === "object"
        ? (inner.fields as Record<string, unknown>)
        : {}),
    };
  }
  if (typeof outer === "string") {
    return { ...fallback, detail: outer };
  }
  return fallback;
}
