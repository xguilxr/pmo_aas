import { apiFetch } from "./api";
import {
  clearSession,
  setAccessToken,
  setActiveTenantId,
  setStoredUser,
  type StoredUser,
} from "./auth-storage";

export type LoginResponse = {
  access_token: string;
  token_type: string;
  user: StoredUser;
  tenants: string[];
  active_tenant_id: string | null;
};

export async function login(identifier: string, password: string): Promise<LoginResponse> {
  const res = await apiFetch<LoginResponse>("/api/v1/auth/login", {
    method: "POST",
    body: { identifier, password },
    auth: false,
  });
  setAccessToken(res.access_token);
  setStoredUser(res.user);
  setActiveTenantId(res.active_tenant_id);
  return res;
}

export async function logout(): Promise<void> {
  try {
    await apiFetch("/api/v1/auth/logout", { method: "POST" });
  } catch {
    // ignorar errores de red en logout
  } finally {
    clearSession();
  }
}

export async function fetchMe(): Promise<StoredUser> {
  const me = await apiFetch<StoredUser>("/api/v1/auth/me");
  setStoredUser(me);
  return me;
}

export async function changePassword(current_password: string, new_password: string): Promise<void> {
  await apiFetch("/api/v1/auth/change-password", {
    method: "POST",
    body: { current_password, new_password },
  });
}
