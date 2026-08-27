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

import { Button } from "@/components/ui/button";
import { Icono } from "@/components/ui/icono";
import { ApiError, apiBase, apiFetch } from "@/lib/api";
import { cn } from "@/lib/cn";

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
  icon: string;
  description: string;
}> = [
  {
    key: "charter",
    label: "Project Charter",
    icon: "file-text",
    description: "Documento fundacional del proyecto (auto-creado).",
  },
  {
    key: "plan",
    label: "Plan",
    icon: "list-check",
    description: "Archivo vivo del plan; DB es la fuente de verdad.",
  },
  {
    key: "raid",
    label: "RAIDs",
    icon: "triangle-alert",
    description: "Riesgos · Acciones · Incidencias · Decisiones (export Excel).",
  },
  {
    key: "organigrama",
    label: "Organigrama",
    icon: "git-branch",
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
    <div className="flex flex-col gap-4 px-6 py-5.5">
      <div className="flex items-end justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-[22px] font-semibold tracking-[-0.02em] text-[var(--text-primary)]">
            Artefactos
          </h1>
          <p className="text-[13px] text-[var(--text-tertiary)]">
            Catálogo curado de artefactos vivos del proyecto.
          </p>
        </div>
        <Link
          href={`/pmo/projects/${id}/documents/legacy`}
          className="text-[12.5px] text-[var(--text-tertiary)] hover:underline"
        >
          Ver archivos legacy →
        </Link>
      </div>

      <div className="flex items-center gap-0.5 border-b border-[var(--border-default)] shadow-[var(--linea-surco)]">
        {TAB_DEFS.map((tab) => {
          const meta = itemsByType.get(tab.key);
          const isActive = active === tab.key;
          return (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActive(tab.key)}
              className={cn(
                "flex h-9.5 items-center gap-1.75 border-b-2 px-3 text-[13px] transition-colors",
                isActive
                  ? "border-[var(--text-primary)] font-semibold text-[var(--text-primary)]"
                  : "border-transparent text-[var(--text-tertiary)] hover:text-[var(--text-primary)]",
              )}
            >
              <Icono nombre={tab.icon} size={15} />
              <span>{tab.label}</span>
              {meta?.placeholder ? (
                <span className="ml-1.5 inline-flex h-4 items-center rounded-[var(--radius-sm)] bg-[var(--color-warning-bg)] px-1.5 text-[9.5px] font-bold uppercase tracking-[0.04em] text-[var(--color-warning-fg)]">
                  Pendiente
                </span>
              ) : null}
            </button>
          );
        })}
      </div>

      {loading ? (
        <div className="text-[13px] text-[var(--text-tertiary)]">Cargando…</div>
      ) : error ? (
        <div className="rounded-[var(--radius-md)] border border-[var(--color-danger-border)] bg-[var(--color-danger-bg)] px-3 py-2 text-[13px] text-[var(--color-danger-fg)]">
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
      <div className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] px-4 py-3.5 shadow-[var(--linea-surco-arriba)]">
        <div className="flex flex-col items-center gap-2 py-6 text-center">
          <Icono nombre="git-branch" size={26} className="text-[var(--text-faint)]" />
          <span className="text-[13.5px] font-medium text-[var(--text-primary)]">
            Organigrama del proyecto
          </span>
          <p className="max-w-[420px] text-[12.5px] text-[var(--text-tertiary)]">
            {meta.placeholder_reason ??
              "Pendiente de redefinición Áreas/Recursos."}
          </p>
        </div>
      </div>
    );
  }

  const detail = TAB_DEFS.find((t) => t.key === meta.type);

  return (
    <div className="flex flex-col gap-4 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-5 shadow-[var(--relieve-isla)]">
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-2.25">
          {detail ? (
            <Icono nombre={detail.icon} size={18} className="text-[var(--text-secondary)]" />
          ) : null}
          <h2 className="text-[16px] font-semibold text-[var(--text-primary)]">{detail?.label}</h2>
        </div>
        <p className="text-[13px] text-[var(--text-tertiary)]">{detail?.description}</p>
      </div>

      <dl className="grid grid-cols-2 gap-4 border-t border-[var(--border-subtle)] pt-1 shadow-[var(--linea-surco-arriba)] sm:grid-cols-4">
        <div className="flex flex-col gap-0.75 pt-3.5">
          <dt className="text-[10.5px] font-semibold uppercase tracking-[0.06em] text-[var(--text-tertiary)]">
            Estado
          </dt>
          <dd className="flex items-center gap-1.5 text-[13px] text-[var(--text-primary)]">
            <span
              className={cn(
                "h-1.75 w-1.75 rounded-full",
                meta.available ? "bg-[var(--color-success-fg)]" : "bg-[var(--text-faint)]",
              )}
            />
            {meta.available ? "Disponible" : "Sin generar"}
          </dd>
        </div>
        <div className="flex flex-col gap-0.75 pt-3.5">
          <dt className="text-[10.5px] font-semibold uppercase tracking-[0.06em] text-[var(--text-tertiary)]">
            Formato
          </dt>
          <dd className="font-mono text-[13px] text-[var(--text-primary)]">
            {meta.source_format ?? "—"}
          </dd>
        </div>
        {meta.filename ? (
          <div className="flex flex-col gap-0.75 pt-3.5">
            <dt className="text-[10.5px] font-semibold uppercase tracking-[0.06em] text-[var(--text-tertiary)]">
              Archivo
            </dt>
            <dd className="truncate text-[12.5px] text-[var(--text-secondary)]">{meta.filename}</dd>
          </div>
        ) : null}
        {meta.size_bytes ? (
          <div className="flex flex-col gap-0.75 pt-3.5">
            <dt className="text-[10.5px] font-semibold uppercase tracking-[0.06em] text-[var(--text-tertiary)]">
              Tamaño
            </dt>
            <dd className="font-mono text-[13px] text-[var(--text-primary)]">
              {formatSize(meta.size_bytes)}
            </dd>
          </div>
        ) : null}
      </dl>

      <div className="flex flex-wrap gap-2 pt-1.5">
        {meta.download_url ? (
          <Button onClick={() => onDownload(meta)} loading={busy}>
            <Icono nombre="download" size={15} /> Descargar
          </Button>
        ) : null}
        {meta.type === "charter" ? (
          <Link href={`/pmo/projects/${projectId}/charter`}>
            <Button variant="secondary">
              <Icono nombre="pen" size={15} /> Editar Charter
            </Button>
          </Link>
        ) : null}
        {meta.type === "plan" ? (
          <Link href={`/pmo/projects/${projectId}/plan`}>
            <Button variant="secondary">
              <Icono nombre="arrow-up-right" size={15} /> Abrir Plan
            </Button>
          </Link>
        ) : null}
        {meta.type === "raid" ? (
          <Link href={`/pmo/projects/${projectId}/raid`}>
            <Button variant="secondary">
              <Icono nombre="arrow-up-right" size={15} /> Abrir RAID
            </Button>
          </Link>
        ) : null}
      </div>

      {meta.type === "plan" && !meta.available ? (
        <p className="text-[12px] text-[var(--text-tertiary)]">
          Aún no hay archivo de Plan importado. La descarga genera la plantilla XLSX
          a partir de las tareas actuales en DB.
        </p>
      ) : null}
    </div>
  );
}
