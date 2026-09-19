"use client";

/**
 * US-287 — Admin › Catálogos: los tipos y las fases de proyecto del inquilino.
 *
 * La pantalla de lo que US-285 y US-286 dejaron debajo. Dos pestañas, una por
 * catálogo, porque son dos listas que no se comparan entre sí.
 *
 * ## Qué se puede y qué no, y por qué se ve
 *
 * La **clave** se muestra y no se edita. Es lo que queda guardado en cada
 * proyecto; renombrarla dejaría huérfano a todo lo que la referencia. Se
 * muestra igualmente porque es lo que sale en un export y en un filtro de URL:
 * esconderla haría imposible relacionar lo que se ve aquí con lo que se ve
 * allá.
 *
 * Las **fases** se renombran, se reordenan y se desactivan, pero no se agregan.
 * El botón no está: una fase nueva no tendría transiciones ni contaría en los
 * KPIs. En vez de dejar el botón y explicar el 422 después, la pestaña lo dice
 * antes.
 *
 * ## Reordenar guarda al soltar, no al final
 *
 * Sin botón de guardar. Cada movimiento manda el orden completo —que es lo que
 * el backend pide— y repinta con lo que devuelve. Un «guardar» al final
 * invitaría a cerrar la pestaña con el orden a medias.
 */
import { useCallback, useEffect, useState } from "react";

import { Banner } from "@/components/ui/banner";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { Icono } from "@/components/ui/icono";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import {
  CATALOGO_LABEL,
  CATALOGOS,
  crearValor,
  editarValor,
  listarCatalogo,
  reordenarCatalogo,
  type Catalogo,
  type ValorDeCatalogo,
} from "@/lib/api/catalogos";
import { cn } from "@/lib/cn";
import { invalidarCatalogo } from "@/lib/hooks/use-catalogo";

export default function CatalogosPage() {
  const [tab, setTab] = useState<Catalogo>("tipo_proyecto");

  return (
    <div className="space-y-4">
      <Breadcrumb items={[{ href: "/admin", label: "Admin" }, { label: "Catálogos" }]} />
      <header className="flex flex-col gap-1.5">
        <div className="flex items-center gap-2.25">
          <Icono nombre="list-check" size={20} className="text-[var(--text-primary)]" />
          <h1 className="text-2xl font-semibold tracking-[-0.02em] text-[var(--text-primary)]">
            Catálogos
          </h1>
        </div>
        <p className="text-sm text-[var(--text-secondary)]">
          Los valores con los que tu organización clasifica sus proyectos. Lo que
          cambies aquí sale en los formularios, los filtros y los gráficos.
        </p>
      </header>

      <div
        role="tablist"
        aria-label="Catálogos"
        className="flex items-center gap-1 border-b border-[var(--border-default)] shadow-[var(--linea-surco)]"
      >
        {CATALOGOS.map((c) => {
          const active = tab === c;
          return (
            <button
              key={c}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => setTab(c)}
              className={cn(
                "inline-flex h-9 items-center gap-1.5 border-b-2 px-2.5 text-[13px] transition-colors",
                active
                  ? "border-[var(--text-primary)] font-semibold text-[var(--text-primary)]"
                  : "border-transparent font-medium text-[var(--text-tertiary)] hover:text-[var(--text-primary)]",
              )}
            >
              {CATALOGO_LABEL[c]}
            </button>
          );
        })}
      </div>

      <PanelDeCatalogo key={tab} catalogo={tab} />
    </div>
  );
}

