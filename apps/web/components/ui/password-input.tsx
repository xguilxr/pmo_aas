"use client";

import { forwardRef, useId, useState, type InputHTMLAttributes } from "react";
import { Eye, EyeOff } from "lucide-react";
import { cn } from "@/lib/cn";
import { Input } from "./input";

/**
 * Campo de contraseña con control para revelar lo escrito.
 *
 * MCS SEG-01 · **ASVS 2.1.12** — «Verify that the user can choose to either
 * temporarily view the entire masked password, or temporarily view the last
 * typed character of the password».
 *
 * ## Por qué es un control de seguridad y no un adorno
 *
 * Un campo enmascarado sin forma de comprobar lo escrito empuja a las dos
 * conductas que ASVS quiere evitar: elegir contraseñas cortas y fáciles de
 * teclear a ciegas, y pegarlas desde un sitio menos seguro para no
 * equivocarse. Poder mirar un segundo lo que uno acaba de escribir es lo que
 * hace practicable una contraseña larga.
 *
 * ## Por qué existe este componente
 *
 * El control ya estaba en `login` y en `reset`, copiado a mano en cada uno, y
 * faltaba en los **nueve** campos de `change-password`, `account` y
 * `superadmin/me` — que son justo las pantallas donde se *elige* una
 * contraseña nueva, o sea donde más falta hace. Una copia por pantalla es lo
 * que produce ese resultado: nadie sabe cuántas hay.
 *
 * Vuelve a `password` al perder el foco: el estado revelado es para
 * comprobar, no para dejarlo puesto mientras alguien pasa por detrás.
 */
type Props = Omit<InputHTMLAttributes<HTMLInputElement>, "type"> & {
  invalid?: boolean;
};

export const PasswordInput = forwardRef<HTMLInputElement, Props>(
  function PasswordInput({ className, disabled, onBlur, ...rest }, ref) {
    const [visible, setVisible] = useState(false);
    const descripcionId = useId();

    return (
      <div className="relative">
        <Input
          ref={ref}
          {...rest}
          type={visible ? "text" : "password"}
          disabled={disabled}
          aria-describedby={visible ? descripcionId : undefined}
          onBlur={(e) => {
            setVisible(false);
            onBlur?.(e);
          }}
          className={cn("pr-10", className)}
        />
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          disabled={disabled}
          // `aria-pressed` dice el estado; la etiqueta dice la acción. Sin las
          // dos, un lector de pantalla anuncia «mostrar contraseña» tanto si
          // está mostrada como si no.
          aria-pressed={visible}
          aria-label={visible ? "Ocultar contraseña" : "Mostrar contraseña"}
          className={cn(
            "absolute right-2 top-1/2 inline-flex h-6 w-6 -translate-y-1/2 items-center",
            "justify-center rounded-[var(--radius-xs)] text-[var(--color-tertiary)]",
            "hover:text-[var(--color-primary)] disabled:cursor-not-allowed",
            "disabled:text-[var(--color-disabled)]",
          )}
        >
          {visible ? (
            <EyeOff className="h-4 w-4" aria-hidden />
          ) : (
            <Eye className="h-4 w-4" aria-hidden />
          )}
        </button>
        {visible ? (
          <span id={descripcionId} className="sr-only" role="status">
            La contraseña está visible en pantalla.
          </span>
        ) : null}
      </div>
    );
  },
);
