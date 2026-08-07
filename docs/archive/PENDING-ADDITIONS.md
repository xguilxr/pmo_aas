---
tipo: archivo
responsable: propietario
estado: archivado
revisado: 2026-05-08
revisar_cada: nunca
---

# PENDING-ADDITIONS.md — Adiciones pendientes a épicas existentes

> Este archivo documenta las user stories `# PENDING` que se deben agregar a cada épica existente.
> Claude Code: al trabajar en un epic, agrega estas US al archivo correspondiente antes de implementar.
> Una vez integradas al epic, marcar como INTEGRATED aquí.

---

## EP001-auth-users.md — Agregar al final

### # PENDING — US-NEW-007 — Toggle dark/light mode en dropdown de usuario

**Como** usuario autenticado
**Quiero** cambiar entre modo oscuro y claro desde el menú de usuario
**Para** elegir mi preferencia visual.

**Criterios de aceptación:**
- [ ] Dropdown de usuario (US-013) incluye toggle dark/light con iconos de luna (🌙) y sol (☀️).
- [ ] Iconos SVG simples, sin emoji.
- [ ] El toggle usa `prefers-color-scheme` como default, sobreescribible.
- [ ] Preferencia guardada en `users.preferences JSONB → { "theme": "dark"|"light"|"system" }`.
- [ ] Cambio aplica inmediatamente sin reload.
- [ ] `PATCH /api/v1/users/me/preferences` — actualiza preferencia.

**Test Cases:**
- `TC-NEW-012` (E2E) — Toggle cambia tema inmediatamente.
- `TC-NEW-013` (integration) — Preferencia persiste entre sesiones ✅

**Estado de integración:** INTEGRATED en EP001 (US-NEW-007).

---

### # PENDING — US-NEW-008 — Toggle de idioma en dropdown de usuario

**Como** usuario autenticado
**Quiero** cambiar el idioma de la interfaz
**Para** operar en mi idioma preferido.

**Criterios de aceptación:**
- [ ] Dropdown de usuario incluye selector de idioma: 🇲🇽 Español / 🇺🇸 English.
- [ ] Idiomas disponibles configurables por tenant en `tenants.settings.available_locales`.
- [ ] Default: idioma del tenant.
- [ ] Preferencia en `users.preferences JSONB → { "locale": "es-MX"|"en-US" }`.
- [ ] Cambio aplica inmediatamente (Next.js i18n router).

**Test Cases:**
- `TC-NEW-014` (E2E) — Cambio de idioma actualiza UI sin reload completo.

**Estado de integración:** INTEGRATED en EP001 (US-NEW-008, traducción UI diferida a post-MVP).

---

### # PENDING — US-NEW-009 — Página de administrar cuenta (perfil + cambiar password)

**Como** usuario autenticado
**Quiero** editar mis datos personales y cambiar mi contraseña
**Para** mantener mi perfil actualizado.

**Criterios de aceptación:**
- [ ] Opción "Administrar cuenta" en dropdown de usuario → navega a `/account`.
- [ ] Página con dos secciones:
  - **Detalles personales**: `full_name`, `email` (readonly si SSO), `avatar` (upload), `phone` (opcional).
  - **Cambiar contraseña**: current + new + confirm (mismos criterios que US-004).
- [ ] `PATCH /api/v1/users/me` — actualizar perfil.
- [ ] Upload avatar: PNG/JPG ≤ 2MB, guardado en `/data/uploads/tenants/{slug}/avatars/{user_id}.{ext}`.
- [ ] Cambio de email requiere verificación (post-MVP).

**Test Cases:**
- `TC-NEW-015` (E2E) — Editar nombre → se refleja en topbar sin reload ✅
- `TC-NEW-016` (integration) — Upload avatar → URL guardada y servida correctamente (PENDIENTE: infra de upload)

**Estado de integración:** INTEGRATED parcial en EP001 (US-NEW-009). Avatar
upload y `phone` pendientes en iteración siguiente.

---

### # PENDING — US-NEW-010 — Color chrome #182e4e + Senior PMO como admin

