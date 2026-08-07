/**
 * Dónde vive la sesión en el navegador.
 *
 * MCS SEG-01 · **ASVS 3.2.3 y 8.2.2** (ADR-033).
 *
 * ## Qué había
 *
 * El token de acceso y el perfil del usuario vivían en `localStorage`.
 * Cualquier guion inyectado —propio, o de cualquier dependencia de npm que
 * entre en el paquete— los lee con una línea, y con el token tiene la sesión
 * completa hasta que caduque. `HttpOnly` no hace mejor al token: hace que el
 * guion no pueda leerlo.
 *
 * ## Qué hay ahora
 *
 * - **El token no está aquí.** Lo emite el API en una cookie `HttpOnly`,
 *   `Secure`, `SameSite=Strict`, con prefijo `__Host-` (ASVS 3.4.4). El
 *   navegador la manda sola en cada petición; este código no la ve ni la
 *   necesita. Por eso `apiFetch` ya no compone `Authorization`.
 * - **El perfil vive en memoria**, no en disco. Sobrevive a la navegación
 *   entre pantallas —que es lo único para lo que se usaba— y no a una recarga:
 *   ahí lo repone `RequireAuth` con `/auth/me`, que es de donde tenía que
 *   haber salido siempre. El perfil guardado podía llevar días de retraso, con
 *   los roles de antes de que un administrador los cambiara.
 * - **En `localStorage` queda lo que no autoriza nada:** un indicador de que
 *   hay sesión abierta —para poder redirigir a `/login` sin esperar un 401—,
 *   el inquilino activo de un superadministrador, el tema y el idioma. El
 *   inquilino activo NO es una credencial: el servidor lo vuelve a comprobar
 *   en cada petición contra el token, así que escribirlo a mano no da acceso a
 *   nada.
 *
 * El indicador de sesión puede mentir —caduca el token y sigue puesto—, y no
 * pasa nada: quien decide es el servidor. Lo que evita es el parpadeo de
 * pintar la aplicación entera para redirigir a `/login` un segundo después.
 */

const SESION_ABIERTA_KEY = "pmoaas.session";
const ACTIVE_TENANT_KEY = "pmoaas.active_tenant_id";

/** Claves que este módulo dejó de usar y hay que retirar del navegador. */
const CLAVES_RETIRADAS = ["pmoaas.access_token", "pmoaas.user"];

export type StoredUser = {
  id: string;
  username: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_superadmin: boolean;
  must_change_password: boolean;
  roles: string[];
  /** ASVS 8.3.3 — lo calcula el servidor contra la versión vigente del aviso. */
  debe_aceptar_privacidad?: boolean;
};

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

/**
 * ASVS 8.2.2 — borra el token y el perfil que quedaron de la versión anterior.
 *
 * Sin esto, quien ya tenía sesión conserva su token en `localStorage`
 * indefinidamente: el agujero se cierra para las sesiones nuevas y sigue
 * abierto justo para los usuarios que ya estaban. Se ejecuta al cargar el
 * módulo, que es lo primero que pasa en cualquier pantalla.
 */
function limpiaLoQueSobra(): void {
  if (!isBrowser()) return;
  for (const clave of CLAVES_RETIRADAS) {
    try {
      window.localStorage.removeItem(clave);
    } catch {
      // Modo privado de Safari lanza al escribir. No es motivo para no cargar.
    }
  }
}

limpiaLoQueSobra();

/** El perfil, en memoria. No se persiste (ASVS 8.2.2). */
let usuarioEnMemoria: StoredUser | null = null;

export function getStoredUser(): StoredUser | null {
  return usuarioEnMemoria;
}

function emitUserUpdated(): void {
  if (!isBrowser()) return;
  window.dispatchEvent(new CustomEvent("pmoaas:user-updated"));
}

export function setStoredUser(user: StoredUser): void {
  usuarioEnMemoria = user;
  // BUG-009: emitir "pmoaas:user-updated" para que los providers que
  // dependen del user (theme, branding, app-shell) se re-sincronicen
  // sin esperar a un full reload.
  emitUserUpdated();
}

export function clearStoredUser(): void {
  usuarioEnMemoria = null;
  emitUserUpdated();
}

/**
 * ¿Hay una sesión abierta, hasta donde el navegador puede saber?
 *
 * No es una credencial y no autoriza nada: la cookie de sesión es `HttpOnly` y
 * este código no la ve. Sirve para no pintar la aplicación entera antes de
 * redirigir a `/login`.
 */
export function hasSession(): boolean {
  if (!isBrowser()) return false;
  try {
    return window.localStorage.getItem(SESION_ABIERTA_KEY) === "1";
  } catch {
    return false;
  }
}

export function marcarSesionAbierta(): void {
  if (!isBrowser()) return;
  try {
    window.localStorage.setItem(SESION_ABIERTA_KEY, "1");
  } catch {
    // Ver `limpiaLoQueSobra`.
  }
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
  usuarioEnMemoria = null;
  if (isBrowser()) {
    try {
      window.localStorage.removeItem(SESION_ABIERTA_KEY);
    } catch {
      // Ver `limpiaLoQueSobra`.
    }
  }
  setActiveTenantId(null);
  emitUserUpdated();
}
