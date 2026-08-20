"use client";

/**
 * Módulo **Artefactos** por proyecto (US-106 / EP018) — 4 tabs fijos:
 * Project Charter, Plan, RAIDs, Organigrama.
 *
 * Se llamaba «Documentos» hasta US-204, y el nombre viejo describía el
 * contenedor en vez del contenido: lo que vive aquí son las **salidas** del
 * proyecto —el acta con sus versiones, el plan exportado, el RAID en Excel, el
 * organigrama derivado de las participaciones—, no una carpeta de archivos que
 * alguien subió. La ruta sigue siendo `/documents`: renombrar una URL rompe los
 * enlaces guardados y no le aporta nada a quien lee.
 *
 * Los archivos sueltos del MVP previo viven en /documents/legacy (mismo
 * endpoint backend, fuera del whitelist de artefactos).
 */
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  Download,
  ExternalLink,
  FileText,
  Layers,
  ListTree,
  Network,
  Pencil,
  ShieldAlert,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { ApiError, apiBase, apiFetch } from "@/lib/api";

type ArtifactType = "charter" | "plan" | "raid" | "organigrama";

type ArtifactMeta = {
  type: ArtifactType;
  available: boolean;
  source_format: string | null;
  filename: string | null;
  size_bytes: number | null;
  download_url: string | null;
  edit_url: string | null;
  placeholder: boolean;
  placeholder_reason: string | null;
};

type ArtifactList = {
  project_id: string;
  items: ArtifactMeta[];
};

const TAB_DEFS: Array<{
  key: ArtifactType;
  label: string;
  icon: React.ReactNode;
  description: string;
}> = [
  {
    key: "charter",
    label: "Project Charter",
    icon: <FileText className="h-4 w-4" aria-hidden />,
    description: "Documento fundacional del proyecto (auto-creado).",
  },
  {
    key: "plan",
    label: "Plan",
    icon: <ListTree className="h-4 w-4" aria-hidden />,
    description: "Archivo vivo del plan; DB es la fuente de verdad.",
  },
  {
    key: "raid",
    label: "RAIDs",
    icon: <ShieldAlert className="h-4 w-4" aria-hidden />,
    description: "Riesgos · Acciones · Incidencias · Decisiones (export Excel).",
  },
  {
    key: "organigrama",
    label: "Organigrama",
    icon: <Network className="h-4 w-4" aria-hidden />,
    description: "Recursos asignados al proyecto.",
  },
];

function formatSize(bytes: number | null): string {
  if (!bytes) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

async function downloadAuthed(path: string, fallbackName: string) {
  const headers: Record<string, string> = { Accept: "application/octet-stream" };
  const res = await fetch(`${apiBase()}${path}`, {
    method: "GET",
    headers,
    credentials: "include",
  });
  if (!res.ok) {
    throw new ApiError(res.status, "DOWNLOAD_FAILED", `Descarga falló (HTTP ${res.status})`);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = fallbackName;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export default function DocumentosPage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<ArtifactList | null>(null);
  const [active, setActive] = useState<ArtifactType>("charter");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setData(await apiFetch<ArtifactList>(`/api/v1/projects/${id}/artifacts`));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron cargar los artefactos");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const itemsByType = useMemo(() => {
    const map = new Map<ArtifactType, ArtifactMeta>();
    data?.items.forEach((it) => map.set(it.type, it));
    return map;
  }, [data]);

  const current = itemsByType.get(active);

  async function handleDownload(meta: ArtifactMeta) {
    if (!meta.download_url) return;
    setBusy(true);
    setError(null);
    try {
      // BUG-057 / ENH-092 / ENH-093: el backend ya expone el filename
      // canónico (`{project-slug}-{tipo}.{ext}`) para cada artefacto.
      // Si no llegó (artefacto deshabilitado), caemos a un default
      // razonable usando la extensión informada por el server.
      const ext = meta.source_format || "xlsx";
      const fallback = `${active}.${ext}`;
      await downloadAuthed(meta.download_url, meta.filename || fallback);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo descargar el artefacto");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4 p-6">
      <header className="flex items-start justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-xl font-semibold">
            <Layers className="h-5 w-5" aria-hidden />
            Artefactos
          </h1>
          <p className="text-sm text-[var(--color-secondary)]">
            Catálogo curado de artefactos vivos del proyecto.
          </p>
        </div>
        <Link
          href={`/pmo/projects/${id}/documents/legacy`}
          className="text-xs text-[var(--color-tertiary)] underline-offset-2 hover:underline"
        >
          Ver archivos legacy →
        </Link>
      </header>

      <div className="flex flex-wrap gap-1 border-b border-[var(--border-default)]">
        {TAB_DEFS.map((tab) => {
          const meta = itemsByType.get(tab.key);
          const isActive = active === tab.key;
          return (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActive(tab.key)}
              className={
                "flex items-center gap-2 border-b-2 px-3 py-2 text-sm transition-colors " +
                (isActive
                  ? "border-[var(--color-primary)] text-[var(--color-primary)]"
                  : "border-transparent text-[var(--color-secondary)] hover:text-[var(--color-primary)]")
              }
            >
              {tab.icon}
              <span>{tab.label}</span>
              {meta?.placeholder ? (
                <span className="rounded bg-[var(--color-warning-bg)] px-1 py-0.5 text-[10px] uppercase text-[var(--color-warning-fg)]">
                  Pendiente
                </span>
              ) : null}
            </button>
          );
        })}
      </div>

      {loading ? (
        <div className="text-sm text-[var(--color-tertiary)]">Cargando…</div>
      ) : error ? (
        <div className="rounded border border-[var(--color-danger-border)] bg-[var(--color-danger-bg)] px-3 py-2 text-sm text-[var(--color-danger-fg)]">
          {error}
        </div>
      ) : current ? (
        <ArtifactPanel
          projectId={id}
          meta={current}
          busy={busy}
          onDownload={handleDownload}
        />
      ) : null}
    </div>
  );
}

