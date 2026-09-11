---
tipo: gestion
responsable: propietario
estado: vigente
revisado: 2026-09-11
revisar_cada: 30d
---

# FASE 7 — Admin (jerarquía, borrado real de usuarios, Plan e IA) y Cuenta

**Qué es.** `/admin/hierarchy` para mover, crear y borrar en el árbol
organización → portafolio → programa → proyecto y dar de baja
organizaciones; borrado real de usuarios; `/admin/ai` dentro de Plan e IA;
`/account` con todo lo del dropdown del avatar. Puntos 9 y 10 de
`../REVAMP-V2-FEEDBACK.md`. Wireframes **W7** (jerarquía) y **W8** (cuenta).
**Tamaño:** L. **Gate:** fase 6 mergeada, W7 y W8 aprobados, decisión
**D4** (dónde queda `/admin/areas`). **Epics:** EP007 (admin), EP001
(usuarios). Nuevo endpoint de borrado permanente → `modelo-amenazas.md`
(ruta destructiva; declararla antes del código, CLAUDE.md §0.3).

**Reglas.** Cinco commits. Todo lo de esta fase es **solo admin del
tenant**: cada endpoint nuevo lleva el mismo `Depends` que
`DELETE /organizations/{org_id}/permanent`.

## Preparación

```bash
git fetch origin main
git checkout -b claude/revamp-v2-f7-admin origin/main
pnpm install --frozen-lockfile
python scripts/proximo_id.py
```

## Hechos verificados

- Usuarios: el botón "Desactivar" está en `admin/users/[id]/page.tsx:569`
  y su confirmación en `:648-649` (`handleDeactivate`), que llama
  `deleteUser` (`:275`). `deleteUser` vive en `apps/web/lib/api/admin.ts:84`
  y hace `DELETE /api/v1/admin/users/{id}`. El backend
  (`apps/api/app/api/v1/endpoints/admin_users.py:352-376`, `delete_user`)
  hace **soft delete**: `u.is_active = False` (:368), audita
  `user.delete`, rechaza si `is_superadmin`. No hay borrado permanente.
- Organizaciones: `DELETE /organizations/{org_id}` (`organizations.py:466`)
  es soft (`is_active = False`, :480); `DELETE /{org_id}/permanent` (:1322)
  es borrado real con preview. Front: `deleteOrganization` :153,
  `previewHardDeleteOrganization` :287, `hardDeleteOrganization(id, confirm)`
  :293 en `lib/api/organizations.ts`.
- Portafolios y programas: soft y hard delete ya expuestos en el front
  (`deletePortfolio` :372, `hardDeletePortfolio` :304, `deleteProgram`
  :260, `hardDeleteProgram` :280, con `previewHardDelete*`).
- `/account/page.tsx` renderiza `NotificationPreferencesSection` (:291) y
  `MisDatosSection` (:292). El dropdown `components/user-menu.tsx` tiene:
  idioma Español/English (:150-151), tema Claro/Oscuro/Sistema (:188-190),
  "Administrar cuenta" → `/account` (:217-225), "Cerrar sesión" (:226-239).
- `/admin/permissions` y `/admin/plan` son solo lectura; `/admin/ai`
  configura proveedor (`platform | byo | disabled`) con
  `updateTenantAIProvider`.
- Formularios de portafolio y programa: creados en la fase 4
  (`components/portfolio-form.tsx`, `program-modal.tsx` con edición).

## Commit 1 — `/admin/hierarchy` (US-A)

**Ruta nueva:** `apps/web/app/(app)/admin/hierarchy/page.tsx`. Diseño W7.

1. Selector de organización arriba (todas las del tenant:
   `listOrganizations()`), independiente del dropdown del header (esto es
   nivel tenant).
2. Árbol: organización → portafolios (`listPortfolios(orgId)`) → programas
   (`listPrograms({ portfolio_id })`) → proyectos
   (`listProjects({ program_id })`). Nodos plegables; icono `folder`/`folders`.
