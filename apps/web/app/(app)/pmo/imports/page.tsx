"use client";

/**
 * US-216 — Onboarding masivo: importar proyectos y recursos.
 *
 * Del artboard «Onboarding masivo — Importación»: subir Excel/CSV → mapear
 * columnas → validar → confirmar. Cierra el bloque B5, «la carga inicial de 23
 * proyectos sin captura manual».
 *
 * ## Por qué la vista previa es un paso propio y no un aviso
 *
 * Una importación masiva es la operación menos reversible del producto: 23
 * proyectos creados mal se borran de uno en uno. Ver antes, fila por fila, lo
 * que va a pasar es lo que la hace segura — y es la diferencia entre un botón
 * que da miedo y uno que se usa.
 *
 * ## Por qué el reporte separa tres estados y no dos
 *
 * `duplicada` no es un error: es una fila que ya existe y que a propósito **no**
 * se actualiza. Mezclarla con las inválidas haría que quien revisa se ponga a
 * arreglar filas que están bien; presentarla como válida haría creer que se van a
 * crear. Son tres cosas distintas y llevan a tres acciones distintas.
 *
 * ## Los planes no se importan desde aquí
 *
 * Tienen su propio importador, en el plan de cada proyecto, porque un WBS es del
 * proyecto: el `1.2` de uno no es el `1.2` de otro. Se dice en la pantalla para
 * que nadie suba un plan aquí y no entienda el 415.
 */
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Icono } from "@/components/ui/icono";
import { Select } from "@/components/ui/select";
import { useOrganizacionActiva } from "@/components/organizacion-activa";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/cn";
import {
  CLASE_IMPORTACION_LABEL,
  ESTADO_FILA_LABEL,
  confirmImport,
  getImportColumns,
  previewImport,
  type ClaseDeImportacion,
  type ColumnaDeImportacion,
  type EstadoDeFila,
  type PreviewDeImportacion,
  type ResultadoDeImportacion,
} from "@/lib/api/tasks";

const BADGE_ESTADO: Record<EstadoDeFila, "success" | "danger" | "warning"> = {
  valida: "success",
  invalida: "danger",
  duplicada: "warning",
};

/** Primero lo que hay que arreglar. */
const ORDEN: EstadoDeFila[] = ["invalida", "duplicada", "valida"];

