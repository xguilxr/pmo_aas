const ACCESS_TOKEN_KEY = "pmoaas.access_token";
const USER_KEY = "pmoaas.user";
const ACTIVE_TENANT_KEY = "pmoaas.active_tenant_id";

export type StoredUser = {
  id: string;
  username: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_superadmin: boolean;
  must_change_password: boolean;
  roles: string[];
};

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

export function getAccessToken(): string | null {
  if (!isBrowser()) return null;
  return window.localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function setAccessToken(token: string): void {
  if (!isBrowser()) return;
  window.localStorage.setItem(ACCESS_TOKEN_KEY, token);
}

export function clearAccessToken(): void {
  if (!isBrowser()) return;
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
}

export function getStoredUser(): StoredUser | null {
  if (!isBrowser()) return null;
  const raw = window.localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as StoredUser;
  } catch {
    return null;
  }
}

function emitUserUpdated(): void {
  if (!isBrowser()) return;
  window.dispatchEvent(new CustomEvent("pmoaas:user-updated"));
}

export function setStoredUser(user: StoredUser): void {
  if (!isBrowser()) return;
  window.localStorage.setItem(USER_KEY, JSON.stringify(user));
  // BUG-009: emitir "pmoaas:user-updated" para que los providers que
  // dependen del user (theme, branding, app-shell) se re-sincronicen
  // sin esperar a un full reload.
  emitUserUpdated();
}

export function clearStoredUser(): void {
  if (!isBrowser()) return;
  window.localStorage.removeItem(USER_KEY);
  emitUserUpdated();
}

export function getActiveTenantId(): string | null {
  if (!isBrowser()) return null;
  return window.localStorage.getItem(ACTIVE_TENANT_KEY);
}

export function setActiveTenantId(id: string | null): void {
  if (!isBrowser()) return;
  if (id) window.localStorage.setItem(ACTIVE_TENANT_KEY, id);
  else window.localStorage.removeItem(ACTIVE_TENANT_KEY);
}

export function clearSession(): void {
  clearAccessToken();
  clearStoredUser();
  setActiveTenantId(null);
}

export function hasSession(): boolean {
  return getAccessToken() !== null;
}