**Como** desarrollador
**Quiero** aplicar el color correcto al chrome de la app y configurar Senior PMO como admin-equivalent
**Para** cumplir los requerimientos de diseño y acceso.

**Criterios de aceptación:**
- [ ] Variable CSS `--chrome-bg` = `#182e4e` en `design-system/style.md` y globals.css.
- [ ] Sidebar y topbar usan `--chrome-bg`.
- [ ] Middleware de rutas `/admin` acepta: rol `Administrador` OR rol `PMO Manager` con flag `is_senior = true`.
- [ ] Alternativa: permiso `is_admin_equivalent` en el JWT para ambos roles.
- [ ] Seed actualiza rol `PMO Manager` con el flag correspondiente.

**Test Cases:**
- `TC-NEW-017` (E2E) — Chrome muestra `#182e4e` en light y dark mode ✅
- `TC-NEW-018` (integration) — Senior PMO puede acceder a `/admin/users` ✅

**Estado de integración:** INTEGRATED en EP001 (US-NEW-010).

---

## EP003-project-requests.md — Agregar a US-015 y nueva US

### # INTEGRATED — Campos adicionales en US-015 (integrado como US-NEW-011)

**Estado de integración:** INTEGRATED en EP003 (US-NEW-011, ver archivo
  del epic para detalles y tests). Los campos text legacy `business_unit`/
  `department` se mantienen hasta migración de datos (fase 2).

---

### # PENDING — Campos adicionales en US-015 (CRITERIOS ORIGINALES, ahora en US-NEW-011)

Campos adicionales al formulario de solicitud:

| Campo | Tipo | Obligatorio | Notas |
|---|---|---|---|
| `requester_name` | text | ✅ | Default: `user.full_name`, editable |
| `requester_email` | email | ✅ | Default: `user.email`, editable |
| `sponsor_email` | email | ✅ | |
| `key_people` | text | opcional | Personas clave del proyecto |
| `if_not_done` | text | opcional | ¿Qué sucede si no se hace? |
| `observations` | text | opcional | Observaciones adicionales |
| `entregables` | text | ✅ | Renombrar/complementar campo `scope` |

- [ ] `business_unit_id` y `department_id` son FK reales (no texto libre) — requiere EP002 completado.
- [ ] Solicitudes accesibles desde menú principal, NO anidadas bajo organización.

---

### # INTEGRATED — US-NEW-012 — Project Charter: tabla + generación al aprobar

**Estado de integración:** INTEGRATED en EP003 (US-NEW-012, ver archivo
  del epic para detalles y tests). PDF nativo queda como follow-up;
  endpoint devuelve HTML imprimible on-demand.

---

### # ORIGINAL — US-NEW-011 (referencia histórica) — Project Charter: tabla + generación al aprobar

**Como** PMO Manager
**Quiero** que al aprobar una solicitud se genere automáticamente un Project Charter
**Para** tener el documento fundacional del proyecto listo.

**Criterios de aceptación:**
- [ ] Al ejecutar `POST /project-requests/{id}/create-project`, además del proyecto se crea `project_charter`.
- [ ] Charter se pre-llena desde datos de la solicitud (ver DB-CHANGES.md sección EP003 para campos).
- [ ] Sección 1 (Info General): desde solicitud + proyecto creado.
- [ ] Sección 2 (Stakeholders): sponsor, sponsor_email, pm_id; lider_negocio y lider_tecnico quedan en blanco para completar.
- [ ] Sección 3 (Clasificación): desde solicitud.
- [ ] Sección 4 (Datos de Gestión): sincronizados dinámicamente desde `projects` al consultar.
- [ ] `GET /api/v1/projects/{id}/charter` — devuelve el charter completo.
- [ ] `PATCH /api/v1/projects/{id}/charter` — permite editar campos de secciones 1-3.
- [ ] `GET /api/v1/projects/{id}/charter/pdf` — genera PDF del charter on-demand.