3. Acciones por nodo (menú "⋯"):
   - Portafolio: editar (`portfolio-form.tsx`), desactivar
     (`deletePortfolio`), **eliminar definitivamente**
     (`previewHardDeletePortfolio` → modal con el conteo del preview →
     `hardDeletePortfolio(id, confirm)` donde `confirm` es el nombre
     tecleado por el admin).
   - Programa: igual con `program-modal.tsx`, `deleteProgram`,
     `previewHardDeleteProgram`/`hardDeleteProgram`.
   - Proyecto: "Mover a…" → `Select` de programa de la misma organización
     → `updateProject(id, { program_id, portfolio_id })`.
   - Organización (raíz): desactivar (`deleteOrganization`) y eliminar
     definitivamente (`previewHardDeleteOrganization` →
     `hardDeleteOrganization`).
4. Sidebar: en `buildAdminNav()` el hijo `orgs-mgmt` cambia a
   `label: "Organizaciones y portafolios"`, `href: "/admin/hierarchy"`.
   `/admin/organizations` sigue existiendo (alta/edición de organización
   con `organization-form.tsx`); enlázala desde la cabecera de
   `/admin/hierarchy` ("Nueva organización", "Editar organización").
5. Permiso: la página se protege como las demás de `/admin`
   (`adminVisible` en el shell + el guard de la ruta; copia el patrón de
   `admin/organizations/page.tsx`).

**TC-F7-01.** Como admin: mover un proyecto de programa se refleja en
`/pmo`; desactivar un programa lo oculta; eliminar definitivamente un
portafolio vacío pide teclear su nombre y lo borra; como usuario `user`,
`/admin/hierarchy` responde 403/redirige.

```
feat(admin): US-A — /admin/hierarchy: árbol org→portafolio→programa→proyecto con mover, crear y borrar
```

## Commit 2 — borrado real de usuarios (US-B)

1. **Modelo de amenazas primero**: en `docs/architecture/modelo-amenazas.md`
   agrega la ruta `DELETE /api/v1/admin/users/{id}/permanent` como
   destino destructivo con control "admin del tenant + confirmación por
   nombre + auditoría". `tests/test_seg06_modelo_amenazas.py` debe seguir
   verde (`amenazas.yaml` si el test lee de ahí; revisa el test).
2. Backend `admin_users.py`: nuevo `@router.delete("/{user_id}/permanent", status_code=204)`
   con el mismo `Depends` que `delete_user`; cuerpo `{ "confirm": "<username>" }`
   (400 si no coincide); rechaza `is_superadmin` y al propio admin que
   llama; audita `user.hard_delete`; borra `UserTenantMembership` del
   usuario y luego el `User`. Si el usuario tiene filas con FK `created_by`
   sin `ON DELETE SET NULL`, el borrado falla con 409 y mensaje "tiene N
   registros asociados; desactívalo en su lugar" — enumera esas FKs en el
   PR (consulta `er-generado.md`, relaciones `USERS |o--o{ … : created_by`).
3. Test `apps/api/tests/test_<us>_user_hard_delete.py`: admin borra a un
   usuario sin registros → 204 y no existe; con `confirm` malo → 400;
   superadmin → 403; usuario con registros asociados → 409.
4. Front: `lib/api/admin.ts` agrega `deleteUserPermanent(id, confirm)`.
   `admin/users/[id]/page.tsx`: el botón de `:569` se queda como
   "Desactivar" (lo que hace hoy) y al lado un botón `variant="danger"`
   "Eliminar definitivamente" → modal que exige teclear el `username` →
   `deleteUserPermanent` → vuelve a `/admin/users`.
5. Corrige los textos: el modal de `:648` dice "desactivar" y está bien;
   el error "No se pudo desactivar" también. El nombre de la función
   `deleteUser` en `admin.ts:84` renómbralo a `deactivateUser` (y sus
   usos: `grep -rn "deleteUser" apps/web`).