/** Pasos del flujo — puramente visual, derivado del estado ya existente. */
type PasoImport = 1 | 2 | 3 | 4;
const PASO_LABEL: Record<PasoImport, string> = {
  1: "Elegir y subir",
  2: "Validar",
  3: "Revisar filas",
  4: "Confirmar",
};

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export default function ImportsPage() {
  // US-205 — la organización se elige en el header y todo opera dentro de ella.
  // Esta pantalla no trae su propio selector: importar «en todas» no significa
  // nada —un proyecto vive en una organización— y `/pmo/imports` no está entre
  // las rutas que agregan, así que `efectiva` siempre es una concreta.
  const { efectiva: orgId, activaObj, cargando, vacio } = useOrganizacionActiva();
  const [clase, setClase] = useState<ClaseDeImportacion>("projects");
  const [columnas, setColumnas] = useState<ColumnaDeImportacion[]>([]);
  const [archivo, setArchivo] = useState<File | null>(null);
  const [preview, setPreview] = useState<PreviewDeImportacion | null>(null);
  const [resultado, setResultado] = useState<ResultadoDeImportacion | null>(null);
  const [subiendo, setSubiendo] = useState(false);
  const [confirmando, setConfirmando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getImportColumns(clase)
      .then((r) => setColumnas(r.columns))
      .catch(() => setColumnas([]));
    // Cambiar de clase invalida lo anterior: las columnas de un proyecto no son
    // las de una persona, y dejar el preview en pantalla lo haría leer como si
    // aplicara a la clase nueva.
    setPreview(null);
    setResultado(null);
    setArchivo(null);
  }, [clase]);

  const obligatorias = useMemo(
    () => columnas.filter((c) => c.required),
    [columnas],
  );

  // Paso actual del flujo — solo presentación, no gobierna nada.
  const paso: PasoImport = resultado ? 4 : preview ? 3 : archivo || subiendo ? 2 : 1;

  /**
   * La plantilla se genera en el navegador desde las columnas que el backend
   * declara. No es un archivo estático: uno se queda viejo el día que se añade
   * una columna, y el usuario descubre el desajuste al subirlo.
   */
  const descargarPlantilla = useCallback(
    (soloObligatorias: boolean) => {
      const cols = soloObligatorias ? obligatorias : columnas;
      if (!cols.length) return;
      const encabezados = cols.map((c) => c.label).join(",");
      // Una fila de ejemplo con los valores admitidos, cuando el vocabulario es
      // cerrado. Sin ella, «Tipo» es una columna vacía que hay que adivinar.
      const ejemplo = cols
        .map((c) => (c.values.length ? c.values[0] : ""))
        .join(",");
      const csv = `﻿${encabezados}\n${ejemplo}\n`;
      const url = URL.createObjectURL(
        new Blob([csv], { type: "text/csv;charset=utf-8" }),
      );
      const a = document.createElement("a");
      a.href = url;
      a.download = `plantilla-${clase}${soloObligatorias ? "-minima" : ""}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    },
    [clase, columnas, obligatorias],
  );

  async function subir() {
    if (!archivo || !orgId) return;
    setSubiendo(true);
    setError(null);
    setResultado(null);
    try {
      setPreview(await previewImport(clase, orgId, archivo));
    } catch (e) {
      setPreview(null);
      setError(
        e instanceof ApiError ? e.message : "No se pudo validar el archivo.",
      );
    } finally {
      setSubiendo(false);
    }
  }

  async function confirmar() {
    if (!preview) return;
    setConfirmando(true);
    setError(null);
    try {
      setResultado(await confirmImport(preview.job_id));
      setPreview(null);
      setArchivo(null);
    } catch (e) {
      setError(
        e instanceof ApiError
          ? e.message
          : "No se pudo confirmar la importación.",
      );
    } finally {
      setConfirmando(false);
    }
  }

  const filas = useMemo(
    () =>
      [...(preview?.rows ?? [])].sort(
        (a, b) => ORDEN.indexOf(a.state) - ORDEN.indexOf(b.state) || a.row - b.row,
      ),
    [preview],
  );

  if (cargando) {
    return (
      <div className="space-y-3 p-6">
        <span
          aria-hidden
          className="block h-8 w-64 animate-pulse rounded bg-[var(--color-muted)]"
        />
        <span
          aria-hidden
          className="block h-40 animate-pulse rounded bg-[var(--color-muted)]"
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4.5 p-6">
      <header className="flex flex-col gap-1.25">
        <nav className="flex items-center gap-1.75 text-[13px] text-[var(--text-tertiary)]">
          <Link href="/pmo/projects" className="text-[var(--text-secondary)] hover:underline">
            Proyectos
          </Link>
          <Icono nombre="chevron-right" size={14} className="text-[var(--border-strong)]" />
          <span className="font-medium text-[var(--text-primary)]">Importar</span>
        </nav>
        <h1 className="text-2xl font-semibold tracking-[-0.02em] text-[var(--text-primary)]">
          Onboarding masivo
        </h1>
        <p className="text-[13px] text-[var(--text-tertiary)]">
          Carga una cartera completa desde Excel o CSV. El archivo se valida
          entero antes de crear nada.
        </p>
      </header>

      {error ? <Banner variant="danger">{error}</Banner> : null}

      {/* DIS-03 — sin organizaciones no hay dónde importar, y el estado vacío
          dice qué hacer en vez de mostrar un selector vacío. */}
      {vacio ? (
        <Banner variant="info">
          Este inquilino todavía no tiene organizaciones. Una importación crea
          proyectos <em>dentro</em> de una, así que hay que crearla primero en
          Admin › Organizaciones.
        </Banner>
      ) : (
        <>
          {/* Pasos del proceso — círculo tinta (hecho), contorno (actual),
              gris (falta), conector de 1px. Sin barra de progreso. */}
          <div className="flex items-center gap-0 border-y border-[var(--border-default)] py-3 shadow-[var(--linea-surco),var(--linea-surco-arriba)]">
            {([1, 2, 3, 4] as PasoImport[]).map((n, i) => (
              <div key={n} className="flex items-center">
                {i > 0 ? <span className="h-px w-11 flex-none bg-[var(--border-default)]" /> : null}
                <span
                  className={cn(
                    "flex items-center gap-2.25",
                    i === 0 ? "pr-4.5" : i === 3 ? "pl-4.5" : "px-4.5",
                  )}
                >
                  <span
                    className={cn(
                      "flex h-5.5 w-5.5 flex-none items-center justify-center rounded-full font-mono text-[11px] font-medium",
                      n < paso
                        ? "bg-[var(--text-primary)] text-[var(--color-inverse)]"
                        : n === paso
                          ? "border border-[var(--text-primary)] text-[var(--text-primary)]"
                          : "border border-[var(--border-strong)] text-[var(--text-faint)]",
                    )}
                  >
                    {n}
                  </span>
                  <span
                    className={cn(
                      "text-[12.5px] font-semibold",
                      n <= paso ? "text-[var(--text-primary)]" : "text-[var(--text-faint)]",
                    )}
                  >
                    {PASO_LABEL[n]}
                  </span>
                </span>
              </div>
            ))}
            {archivo ? (
              <span className="ml-auto text-[12px] text-[var(--text-tertiary)]">
                {archivo.name} · {formatSize(archivo.size)}
              </span>
            ) : null}
          </div>

          <div className="grid gap-6 sm:grid-cols-2">
            <label className="flex flex-col gap-2 text-[11px] text-[var(--text-tertiary)]">
              Qué se importa
              <Select
                value={clase}
                onChange={(e) =>
                  setClase(e.target.value as ClaseDeImportacion)
                }
              >
                {(
                  Object.keys(CLASE_IMPORTACION_LABEL) as ClaseDeImportacion[]
                ).map((k) => (
                  <option key={k} value={k}>
                    {CLASE_IMPORTACION_LABEL[k]}
                  </option>
                ))}
              </Select>
              <span className="leading-[1.5] text-[var(--text-faint)]">
                Los planes se importan desde el plan de cada proyecto: un
                código WBS es del proyecto, el «1.2» de uno no es el de otro.
              </span>
            </label>
            <div className="flex flex-col gap-2 text-[11px] text-[var(--text-tertiary)]">
              Organización de destino
              <p className="text-[13px] font-medium text-[var(--text-primary)]">
                {activaObj?.name ?? "—"}
              </p>
              <span className="leading-[1.5] text-[var(--text-faint)]">
                Se cambia en el selector del header. Los duplicados se buscan
                dentro de ella
                {clase === "resources"
                  ? "; las personas son del inquilino entero, porque su carga de"
                    + " capacidad se calcula por persona"
                  : ""}
                .
              </span>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => descargarPlantilla(false)}
              disabled={!columnas.length}
            >
              <Icono nombre="download" size={15} />
              Plantilla completa
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => descargarPlantilla(true)}
              disabled={!obligatorias.length}
              title="Solo las columnas obligatorias — la misma plantilla sin lo opcional"
            >
              <Icono nombre="download" size={15} />
              Plantilla mínima ({obligatorias.length} columnas)
            </Button>
            <label className="inline-flex h-8 cursor-pointer items-center gap-2 rounded-[var(--radius-md)] border border-dashed border-[var(--border-strong)] px-3 text-[12.5px] text-[var(--text-tertiary)] hover:border-[var(--color-accent)]">
              <Icono nombre="upload" size={15} />
              {archivo ? archivo.name : "Elegí el archivo a importar · .csv, .xlsx"}
              <input
                type="file"
                accept=".csv,.xlsx"
                onChange={(e) => {
                  setArchivo(e.target.files?.[0] ?? null);
                  setPreview(null);
                  setResultado(null);
                }}
                className="sr-only"
                aria-label="Archivo a importar"
              />
            </label>
            <Button
              type="button"
              onClick={() => void subir()}
              disabled={!archivo || !orgId || subiendo}
              loading={subiendo}
            >
              <Icono nombre="upload" size={15} />
              Validar
            </Button>
            <span className="ml-auto inline-flex items-center gap-1.75 text-[12.5px] text-[var(--text-tertiary)]">
              <Icono nombre="info" size={14} />
              Espera {columnas.length} columnas, {obligatorias.length} obligatorias
            </span>
          </div>

          <details className="text-xs">
            <summary className="cursor-pointer text-[var(--text-faint)]">
              Qué columnas espera ({columnas.length}, {obligatorias.length}{" "}
              obligatorias)
            </summary>
            <ul className="mt-2 space-y-1">
              {columnas.map((c) => (
                <li key={c.key}>
                  <span className="font-medium">{c.label}</span>
                  {c.required ? (
                    <span className="ml-1 text-[var(--color-danger-fg)]">
                      obligatoria
                    </span>
                  ) : null}
                  <span className="block text-[11px] text-[var(--text-faint)]">
                    {c.help}
                    {c.values.length
                      ? ` Valores: ${c.values.join(", ")}.`
                      : ""}
                  </span>
                </li>
              ))}
            </ul>
          </details>

          {resultado ? (
            <Banner variant="success">
              <span className="flex flex-wrap items-center gap-x-3">
                <strong>{resultado.created_count} creados.</strong>
                {/* Los tres números van juntos: «18 creados» sin decir que 5
                    quedaron fuera es mentir por omisión. */}
                <span>
                  {resultado.skipped_invalid} con errores y{" "}
                  {resultado.skipped_duplicate} ya existentes quedaron fuera.
                </span>
                {clase === "projects" ? (
                  <Link href="/pmo" className="underline">
                    Ver la cartera
                  </Link>
                ) : (
                  <Link href="/pmo/resources" className="underline">
                    Ver los recursos
                  </Link>
                )}
              </span>
            </Banner>
          ) : null}

          {preview ? (
            <div className="flex min-h-0 flex-col gap-3 border-t border-[var(--border-default)] pt-4 shadow-[var(--linea-surco-arriba)]">
              <div className="flex flex-wrap items-center gap-5">
                <span className="flex items-baseline gap-1.75 text-[13px] text-[var(--text-secondary)]">
                  <span className="font-mono text-[19px] font-medium text-[var(--text-primary)]">
                    {preview.summary.total}
                  </span>
                  filas leídas
                </span>
                <span className="flex items-baseline gap-1.75 text-[13px] text-[var(--text-secondary)]">
                  <span className="font-mono text-[19px] font-medium text-[var(--color-success-fg)]">
                    {preview.summary.valid}
                  </span>
                  se van a crear
                </span>
                <span className="flex items-baseline gap-1.75 text-[13px] text-[var(--text-secondary)]">
                  <span className="font-mono text-[19px] font-medium text-[var(--color-danger-fg)]">
                    {preview.summary.invalid}
                  </span>
                  con errores
                </span>
                <span className="flex items-baseline gap-1.75 text-[13px] text-[var(--text-secondary)]">
                  <span className="font-mono text-[19px] font-medium text-[var(--color-warning-fg)]">
                    {preview.summary.duplicate}
                  </span>
                  ya existen
                </span>
                <Button
                  type="button"
                  className="ml-auto"
                  onClick={() => void confirmar()}
                  disabled={preview.summary.valid === 0 || confirmando}
                  loading={confirmando}
                >
                  <Icono nombre="check" size={15} />
                  Crear {preview.summary.valid}
                </Button>
              </div>

              {/* Nada que crear no es un error del sistema: puede ser un archivo
                  ya importado. Decir cuál de los dos casos es evita que alguien
                  busque un fallo donde no hay ninguno. */}
              {preview.summary.valid === 0 ? (
                <Banner variant="info">
                  Ninguna fila se puede crear.{" "}
                  {preview.summary.duplicate === preview.summary.total
                    ? "Todas existen ya: este archivo probablemente se importó antes."
                    : "Corrige los errores marcados abajo y vuelve a subirlo."}
                </Banner>
              ) : null}

              {preview.unmapped_headers.length ? (
                <div className="flex items-start gap-2 rounded-[var(--radius-md)] border border-[var(--border-strong)] px-3 py-2.25 text-xs text-[var(--text-tertiary)] shadow-[var(--linea-surco-arriba)]">
                  <Icono nombre="info" size={14} className="mt-0.25 flex-none" />
                  <span>
                    Columnas del archivo que no se reconocieron y se van a
                    ignorar:{" "}
                    <span className="text-[var(--text-secondary)]">
                      {preview.unmapped_headers.join(", ")}
                    </span>
                    .
                  </span>
                </div>
              ) : null}

              {preview.truncated ? (
                <Banner variant="warning">
                  El archivo trae más de {preview.max_rows} filas y solo se
                  leyeron las primeras. Divídelo y sube las partes.
                </Banner>
              ) : null}

              <div className="overflow-x-auto rounded-[var(--radius-xl)] border border-[var(--border-default)] shadow-[var(--relieve-isla)]">
                <table className="w-full text-[12.5px]">
                  <thead className="border-b border-[var(--border-default)] bg-[var(--color-subtle)] text-left text-[10.5px] font-semibold uppercase tracking-[0.07em] text-[var(--text-tertiary)] shadow-[var(--linea-surco)]">
                    <tr>
                      <th className="h-8.5 w-16 px-3.5">Fila</th>
                      <th className="h-8.5 px-3.5">Nombre</th>
                      <th className="h-8.5 w-42 px-3.5">Estado</th>
                      <th className="h-8.5 px-3.5">Detalle</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filas.map((f) => (
                      <tr
                        key={f.row}
                        className="h-10 border-b border-[var(--border-subtle)] shadow-[var(--linea-surco)] even:bg-[var(--color-subtle)]/40"
                      >
                        <td className="px-3.5 font-mono text-[12px] text-[var(--text-tertiary)]">
                          {f.row}
                        </td>
                        <td className="overflow-hidden px-3.5 text-ellipsis whitespace-nowrap text-[var(--text-primary)]">
                          {f.name ?? "—"}
                        </td>
                        <td className="px-3.5">
                          <Badge variant={BADGE_ESTADO[f.state]}>
                            {ESTADO_FILA_LABEL[f.state]}
                          </Badge>
                        </td>
                        <td className="overflow-hidden px-3.5 text-ellipsis whitespace-nowrap text-[12px] text-[var(--text-secondary)]">
                          {f.conflicts_with
                            ? `Choca con ${f.conflicts_with}`
                            : null}
                          {f.problems.map((p) => (
                            <span key={p.column} className="block">
                              {p.message}
                            </span>
                          ))}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <p className="text-[11px] text-[var(--text-faint)]">
                Las filas que ya existen <strong>no se actualizan</strong>. Si
                alguien corrigió un dato en la aplicación después de la primera
                carga, resubir el archivo original no lo pisa.
              </p>
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}
