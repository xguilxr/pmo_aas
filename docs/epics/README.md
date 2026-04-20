# Épicas — PMO-aaS

**ID:** `DOC-EPICS`  
**Última actualización:** 2026-04-20  
**Metodología:** 1 US = 1 commit = 1 sesión de trabajo

---

## Índice de épicas

| # | Épica | Estado | Cambios v2 | Dependencias |
|---|---|---|---|---|
| [EP001](./EP001-auth-users.md) | Login y gestión de usuarios | MVP | ⚠️ ACTUALIZADA | — |
| [EP002](./EP002-org-hierarchy.md) | Jerarquía org/BU/depto/programa/proyecto | MVP | 🔴 CAMBIO MAYOR | EP001 |
| [EP003](./EP003-project-requests.md) | Solicitud, aprobación y Project Charter | MVP | ⚠️ ACTUALIZADA | EP001, EP002 |
| [EP004](./EP004-dashboard.md) | Dashboard y KPIs | MVP | ⚠️ ACTUALIZADA | EP001, EP002, EP005 |
| [EP005](./EP005-projects.md) | Gestión de proyectos | MVP | ⚠️ ACTUALIZADA | EP001, EP002, EP003 |
| [EP006](./EP006-project-modules.md) | Módulos del proyecto (RAID, Docs, Minutas, Reportes) | MVP | ⚠️ ACTUALIZADA | EP005 |
| [EP007](./EP007-admin.md) | Panel de administración | MVP | ⚠️ ACTUALIZADA | EP001, EP002 |
| [EP008](./EP008-ai.md) | IA: minutas y reportes | MVP | ✅ SIN CAMBIOS | EP005, EP006 |
| [EP009](./EP009-ms-project.md) | Integración Microsoft Project | MVP | ✅ SIN CAMBIOS | EP005 |
| [EP010](./EP010-superadmin-panel.md) | Panel Super Admin | MVP | ⚠️ ACTUALIZADA | EP001, EP002 |
| [EP011](./EP011-notifications.md) | Sistema de notificaciones | POST-MVP | 🆕 NUEVA | EP001, EP003 |
| [EP012](./EP012-db-migration.md) | Instalación productivo Hostgator MySQL (code-compat + fresh install) | POST-MVP / release v1.0 | 🆕 NUEVA | Todas |
| [EP013](./EP013-navigation-refactor.md) | Refactor de navegación (sidebar + admin + tabs inline) — issue #17 | v1.1 | 🆕 NUEVA | EP001, EP002, EP005, EP006, EP007, EP010 |
| [EP014](./EP014-operational-deliverables.md) | Entregables operativos (reportes Python sin IA + PDF + formato minuta) — issue #18 | v1.1 | 🆕 NUEVA | EP005, EP006, EP008 |

---

## Convenciones de identificación

- **EP-XXX** — épica (3 dígitos).
- **US-XXX** — user story global, única en todo el producto.
- **TC-XXX** — test case, único global.
- **TC-MT-XXX** — test case de multi-tenant isolation (transversal).
- **# PENDING** — user story pendiente de implementar.
- **# IN-PROGRESS** — user story en desarrollo activo.
- **# DONE** — user story implementada y con tests verdes.

---

## Mecánica de ejecución (Claude Code)

```
1 US = 1 commit — luego continúa con la siguiente sin parar
```

**Prompt estándar para Claude Code:**
```
Lee SPRINT.md y los archivos de epic necesarios.
Trabaja el backlog en orden. Por cada US:
  1. Implementa la US completa.
  2. Haz commit: "feat([módulo]): US-XXX — [título corto]"
  3. Marca la US como DONE en SPRINT.md.
  4. Mueve la siguiente a IN-PROGRESS.
  5. Continúa con la siguiente US sin esperar.
Sigue hasta que no queden US en QUEUE o llegues al límite de contexto.
No acumules cambios de varias US en un solo commit.
```

**Reglas:**
- Cada US tiene su propio commit antes de arrancar la siguiente.
- Claude Code lee solo los archivos de epic relevantes + SPRINT.md.
- Si una US requiere migración de BD, consultar DB-CHANGES.md primero.
- Si hay duda de arquitectura, consultar DECISIONS.md antes de implementar.
- Si el contexto se agota a mitad de una US, hacer commit del avance parcial con prefijo `wip:` y anotar en SPRINT.md dónde quedó.

---

## Archivos de soporte

| Archivo | Propósito |
|---|---|
| [SPRINT.md](./SPRINT.md) | Tarea activa + próximas 3 en cola |
| [DB-CHANGES.md](./DB-CHANGES.md) | Cambios de schema agrupados por epic |
| [DECISIONS.md](./DECISIONS.md) | Decisiones arquitectónicas y su rationale |

---

## Resumen de gaps identificados (v1 → v2)

### Cambios de BD requeridos (ver DB-CHANGES.md)
- Nueva tabla `business_units` (EP002)
- Nueva tabla `departments` (EP002)
- `programs` ahora tiene FK a `department_id` (no directo a org)
- `projects` puede tener FK a `department_id` además de `program_id`
- `project_requests` nuevos campos: `requester_email`, `sponsor_email`, `key_people`, `if_not_done`, `observations`
- `project_charter` nueva tabla (EP003)
- `project_areas` nueva tabla (EP005)
- `notifications` nueva tabla (EP011)

### Rol Senior PMO
`Admin` Y `Senior PMO` tienen permisos de administrador. Esto afecta middleware de rutas `/admin` en EP001 y EP007.

---

## Orden de ejecución de los bloques pendientes

Los bloques 1-8 están DONE. Lo que queda, en orden:

| Bloque | Epic | Issue origen | Alcance resumido |
|---|---|---|---|
| **9** | EP013 | #17 | Refactor de navegación: sidebar principal con drill-down real, sidebar admin consolidado, logo del tenant en chrome, tabs inline en detalle de proyecto (supersede US-NEW-017) |
| **10** | EP014 | #18 | Reportes operativos Python sin IA (Avance + Seguimiento) con PDF descargable; formato estandarizado + export de Minuta IA (.docx/.md/.txt/.pdf) |
| **11** | EP011 | — | Notificaciones (POST-MVP): tabla + in-app center + email via Resend |
| **12** | EP012 | — | Instalación productivo Hostgator MySQL (fresh install). Staging sigue en Railway Postgres |

### Ajustes clave respecto a la versión anterior del roadmap
- **US-NEW-017** (tabs inline) queda **superseded** por US-NEW-035 (EP013). Sus dependencias están DONE, se construye como parte del bloque 9.
- **EP012** ya no es "migración zero-downtime PG→MySQL". Es **fresh install** productivo en Hostgator MySQL + compatibilidad dialect-agnostic del código. Staging se queda en Railway Postgres (DEC-017/018/019).
- Issues **#17** y **#18** quedan incorporados antes de los bloques POST-MVP previos.