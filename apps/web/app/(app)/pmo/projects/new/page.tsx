import { ProjectForm } from "@/components/project-form";

export default function NewProjectPage() {
  return (
    <div className="mx-auto max-w-4xl">
      <ProjectForm mode="create" />
    </div>
  );
}
