"use client";

import { useEffect, useRef } from "react";
import { logout } from "@/lib/auth";
import { getAccessToken } from "@/lib/auth-storage";

const INACTIVITY_TIMEOUT_MIN = 15;

export function useInactivityLogout() {
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  const resetInactivityTimer = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    const token = getAccessToken();
    if (!token) return;

    timeoutRef.current = setTimeout(() => {
      logout();
      window.location.href = "/login";
    }, INACTIVITY_TIMEOUT_MIN * 60 * 1000);
  };

  useEffect(() => {
    const token = getAccessToken();
    if (!token) return;

    resetInactivityTimer();

    const events = ["mousedown", "keydown", "scroll", "touchstart"];

    events.forEach((event) => {
      window.addEventListener(event, resetInactivityTimer);
    });

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      events.forEach((event) => {
        window.removeEventListener(event, resetInactivityTimer);
      });
    };
  }, []);
}
