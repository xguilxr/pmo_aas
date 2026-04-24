import Link from "next/link";

import { ProjectForm } from "@/components/project-form";

export default function NewProjectPage() {
  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <header>
        <nav className="text-[11px] text-[var(--text-tertiary)]">
          <Link href="/pmo/projects" className="hover:underline">
            Proyectos
          </Link>
          <span className="mx-1">/</span>
          <span>Nuevo</span>
        </nav>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
          Nuevo proyecto
        </h1>
        <p className="mt-1 text-[13px] text-[var(--text-tertiary)]">
          Completa los datos principales. Podrás ajustar fase, presupuesto real y salud más tarde.
        </p>
      </header>
      <ProjectForm mode="create" />
    </div>
  );
}