**Test Cases:**
- `TC-NEW-019` (integration) — Aprobar solicitud → charter creado con datos correctos.
- `TC-NEW-020` (integration) — Sección 4 refleja datos actuales del proyecto.
- `TC-NEW-021` (E2E) — PDF del charter descargable con layout limpio.

**Estado de integración:** # PENDING en EP003

---

## EP004-dashboard.md — Agregar user stories

### # INTEGRATED — US-NEW-014 — Filtro de organización en dashboard

**Estado de integración:** INTEGRATED en EP004 (US-NEW-014). Backend
  expone `organization_id` en `/dashboard/kpis` y `/dashboard/charts`.

---

### # PENDING (referencia histórica) — US-NEW-014 — Filtro de organización en dashboard

**Criterios de aceptación:**
- [ ] Filtro por organización en la parte superior del dashboard, default vacío (sin filtro).
- [ ] Al seleccionar una org, todos los KPIs, gráficos y Plan vs Real se filtran por esa org.
- [ ] Estado del filtro en URL (`?org_id=...`).
- [ ] "Limpiar filtro" regresa a vista completa.

---

### # INTEGRATED — US-BUG-002 — Fix distorsión en gráficas de barra

**Estado de integración:** INTEGRATED en EP004. Gráficas de barra ahora:
  - Usan viewBox 300×100 con `preserveAspectRatio="xMidYMid meet"`
    (ya no `"none"`, evita distorsión horizontal).
  - Contenedor con `aspect-ratio: 3/1` (responsive sin deformar).
  - Grid horizontal con 4 ticks + labels del eje Y.
  - Labels de categorías con truncamiento automático según ancho de barra.

---

### # PENDING (referencia) — US-BUG-002 — Fix distorsión en gráficas de barra

**Criterios de aceptación:**
- [ ] Labels de categorías en eje X no se cortan ni se superponen.
- [ ] Valores numéricos en eje Y tienen escala correcta.
- [ ] Usar `<ResponsiveContainer>` de Recharts con `aspect` ratio apropiado.
- [ ] Verificar en mobile, tablet y desktop.

---

### # INTEGRATED — US-NEW-015 — KPIs respetan jerarquía de roles

**Estado de integración:** INTEGRATED en EP004. Helper `scoped_project_ids`
  aplicado a `/kpis`, `/charts` y `/plan-vs-actual`:
  - Admin-equivalente (via `is_admin_equivalent`): sin restricción.
  - Project Manager / resto de roles: sólo proyectos donde es `pm_id` o
    está en `project_members`.
  - Lista vacía → endpoints devuelven ceros (no error).
  La granularidad "Program Manager ve su programa" queda para US futura
  (requiere tabla program_managers o equivalente).

---

### # PENDING (referencia) — US-NEW-015 — KPIs respetan jerarquía de roles

**Criterios de aceptación:**
- [ ] Admin / Senior PMO: ven todos los KPIs del tenant. Filtros disponibles: org, programa, PM asignado.
- [ ] Program Manager: ven KPIs a nivel de sus programas y PMs asignados bajo ellos.
- [ ] Project Manager: solo ven KPIs de sus proyectos asignados.
- [ ] Lógica en `GET /api/v1/dashboard/kpis` según rol del usuario en sesión.

---

### # INTEGRATED — US-BUG-003 — Fix layout Plan vs Real

**Estado de integración:** INTEGRATED en EP004 (US-BUG-003).
  - Header de Plan vs Real con filtros Org + Fase + botón Exportar en la
    misma fila horizontal (ya era así; verificado).
  - Tabla con nueva columna "PM asignado":
    - Celda vacía ("—") si no hay PM.
    - Link al perfil del PM (`/admin/users/{id}`) si hay nombre.
  - Backend `/plan-vs-actual` devuelve `pm_id` y `pm_name`.
  - CSV export incluye columna `pm_name`.

---

### # PENDING (referencia) — US-BUG-003 — Fix layout Plan vs Real

**Criterios de aceptación:**
- [ ] Filtro "Organizaciones" y filtro "Fases" al mismo nivel horizontal (misma fila, no uno encima del otro).
- [ ] Botón "Exportar" en la misma fila horizontal que los filtros.
- [ ] Tabla agrega columna "PM Asignado" — si no hay PM, celda vacía.
- [ ] Columna PM muestra `full_name` del PM, clickeable al perfil.

