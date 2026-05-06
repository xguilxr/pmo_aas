import { BackLink } from "@/components/back-link";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { ProjectForm } from "@/components/project-form";

export default function NewProjectPage() {
  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <div className="flex items-center gap-2">
        <BackLink fallbackHref="/pmo/projects" />
        <Breadcrumb
          items={[
            { href: "/pmo/projects", label: "Proyectos" },
            { label: "Nuevo" },
          ]}
        />
      </div>
      <header>
        <h1 className="text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
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
