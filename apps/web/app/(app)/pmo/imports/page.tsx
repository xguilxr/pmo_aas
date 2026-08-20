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
import { CheckCircle2, FileDown, Info, Upload } from "lucide-react";

import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { useOrganizacionActiva } from "@/components/organizacion-activa";
import { ApiError } from "@/lib/api";
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

const CLASE_ESTADO: Record<EstadoDeFila, string> = {
  valida: "bg-[var(--color-success-bg)] text-[var(--color-success-fg)]",
  invalida: "bg-[var(--color-danger-bg)] text-[var(--color-danger-fg)]",
  duplicada: "bg-[var(--color-warning-bg)] text-[var(--color-warning-fg)]",
};

/** Primero lo que hay que arreglar. */
const ORDEN: EstadoDeFila[] = ["invalida", "duplicada", "valida"];

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
    <div className="space-y-5 p-6">
      <header>
        <nav className="text-[11px] text-[var(--text-tertiary)]">
          <Link href="/pmo/projects" className="hover:underline">
            Proyectos
          </Link>
          <span className="mx-1">/</span>
          <span>Importar</span>
        </nav>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
          Onboarding masivo
        </h1>
        <p className="mt-1 text-[13px] text-[var(--color-secondary)]">
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
          <section className="space-y-3 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--shadow-sm)]">
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="block text-xs">
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
                <span className="mt-0.5 block text-[11px] text-[var(--color-tertiary)]">
                  Los planes se importan desde el plan de cada proyecto: un
                  código WBS es del proyecto, el «1.2» de uno no es el de otro.
                </span>
              </label>
              <div className="text-xs">
                Organización de destino
                <p className="mt-1 font-medium text-[var(--text-primary)]">
                  {activaObj?.name ?? "—"}
                </p>
                <span className="mt-0.5 block text-[11px] text-[var(--color-tertiary)]">
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
                size="sm"
                variant="secondary"
                onClick={() => descargarPlantilla(false)}
                disabled={!columnas.length}
              >
                <FileDown className="mr-1 h-4 w-4" aria-hidden />
                Plantilla completa
              </Button>
              <Button
                type="button"
                size="sm"
                variant="secondary"
                onClick={() => descargarPlantilla(true)}
                disabled={!obligatorias.length}
                title="Solo las columnas obligatorias — la misma plantilla sin lo opcional"
              >
                <FileDown className="mr-1 h-4 w-4" aria-hidden />
                Plantilla mínima ({obligatorias.length} columnas)
              </Button>
              <input
                type="file"
                accept=".csv,.xlsx"
                onChange={(e) => {
                  setArchivo(e.target.files?.[0] ?? null);
                  setPreview(null);
                  setResultado(null);
                }}
                className="text-xs"
                aria-label="Archivo a importar"
              />
              <Button
                type="button"
                size="sm"
                onClick={() => void subir()}
                disabled={!archivo || !orgId || subiendo}
                loading={subiendo}
              >
                <Upload className="mr-1 h-4 w-4" aria-hidden />
                Validar
              </Button>
            </div>

            <details className="text-xs">
              <summary className="cursor-pointer text-[var(--color-tertiary)]">
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
                    <span className="block text-[11px] text-[var(--color-tertiary)]">
                      {c.help}
                      {c.values.length
                        ? ` Valores: ${c.values.join(", ")}.`
                        : ""}
                    </span>
                  </li>
                ))}
              </ul>
            </details>
          </section>

          {resultado ? (
            <Banner variant="success">
              <span className="flex flex-wrap items-center gap-x-3">
                <CheckCircle2 className="h-4 w-4" aria-hidden />
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
            <section className="space-y-3 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--shadow-sm)]">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap items-center gap-x-5 gap-y-1 text-xs">
                  <span>
                    <strong>{preview.summary.total}</strong> filas leídas
                  </span>
                  <span className="text-[var(--color-success-fg)]">
                    {preview.summary.valid} se van a crear
                  </span>
                  <span className="text-[var(--color-danger-fg)]">
                    {preview.summary.invalid} con errores
                  </span>
                  <span className="text-[var(--color-warning-fg)]">
                    {preview.summary.duplicate} ya existen
                  </span>
                </div>
                <Button
                  type="button"
                  size="sm"
                  onClick={() => void confirmar()}
                  disabled={preview.summary.valid === 0 || confirmando}
                  loading={confirmando}
                >
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
                <p className="flex items-start gap-1.5 text-[11px] text-[var(--color-tertiary)]">
                  <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
                  Columnas del archivo que no se reconocieron y se van a
                  ignorar: {preview.unmapped_headers.join(", ")}.
                </p>
              ) : null}

              {preview.truncated ? (
                <Banner variant="warning">
                  El archivo trae más de {preview.max_rows} filas y solo se
                  leyeron las primeras. Divídelo y sube las partes.
                </Banner>
              ) : null}

              <div className="overflow-x-auto">
                <table className="w-full text-[13px]">
                  <thead className="bg-[var(--color-muted)] text-left text-[11px] uppercase tracking-wide text-[var(--color-tertiary)]">
                    <tr>
                      <th className="px-2 py-1.5">Fila</th>
                      <th className="px-2 py-1.5">Nombre</th>
                      <th className="px-2 py-1.5">Estado</th>
                      <th className="px-2 py-1.5">Detalle</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filas.map((f) => (
                      <tr
                        key={f.row}
                        className="border-t border-[var(--border-subtle)]"
                      >
                        <td className="px-2 py-1.5 text-[11px] text-[var(--color-tertiary)]">
                          {f.row}
                        </td>
                        <td className="px-2 py-1.5">{f.name ?? "—"}</td>
                        <td className="px-2 py-1.5">
                          <span
                            className={`inline-block rounded px-1.5 py-0.5 text-[11px] ${CLASE_ESTADO[f.state]}`}
                          >
                            {ESTADO_FILA_LABEL[f.state]}
                          </span>
                        </td>
                        <td className="px-2 py-1.5 text-[11px] text-[var(--color-secondary)]">
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

              <p className="text-[11px] text-[var(--color-tertiary)]">
                Las filas que ya existen <strong>no se actualizan</strong>. Si
                alguien corrigió un dato en la aplicación después de la primera
                carga, resubir el archivo original no lo pisa.
              </p>
            </section>
          ) : null}
        </>
      )}
    </div>
  );
}