**Estado de integración:** # PENDING en EP004

---

## EP005-projects.md — Agregar user stories

### # INTEGRATED — US-NEW-016 — Unificar Plan + Gantt en una sola pestaña

**Estado de integración:** INTEGRATED en EP005 (US-NEW-016).
  - Nueva ruta `/admin/projects/{id}/plan` con toggle Lista/Dividida/Gantt.
  - URL refleja modo con `?view=list|gantt` (default = split).
  - Sidebar: "Tareas" + "Gantt" reemplazadas por "Plan".
  - `/gantt` es ahora redirect permanente a `/plan?view=gantt` (compat).
  - Link "Abrir editor completo" desde la lista al editor detallado
    (`/tasks`) para edición avanzada.

---

### # PENDING (referencia) — US-NEW-016

**Criterios de aceptación:**
- [ ] Pestaña "Plan" en el detalle del proyecto contiene: lista de tareas (izquierda) + Gantt (derecha/abajo).
- [ ] Toggle para mostrar solo lista, solo Gantt, o vista dividida.
- [ ] Eliminar pestaña "Gantt" separada.
- [ ] URL: `/projects/{id}/plan`.

---

### # SUPERSEDED — US-NEW-017 — Tabs inline para módulos del proyecto (sin cambio de página)

**Estado:** SUPERSEDED por US-NEW-035 en EP013 (bloque 9 del sprint, issue #17).
Sus dependencias (US-NEW-016, 018, 019, 020, 021, 022) están DONE, pero el issue #17
pide un alcance más amplio que la absorbe: quitar "Módulos de proyecto" del sidebar
y consolidar todos los módulos como tabs inline. La implementación ocurre en
US-NEW-035.

**Criterios originales (referencia histórica):**
- [ ] Los botones actuales (Riesgos, AIDs, Cambios, Documentos, Lecciones, Minutas, Reportes) se convierten en tabs/pestañas en la misma página del proyecto.
- [ ] Click en tab actualiza el panel inferior de la página, NO navega a una URL diferente.
- [ ] URL puede reflejar tab activa como query param: `/projects/{id}?tab=risks`.
- [ ] Tab activa resaltada visualmente.
- [ ] Agregar tabs: Charter, RAID, Plan, Cambios, Áreas, Documentos, Minutas, Reportes.
- [ ] Tabs que exceden el ancho usan scroll horizontal o dropdown "más".

---

### # INTEGRATED — US-NEW-018 — Módulo Área/Organigrama del proyecto

**Estado de integración:** INTEGRATED en EP005 (US-NEW-018). CRUD completo
  backend + UI en `/admin/projects/{id}/areas`. Los areas son referenciables
  como texto — la integración con tareas/RAIDs/minutas como selector visual
  queda para sus US respectivas.

---

### # PENDING (referencia) — US-NEW-018

**Como** PM
**Quiero** registrar actores y áreas involucradas en el proyecto
**Para** referenciarlos en tareas, RAIDs y minutas sin que deban tener acceso a la plataforma.

**Criterios de aceptación:**
- [ ] Tab "Áreas" en el detalle del proyecto.
- [ ] CRUD de `project_areas`: nombre, tipo (área/actor/equipo), descripción, contacto (nombre + email).
- [ ] Las áreas aparecen como opción en: asignación de tareas (campo `area_reference`), minutas (participantes externos), RAIDs (owner_name).
- [ ] `GET /api/v1/projects/{id}/areas`.
- [ ] `POST /api/v1/projects/{id}/areas`.
- [ ] `PATCH /api/v1/project-areas/{id}`.
- [ ] `DELETE /api/v1/project-areas/{id}`.

**Test Cases:**
- `TC-NEW-025` (integration) — CRUD completo de areas.
- `TC-NEW-026` (E2E) — Área creada aparece en selector de participantes de minuta.

**Estado de integración:** # PENDING en EP005

---

## EP006-project-modules.md — Agregar user stories

### # INTEGRATED — US-NEW-019 — Consolidar RAID (vista unificada)

**Estado de integración:** INTEGRATED en EP006 (US-NEW-019). XLSX con
  4 sheets queda como follow-up; CSV cumple el caso de uso.

---

### # PENDING (referencia) — US-NEW-019

**Criterios de aceptación:**
- [ ] Tab "RAID" en el detalle del proyecto que muestra 4 sub-tabs: Riesgos (R) | Acciones (A) | Incidentes (I) | Decisiones (D).
- [ ] Riesgos: tabla `risks`.
- [ ] Acciones: tabla `issues WHERE type='action'`.
- [ ] Incidentes: tabla `issues WHERE type='issue'` (renombrar `type` valor a 'incident' — ver DECISIONS.md DEC-007).
- [ ] Decisiones: tabla `issues WHERE type='decision'`.
- [ ] Vista summary del RAID: contador por categoría en el header del tab.
- [ ] Export RAID: XLSX con 4 sheets (una por letra), descargable.

---

### # INTEGRATED — US-NEW-020 — Categorías de documentos actualizadas

**Estado de integración:** INTEGRATED en EP006 (US-NEW-020).
  - Enum extendido: charter | plan | raid_export | transcript | minute |
    report | lesson | contract | other.
  - Filtro `?category=` en el GET de documents.
  - PATCH `/api/v1/documents/{id}` para retaggar sin subir archivo.
  - Charter ya se guarda como `category='charter'` (US-NEW-013).
  - RAID export → `raid_export` y minutas → `minute` se usarán desde UI
    cuando las flows específicas lo expongan (sin cambios de schema
    adicionales).

---

### # PENDING (referencia) — US-NEW-020

**Criterios de aceptación:**
- [ ] Campo `category` en documentos acepta: `charter` | `plan` | `raid_export` | `transcript` | `minute` | `report` | `lesson` | `contract` | `other`.
- [ ] Al generar charter → se guarda copia PDF en documentos con `category='charter'`.
- [ ] Export RAID → se guarda en documentos con `category='raid_export'`.
- [ ] Minutas generadas → referencia en documentos con `category='minute'`.

---

### # INTEGRATED — US-NEW-021 — Consolidar pestañas de Minutas en 1

**Estado de integración:** INTEGRATED en EP006 (US-NEW-021). Sidebar
  unificado; CTA "Generar con IA" dentro de la pestaña Minutas.

---

### # PENDING (referencia) — US-NEW-021

**Criterios de aceptación:**
- [ ] Si actualmente hay 2 pestañas separadas para minutas (ej: "Minutas" y "Minuta IA"), unificarlas en 1.
- [ ] La pestaña única "Minutas" tiene: listado de minutas pasadas + botón "Nueva minuta" (manual) + botón "Generar con IA" (si IA habilitada).
- [ ] La minuta generada con IA entra al mismo flujo de revisión/edición que la manual.

---

### # INTEGRATED — US-NEW-022 — Módulo Reportes dentro del proyecto

**Estado de integración:** INTEGRATED en EP006 (US-NEW-022). CRUD manual
  + reutilización del generador IA + editor con secciones editables.

---

### # PENDING (referencia) — US-NEW-022

**Como** PM
**Quiero** generar y gestionar reportes del proyecto
**Para** comunicar avance a stakeholders periódicamente.

**Criterios de aceptación:**
- [ ] Tab "Reportes" en el detalle del proyecto.
- [ ] Listado de reportes pasados con: fecha, periodo (semanal/mensual), estado (borrador/enviado), destinatarios.
- [ ] Botón "Nuevo Reporte" → formulario con: periodo, destinatarios, include_pdf toggle.
- [ ] "Generar con IA" → invoca EP008 `POST /projects/{id}/reports/draft`.
- [ ] Reporte manual: editor tipo Notion con secciones predefinidas.
- [ ] Secciones sugeridas: Resumen Ejecutivo, Avance del Plan, Acciones Pendientes, Decisiones Requeridas, Riesgos Top.
- [ ] Periodicidades: diario, semanal, mensual.
- [ ] Caso de uso "lunes de persecución": reporte semanal que lista acciones que el PM debe perseguir esa semana.

**Test Cases:**
- `TC-NEW-027` (E2E) — Crear reporte manual → guardar → enviar.
- `TC-NEW-028` (integration) — Reporte incluye top acciones vencidas ordenadas por fecha compromiso.

**Estado de integración:** # PENDING en EP006

---

## EP007-admin.md — Agregar user stories

### # INTEGRATED — US-NEW-023 — Gestión de Tenant (acciones propuestas)

**Estado de integración:** INTEGRATED en EP007 (US-NEW-023).

---

### # PENDING (referencia) — US-NEW-023

**Propuesta de acciones disponibles para Admin/Senior PMO en su propio tenant:**

**Criterios de aceptación:**
- [ ] Sección "Mi Tenant" en `/admin/tenant`:
  - Información del tenant: nombre, logo, slug (readonly).
  - Configuración (ya en US-041): idioma, moneda, timezone, IA, etc.
  - Plan actual (readonly, con link a "Contactar soporte").
  - Estadísticas del tenant: usuarios activos, proyectos, storage usado.
- [ ] Acciones disponibles:
  - Editar nombre y logo del tenant.
  - Cambiar configuraciones (US-041 existente).
  - Ver uso de storage.
  - *(NO incluir: eliminar tenant, cambiar slug — solo superadmin)*.

---

### # INTEGRATED — US-NEW-024 — Gestión jerarquía org completa (BU + Depto) en Admin

**Estado de integración:** INTEGRATED en EP007 (US-NEW-024). Tree inline
  con CRUD de BU/Depto + botón "Ver proyectos".

---

### # PENDING (referencia) — US-NEW-024

**Criterios de aceptación:**
- [ ] En `/admin/organizations`, expandir US-039 para incluir gestión de BUs y Deptos.
- [ ] Vista de tree: Org → BUs → Deptos con acciones inline (editar, desactivar).
- [ ] Formulario de edición de org incluye sección colapsable de BUs y Deptos.
- [ ] Crear/editar/desactivar BU desde el panel admin (llama a endpoints de EP002).
- [ ] Crear/editar/desactivar Depto desde el panel admin (llama a endpoints de EP002).
- [ ] Botón "Ver proyectos de esta org" en el panel.

**Estado de integración:** # PENDING en EP007

---

## EP010-superadmin-panel.md — Agregar a user stories existentes

### # INTEGRATED — US-NEW-025 — Iconos + jerarquía en paneles de tenant

**Estado de integración:** INTEGRATED en EP010 (US-NEW-025). Backend
  expone 4 counts por tenant + `hierarchy` en drill-down. UI con
  iconos y status dot.

---

### # PENDING (referencia) — Fix en US-053 y US-055 (iconos y jerarquía en paneles de tenant)

**Criterios de aceptación (adicionales):**
- [ ] Cards de tenant en lista y en drill-down muestran iconos por categoría:
  - 🏢 Organizaciones (count)
  - 👥 Usuarios (count)
  - 📋 Programas (count)
  - 📁 Proyectos (count)
- [ ] Iconos SVG simples del design system, no emoji.
- [ ] En drill-down del tenant, sección Overview muestra la jerarquía:
  - Org count → BU count → Depto count → Programa count → Proyecto count.
- [ ] Indicador activo/inactivo: punto verde (activo) / rojo (inactivo) visible en cada card de tenant.

### # INTEGRATED — US-NEW-026 — Visión General = Tenants + Health

**Estado de integración:** INTEGRATED en EP010 (US-NEW-026).

---

### # PENDING (referencia) — Fix en dashboard US-053 (Visión General = Tenants + Health)

**Criterios de aceptación (adicionales):**
- [ ] Página principal `/superadmin` combina: KPI de tenants + widget de Health de sistemas.
- [ ] No son páginas separadas; Health aparece como sección inferior del dashboard principal.
- [ ] Esto reemplaza tener "Visión General" y "Health" como rutas separadas (si así estaba antes).

**Estado de integración:** # PENDING en EP010

---

## EP013-navigation-refactor.md — Bloque 9 (issue #17)

Documento completo con criterios de aceptación y test cases en
[`EP013-navigation-refactor.md`](./EP013-navigation-refactor.md). Resumen:

| US | Título | Estado |
|---|---|---|
| US-NEW-031 | Upload y display del logo del tenant en chrome | # PENDING |
| US-NEW-032 | Restructurar sidebar principal (drill-down real) | # PENDING |
| US-NEW-033 | Panel de organización → página de recursos reales (fix bug) | # PENDING |
| US-NEW-034 | Página resumen de programa (KPIs + proyectos) | # PENDING |
| US-NEW-035 | Tabs inline en detalle de proyecto (supersede US-NEW-017) | # PENDING |
| US-NEW-036 | Restructurar sidebar Admin (4 ítems raíz; fusionar Mi Tenant + Panel + Configuración) | # PENDING |

Decisiones a registrar en DECISIONS.md al cierre: DEC-011, DEC-012, DEC-013.

---

## EP014-operational-deliverables.md — Bloque 10 (issue #18)

Documento completo en [`EP014-operational-deliverables.md`](./EP014-operational-deliverables.md).
Resumen:

| US | Título | Estado |
|---|---|---|
| US-NEW-037 | Infra compartida de exportación a PDF (WeasyPrint) | # PENDING |
| US-NEW-038 | Reporte de Avance de Proyecto (Python, BD, PDF) | # PENDING |
| US-NEW-039 | Reporte de Seguimiento de Actividades (Python, BD, PDF) | # PENDING |
| US-NEW-040 | Formato estandarizado + export (.docx/.md/.txt/.pdf) de Minuta IA | # PENDING |

**Criterio explícito del usuario:** los reportes **no dependen de IA** — son Python
+ Jinja2 sobre datos de la BD. La IA sigue siendo opcional para el módulo
"reporte narrativo" (EP006/EP008); los de este bloque son motor separado.

Decisiones a registrar: DEC-014, DEC-015, DEC-016.

---

## EP012-db-migration.md — Bloque 12 (reestructurado)

La épica cambia de "migración zero-downtime" a **"instalación productivo en
Hostgator MySQL + compatibilidad dialect-agnostic del código"**:

| US | Título | Estado |
|---|---|---|
| US-NEW-029 | Compatibilidad MySQL del código (reemplazar PG-específicos) | # PENDING |
| US-NEW-030 | Setup Hostgator MySQL + pipeline de deploy productivo (fresh install) | # PENDING |

**Staging se queda en Railway Postgres**; productivo es instalación fresca. DEC-017,
DEC-018, DEC-019 a registrar.

---

## EP015-superadmin-nav-refactor.md — Bloque 11 (issue #19)

Documento completo en [`EP015-superadmin-nav-refactor.md`](./EP015-superadmin-nav-refactor.md).

| US | Título | Estado |
|---|---|---|
| US-NEW-041 | Sidebar super admin aislado (4 ítems raíz) | # PENDING |
| US-NEW-042 | Página `/superadmin/users` cross-tenant | # PENDING |
| US-NEW-043 | Visión General con Health al top | # PENDING |

DEC-020/021/022 a registrar.

---

## EP016-local-ai-tunnel.md — Bloque 12 (modelo IA local)

Documento completo en [`EP016-local-ai-tunnel.md`](./EP016-local-ai-tunnel.md). Uso: runbook operativo + config por-tenant para conectar el worker EP008 a un Ollama local expuesto vía Cloudflare Tunnel.

| US | Título | Estado |
|---|---|---|
| US-NEW-044 | Runbook `docs/ai/local-ollama-setup.md` paso a paso | # PENDING |
| US-NEW-045 | Config + smoke test del túnel + fallback a cascada | # PENDING |

DEC-023/024/025 a registrar. Alimenta EP014 US-NEW-040 (minuta estandarizada) con un proveedor IA privado y sin costo por token.
