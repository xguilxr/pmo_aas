"use client";

/**
 * US-212 / D-6 — La línea base del plan.
 *
 * El artboard «Proyecto — Plan» pide «Baseline (capturar / comparar)», marcado
 * como nuevo, y un Gantt «baseline vs actual».
 *
 * ## Sin línea base no se muestra un cero, se dice que no hay
 *
 * Es la trampa que este panel existe para no caer. Un proyecto sin promesa
 * capturada tiene desviación **desconocida**, no cero, y pintarlo en verde es
 * cómo un tablero acaba lleno de semáforos que no significan nada (MCS DAT-12).
 * El estado vacío de aquí no es decorativo: es la respuesta correcta.
 *
 * ## Por qué se muestran dos derivas
 *
 * `slip_days` compara el plan de hoy con lo prometido, y **se puede hacer
 * desaparecer** reescribiendo fechas. `actual_slip_days` compara el cierre real
 * con lo prometido, y no. Un panel que solo mostrara la primera premiaría
 * replanificar, que es lo contrario de lo que una línea base sirve para vigilar.
 *
 * ## Por qué «nuevas» y «retiradas» van aparte de las corridas
 *
 * No son atrasos: son alcance. Un proyecto puede tener cero tareas corridas y
 * treinta nuevas —eso no es un plan que se cumple, es un plan que creció—, y
 * sumarlas en un solo número pierde la conversación que hay que tener.
 */
import { useCallback, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Icono } from "@/components/ui/icono";
import { Input } from "@/components/ui/input";
import { MarcaDeDatos, useLectura } from "@/components/ui/marca-de-datos";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { ApiError } from "@/lib/api";
import { confirmarDestructivo } from "@/lib/confirmar";
import {
  ESTADO_BASELINE_LABEL,
  capturePlanBaseline,
  deletePlanBaseline,
  getBaselineComparison,
  listPlanBaselines,
  type ComparacionBaseline,
  type EstadoBaseline,
  type FilaBaseline,
  type LineaBase,
} from "@/lib/api/tasks";

const FECHA = new Intl.DateTimeFormat("es-MX", {
  day: "2-digit",
  month: "short",
  year: "2-digit",
});

function fecha(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "—" : FECHA.format(d);
}

/**
 * Los días de deriva, con signo y en palabras.
 *
 * `null` es «sin fecha» y no «0 d»: una tarea sin fin no está en fecha, es que
 * no se sabe. Es la misma regla que el backend aplica al calcularla.
 */
function deriva(dias: number | null): { texto: string; clase: string } {
  if (dias === null) return { texto: "sin fecha", clase: "text-[var(--color-tertiary)]" };
  if (dias === 0) return { texto: "en fecha", clase: "text-[var(--color-tertiary)]" };
  if (dias > 0)
    return { texto: `+${dias} d`, clase: "font-medium text-[var(--color-danger-fg)]" };
  return { texto: `${dias} d`, clase: "font-medium text-[var(--color-success-fg)]" };
}

const VARIANTE_ESTADO: Record<
  EstadoBaseline,
  "danger" | "success" | "warning" | "neutral"
> = {
  corrida: "danger",
  adelantada: "success",
  nueva: "warning",
  retirada: "neutral",
  sin_cambio: "neutral",
};

/** El orden de lectura: primero lo que duele. */
const ORDEN: EstadoBaseline[] = [
  "corrida",
  "nueva",
  "retirada",
  "adelantada",
  "sin_cambio",
];

