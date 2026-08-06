---
responsable: propietario
estado: vigente
revisado: 2026-08-04
revisar_cada: 90d
---

# Épicas — PMO-aaS

**ID:** `DOC-EPICS`
**Última actualización:** 2026-08-04
**Metodología:** 1 US = 1 commit = 1 sesión de trabajo

> **Este archivo es lo único de `docs/epics/` que se carga en toda sesión**
> (`CLAUDE.md` §1). El epic entero se abre **cuando se va a tocar**, no antes:
> cargarlo «por si acaso» metía un documento funcional completo en el contexto
> permanente antes de saber si se iba a usar. Aquí está lo que hace falta para
> decidir cuál abrir, y nada más (MCA CTX-04).

---

## Índice de épicas

| # | Épica | Estado | Dependencias |
|---|---|---|---|
| [EP001](./EP001-auth-users.md) | Login y gestión de usuarios | MVP | — |
| [EP002](./EP002-org-hierarchy.md) | Jerarquía org/BU/depto/programa/proyecto | MVP | EP001 |
| [EP003](./EP003-project-requests.md) | Solicitud, aprobación y Project Charter | MVP | EP001, EP002 |
| [EP004](./EP004-dashboard.md) | Dashboard y KPIs | MVP | EP001, EP002, EP005 |
| [EP005](./EP005-projects.md) | Gestión de proyectos | MVP | EP001, EP002, EP003 |
| [EP006](./EP006-project-modules.md) | Módulos del proyecto (RAID, Docs, Minutas, Reportes) | MVP | EP005 |
| [EP007](./EP007-admin.md) | Panel de administración | MVP | EP001, EP002 |
| [EP008](./EP008-ai.md) | IA: minutas y reportes | MVP | EP005, EP006 |
| [EP009](./EP009-ms-project.md) | Integración Microsoft Project | MVP | EP005 |
| [EP010](./EP010-superadmin-panel.md) | Panel Super Admin | MVP | EP001, EP002 |
| [EP011](./EP011-notifications.md) | Sistema de notificaciones | POST-MVP | EP001, EP003 |
| ~~[EP012](./EP012-db-migration.md)~~ | ❌ **CANCELADA** — migración HostGator MySQL (DEC-013). Productivo corre 100% en Railway. | — | — |
| [EP013](./EP013-navigation-refactor.md) | Refactor de navegación (sidebar + admin + tabs inline) — issue #17 | v1.1 | EP001, EP002, EP005, EP006, EP007, EP010 |
| [EP014](./EP014-operational-deliverables.md) | Entregables operativos (reportes Python sin IA + PDF + formato minuta) — issue #18 | v1.1 | EP005, EP006, EP008 |
| [EP015](./EP015-superadmin-nav-refactor.md) | Refactor de navegación del SuperAdmin — issue #19 | v1.1 | EP010 |
| ~~[EP016](./EP016-local-ai-tunnel.md)~~ | ❌ **ARCHIVADA** — IA local (Ollama + Cloudflare/Tailscale). Superseded por DEC-017; código eliminado en BUG-053 (2026-05-08). | — | — |
| [EP017](./EP017-project-directory.md) | Directorio de proyecto (áreas, equipos, actores, participaciones) | v1.2 | EP005, EP006 |
| [EP018](./EP018-documents-artifacts.md) | Documentos y artefactos de proyecto | v1.3 | EP005, EP006 |
| [EP019](./EP019-changes-approval.md) | Gestión de cambios + flujo de aprobación | v1.4 | EP005, EP006 |
| [EP020](./EP020-report-builder.md) | Report Builder (Niveles 1, 2, 4) + catálogo 22 secciones | v1.5 | EP005, EP006, EP007, EP008, EP014, EP018 |

---

## Lo que no se repite aquí

| Tema | Dónde vive |
|---|---|
| Convenciones de identificación (`US-###`, `TC-###`, estados) | `CLAUDE.md` §2 |
| Mecánica de ejecución y la regla 1 US = 1 commit | `CLAUDE.md` §3 y §7 |
| Cómo se cierra un item | Skill `cerrar-item` |
| Cómo se comprueba que funciona | Skill `verificar` |

Lo tenía duplicado hasta 2026-08-04. Un hecho en dos sitios es un hecho que
envejece en uno de los dos (MCA CTX-06).

---

## Archivos de soporte

| Archivo | Propósito |
|---|---|
| [SPRINT.md](./SPRINT.md) | Tarea activa + próximas 3 en cola |
| [DB-CHANGES.md](./DB-CHANGES.md) | Cambios de schema agrupados por epic |
| [DECISIONS.md](./DECISIONS.md) | Decisiones arquitectónicas y su rationale |

---

## Orden de ejecución de los bloques

> **Nota 2026-05-23:** este roadmap planeado quedó superado por la
> ejecución real. Los bloques originales 9-11 (EP013, EP014, EP015)
> están **DONE**. El bloque 12 (EP016 Ollama) y bloque 14 (EP012
> MySQL) fueron **cancelados** (ver DEC-013 y BUG-053). EP011
> (notificaciones) se entregó como parte del trabajo operativo
> (`apps/api/app/api/v1/endpoints/notifications.py`, `notification-bell.tsx`).
>
> Para ver el estado vigente del sprint y los issues abiertos,
> consultar `docs/project-management/SPRINT.md`.

### Cambios clave en el roadmap original

- **EP012** (migración MySQL HostGator) → **CANCELADA** en DEC-013.
  Productivo corre 100% en Railway Postgres.
- **EP016** (IA local Ollama via tunnel/tailnet) → **ARCHIVADA**.
  Superseded por DEC-017 (modos `platform`/`byo`) y eliminada del
  código por BUG-053 (2026-05-08). `OllamaProvider` ya no existe.
- **US-017** (tabs inline) → superseded por US-035 (EP013), DONE.
- Nuevas epics posteriores: EP017 (project directory),
  EP018 (documents-artifacts), EP019 (changes approval),
  EP020 (report builder Niveles 1/2/4). Ver tabla principal arriba.