---
tipo: epica
responsable: propietario
estado: vigente
revisado: 2026-08-12
revisar_cada: 90d
---

# Épicas — PMO-aaS

**ID:** `DOC-EPICS`
**Última actualización:** 2026-08-12
**Metodología:** 1 US = 1 commit = 1 sesión de trabajo

> Este archivo es lo único de `docs/epics/` que se carga en toda sesión
> (`CLAUDE.md` §1). El epic entero se abre **cuando se va a tocar**, no antes
> (MCA CTX-04). Aquí está lo necesario para decidir cuál abrir, y nada más.

---

## Índice de épicas

| # | Épica | Estado | Dependencias |
|---|---|---|---|
| [EP001](./EP001-auth-users.md) | Login y gestión de usuarios | MVP | — |
| [EP002](./EP002-org-hierarchy.md) | Jerarquía org → portafolio ⊃ programa → proyecto | MVP | EP001 |
| [EP003](./EP003-project-requests.md) | Solicitud, aprobación y Project Charter | MVP | EP001, EP002 |
| [EP004](./EP004-dashboard.md) | Dashboard y KPIs | MVP | EP001, EP002, EP005 |
| [EP005](./EP005-projects.md) | Gestión de proyectos | MVP | EP001, EP002, EP003 |
| [EP006](./EP006-project-modules.md) | Módulos del proyecto (RAID, Docs, Minutas, Reportes) | MVP | EP005 |
| [EP007](./EP007-admin.md) | Panel de administración | MVP | EP001, EP002 |
| [EP008](./EP008-ai.md) | IA: minutas y reportes | MVP | EP005, EP006 |
| [EP009](./EP009-ms-project.md) | Integración Microsoft Project | MVP | EP005 |
| [EP010](./EP010-superadmin-panel.md) | Panel Super Admin | MVP | EP001, EP002 |
| [EP011](../archive/epics/EP011-notifications.md) | Sistema de notificaciones | archivada 2026-08-12 | EP001, EP003 |
| ~~[EP012](../archive/cancelled-epics/EP012-db-migration.md)~~ | ❌ **CANCELADA** — migración HostGator MySQL (DEC-013). Productivo corre 100% en Railway. | — | — |
| [EP013](../archive/epics/EP013-navigation-refactor.md) | Refactor de navegación (sidebar + admin + tabs inline) — issue #17 | archivada 2026-08-12 | EP001, EP002, EP005, EP006, EP007, EP010 |
| [EP014](../archive/epics/EP014-operational-deliverables.md) | Entregables operativos (reportes Python sin IA + PDF + formato minuta) — issue #18 | archivada 2026-08-12 | EP005, EP006, EP008 |
| [EP015](../archive/epics/EP015-superadmin-nav-refactor.md) | Refactor de navegación del SuperAdmin — issue #19 | archivada 2026-08-12 | EP010 |
| ~~[EP016](../archive/cancelled-epics/EP016-local-ai-tunnel.md)~~ | ❌ **ARCHIVADA** — IA local (Ollama + Cloudflare/Tailscale). Superseded por DEC-017; código eliminado en BUG-053 (2026-05-08). | — | — |
| [EP017](./EP017-project-directory.md) | Directorio de proyecto (áreas, equipos, actores, participaciones) | v1.2 | EP005, EP006 |
| [EP018](./EP018-documents-artifacts.md) | Documentos y artefactos de proyecto | v1.3 | EP005, EP006 |
| [EP019](./EP019-changes-approval.md) | Gestión de cambios + flujo de aprobación | v1.4 | EP005, EP006 |
| [EP020](./EP020-report-builder.md) | Report Builder (Niveles 1, 2, 4) + catálogo 22 secciones | v1.5 | EP005, EP006, EP007, EP008, EP014, EP018 |
| [EP021](./EP021-catalogo-de-ia.md) | Catálogo de IA y roles de agente (4 decisiones tomadas; US-223–226 listas) | v2.0 | EP008 |

El estado vigente del sprint y los issues abiertos:
`docs/project-management/SPRINT.md`.

---

## Lo que no se repite aquí

| Tema | Dónde vive |
|---|---|
| Convenciones de identificación (`US-###`, `TC-###`, estados) | `CLAUDE.md` §2 |
| Mecánica de ejecución y la regla 1 US = 1 commit | `CLAUDE.md` §3 y §7 |
| Cómo se cierra un item | Skill `cerrar-item` |
| Cómo se comprueba que funciona | Skill `verificar` |

---

## Archivos de soporte

| Archivo | Propósito |
|---|---|
| [SPRINT.md](../project-management/SPRINT.md) | Tarea activa + cola |
| [DB-CHANGES.md](./DB-CHANGES.md) | Cambios de schema agrupados por epic |
| [DECISIONS.md](./DECISIONS.md) | Decisiones arquitectónicas y su rationale |