export function LineaBasePlan({
  projectId,
  puedeEditar,
}: {
  projectId: string;
  /** Sin permiso de escritura no se ofrece capturar ni borrar. */
  puedeEditar: boolean;
}) {
  const [lineas, setLineas] = useState<LineaBase[]>([]);
  const [elegida, setElegida] = useState<string>("");
  const [comparacion, setComparacion] = useState<ComparacionBaseline | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [abierta, setAbierta] = useState(false);
  const [capturando, setCapturando] = useState(false);
  const [nombre, setNombre] = useState("");
  const [nota, setNota] = useState("");
  const [verTabla, setVerTabla] = useState(false);
  const leido = useLectura(comparacion);

  const cargar = useCallback(
    async (baselineId?: string) => {
      setCargando(true);
      try {
        const [lista, comp] = await Promise.all([
          listPlanBaselines(projectId),
          getBaselineComparison(projectId, baselineId),
        ]);
        setLineas(lista.baselines);
        setComparacion(comp);
        setElegida(comp.baseline?.id ?? "");
        setError(null);
      } catch (e) {
        setComparacion(null);
        setError(
          e instanceof ApiError
            ? e.message
            : "No se pudo cargar la línea base del plan.",
        );
      } finally {
        setCargando(false);
      }
    },
    [projectId],
  );

  useEffect(() => {
    void cargar();
  }, [cargar]);

  async function capturar() {
    if (!nombre.trim()) return;
    setCapturando(true);
    try {
      const creada = await capturePlanBaseline(projectId, {
        name: nombre.trim(),
        note: nota.trim() || null,
      });
      setAbierta(false);
      setNombre("");
      setNota("");
      await cargar(creada.id);
    } catch (e) {
      setError(
        e instanceof ApiError ? e.message : "No se pudo capturar la línea base.",
      );
    } finally {
      setCapturando(false);
    }
  }

  async function borrar(base: LineaBase) {
    // DIS-04 — nombra el objeto y dice la consecuencia. Lo que quien confirma no
    // puede inferir es que la comparación pasa a hacerse contra otra promesa.
    const ok = confirmarDestructivo({
      objeto: `la línea base «${base.name}» (${base.task_count} tareas, capturada el ${fecha(base.captured_at)})`,
      consecuencia:
        "El plan deja de compararse contra ella. Ninguna tarea cambia, pero la desviación medida contra esta promesa se pierde.",
      reversibilidad: "definitiva",
    });
    if (!ok) return;
    try {
      await deletePlanBaseline(projectId, base.id);
      await cargar();
    } catch (e) {
      setError(
        e instanceof ApiError ? e.message : "No se pudo borrar la línea base.",
      );
    }
  }

  if (cargando) {
    return (
      <span
        aria-hidden
        className="block h-20 animate-pulse rounded-[var(--radius-lg)] bg-[var(--color-muted)]"
      />
    );
  }

  // `r` se estrecha aquí y no en cada uso: un `?? 0` disperso por la plantilla
  // pinta ceros donde no hay dato, que es justo lo que este panel existe para
  // no hacer (DAT-12). Si no hay resumen, se muestra el estado vacío.
  const r = comparacion?.has_baseline ? comparacion.summary : null;
  const base = comparacion?.baseline ?? null;
  const filas = comparacion?.rows ?? [];
  const ordenadas = [...filas].sort(
    (a, b) => ORDEN.indexOf(a.state) - ORDEN.indexOf(b.state),
  );

  return (
    <section
      aria-label="Línea base del plan"
      className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-4 shadow-[var(--relieve-isla)]"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-[13px] font-semibold text-[var(--color-primary)]">
            Línea base
          </h2>
          <p className="text-[11px] text-[var(--color-tertiary)]">
            La promesa contra la que se mide la desviación del plan.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {lineas.length > 1 ? (
            <Select
              value={elegida}
              onChange={(e) => void cargar(e.target.value)}
              aria-label="Contra qué línea base comparar"
              className="max-w-[16rem]"
            >
              {lineas.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name} — {fecha(b.captured_at)}
                </option>
              ))}
            </Select>
          ) : null}
          {puedeEditar ? (
            <Button type="button" size="sm" onClick={() => setAbierta(true)}>
              <Icono nombre="camera" size={15} />
              Capturar
            </Button>
          ) : null}
        </div>
      </div>

      {error ? (
        <Banner variant="danger" className="mt-2">
          {error}
        </Banner>
      ) : null}

      {/* DAT-11 — los números de abajo son del momento de leer, comparados
          contra una foto con fecha. Decir «vivo» sin nombrar contra qué dejaría
          a medias la mitad que sí es una instantánea. */}
      {leido && comparacion?.has_baseline ? (
        <MarcaDeDatos
          periodo="vivo"
          detalle={`contra «${comparacion.baseline?.name ?? "la línea base"}», capturada el ${fecha(comparacion.baseline?.captured_at)}`}
          actualizado={leido}
          className="mt-1"
        />
      ) : null}

      {/* DIS-03 + DAT-12 — el estado vacío no es decorativo: es la respuesta.
          «Sin línea base» ≠ «desviación cero», y este es el único sitio donde
          esa diferencia se puede explicar. */}
      {!r || !base ? (
        <div className="mt-3 flex items-start gap-2 rounded-[var(--radius-md)] border border-dashed border-[var(--border-default)] p-3">
          <Icono
            nombre="camera-off"
            size={16}
            className="mt-0.5 shrink-0 text-[var(--color-tertiary)]"
          />
          <p className="text-[13px] text-[var(--color-secondary)]">
            Este plan no tiene línea base. Mientras no la tenga, su desviación no
            es cero: es <strong>desconocida</strong>, porque no hay ninguna fecha
            prometida contra la que comparar.
            {puedeEditar
              ? " Captúrala cuando el plan quede acordado."
              : " La captura quien pueda editar el plan."}
          </p>
        </div>
      ) : (
        <>
          <div className="mt-3 grid grid-cols-2 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--relieve-isla)] sm:grid-cols-4 [&>*+*]:border-l [&>*+*]:border-[var(--border-default)]">
            <Dato
              etiqueta="Fin prometido"
              valor={fecha(r.baseline_finish)}
              pie={base.name}
            />
            <Dato
              etiqueta="Fin del plan"
              valor={fecha(r.plan_finish)}
              pie={
                r.project_slip_days === null
                  ? "sin fechas para comparar"
                  : r.project_slip_days === 0
                    ? "sin corrimiento"
                    : `${deriva(r.project_slip_days).texto} contra la base`
              }
              clasePie={deriva(r.project_slip_days).clase}
            />
            <Dato
              etiqueta="Tareas corridas"
              valor={String(r.slipped)}
              pie={
                r.worst_slip_days
                  ? `la peor, +${r.worst_slip_days} d`
                  : "ninguna se movió"
              }
            />
            <Dato
              etiqueta="Alcance"
              valor={`+${r.added} / −${r.removed}`}
              pie="nuevas / retiradas desde la base"
            />
          </div>

          <p className="mt-2 text-[11px] text-[var(--color-tertiary)]">
            Capturada el {fecha(base.captured_at)}
            {base.captured_by_name ? ` por ${base.captured_by_name}` : ""}
            {` · ${base.task_count} tareas`}
            {base.note ? ` · ${base.note}` : ""}
            {comparacion && comparacion.baseline_count > 1
              ? ` · ${comparacion.baseline_count} capturas en total`
              : ""}
          </p>

          <div className="mt-2 flex flex-wrap items-center gap-2">
            <Button
              type="button"
              size="sm"
              variant="secondary"
              onClick={() => setVerTabla((v) => !v)}
              aria-expanded={verTabla}
            >
              <Icono
                nombre="chevron-down"
                size={14}
                className={verTabla ? "rotate-180 transition-transform" : "transition-transform"}
              />
              {verTabla ? "Ocultar comparación" : `Comparar tarea por tarea (${filas.length})`}
            </Button>
            {puedeEditar ? (
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={() => void borrar(base)}
                aria-label="Borrar esta línea base"
              >
                <Icono nombre="bin" size={14} />
              </Button>
            ) : null}
          </div>

          {verTabla ? (
            filas.length === 0 ? (
              <p className="mt-3 text-[13px] text-[var(--color-tertiary)]">
                Ni la línea base ni el plan tienen tareas todavía.
              </p>
            ) : (
              <div className="mt-3 overflow-x-auto">
                <table className="w-full table-fixed text-[13px]">
                  <thead className="border-b border-[var(--border-default)] bg-[var(--color-subtle)] text-left text-[10.5px] font-semibold uppercase tracking-[0.07em] text-[var(--color-tertiary)] shadow-[var(--linea-surco)]">
                    <tr>
                      <th className="h-8.5 w-[9%] px-2">WBS</th>
                      <th className="h-8.5 w-[29%] px-2">Tarea</th>
                      <th className="h-8.5 w-[13%] px-2">Fin base</th>
                      <th className="h-8.5 w-[13%] px-2">Fin plan</th>
                      <th className="h-8.5 w-[14%] px-2 pr-3.5 text-right">Deriva plan</th>
                      <th className="h-8.5 w-[14%] px-2 pr-3.5 text-right">Deriva real</th>
                      <th className="h-8.5 w-[8%] px-2">Estado</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ordenadas.map((f) => (
                      <Fila key={`${f.state}-${f.task_id}`} f={f} />
                    ))}
                  </tbody>
                </table>
                <p className="mt-2 text-[11px] text-[var(--color-tertiary)]">
                  La <strong>deriva del plan</strong> se puede hacer desaparecer
                  reescribiendo fechas; la <strong>real</strong> —el cierre contra
                  lo prometido— no. Por eso van las dos.
                </p>
              </div>
            )
          ) : null}
        </>
      )}

      <Modal
        open={abierta}
        onClose={() => setAbierta(false)}
        title="Capturar línea base del plan"
      >
        <div className="space-y-3">
          <p className="text-[13px] text-[var(--color-secondary)]">
            Copia las fechas del plan de hoy como promesa. No sustituye a las
            capturas anteriores: se apilan, y el plan se puede comparar contra
            cualquiera de ellas.
          </p>
          <label className="block text-xs">
            Nombre *
            <Input
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              placeholder="Ej. Firmada con el cliente"
              maxLength={200}
            />
            <span className="mt-0.5 block text-[11px] text-[var(--color-tertiary)]">
              «Línea base 3» no le dice a nadie contra qué está comparando.
            </span>
          </label>
          <label className="block text-xs">
            Por qué se captura
            <Input
              value={nota}
              onChange={(e) => setNota(e.target.value)}
              placeholder="Ej. Replan aprobado en comité del 12-ago"
              maxLength={2000}
            />
            <span className="mt-0.5 block text-[11px] text-[var(--color-tertiary)]">
              Es lo que contesta «¿y esto por qué se movió?» seis meses después.
            </span>
          </label>
          <div className="flex justify-end gap-2 pt-1">
            <Button variant="secondary" onClick={() => setAbierta(false)}>
              Cancelar
            </Button>
            <Button
              onClick={() => void capturar()}
              loading={capturando}
              disabled={!nombre.trim()}
            >
              Capturar
            </Button>
          </div>
        </div>
      </Modal>
    </section>
  );
}

