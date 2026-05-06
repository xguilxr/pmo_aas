import { BackLink } from "@/components/back-link";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { RequestForm } from "@/components/request-form";

export default function NewRequestPage() {
  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <div className="flex items-center gap-2">
        <BackLink fallbackHref="/pmo/requests" />
        <Breadcrumb
          items={[
            { href: "/pmo/requests", label: "Solicitudes" },
            { label: "Nueva" },
          ]}
        />
      </div>
      <header>
        <h1 className="text-2xl font-semibold text-[var(--color-primary)]">
          Nueva solicitud de proyecto
        </h1>
        <p className="mt-1 text-sm text-[var(--color-tertiary)]">
          Completa los datos en 4 pasos. Tu avance se guarda automáticamente cada 30 segundos.
        </p>
      </header>
      <RequestForm />
    </div>
  );
}
