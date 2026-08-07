"use client";

import { useState } from "react";
import { Download, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiBase, ApiError, apiFetch } from "@/lib/api";
import { clearSession, getStoredUser } from "@/lib/auth-storage";

/**
 * MCS SEG-01 · ASVS 8.3.2 — «users have a method to remove or export their data
 * on demand».
 *
 * ## El orden de la pantalla no es estético
 *
 * Exportar va **arriba** y suprimir abajo, con una separación visible. Quien
 * viene a borrarse suele querer también su copia, y una vez anonimizado ya no
 * hay forma de recuperarla: poner la descarga primero es lo que evita esa
 * pérdida silenciosa.
 *
 * ## La supresión pide re-teclear el correo
 *
 * Mismo patrón que el borrado permanente de entidades: una acción irreversible
 * no puede depender de un solo clic. El correo es lo que la persona sabe sin
 * buscarlo, así que no obliga a ir a otra pantalla a copiarlo.
 *
 * La decisión de anonimizar en vez de borrar, y por qué, está en ADR-034 y en
 * `services/datos_personales.py`. Aquí se dice en el lenguaje de quien lo lee.
 */
export function MisDatosSection() {
  const [descargando, setDescargando] = useState(false);
  const [confirmacion, setConfirmacion] = useState("");
  const [suprimiendo, setSuprimiendo] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const correo = getStoredUser()?.email ?? "";

  async function exportar() {
    setDescargando(true);
    setError(null);
    try {
      // Descarga directa: la respuesta es un archivo, no JSON que la aplicación
      // vaya a interpretar. `credentials: "include"` lleva la cookie de sesión.
      const res = await fetch(`${apiBase()}/api/v1/users/me/datos-personales`, {
        credentials: "include",
        cache: "no-store",
      });
      if (!res.ok) throw new ApiError(res.status, "UNKNOWN", "No se pudo exportar");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "mis-datos.json";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setError("No se pudo generar la copia de tus datos. Inténtalo de nuevo.");
    } finally {
      setDescargando(false);
    }
  }

  async function suprimir() {
    setSuprimiendo(true);
    setError(null);
    try {
      await apiFetch("/api/v1/users/me/datos-personales/suprimir", {
        method: "POST",
        body: { confirmacion },
      });
      // La cuenta queda inactiva: no hay a dónde volver dentro de la aplicación.
      clearSession();
      window.location.href = "/login";
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "No se pudo completar la solicitud. Inténtalo de nuevo.",
      );
      setSuprimiendo(false);
    }
  }

  return (
    <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-6">
      <h2 className="text-lg font-semibold text-[var(--color-primary)]">Tus datos</h2>

      <div className="mt-4">
        <h3 className="text-sm font-medium text-[var(--color-secondary)]">
          Descargar una copia
        </h3>
        <p className="mt-1 text-sm text-[var(--color-tertiary)]">
          Un archivo JSON con tu cuenta, tus preferencias y el registro de lo que
          has hecho en la plataforma. No incluye el texto que otras personas
          escribieron y que puede mencionarte por tu nombre.
        </p>
        <Button
          variant="secondary"
          className="mt-3"
          onClick={exportar}
          loading={descargando}
        >
          <Download className="h-4 w-4" aria-hidden />
          Descargar mis datos
        </Button>
      </div>

      <div className="mt-6 border-t border-[var(--border-default)] pt-6">
        <h3 className="text-sm font-medium text-[var(--color-danger-fg)]">
          Eliminar mis datos personales
        </h3>
        <p className="mt-1 text-sm text-[var(--color-tertiary)]">
          Tu nombre, tu correo y tus preferencias se sustituyen por un marcador
          anónimo, y tu cuenta se desactiva. El historial de los proyectos se
          conserva sin poder atribuirse a ti, porque es información de tu
          organización. <strong>No se puede deshacer</strong> — si quieres una
          copia, descárgala antes.
        </p>

        <label
          htmlFor="confirmar-supresion"
          className="mt-4 block text-xs font-medium text-[var(--color-secondary)]"
        >
          Escribe {correo || "tu correo"} para confirmar
        </label>
        <Input
          id="confirmar-supresion"
          className="mt-1.5"
          value={confirmacion}
          onChange={(e) => setConfirmacion(e.target.value)}
          placeholder={correo}
          autoComplete="off"
        />

        {error ? (
          <div
            role="alert"
            className="mt-3 rounded-[var(--radius-md)] border border-[var(--color-danger-border)] bg-[var(--color-danger-bg)] px-3 py-2 text-sm text-[var(--color-danger-fg)]"
          >
            {error}
          </div>
        ) : null}

        <Button
          variant="danger"
          className="mt-3"
          onClick={suprimir}
          loading={suprimiendo}
          disabled={confirmacion.trim().toLowerCase() !== correo.toLowerCase()}
        >
          <Trash2 className="h-4 w-4" aria-hidden />
          Eliminar mis datos
        </Button>
      </div>
    </section>
  );
}