**TC-F7-02.** Los cuatro casos del test verdes. En la UI, "Desactivar"
deja al usuario inactivo; "Eliminar definitivamente" con el nombre
tecleado lo borra y ya no aparece en `/admin/users`.

```
feat(admin): US-B — borrado permanente de usuarios con confirmación por nombre (refs REVAMP-V2 §10)
```

## Commit 3 — Plan e IA en una página (US-C)

1. `admin/plan/page.tsx`: barra de pestañas `Plan | IA` (patrón de
   `project-tabs-bar.tsx`). `Plan`: contenido actual. `IA`: el contenido de
   `admin/ai/page.tsx` extraído a `components/admin/configuracion-ia.tsx`.
2. `admin/ai/page.tsx` se borra; `next.config.js` `redirects()`:
   `/admin/ai` → `/admin/plan?tab=ia`.
3. Quita el `<Link>` temporal "Configurar IA" de la fase 1.
4. No cambies la lógica de proveedor (D5 sigue abierta): esta fase solo
   junta las dos páginas.

**TC-F7-03.** `/admin/plan?tab=ia` muestra la configuración de proveedor y
guardar funciona igual que antes; `/admin/ai` redirige.

```
feat(admin): US-C — Plan e IA en una sola página con pestañas
```

## Commit 4 — `/admin/areas` según D4 (US-D)

Con D4 = "dentro de Recursos" (recomendada): en `/pmo/resources` agrega
la pestaña "Áreas y equipos" que monta los paneles que hoy usa
`admin/areas/page.tsx` (`AreasAndTeamsPanel`, `TenantActorsPanel` en
`components/directory/`), visibles solo si `canUpdate("areas")` o el
permiso equivalente. Redirect `/admin/areas` → `/pmo/resources?tab=areas`.
Con D4 = "queda en Admin": agrega el hijo `areas` a `buildAdminNav()` y no
hay más cambio.

```
feat(web): US-D — áreas y equipos como pestaña de Recursos (D4)
```

## Commit 5 — Cuenta (US-E)

**Archivo:** `apps/web/app/(app)/account/page.tsx`. Diseño W8.

1. Secciones en este orden: Datos personales (`MisDatosSection`, ya
   existe), Preferencias (nuevo: idioma y tema — reusa los dos
   `radiogroup` de `user-menu.tsx:150-151` y `:188-190` extraídos a
   `components/preferencias-de-interfaz.tsx` para que el menú y la página
   compartan el mismo componente), Notificaciones
   (`NotificationPreferencesSection`, ya existe), Seguridad (cambio de
   contraseña: enlaza a `/change-password` si la página existe fuera de
   `(app)`; verifica en `navigation.md`), Sesión (botón "Cerrar sesión",
   misma acción que `user-menu.tsx:226-239`).
2. `user-menu.tsx` queda con: Preferencias (mismo componente), "Administrar
   cuenta", "Cerrar sesión". Nada se pierde del menú; solo se comparte.

**TC-F7-05.** Cambiar el idioma en `/account` cambia la interfaz y el
menú del avatar lo refleja; cerrar sesión desde la página funciona.

```
feat(web): US-E — /account con datos, preferencias, notificaciones y sesión (refs REVAMP-V2 §9)
```

## Verificación antes de push

```bash
pnpm --filter @pmoaas/web exec tsc --noEmit
python scripts/check_tokens.py
cd apps/api && .venv/bin/python -m ruff check . && .venv/bin/python -m pytest -q -n auto -m "not heavy"
python scripts/check_impacto_documental.py
```

## Cierre

PR `Revamp v2 — fase 7: admin y cuenta`. `cerrar-item` × 5. Feedback: 9,
10, 12 → `hecho`. `SPRINT.md` → "8 (reportes)". Antes: W5.

## Qué NO hacer

- No exponer borrado permanente a nadie que no sea admin del tenant.
- No decidir D5 (BYOK) aquí.
- No borrar `/admin/organizations` ni `/admin/permissions`.
