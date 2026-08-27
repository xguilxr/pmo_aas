"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { Icono } from "@/components/ui/icono";
import { cn } from "@/lib/cn";

type ProjectTab = {
  id: string;
  label: string;
  icono: string;
  href: (projectId: string) => string;
  match: (pathname: string, projectId: string) => boolean;
};

const TABS: ProjectTab[] = [
  {
    id: "overview",
    label: "Resumen",
    icono: "circle-check",
    href: (id) => `/pmo/projects/${id}`,
    match: (p, id) =>
      p === `/pmo/projects/${id}` ||
      /^\/admin\/projects\/[^/]+\/edit/.test(p),
  },
  {
    id: "plan",
    label: "Plan",
    icono: "list-check",
    href: (id) => `/pmo/projects/${id}/plan`,
    match: (p) =>
      /^\/admin\/projects\/[^/]+\/(plan|tasks|gantt)/.test(p),
  },
  {
    // US-219 — el Project Board del artboard «Boards». Va detrás del Plan porque
    // es el mismo dato leído de otra forma: el plan lo ordena por WBS, el board
    // por estado. Aquí sí se arrastra —`tasks.status` lo declara una persona—, a
    // diferencia del Portfolio Board, cuyo estatus es derivado.
    id: "board",
    label: "Board",
    icono: "grid-2x2",
    href: (id) => `/pmo/projects/${id}/board`,
    match: (p) => /^\/pmo\/projects\/[^/]+\/board/.test(p),
  },
  {
    id: "raid",
    label: "RAID",
    icono: "triangle-alert",
    href: (id) => `/pmo/projects/${id}/raid`,
    match: (p) => /^\/admin\/projects\/[^/]+\/(raid|risks|issues)/.test(p),
  },
  {
    id: "areas",
    // US-204 — el mockup lo llama «Recursos», sin la barra. «Áreas/Recursos»
    // era el rastro de la migración de ENH-078 (la feature se movió al catálogo
    // del inquilino) y decía dos cosas para no equivocarse en ninguna. La ruta
    // sigue siendo `/areas`: renombrar una URL rompe los enlaces guardados y no
    // aporta nada al lector.
    label: "Recursos",
    icono: "users",
    href: (id) => `/pmo/projects/${id}/areas`,
    match: (p) => /^\/admin\/projects\/[^/]+\/areas/.test(p),
  },
  {
    id: "documents",
    // US-204 — «Artefactos»: lo que vive ahí son las salidas del proyecto
    // (acta, plan, RAID exportado, organigrama derivado), no una carpeta de
    // archivos sueltos. La ruta se queda en `/documents` por lo mismo que
    // arriba.
    label: "Artefactos",
    icono: "file-text",
    href: (id) => `/pmo/projects/${id}/documents`,
    match: (p) => /^\/admin\/projects\/[^/]+\/documents/.test(p),
  },
  {
    id: "minutes",
    label: "Minutas",
    icono: "file-spreadsheet",
    href: (id) => `/pmo/projects/${id}/minutes`,
    match: (p) =>
      /^\/admin\/projects\/[^/]+\/(minutes|ai-minutes)/.test(p),
  },
  {
    id: "reports",
    label: "Reportes",
    icono: "trending-up",
    href: (id) => `/pmo/projects/${id}/reports`,
    match: (p) => /^\/admin\/projects\/[^/]+\/reports/.test(p),
  },
  {
    id: "changes",
    label: "Cambios",
    icono: "git-branch",
    href: (id) => `/pmo/projects/${id}/changes`,
    match: (p) => /^\/admin\/projects\/[^/]+\/changes/.test(p),
  },
  {
    id: "lessons",
    label: "Lecciones",
    // Sin equivalente de Lightbulb en el set Keyline; `info` es el
    // provisional de la especificación de revamp (§2).
    icono: "info",
    href: (id) => `/pmo/projects/${id}/lessons`,
    match: (p) => /^\/admin\/projects\/[^/]+\/lessons/.test(p),
  },
];

/**
 * Barra de tabs del detalle de proyecto (US-035 / supersede US-017).
 * Se renderiza como parte del layout del proyecto, de modo que persiste
 * cruzando las sub-rutas de módulos: el usuario cambia de módulo sin
 * perder el header ni el contexto visual.
 */
export function ProjectTabsBar({ projectId }: { projectId: string }) {
  const pathname = usePathname();
  if (pathname.endsWith("/new") || pathname.includes("/projects/new")) {
    return null;
  }
  return (
    <nav
      aria-label="Módulos del proyecto"
      className="sticky top-0 z-20 -mx-4 mb-6 flex h-11.5 items-center gap-0.5 overflow-x-auto border-b border-[var(--border-default)] bg-[var(--color-app)] px-4 shadow-[var(--linea-surco)] lg:-mx-8 lg:px-8"
    >
      {TABS.map((tab) => {
        const active = tab.match(pathname, projectId);
        return (
          <Link
            key={tab.id}
            href={tab.href(projectId)}
            prefetch={false}
            className={cn(
              "inline-flex h-7.5 flex-none items-center gap-1.75 rounded-[var(--radius-md)] px-2.5 text-[12.5px] transition-colors",
              active
                ? "bg-[var(--color-primary)] font-medium text-[var(--color-inverse)]"
                : "text-[var(--text-secondary)] hover:bg-[var(--color-subtle)]",
            )}
            aria-current={active ? "page" : undefined}
          >
            <Icono nombre={tab.icono} size={15} />
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
