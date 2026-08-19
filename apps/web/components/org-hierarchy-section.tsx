"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import {
  Briefcase,
  ChevronRight,
  ExternalLink,
  Pencil,
  Plus,
  PowerOff,
  Workflow,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { MarcaDeDatos, useLectura } from "@/components/ui/marca-de-datos";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api";
import {
  createPortfolio,
  createProgram,
  deletePortfolio,
  deleteProgram,
  hardDeletePortfolio,
  hardDeleteProgram,
  listPortfolios,
  listPrograms,
  previewHardDeletePortfolio,
  previewHardDeleteProgram,
  updatePortfolio,
  updateProgram,
  type Portfolio,
  type Program,
} from "@/lib/api/organizations";
import { HardDeleteButton } from "@/components/hard-delete-button";
import { cn } from "@/lib/cn";

/**
 * US-200 / ADR-037 — la jerarquía de la organización es Portafolio ⊃ Programa.
 *
 * Reemplaza a la sección de unidades de negocio y departamentos, que modelaba el
 * organigrama del cliente y nunca se usó. El portafolio agrupa por **decisión de
 * inversión**; el programa, por **coordinación**.
 *
 * Los programas se cargan al expandir y no todos de golpe: una organización con
 * veinte portafolios pediría veinte listas para pintar una pantalla en la que
 * casi todo está colapsado.
 */

type ProgramasPorPortafolio = Record<string, Program[] | "loading" | "error">;

