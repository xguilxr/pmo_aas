"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState, type FormEvent } from "react";

import { Banner } from "@/components/ui/banner";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Icono } from "@/components/ui/icono";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { ApiError } from "@/lib/api";
import { createUser, listRoles, type AdminRole, type RoleType } from "@/lib/api/admin";
import { listOrganizations, type Organization } from "@/lib/api/organizations";
import { checkPasswordPolicy, generatePassword, passwordPolicyOk } from "@/lib/password";

const POLICY_ERRORS: Record<string, string> = {
  password_too_short: "Contraseña: al menos 8 caracteres",
  password_too_long: "Contraseña: máximo 128 caracteres",
  password_missing_uppercase: "Contraseña: incluye una mayúscula",
  password_missing_digit: "Contraseña: incluye un dígito",
  password_missing_symbol: "Contraseña: incluye un símbolo",
};

export default function NewUserPage() {
  const router = useRouter();

  const [fullName, setFullName] = useState("");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isActive, setIsActive] = useState(true);
  const [roleIds, setRoleIds] = useState<string[]>([]);
  const [roleType, setRoleType] = useState<RoleType>("user");

  const [roles, setRoles] = useState<AdminRole[]>([]);
  const [loadingRoles, setLoadingRoles] = useState(true);
  const [orgs, setOrgs] = useState<Organization[]>([]);
  // US-078: default = todas incluidas → ninguna excluida.
  const [excludedOrgIds, setExcludedOrgIds] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      listRoles(),
      listOrganizations({ is_active: true }),
    ])
      .then(([r, orgList]) => {
        if (cancelled) return;
        setRoles(r);
        setOrgs(orgList);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(
            err instanceof ApiError ? err.message : "No se pudieron cargar los datos del formulario",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingRoles(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const policyChecks = useMemo(() => checkPasswordPolicy(password), [password]);
  const usernameValid = /^[a-zA-Z0-9_.\-]{3,64}$/.test(username);
  const emailValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  const canSubmit =
    fullName.trim().length >= 2 &&
    usernameValid &&
    emailValid &&
    passwordPolicyOk(password);

  function toggleRole(id: string, checked: boolean) {
    setRoleIds((prev) => (checked ? [...prev, id] : prev.filter((r) => r !== id)));
  }

  function handleGenerate() {
    const pwd = generatePassword(16);
    setPassword(pwd);
    setShowPassword(true);
  }

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      const created = await createUser({
        full_name: fullName.trim(),
        username: username.trim().toLowerCase(),
        email: email.trim().toLowerCase(),
        password,
        role_ids: roleIds,
        is_active: isActive,
        role_type: roleType,
        excluded_organization_ids: excludedOrgIds,
      });
      router.replace(`/admin/users/${created.id}?created=1`);
    } catch (err) {
      if (err instanceof ApiError) {
        const fieldCode =
          err.fields && typeof err.fields === "object" && "code" in err.fields
            ? String((err.fields as { code?: unknown }).code ?? "")
            : "";
        setError(POLICY_ERRORS[fieldCode] ?? err.message);
      } else {
        setError("No se pudo crear el usuario");
      }
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="space-y-2">
        <Breadcrumb
          items={[
            { href: "/admin/users", label: "Usuarios" },
            { label: "Nuevo usuario" },
          ]}
        />
        <div>
          <h1 className="text-2xl font-semibold text-[var(--text-primary)]">Nuevo usuario</h1>
          <p className="mt-1 text-[13px] text-[var(--text-tertiary)]">
            Crea una cuenta y asígnale roles. La contraseña se entrega una sola vez.
          </p>
        </div>
      </div>

      <form
        onSubmit={handleSubmit}
        noValidate
        className="space-y-5 rounded-[var(--radius-window)] border border-[var(--border-subtle)] bg-[var(--color-surface)] p-8"
      >
        <div>
          <label htmlFor="full_name" className="mb-1.5 block text-[12.5px] font-medium text-[var(--text-secondary)]">
            Nombre completo
          </label>
          <Input
            id="full_name"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            disabled={submitting}
            placeholder="Ana López"
            required
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="username" className="mb-1.5 block text-[12.5px] font-medium text-[var(--text-secondary)]">
              Usuario
            </label>
            <Input
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              disabled={submitting}
              placeholder="ana.lopez"
              autoComplete="off"
              required
              invalid={username.length > 0 && !usernameValid}
            />
            <p className="mt-1 text-[12px] text-[var(--text-tertiary)]">
              3 a 64 caracteres. Letras, números, <code>.</code> <code>_</code> <code>-</code>.
            </p>
          </div>
          <div>
            <label htmlFor="email" className="mb-1.5 block text-[12.5px] font-medium text-[var(--text-secondary)]">
              Correo
            </label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={submitting}
              placeholder="ana@empresa.com"
              autoComplete="off"
              required
              invalid={email.length > 0 && !emailValid}
            />
          </div>
        </div>

        <div>
          <div className="mb-1.5 flex items-center justify-between">
            <label htmlFor="password" className="block text-[12.5px] font-medium text-[var(--text-secondary)]">
              Contraseña inicial
            </label>
            <button
              type="button"
              onClick={handleGenerate}
              disabled={submitting}
              className="inline-flex items-center gap-1 text-xs font-medium text-[var(--text-primary)] hover:underline"
            >
              <Icono nombre="refresh-cw" size={13} />
              Generar segura
            </button>
          </div>
          <div className="relative">
            <Input
              id="password"
              type={showPassword ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={submitting}
              autoComplete="new-password"
              required
              className="pr-10"
            />
            <button
              type="button"
              onClick={() => setShowPassword((v) => !v)}
              aria-pressed={showPassword}
              aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
              className="absolute right-2 top-1/2 inline-flex h-6 w-6 -translate-y-1/2 items-center justify-center rounded-[var(--radius-xs)] text-[var(--text-tertiary)] hover:text-[var(--text-primary)]"
            >
              <Icono nombre={showPassword ? "eye-off" : "eye"} size={15} />
            </button>
          </div>
          <ul className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
            {policyChecks.map((c) => (
              <li
                key={c.label}
                className={
                  c.ok
                    ? "flex items-center gap-1.5 text-[var(--color-success-fg)]"
                    : "flex items-center gap-1.5 text-[var(--text-tertiary)]"
                }
              >
                <Icono nombre={c.ok ? "check" : "x"} size={13} />
                {c.label}
              </li>
            ))}
          </ul>
        </div>

        <div>
          <p className="mb-2 text-[12.5px] font-medium text-[var(--text-secondary)]">Roles</p>
          {loadingRoles ? (
            <p className="text-xs text-[var(--text-tertiary)]">Cargando roles…</p>
          ) : roles.length === 0 ? (
            <p className="text-xs text-[var(--text-tertiary)]">
              Los permisos se gestionan por <Link href="/admin/permissions" className="underline">capability del rol</Link>{" "}
              (admin/user). La asignación se hará desde esta página en US-078.
            </p>
          ) : (
            <div className="grid gap-2 sm:grid-cols-2">
              {roles.map((r) => {
                const checked = roleIds.includes(r.id);
                return (
                  <label
                    key={r.id}
                    className="flex cursor-pointer items-start gap-2 rounded-[var(--radius-md)] border border-[var(--border-default)] p-3 hover:bg-[var(--color-subtle)]"
                  >
                    <Checkbox
                      checked={checked}
                      onChange={(e) => toggleRole(r.id, e.target.checked)}
                      disabled={submitting}
                    />
                    <div className="flex-1">
                      <div className="text-sm font-medium text-[var(--text-primary)]">
                        {r.name}
                      </div>
                      {r.description ? (
                        <div className="text-xs text-[var(--text-tertiary)]">{r.description}</div>
                      ) : null}
                    </div>
                  </label>
                );
              })}
            </div>
          )}
        </div>

        <div>
          <label htmlFor="role_type" className="mb-1.5 block text-[12.5px] font-medium text-[var(--text-secondary)]">
            Rol del tenant
          </label>
          <Select
            id="role_type"
            value={roleType}
            onChange={(e) => setRoleType(e.target.value as RoleType)}
            disabled={submitting}
          >
            <option value="user">PM — operador del tenant (visibilidad por asignación)</option>
            <option value="pm_sr">PM Sr — acceso admin completo al tenant</option>
            <option value="admin">Admin — metaconfig + acceso admin completo</option>
          </Select>
          <p className="mt-1 text-xs text-[var(--text-tertiary)]">
            <Link href="/admin/permissions" className="underline">
              Ver qué hace cada rol
            </Link>
          </p>
        </div>

        <div>
          <p className="mb-2 text-[12.5px] font-medium text-[var(--text-secondary)]">
            Acceso a organizaciones
          </p>
          <p className="mb-2 text-xs text-[var(--text-tertiary)]">
            Por defecto el usuario tendrá acceso a todas las organizaciones del
            tenant. Desmarca para excluirlo de orgs específicas.
          </p>
          {orgs.length === 0 ? (
            <p className="text-xs text-[var(--text-tertiary)]">
              Sin organizaciones activas en el tenant.
            </p>
          ) : (
            <div className="grid gap-1.5 sm:grid-cols-2">
              {orgs.map((o) => {
                const included = !excludedOrgIds.includes(o.id);
                return (
                  <label
                    key={o.id}
                    className="flex cursor-pointer items-center gap-2 rounded-[var(--radius-md)] border border-[var(--border-default)] px-3 py-2 hover:bg-[var(--color-subtle)]"
                  >
                    <Checkbox
                      checked={included}
                      onChange={(e) =>
                        setExcludedOrgIds((prev) =>
                          e.target.checked
                            ? prev.filter((id) => id !== o.id)
                            : Array.from(new Set([...prev, o.id]))
                        )
                      }
                      disabled={submitting}
                    />
                    <span className="text-sm text-[var(--text-primary)]">
                      {o.name}
                    </span>
                  </label>
                );
              })}
            </div>
          )}
        </div>

        <Switch
          id="is_active"
          checked={isActive}
          onChange={setIsActive}
          disabled={submitting}
          label="Cuenta activa al crear"
        />

        {error ? <Banner variant="danger">{error}</Banner> : null}

        <div className="flex justify-end gap-2 border-t border-[var(--border-default)] pt-4 shadow-[var(--linea-surco-arriba)]">
          <Button
            type="button"
            variant="secondary"
            onClick={() => router.push("/admin/users")}
            disabled={submitting}
          >
            Cancelar
          </Button>
          <Button type="submit" loading={submitting} disabled={!canSubmit}>
            Crear usuario
          </Button>
        </div>
      </form>
    </div>
  );
}