function ArtifactPanel({
  projectId,
  meta,
  busy,
  onDownload,
}: {
  projectId: string;
  meta: ArtifactMeta;
  busy: boolean;
  onDownload: (m: ArtifactMeta) => void;
}) {
  if (meta.placeholder) {
    return (
      <div className="rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-sm)]">
        <div className="flex flex-col items-center gap-2 py-8 text-center">
          <Network className="h-8 w-8 text-[var(--color-tertiary)]" aria-hidden />
          <h3 className="text-base font-medium">Organigrama del proyecto</h3>
          <p className="max-w-md text-sm text-[var(--color-secondary)]">
            {meta.placeholder_reason ??
              "Pendiente de redefinición Áreas/Recursos."}
          </p>
        </div>
      </div>
    );
  }

  const detail = TAB_DEFS.find((t) => t.key === meta.type);

  return (
    <div className="space-y-4 rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--shadow-sm)]">
      <div>
        <h2 className="flex items-center gap-2 text-base font-medium">
          {detail?.icon}
          {detail?.label}
        </h2>
        <p className="text-sm text-[var(--color-secondary)]">{detail?.description}</p>
      </div>

      <dl className="grid gap-3 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-[var(--color-tertiary)]">Estado</dt>
          <dd>{meta.available ? "Disponible" : "Sin generar"}</dd>
        </div>
        <div>
          <dt className="text-[var(--color-tertiary)]">Formato</dt>
          <dd>{meta.source_format ?? "—"}</dd>
        </div>
        {meta.filename ? (
          <div>
            <dt className="text-[var(--color-tertiary)]">Archivo</dt>
            <dd className="truncate">{meta.filename}</dd>
          </div>
        ) : null}
        {meta.size_bytes ? (
          <div>
            <dt className="text-[var(--color-tertiary)]">Tamaño</dt>
            <dd>{formatSize(meta.size_bytes)}</dd>
          </div>
        ) : null}
      </dl>

      <div className="flex flex-wrap gap-2">
        {meta.download_url ? (
          <Button onClick={() => onDownload(meta)} loading={busy}>
            <Download className="h-4 w-4" aria-hidden /> Descargar
          </Button>
        ) : null}
        {meta.type === "charter" ? (
          <Link href={`/pmo/projects/${projectId}/charter`}>
            <Button variant="secondary">
              <Pencil className="h-4 w-4" aria-hidden /> Editar Charter
            </Button>
          </Link>
        ) : null}
        {meta.type === "plan" ? (
          <Link href={`/pmo/projects/${projectId}/plan`}>
            <Button variant="secondary">
              <ExternalLink className="h-4 w-4" aria-hidden /> Abrir Plan
            </Button>
          </Link>
        ) : null}
        {meta.type === "raid" ? (
          <Link href={`/pmo/projects/${projectId}/raid`}>
            <Button variant="secondary">
              <ExternalLink className="h-4 w-4" aria-hidden /> Abrir RAID
            </Button>
          </Link>
        ) : null}
      </div>

      {meta.type === "plan" && !meta.available ? (
        <p className="text-xs text-[var(--color-tertiary)]">
          Aún no hay archivo de Plan importado. La descarga genera la plantilla XLSX
          a partir de las tareas actuales en DB.
        </p>
      ) : null}
    </div>
  );
}