function usePortafolios(orgId: string) {
  const [portafolios, setPortafolios] = useState<Portfolio[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [programas, setProgramas] = useState<ProgramasPorPortafolio>({});

  async function refrescarPortafolios() {
    setLoading(true);
    setError(null);
    try {
      setPortafolios(await listPortfolios(orgId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar portafolios");
    } finally {
      setLoading(false);
    }
  }

  async function refrescarProgramas(portfolioId: string) {
    setProgramas((s) => ({ ...s, [portfolioId]: "loading" }));
    try {
      const filas = await listPrograms({
        organization_id: orgId,
        portfolio_id: portfolioId,
      });
      setProgramas((s) => ({ ...s, [portfolioId]: filas }));
    } catch {
      setProgramas((s) => ({ ...s, [portfolioId]: "error" }));
    }
  }

  useEffect(() => {
    void refrescarPortafolios();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orgId]);

  return {
    portafolios,
    loading,
    error,
    programas,
    refrescarPortafolios,
    refrescarProgramas,
  };
}

type EstadoFicha = { name: string; code: string; description: string };

const VACIO: EstadoFicha = { name: "", code: "", description: "" };

export function OrgHierarchySection({ orgId }: { orgId: string }) {
  const {
    portafolios,
    loading,
    error,
    programas,
    refrescarPortafolios,
    refrescarProgramas,
  } = usePortafolios(orgId);

  const [abiertos, setAbiertos] = useState<Set<string>>(new Set());

  const [modalPortafolio, setModalPortafolio] = useState<
    { mode: "create" } | { mode: "edit"; portafolio: Portfolio } | null
  >(null);
  const [modalPrograma, setModalPrograma] = useState<
    | { mode: "create"; portfolioId: string }
    | { mode: "edit"; programa: Program }
    | null
  >(null);
  const [confirmarPortafolio, setConfirmarPortafolio] = useState<Portfolio | null>(null);
  const [confirmarPrograma, setConfirmarPrograma] = useState<Program | null>(null);

  // MCS DAT-11 — los conteos de programas y proyectos son derivados, se
  // calculan al leer. «Vivo» no es una excusa para no declararlo: es
  // precisamente lo que hay que declarar, porque el número de esta pantalla
  // envejece mientras alguien la deja abierta.
  const leido = useLectura(portafolios);

  function alternar(portfolioId: string) {
    setAbiertos((prev) => {
      const siguiente = new Set(prev);
      if (siguiente.has(portfolioId)) {
        siguiente.delete(portfolioId);
      } else {
        siguiente.add(portfolioId);
        if (!programas[portfolioId]) void refrescarProgramas(portfolioId);
      }
      return siguiente;
    });
  }

  async function archivarPortafolio(portafolio: Portfolio, force: boolean) {
    await deletePortfolio(portafolio.id, force);
    setConfirmarPortafolio(null);
    await refrescarPortafolios();
    if (force) await refrescarProgramas(portafolio.id);
  }

  async function archivarPrograma(programa: Program) {
    await deleteProgram(programa.id);
    setConfirmarPrograma(null);
    await refrescarProgramas(programa.portfolio_id);
    // El conteo de programas del portafolio es derivado: se recarga con él.
    await refrescarPortafolios();
  }

  return (
    <section className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] shadow-[var(--shadow-sm)]">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--border-default)] px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold text-[var(--color-primary)]">
            Jerarquía: portafolios y programas
          </h2>
          <p className="text-xs text-[var(--color-tertiary)]">
            El portafolio agrupa por decisión de inversión; el programa, por
            coordinación. Los proyectos cuelgan de uno, del otro, o de ninguno.
          </p>
        </div>
        <div className="flex gap-2">
          <Link href={`/pmo/projects?organization_id=${orgId}`}>
            <Button variant="secondary" size="sm">
              <ExternalLink className="h-4 w-4" aria-hidden />
              Ver proyectos
            </Button>
          </Link>
          <Button size="sm" onClick={() => setModalPortafolio({ mode: "create" })}>
            <Plus className="h-4 w-4" aria-hidden /> Nuevo portafolio
          </Button>
        </div>
        {leido ? (
          <MarcaDeDatos periodo="vivo" actualizado={leido} className="basis-full" />
        ) : null}
      </header>

      {error ? (
        <div className="p-4">
          <Banner variant="danger">{error}</Banner>
        </div>
      ) : null}

      {loading ? (
        <div className="space-y-2 p-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      ) : portafolios.length === 0 ? (
        <div className="p-8 text-center text-sm text-[var(--color-tertiary)]">
          Aún no hay portafolios. Crea el primero con «Nuevo portafolio».
        </div>
      ) : (
        <ul className="divide-y divide-[var(--border-subtle)]">
          {portafolios.map((portafolio) => {
            const abierto = abiertos.has(portafolio.id);
            const susProgramas = programas[portafolio.id];
            return (
              <li key={portafolio.id}>
                <div className="flex items-center gap-2 px-3 py-2.5 hover:bg-[var(--color-subtle)]">
                  <button
                    type="button"
                    onClick={() => alternar(portafolio.id)}
                    aria-expanded={abierto}
                    aria-label={abierto ? "Colapsar" : "Expandir"}
                    className="inline-flex h-6 w-6 flex-none items-center justify-center text-[var(--color-tertiary)]"
                  >
                    <ChevronRight
                      className={cn(
                        "h-4 w-4 transition-transform",
                        abierto && "rotate-90",
                      )}
                      aria-hidden
                    />
                  </button>
                  <Briefcase
                    className="h-4 w-4 flex-none text-[var(--color-tertiary)]"
                    aria-hidden
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="truncate text-sm font-medium text-[var(--color-primary)]">
                        {portafolio.name}
                      </span>
                      {portafolio.code ? (
                        <Badge variant="neutral">{portafolio.code}</Badge>
                      ) : null}
                      {!portafolio.is_active ? (
                        <Badge variant="danger">Inactivo</Badge>
                      ) : null}
                      <span className="text-xs text-[var(--color-tertiary)]">
                        {portafolio.program_count} programa
                        {portafolio.program_count === 1 ? "" : "s"} ·{" "}
                        {portafolio.active_project_count} proyecto
                        {portafolio.active_project_count === 1 ? "" : "s"} activo
                        {portafolio.active_project_count === 1 ? "" : "s"}
                      </span>
                    </div>
                    {portafolio.description ? (
                      <div className="truncate text-xs text-[var(--color-tertiary)]">
                        {portafolio.description}
                      </div>
                    ) : null}
                  </div>
                  <div className="flex gap-1">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() =>
                        setModalPrograma({
                          mode: "create",
                          portfolioId: portafolio.id,
                        })
                      }
                      title="Nuevo programa"
                      aria-label={`Nuevo programa en ${portafolio.name}`}
                    >
                      <Plus className="h-4 w-4" aria-hidden />
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setModalPortafolio({ mode: "edit", portafolio })}
                      title="Editar"
                      aria-label={`Editar ${portafolio.name}`}
                    >
                      <Pencil className="h-4 w-4" aria-hidden />
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setConfirmarPortafolio(portafolio)}
                      title="Archivar"
                      aria-label={`Archivar ${portafolio.name}`}
                    >
                      <PowerOff className="h-4 w-4" aria-hidden />
                      <span className="ml-1 text-xs">Archivar</span>
                    </Button>
                    {!portafolio.is_active ? (
                      <HardDeleteButton
                        preview={() => previewHardDeletePortfolio(portafolio.id)}
                        hardDelete={(slug) => hardDeletePortfolio(portafolio.id, slug)}
                        onDeleted={() => void refrescarPortafolios()}
                        entityLabel="Portafolio"
                        triggerVariant="ghost"
                        triggerLabel="Eliminar"
                      />
                    ) : null}
                  </div>
                </div>

                {abierto ? (
                  <ul className="divide-y divide-[var(--border-subtle)] bg-[var(--color-app)]">
                    {susProgramas === "loading" ? (
                      <li className="px-10 py-2 text-xs text-[var(--color-tertiary)]">
                        Cargando programas…
                      </li>
                    ) : susProgramas === "error" ? (
                      <li className="px-10 py-2 text-xs text-[var(--color-danger-fg)]">
                        Error al cargar programas.
                      </li>
                    ) : !susProgramas || susProgramas.length === 0 ? (
                      <li className="px-10 py-2 text-xs italic text-[var(--color-tertiary)]">
                        Sin programas. Los proyectos pueden colgar directo del
                        portafolio; usa «+» si quieres coordinarlos en uno.
                      </li>
                    ) : (
                      susProgramas.map((programa) => (
                        <li
                          key={programa.id}
                          className="flex items-center gap-2 py-2 pl-10 pr-3 hover:bg-[var(--color-subtle)]"
                        >
                          <Workflow
                            className="h-4 w-4 flex-none text-[var(--color-tertiary)]"
                            aria-hidden
                          />
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2">
                              <Link
                                href={`/pmo/programs/${programa.id}`}
                                className="truncate text-sm text-[var(--color-primary)] hover:underline"
                              >
                                {programa.name}
                              </Link>
                              {!programa.is_active ? (
                                <Badge variant="danger">Inactivo</Badge>
                              ) : null}
                            </div>
                            {programa.description ? (
                              <div className="truncate text-xs text-[var(--color-tertiary)]">
                                {programa.description}
                              </div>
                            ) : null}
                          </div>
                          <div className="flex gap-1">
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => setModalPrograma({ mode: "edit", programa })}
                              title="Editar"
                              aria-label={`Editar ${programa.name}`}
                            >
                              <Pencil className="h-4 w-4" aria-hidden />
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => setConfirmarPrograma(programa)}
                              title="Archivar"
                              aria-label={`Archivar ${programa.name}`}
                            >
                              <PowerOff className="h-4 w-4" aria-hidden />
                              <span className="ml-1 text-xs">Archivar</span>
                            </Button>
                            {!programa.is_active ? (
                              <HardDeleteButton
                                preview={() => previewHardDeleteProgram(programa.id)}
                                hardDelete={(slug) => hardDeleteProgram(programa.id, slug)}
                                onDeleted={() => {
                                  void refrescarProgramas(programa.portfolio_id);
                                  void refrescarPortafolios();
                                }}
                                entityLabel="Programa"
                                triggerVariant="ghost"
                                triggerLabel="Eliminar"
                              />
                            ) : null}
                          </div>
                        </li>
                      ))
                    )}
                  </ul>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}

      <FichaModal
        title={
          modalPortafolio?.mode === "edit" ? "Editar portafolio" : "Nuevo portafolio"
        }
        conCodigo
        open={modalPortafolio !== null}
        onClose={() => setModalPortafolio(null)}
        initial={
          modalPortafolio?.mode === "edit"
            ? {
                name: modalPortafolio.portafolio.name,
                code: modalPortafolio.portafolio.code ?? "",
                description: modalPortafolio.portafolio.description ?? "",
              }
            : VACIO
        }
        onSubmit={async (estado) => {
          const cuerpo = {
            name: estado.name,
            code: estado.code || null,
            description: estado.description || null,
          };
          if (modalPortafolio?.mode === "edit") {
            await updatePortfolio(modalPortafolio.portafolio.id, cuerpo);
          } else {
            await createPortfolio(orgId, cuerpo);
          }
          setModalPortafolio(null);
          await refrescarPortafolios();
        }}
      />

      <FichaModal
        title={modalPrograma?.mode === "edit" ? "Editar programa" : "Nuevo programa"}
        open={modalPrograma !== null}
        onClose={() => setModalPrograma(null)}
        initial={
          modalPrograma?.mode === "edit"
            ? {
                name: modalPrograma.programa.name,
                code: "",
                description: modalPrograma.programa.description ?? "",
              }
            : VACIO
        }
        onSubmit={async (estado) => {
          if (modalPrograma?.mode === "edit") {
            await updateProgram(modalPrograma.programa.id, {
              name: estado.name,
              description: estado.description || null,
            });
            const portfolioId = modalPrograma.programa.portfolio_id;
            setModalPrograma(null);
            await refrescarProgramas(portfolioId);
          } else if (modalPrograma?.mode === "create") {
            const portfolioId = modalPrograma.portfolioId;
            await createProgram({
              name: estado.name,
              organization_id: orgId,
              portfolio_id: portfolioId,
              description: estado.description || null,
            });
            setModalPrograma(null);
            await refrescarProgramas(portfolioId);
            await refrescarPortafolios();
            setAbiertos((prev) => new Set(prev).add(portfolioId));
          }
        }}
      />

      <ConfirmarArchivadoModal
        target={confirmarPortafolio}
        label="portafolio"
        conCascada
        onClose={() => setConfirmarPortafolio(null)}
        onConfirm={async (force) => {
          if (confirmarPortafolio) await archivarPortafolio(confirmarPortafolio, force);
        }}
      />

      <ConfirmarArchivadoModal
        target={confirmarPrograma}
        label="programa"
        onClose={() => setConfirmarPrograma(null)}
        onConfirm={async () => {
          if (confirmarPrograma) await archivarPrograma(confirmarPrograma);
        }}
      />
    </section>
  );
}

function FichaModal({
  open,
  onClose,
  title,
  initial,
  conCodigo = false,
  onSubmit,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  initial: EstadoFicha;
  /** El código corto solo lo tiene el portafolio (para reportes y filtros). */
  conCodigo?: boolean;
  onSubmit: (estado: EstadoFicha) => Promise<void>;
}) {
  const [estado, setEstado] = useState(initial);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setEstado(initial);
      setError(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  async function enviar(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (estado.name.trim().length < 2) {
      setError("El nombre es obligatorio (mínimo 2 caracteres)");
      return;
    }
    setGuardando(true);
    setError(null);
    try {
      await onSubmit({
        name: estado.name.trim(),
        code: estado.code.trim(),
        description: estado.description.trim(),
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al guardar");
    } finally {
      setGuardando(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={title}>
      <form onSubmit={enviar} className="space-y-3">
        <div>
          <label className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]">
            Nombre
          </label>
          <Input
            value={estado.name}
            onChange={(e) => setEstado({ ...estado, name: e.target.value })}
            minLength={2}
            maxLength={200}
            required
          />
        </div>
        {conCodigo ? (
          <div>
            <label className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]">
              Código
            </label>
            <Input
              value={estado.code}
              onChange={(e) => setEstado({ ...estado, code: e.target.value })}
              maxLength={32}
              placeholder="Opcional — para reportes y tablas estrechas (ej. TRX26)"
            />
          </div>
        ) : null}
        <div>
          <label className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]">
            Descripción
          </label>
          <Textarea
            rows={3}
            value={estado.description}
            onChange={(e) => setEstado({ ...estado, description: e.target.value })}
          />
        </div>
        {error ? <Banner variant="danger">{error}</Banner> : null}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" loading={guardando}>
            Guardar
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function ConfirmarArchivadoModal<T extends { name: string }>({
  target,
  label,
  conCascada = false,
  onClose,
  onConfirm,
}: {
  target: T | null;
  label: string;
  /** Solo el portafolio tiene hijos que archivar en cascada. */
  conCascada?: boolean;
  onClose: () => void;
  onConfirm: (force: boolean) => Promise<void> | void;
}) {
  const [cargando, setCargando] = useState(false);
  const [force, setForce] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (target) {
      setForce(false);
      setError(null);
    }
  }, [target]);

  async function ejecutar() {
    if (!target) return;
    setCargando(true);
    setError(null);
    try {
      await onConfirm(force);
    } catch (err) {
      if (err instanceof ApiError && err.code === "BUSINESS_RULE") {
        setError(`${err.message} Marca «Forzar» para archivarlos en cascada.`);
      } else {
        setError(err instanceof ApiError ? err.message : "Error al archivar");
      }
    } finally {
      setCargando(false);
    }
  }

  return (
    <Modal open={target !== null} onClose={onClose} title={`Archivar ${label}`}>
      <p className="text-sm text-[var(--color-secondary)]">
        ¿Archivar <strong>{target?.name}</strong>? Queda inactivo y sale de las
        listas; nada se borra. El borrado permanente es un segundo paso, y pide
        escribir el nombre.
      </p>
      {conCascada ? (
        <label className="mt-3 inline-flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={force}
            onChange={(e) => setForce(e.target.checked)}
          />
          Forzar (archiva también sus programas)
        </label>
      ) : null}
      {error ? (
        <div className="mt-3">
          <Banner variant="danger">{error}</Banner>
        </div>
      ) : null}
      <div className="mt-4 flex justify-end gap-2">
        <Button variant="ghost" onClick={onClose}>
          Cancelar
        </Button>
        <Button variant="danger" loading={cargando} onClick={ejecutar}>
          Archivar
        </Button>
      </div>
    </Modal>
  );
}
