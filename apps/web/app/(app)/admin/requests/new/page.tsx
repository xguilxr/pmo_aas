import Link from "next/link";

import { RequestForm } from "@/components/request-form";

export default function NewRequestPage() {
  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <header>
        <nav className="text-xs text-[var(--color-tertiary)]">
          <Link href="/admin/requests" className="hover:underline">
            Solicitudes
          </Link>
          <span className="mx-1">/</span>
          <span>Nueva</span>
        </nav>
        <h1 className="mt-1 text-2xl font-semibold text-[var(--color-primary)]">
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
