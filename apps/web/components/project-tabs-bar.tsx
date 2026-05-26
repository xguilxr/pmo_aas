"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  BarChart3,
  FileText,
  GitBranch,
  Lightbulb,
  ListTree,
  MessageSquareText,
  ShieldAlert,
  Users,
} from "lucide-react";

import { cn } from "@/lib/cn";

type ProjectTab = {
  id: string;
  label: string;
  icon: React.ReactNode;
  href: (projectId: string) => string;
  match: (pathname: string, projectId: string) => boolean;
};

const TABS: ProjectTab[] = [
  {
    id: "overview",
    label: "Resumen",
    icon: <Activity className="h-4 w-4" aria-hidden />,
    href: (id) => `/pmo/projects/${id}`,
    match: (p, id) =>
      p === `/pmo/projects/${id}` ||
      /^\/admin\/projects\/[^/]+\/edit/.test(p),
  },
  {
    id: "plan",
    label: "Plan",
    icon: <ListTree className="h-4 w-4" aria-hidden />,
    href: (id) => `/pmo/projects/${id}/plan`,
    match: (p) =>
      /^\/admin\/projects\/[^/]+\/(plan|tasks|gantt)/.test(p),
  },
  {
    id: "raid",
    label: "RAID",
    icon: <ShieldAlert className="h-4 w-4" aria-hidden />,
    href: (id) => `/pmo/projects/${id}/raid`,
    match: (p) => /^\/admin\/projects\/[^/]+\/(raid|risks|issues)/.test(p),
  },
  {
    id: "areas",
    label: "Áreas/Recursos",
    icon: <Users className="h-4 w-4" aria-hidden />,
    href: (id) => `/pmo/projects/${id}/areas`,
    match: (p) => /^\/admin\/projects\/[^/]+\/areas/.test(p),
  },
  {
    id: "documents",
    label: "Documentos",
    icon: <FileText className="h-4 w-4" aria-hidden />,
    href: (id) => `/pmo/projects/${id}/documents`,
    match: (p) => /^\/admin\/projects\/[^/]+\/documents/.test(p),
  },
  {
    id: "minutes",
    label: "Minutas",
    icon: <MessageSquareText className="h-4 w-4" aria-hidden />,
    href: (id) => `/pmo/projects/${id}/minutes`,
    match: (p) =>
      /^\/admin\/projects\/[^/]+\/(minutes|ai-minutes)/.test(p),
  },
  {
    id: "reports",
    label: "Reportes",
    icon: <BarChart3 className="h-4 w-4" aria-hidden />,
    href: (id) => `/pmo/projects/${id}/reports`,
    match: (p) => /^\/admin\/projects\/[^/]+\/reports/.test(p),
  },
  {
    id: "changes",
    label: "Cambios",
    icon: <GitBranch className="h-4 w-4" aria-hidden />,
    href: (id) => `/pmo/projects/${id}/changes`,
    match: (p) => /^\/admin\/projects\/[^/]+\/changes/.test(p),
  },
  {
    id: "lessons",
    label: "Lecciones",
    icon: <Lightbulb className="h-4 w-4" aria-hidden />,
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
      className="sticky top-0 z-20 -mx-4 -mt-6 mb-6 border-b border-[var(--border-default)] bg-[var(--color-app)] px-4 pt-6 lg:-mx-8 lg:px-8 relative before:absolute before:inset-0 before:-z-10 before:bg-[var(--color-app)]"
    >
      <ul className="flex flex-wrap justify-center gap-1 overflow-x-auto py-3">
        {TABS.map((tab) => {
          const active = tab.match(pathname, projectId);
          return (
            <li key={tab.id} className="flex-none">
              <Link
                href={tab.href(projectId)}
                prefetch={false}
                className={cn(
                  "inline-flex h-9 items-center gap-1.5 rounded-[var(--radius-md)] px-3 text-sm transition-colors",
                  active
                    ? "bg-[var(--color-surface)] font-semibold text-[var(--color-primary)] shadow-[var(--shadow-sm)]"
                    : "text-[var(--color-tertiary)] hover:bg-[var(--color-subtle)] hover:text-[var(--color-primary)]",
                )}
                aria-current={active ? "page" : undefined}
              >
                {tab.icon}
                {tab.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
