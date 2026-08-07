import { apiFetch } from "./api";
import {
  clearSession,
  marcarSesionAbierta,
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

/**
 * ASVS 4.3.1 — respuesta del primer paso cuando la cuenta llega a una interfaz
 * de administración: todavía no hay sesión, hay un desafío.
 */
export type DesafioMfa = {
  mfa_required: true;
  desafio: string;
  detalle: string;
  /** Cuántos días se recuerda el equipo. Lo dice el servidor, que es quien lo
   *  configura: escribirlo también aquí garantizaría que un día discrepen. */
  dias_recordado: number;
};

export function esDesafio(res: LoginResponse | DesafioMfa): res is DesafioMfa {
  return (res as DesafioMfa).mfa_required === true;
}

export async function login(
  identifier: string,
  password: string,
): Promise<LoginResponse | DesafioMfa> {
  const res = await apiFetch<LoginResponse | DesafioMfa>("/api/v1/auth/login", {
    method: "POST",
    body: { identifier, password },
    auth: false,
  });
  // Sin sesión todavía: el segundo paso es `verificarCodigo`.
  if (esDesafio(res)) return res;
  // ASVS 3.2.3 / 8.2.2 — el token viene además en el cuerpo, para el SDK, pero
  // el navegador no lo guarda: su copia es la cookie `HttpOnly` que el API
  // acaba de emitir. Aquí solo queda constancia de que hay sesión abierta.
  marcarSesionAbierta();
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

/** ASVS 4.3.1 — segundo paso: canjea el código del correo por una sesión. */
export async function verificarCodigo(
  desafio: string,
  codigo: string,
  recordarEquipo: boolean,
): Promise<LoginResponse> {
  const res = await apiFetch<LoginResponse>("/api/v1/auth/verificar-codigo", {
    method: "POST",
    body: { desafio, codigo, recordar_equipo: recordarEquipo },
    auth: false,
  });
  marcarSesionAbierta();
  setStoredUser(res.user);
  setActiveTenantId(res.active_tenant_id);
  return res;
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

/**
 * US-063 — "Olvidé mi contraseña". Siempre resuelve sin error cuando el
 * backend devuelve 204 (no revela si el email existe).
 */
export async function forgotPassword(email: string): Promise<void> {
  await apiFetch("/api/v1/auth/forgot-password", {
    method: "POST",
    body: { email },
    auth: false,
  });
}

/** US-063 — fija la nueva password a partir del token recibido por email. */
export async function resetPassword(
  token: string,
  new_password: string,
): Promise<void> {
  await apiFetch("/api/v1/auth/reset-password", {
    method: "POST",
    body: { token, new_password },
    auth: false,
  });
}