function Dato({
  etiqueta,
  valor,
  pie,
  clasePie,
}: {
  etiqueta: string;
  valor: string;
  pie: string;
  clasePie?: string;
}) {
  return (
    <div className="flex flex-col gap-1 p-4">
      <div className="text-[10.5px] font-semibold uppercase tracking-[0.07em] text-[var(--color-tertiary)]">
        {etiqueta}
      </div>
      <div className="font-mono text-[15px] font-semibold tabular-nums text-[var(--color-primary)]">
        {valor}
      </div>
      <div
        className={`text-[11px] ${clasePie || "text-[var(--color-tertiary)]"}`}
      >
        {pie}
      </div>
    </div>
  );
}

function Fila({ f }: { f: FilaBaseline }) {
  const plan = deriva(f.slip_days);
  const real = deriva(f.actual_slip_days);
  return (
    <tr className="h-10.5 border-b border-[var(--border-subtle)] shadow-[var(--linea-surco)] hover:bg-[var(--color-subtle)]">
      <td className="overflow-hidden text-ellipsis whitespace-nowrap px-2 text-[11px] text-[var(--color-tertiary)]">
        {f.wbs_code ?? "—"}
      </td>
      <td className="overflow-hidden text-ellipsis whitespace-nowrap px-2 text-[var(--color-primary)]">
        {f.name}
        {f.is_milestone ? (
          <span className="ml-1 text-[11px] text-[var(--color-tertiary)]">
            (hito)
          </span>
        ) : null}
      </td>
      <td className="px-2 font-mono text-[12px] text-[var(--color-secondary)]">
        {fecha(f.baseline_end)}
      </td>
      <td className="px-2 font-mono text-[12px] text-[var(--color-secondary)]">
        {fecha(f.plan_end)}
      </td>
      <td className={`px-2 pr-3.5 text-right font-mono text-[12px] ${plan.clase}`}>
        {plan.texto}
      </td>
      <td className={`px-2 pr-3.5 text-right font-mono text-[12px] ${real.clase}`}>
        {f.actual_slip_days === null ? "sin cerrar" : real.texto}
      </td>
      <td className="px-2">
        <Badge variant={VARIANTE_ESTADO[f.state]}>
          {ESTADO_BASELINE_LABEL[f.state]}
        </Badge>
      </td>
    </tr>
  );
}