function PanelDeCatalogo({ catalogo }: { catalogo: Catalogo }) {
  const [valores, setValores] = useState<ValorDeCatalogo[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [creando, setCreando] = useState(false);
  const [editando, setEditando] = useState<ValorDeCatalogo | null>(null);

  // Las fases no se agregan: no tendrían transiciones ni contarían en los KPIs.
  const seAgrega = catalogo === "tipo_proyecto";

  const refrescar = useCallback(async () => {
    setError(null);
    // US-288 — el resto de las pantallas lee este catálogo desde una caché de
    // módulo. Esta es la única que lo escribe, así que es la única que tiene
    // que tirarla: sin esto, el formulario de alta seguiría ofreciendo un tipo
    // que acaban de retirar hasta la siguiente recarga completa.
    invalidarCatalogo(catalogo);
    try {
      // Con los inactivos: esta es la pantalla donde se vuelven a activar, y
      // sin ellos un valor retirado desaparecería sin forma de recuperarlo.
      setValores(await listarCatalogo(catalogo, { incluirInactivos: true }));
    } catch (e) {
      setError(
        e instanceof ApiError ? e.message : "No se pudo cargar el catálogo.",
      );
      setValores([]);
    }
  }, [catalogo]);

  useEffect(() => {
    void refrescar();
  }, [refrescar]);

  async function mover(indice: number, direccion: -1 | 1) {
    if (!valores) return;
    const destino = indice + direccion;
    if (destino < 0 || destino >= valores.length) return;
    const claves = valores.map((v) => v.clave);
    [claves[indice], claves[destino]] = [claves[destino], claves[indice]];
    setOcupado(true);
    setError(null);
    try {
      setValores(await reordenarCatalogo(catalogo, claves));
    } catch (e) {
      setError(
        e instanceof ApiError ? e.message : "No se pudo guardar el orden.",
      );
      await refrescar();
    } finally {
      setOcupado(false);
    }
  }

  async function alternarActivo(valor: ValorDeCatalogo) {
    setOcupado(true);
    setError(null);
    try {
      await editarValor(catalogo, valor.id, { activo: !valor.activo });
      setAviso(
        valor.activo
          ? `«${valor.etiqueta}» ya no se ofrece. Los proyectos que lo tienen lo conservan.`
          : `«${valor.etiqueta}» vuelve a estar disponible.`,
      );
      await refrescar();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo cambiar el estado.");
    } finally {
      setOcupado(false);
    }
  }

  if (valores === null) return <Skeleton className="h-64 w-full" />;

  return (
    <div className="space-y-3">
      {error ? <Banner variant="danger">{error}</Banner> : null}
      {aviso ? <Banner variant="success">{aviso}</Banner> : null}

      <div className="flex items-center justify-between gap-2">
        <p className="text-sm text-[var(--text-tertiary)]">
          {seAgrega
            ? "Agrega los tuyos, renómbralos y ordénalos. El orden es el de los desplegables."
            : "Renombra y ordena las fases. Agregar una nueva llega cuando traiga su ciclo de vida: hoy no tendría transiciones ni contaría en los indicadores."}
        </p>
        {seAgrega ? (
          <Button onClick={() => setCreando(true)} disabled={ocupado}>
            <Icono nombre="plus" size={15} />
            Agregar tipo
          </Button>
        ) : null}
      </div>

      {valores.length === 0 ? (
        <p className="rounded-[var(--radius-xl)] border border-[var(--border-default)] p-6 text-center text-sm text-[var(--text-tertiary)]">
          Este catálogo está vacío. Sin valores no se puede dar de alta un
          proyecto.
        </p>
      ) : (
        <div className="overflow-hidden rounded-[var(--radius-xl)] border border-[var(--border-default)]">
          <table className="w-full text-sm">
            <thead className="bg-[var(--color-subtle)]">
              <tr className="h-[34px] text-left text-[12px] text-[var(--text-secondary)]">
                <th className="px-3 font-medium">Nombre</th>
                <th className="px-3 font-medium">Clave</th>
                <th className="px-3 font-medium">Estado</th>
                <th className="px-3 text-right font-medium">Orden</th>
                <th className="px-3 text-right font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {valores.map((v, i) => (
                <tr
                  key={v.id}
                  className="h-[42px] border-t border-[var(--border-default)]"
                >
                  <td className="px-3 text-[var(--text-primary)]">{v.etiqueta}</td>
                  <td className="px-3 font-mono text-[12px] text-[var(--text-tertiary)]">
                    {v.clave}
                  </td>
                  <td className="px-3">
                    {v.activo ? (
                      <span className="text-[var(--color-success-fg)]">Activo</span>
                    ) : (
                      <span className="text-[var(--text-tertiary)]">Retirado</span>
                    )}
                  </td>
                  <td className="px-3">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        type="button"
                        aria-label={`Subir ${v.etiqueta}`}
                        disabled={ocupado || i === 0}
                        onClick={() => mover(i, -1)}
                        className="rounded-[var(--radius-md)] p-1 text-[var(--text-tertiary)] hover:text-[var(--text-primary)] disabled:opacity-40"
                      >
                        <Icono nombre="arrow-up" size={14} />
                      </button>
                      <button
                        type="button"
                        aria-label={`Bajar ${v.etiqueta}`}
                        disabled={ocupado || i === valores.length - 1}
                        onClick={() => mover(i, 1)}
                        className="rounded-[var(--radius-md)] p-1 text-[var(--text-tertiary)] hover:text-[var(--text-primary)] disabled:opacity-40"
                      >
                        <Icono nombre="arrow-down" size={14} />
                      </button>
                    </div>
                  </td>
                  <td className="px-3">
                    <div className="flex items-center justify-end gap-2">
                      <Button
                        variant="ghost"
                        onClick={() => setEditando(v)}
                        disabled={ocupado}
                      >
                        Editar
                      </Button>
                      <Button
                        variant="ghost"
                        onClick={() => alternarActivo(v)}
                        disabled={ocupado}
                      >
                        {v.activo ? "Retirar" : "Reactivar"}
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="text-[12px] text-[var(--text-tertiary)]">
        La clave es lo que queda guardado en cada proyecto y no se puede cambiar:
        renombrarla dejaría sin referencia a los que ya la tienen. Lo que se
        edita es el nombre.
      </p>

      {creando ? (
        <ModalDeValor
          titulo={`Agregar a ${CATALOGO_LABEL[catalogo].toLowerCase()}`}
          onClose={() => setCreando(false)}
          onGuardar={async (etiqueta) => {
            await crearValor(catalogo, { etiqueta });
            setCreando(false);
            setAviso(`«${etiqueta}» ya está disponible en los formularios.`);
            await refrescar();
          }}
        />
      ) : null}

      {editando ? (
        <ModalDeValor
          titulo="Cambiar el nombre"
          inicial={editando.etiqueta}
          clave={editando.clave}
          onClose={() => setEditando(null)}
          onGuardar={async (etiqueta) => {
            await editarValor(catalogo, editando.id, { etiqueta });
            setEditando(null);
            await refrescar();
          }}
        />
      ) : null}
    </div>
  );
}

function ModalDeValor({
  titulo,
  inicial = "",
  clave,
  onClose,
  onGuardar,
}: {
  titulo: string;
  inicial?: string;
  /** Solo al editar: se muestra para que se vea qué NO cambia. */
  clave?: string;
  onClose: () => void;
  onGuardar: (etiqueta: string) => Promise<void>;
}) {
  const [etiqueta, setEtiqueta] = useState(inicial);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function enviar() {
    if (!etiqueta.trim()) return;
    setGuardando(true);
    setError(null);
    try {
      await onGuardar(etiqueta.trim());
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo guardar.");
      setGuardando(false);
    }
  }

  return (
    <Modal
      open={true}
      title={titulo}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={guardando}>
            Cancelar
          </Button>
          <Button
            onClick={enviar}
            loading={guardando}
            disabled={!etiqueta.trim()}
          >
            Guardar
          </Button>
        </>
      }
    >
      <div className="space-y-3">
        {error ? <Banner variant="danger">{error}</Banner> : null}
        <label className="block text-xs text-[var(--text-secondary)]">
          Nombre
          <Input
            value={etiqueta}
            onChange={(e) => setEtiqueta(e.target.value)}
            placeholder="Mantenimiento evolutivo"
            autoFocus
          />
        </label>
        {clave ? (
          <p className="text-[12px] text-[var(--text-tertiary)]">
            La clave <code className="font-mono">{clave}</code> no cambia: es la
            que tienen guardada los proyectos.
          </p>
        ) : (
          <p className="text-[12px] text-[var(--text-tertiary)]">
            La clave se genera del nombre y ya no cambia, así que elígelo con
            calma. El nombre sí se puede editar después.
          </p>
        )}
      </div>
    </Modal>
  );
}
