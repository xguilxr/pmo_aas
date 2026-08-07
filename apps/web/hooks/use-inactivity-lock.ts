"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { hasSession } from "@/lib/auth-storage";

const INACTIVITY_TIMEOUT_MIN = 15;

/**
 * ENH-160 — Bloqueo por inactividad (antes era logout duro + redirect).
 *
 * Tras 15 min sin actividad, en lugar de descartar la sesión y mandar a
 * `/login` (perdiendo ruta y estado en memoria), expone `locked = true` para
 * que la UI muestre un overlay de re-login encima del contenido con blur. El
 * desbloqueo es explícito (`unlock`) tras re-autenticar, así no se pierde
 * progreso: nunca hay redirect ni reload.
 */
export function useInactivityLock() {
  const [locked, setLocked] = useState(false);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  // Espejo de `locked` para que los listeners (closures estables) lean el
  // valor actual sin re-suscribirse en cada render.
  const lockedRef = useRef(false);

  const clearTimer = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  const scheduleLock = useCallback(() => {
    clearTimer();
    // No re-armar si ya está bloqueado o no hay sesión.
    if (lockedRef.current) return;
    if (!hasSession()) return;

    timeoutRef.current = setTimeout(() => {
      lockedRef.current = true;
      setLocked(true);
    }, INACTIVITY_TIMEOUT_MIN * 60 * 1000);
  }, [clearTimer]);

  const unlock = useCallback(() => {
    lockedRef.current = false;
    setLocked(false);
    scheduleLock();
  }, [scheduleLock]);

  useEffect(() => {
    if (!hasSession()) return;

    scheduleLock();

    const events = ["mousedown", "keydown", "scroll", "touchstart"];
    const onActivity = () => {
      // Mientras está bloqueado, la actividad del usuario no re-arma el timer:
      // el desbloqueo solo ocurre tras re-autenticar.
      if (lockedRef.current) return;
      scheduleLock();
    };

    events.forEach((event) => window.addEventListener(event, onActivity));

    return () => {
      clearTimer();
      events.forEach((event) => window.removeEventListener(event, onActivity));
    };
  }, [scheduleLock, clearTimer]);

  return { locked, unlock };
}
