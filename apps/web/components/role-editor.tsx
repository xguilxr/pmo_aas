"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState, type FormEvent } from "react";
import { ArrowLeft, ShieldCheck, Trash2 } from "lucide-react";

import { PermissionsMatrix } from "@/components/permissions-matrix";
import { Badge } from "@/components/ui/badge";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api";
import {
  createRole,
  deleteRole,
  updateRole,
  type AdminRole,
} from "@/lib/api/admin";

type Props = {
  mode: "create" | "edit";
  initial?: AdminRole;
};

type Notice =
  | { kind: "success"; message: string }
  | { kind: "danger"; message: string }
  | null;

export function RoleEditor({ mode, initial }: Props) {
  const router = useRouter();
  const [name, setName] = useState(initial?.name ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [permissions, setPermissions] = useState<Record<string, string[]>>(
    initial?.permissions ?? {},
  );
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [notice, setNotice] = useState<Notice>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const isSystem = initial?.is_system === true;
  const moduleCount = useMemo(() => Object.keys(permissions).length, [permissions]);
  const dirty = useMemo(() => {
    if (mode === "create") return true;
    if (!initial) return false;
    if (name.trim() !== initial.name) return true;
    if ((description ?? "").trim() !== (initial.description ?? "").trim()) return true;
    return JSON.stringify(permissions) !== JSON.stringify(initial.permissions);
  }, [mode, initial, name, description, permissions]);

  const canSubmit = name.trim().length >= 2 && moduleCount > 0;

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!canSubmit) return;
    setSaving(true);
    setNotice(null);
    try {
      if (mode === "create") {
        const created = await createRole({
          name: name.trim(),
          description: description.trim() || null,
          permissions,
        });
        router.replace(`/admin/roles/${created.id}?created=1`);
      } else if (initial) {
        const updated = await updateRole(initial.id, {
          name: name.trim(),
          description: description.trim() || null,
          permissions,
        });
        setNotice({ kind: "success", message: "Rol actualizado" });
        setName(updated.name);
        setDescription(updated.description ?? "");
        setPermissions(updated.permissions);
      }
    } catch (err) {
      setNotice({
        kind: "danger",
        message: err instanceof ApiError ? err.message : "No se pudo guardar el rol",
      });
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!initial || isSystem) return;
    setDeleting(true);
    try {
      await deleteRole(initial.id);
      router.replace("/admin/roles");
    } catch (err) {
      setConfirmDelete(false);
      setDeleting(false);
      setNotice({
        kind: "danger",
        message: err instanceof ApiError ? err.message : "No se pudo borrar el rol",
      });
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div>
        <Link
          href="/admin/roles"
          className="inline-flex items-center gap-1 text-sm text-[var(--color-tertiary)] hover:text-[var(--color-primary)]"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden />
          Volver a roles
        </Link>
        <div className="mt-2 flex flex-wrap items-end justify-between gap-2">
          <div>
            <h1 className="text-2xl font-semibold text-[var(--color-primary)]">
              {mode === "create" ? "Nuevo rol" : initial?.name}
            </h1>
            <p className="text-sm text-[var(--color-tertiary)]">
              {mode === "create"
                ? "Define el nombre y la matriz de permisos."
                : "Modifica permisos. Aplica al instante a los usuarios con este rol."}
            </p>
          </div>
          {isSystem ? (
            <Badge variant="info">
              <ShieldCheck className="h-3 w-3" aria-hidden />
              Rol del sistema
            </Badge>
          ) : null}
        </div>
      </div>

      {notice ? (
        <Banner variant={notice.kind === "success" ? "success" : "danger"}>
          {notice.message}
        </Banner>
      ) : null}

      <form
        onSubmit={handleSubmit}
        noValidate
        className="space-y-5 rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-sm)]"
      >
        <div className="grid gap-4 sm:grid-cols-[1fr_2fr]">
          <div>
            <label htmlFor="name" className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]">
              Nombre
            </label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={saving}
              required
            />
          </div>
          <div>
            <label
              htmlFor="description"
              className="mb-1.5 block text-sm font-medium text-[var(--color-secondary)]"
            >
              Descripción
            </label>
            <Textarea
              id="description"
              value={description ?? ""}
              onChange={(e) => setDescription(e.target.value)}
              disabled={saving}
              rows={2}
            />
          </div>
        </div>

        <div>
          <div className="mb-2 flex items-center justify-between">
            <p className="text-sm font-medium text-[var(--color-secondary)]">Permisos</p>
            <span className="text-xs text-[var(--color-tertiary)]">
              {moduleCount} módulo{moduleCount === 1 ? "" : "s"} activo{moduleCount === 1 ? "" : "s"}
            </span>
          </div>
          <PermissionsMatrix value={permissions} onChange={setPermissions} disabled={saving} />
          {moduleCount === 0 ? (
            <p className="mt-2 text-xs text-[var(--color-warning-fg)]">
              Selecciona al menos un permiso para poder guardar.
            </p>
          ) : null}
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-[var(--border-default)] pt-4">
          <div>
            {mode === "edit" && initial && !isSystem ? (
              <Button
                type="button"
                variant="danger"
                onClick={() => setConfirmDelete(true)}
                disabled={saving}
              >
                <Trash2 className="h-4 w-4" aria-hidden />
                Borrar rol
              </Button>
            ) : null}
          </div>
          <div className="flex gap-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => router.push("/admin/roles")}
              disabled={saving}
            >
              Cancelar
            </Button>
            <Button type="submit" loading={saving} disabled={!dirty || !canSubmit}>
              {mode === "create" ? "Crear rol" : "Guardar cambios"}
            </Button>
          </div>
        </div>
      </form>

      <Modal
        open={confirmDelete}
        onClose={() => setConfirmDelete(false)}
        title="Borrar rol"
        description="Los usuarios con este rol perderán esos permisos. Esta acción no se puede deshacer."
        footer={
          <>
            <Button
              variant="secondary"
              onClick={() => setConfirmDelete(false)}
              disabled={deleting}
            >
              Cancelar
            </Button>
            <Button variant="danger" onClick={handleDelete} loading={deleting}>
              Borrar
            </Button>
          </>
        }
      >
        <p className="text-sm text-[var(--color-secondary)]">
          ¿Confirmas borrar el rol <strong>{initial?.name}</strong>?
        </p>
      </Modal>
    </div>
  );
}
