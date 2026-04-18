# EP007 — Panel de Administración

| Campo | Valor |
|---|---|
| **ID** | EP007 |
| **Prioridad** | Alta |
| **Dependencias** | EP001, EP002 |
| **Módulo** | `admin.*` |
| **Estado** | MVP |

## Objetivo de negocio

Centralizar en un panel único la gestión de usuarios, roles, organizaciones y proyectos del tenant, con vistas optimizadas para operaciones rápidas (crear, editar, desactivar, resetear, etc.).

---

## US-037 — Panel de administración de usuarios

**Como** Administrador
**Quiero** una tabla completa de usuarios con acciones rápidas
**Para** onboardear y gestionar el equipo.

**Criterios de aceptación:**
- [ ] Columnas: nombre, username, email, roles (chips), estado (activo/bloqueado), último login, acciones.
- [ ] Acciones inline: editar, activar/desactivar, resetear password, desbloquear, impersonate (solo superadmin).
- [ ] Búsqueda fuzzy + filtros (rol, estado).
- [ ] Export CSV/XLSX con filtros aplicados.
- [ ] No se permite desactivar la cuenta propia.
- [ ] Bulk actions: asignar rol a varios seleccionados, desactivar masivo (con confirmación).

**Test Cases:**
- `TC-098` (integration) — Desactivar cuenta propia → 422 `BUSINESS_RULE`.
- `TC-099` (integration) — Bulk asignar rol a 10 users → todos afectados, audit log con 10 entradas.
- `TC-100` (E2E) — Export CSV descarga con headers correctos.

---

## US-038 — Panel de administración de roles

**Como** Administrador
**Quiero** definir roles con matriz de permisos (checkboxes por módulo × acción)
**Para** controlar acceso granular.

**Criterios de aceptación:**
- [ ] Tabla de roles con `name`, `description`, `user_count`, acciones.
- [ ] Editor de rol: matriz visual 12×8 (módulos × acciones) con checkboxes.
- [ ] Toggle "seleccionar todos" por fila y por columna.
- [ ] Preview "Este cambio afecta a N usuarios: …" antes de guardar.
- [ ] Roles sistema (`is_system=true`) muestran badge "Sistema" y deshabilitan borrar.
- [ ] Duplicar rol (as template).

**Test Cases:**
- `TC-101` (E2E) — Toggle "todos" marca fila completa.
- `TC-102` (E2E) — Preview muestra lista de afectados.
- `TC-103` (integration) — Duplicar rol → copia `permissions` pero `is_system=false`.

---

## US-039 — Panel de administración de organizaciones

**Como** Administrador
**Quiero** gestionar organizaciones desde un panel con métricas
**Para** ver impacto.

**Criterios de aceptación:**
- [ ] Cards con métricas por org: `project_count_active`, `budget_total`, `user_count`.
- [ ] Link rápido a "Ver proyectos de esta org".
- [ ] Upload logo inline con preview + crop 1:1.
- [ ] Soft delete con confirmación y advertencia de proyectos afectados.

**Test Cases:**
- `TC-104` (integration) — Métricas por org coinciden con queries directas.
- `TC-105` (E2E) — Upload logo con crop → guardado correcto.

---

## US-040 — Panel de administración de proyectos (supervisión)

**Como** Administrador
**Quiero** ver **todos** los proyectos del tenant sin filtro de miembro
**Para** supervisión global.

**Criterios de aceptación:**
- [ ] Endpoint especial `GET /api/v1/admin/projects` — bypass filtro `is_member`.
- [ ] Solo accesible con permiso `admin.projects:read`.
- [ ] Métricas globales: total, por estado, por organización, desviaciones.
- [ ] Acciones: cambiar PM, forzar cierre (con comentario).

**Test Cases:**
- `TC-106` (integration) — User sin `admin.projects:read` → 403.
- `TC-107` (integration) — Admin ve todos los proyectos incluidos los de orgs inactivas.

---

## US-041 — Configuración del tenant

**Como** Administrador
**Quiero** configurar preferencias del tenant
**Para** personalizar.

**Criterios de aceptación:**
- [ ] Sección "Configuración" con:
  - Idioma default (`es-MX` / `en-US`).
  - Moneda default (`MXN`, `USD`, `EUR`).
  - Formato de fecha.
  - Timezone.
  - Logo corporativo + color primario (para PDFs exportados).
  - Modo IA (`ollama`/`claude`/`disabled`).
- [ ] Se guarda en `tenants.settings` (JSONB).
- [ ] Cambio de idioma default no afecta preferencia individual de users.

**Test Cases:**
- `TC-108` (integration) — Actualizar `settings.locale` → próximo login muestra UI en ese idioma.
- `TC-109` (integration) — Color primario se refleja en PDF exportado.

---

## US-042 — Logs de auditoría (visible para Admin del tenant)

**Como** Administrador
**Quiero** consultar quién hizo qué cuándo
**Para** forensía y compliance.

**Criterios de aceptación:**
- [ ] `GET /api/v1/admin/audit-logs?action=&user_id=&entity_type=&date_from=&date_to=&cursor=`.
- [ ] Solo ve eventos del **tenant propio** (RLS estricto).
- [ ] Incluye `action`, `module`, `entity_type`, `entity_id`, `details`, `ip_address`, `occurred_at`, `user_display`.
- [ ] Export CSV para período.

**Test Cases:**
- `TC-110` (integration) — Admin A no ve eventos de tenant B (TC-MT-006).
- `TC-111` (integration) — Filtros combinados devuelven exacto.

---

## Notas técnicas

- Panel admin es una ruta protegida `/admin` en Next.js con `middleware.ts` que verifica permiso.
- Bulk actions usan endpoints que aceptan arrays, con validación de tamaño máx (100).
- Logs de auditoría usan cursor pagination por performance (tabla grande).

### Endpoints
```
GET    /api/v1/admin/users
POST   /api/v1/admin/users/bulk
POST   /api/v1/admin/users/{id}/impersonate      (superadmin only)

GET    /api/v1/admin/roles
POST   /api/v1/admin/roles
POST   /api/v1/admin/roles/{id}/duplicate
GET    /api/v1/admin/roles/{id}/impact           (preview de afectados)

GET    /api/v1/admin/organizations
GET    /api/v1/admin/projects                    (bypass member filter)

GET    /api/v1/admin/settings
PATCH  /api/v1/admin/settings
POST   /api/v1/admin/settings/logo

GET    /api/v1/admin/audit-logs
GET    /api/v1/admin/audit-logs/export.csv
```

---

## Definition of Done

- [ ] Panel accesible en `/admin` con navegación lateral: Users, Roles, Orgs, Projects, Settings, Logs.
- [ ] Bulk actions probadas con 100 elementos sin degradar performance.
- [ ] TC-MT-005 (admin A no gestiona B) y TC-MT-006 (logs aislados) verdes.
- [ ] UI elegante con tablas densas estilo macOS Finder (ver design system).
