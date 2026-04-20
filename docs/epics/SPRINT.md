# SPRINT.md — Tarea activa

> **Regla:** Claude Code lee SOLO este archivo + el epic relevante. 1 US = 1 commit. Al terminar, marcar DONE y mover la siguiente a IN-PROGRESS.

---

## 🔴 IN-PROGRESS

```
— Sin US activa —

Bloques 1-8 (EP001–EP007, EP010) completos en esta rama
(26 US implementadas).

Siguen pendientes por orden:
  Bloque 9  — EP013 Refactor de navegación (issue #17)
  Bloque 10 — EP014 Entregables operativos (issue #18)
  Bloque 11 — EP011 Notificaciones (POST-MVP)
  Bloque 12 — EP012 Instalación productivo Hostgator MySQL

Nota sobre US-NEW-017 (tabs inline, diferida en US-NEW-016):
sus dependencias están DONE pero el issue #17 pide un alcance más
amplio que la reemplaza (ver US-NEW-035 en EP013). US-NEW-017 queda
marcada como **superseded** — se implementa como parte del bloque 9.
```

---

## ⏳ QUEUE (próximas 3)

| # | US | Epic | Título | Tipo |
|---|---|---|---|---|
| 1 | US-NEW-031 | EP013 | Upload y display del logo del tenant en chrome | Bloque 9 |
| 2 | US-NEW-032 | EP013 | Restructurar sidebar principal (drill-down real) | Bloque 9 |
| 3 | US-NEW-033 | EP013 | Panel de organización → página de recursos reales | Bloque 9 |

> Backlog completo del bloque 9 al 12 está listado abajo, en orden.

---

## ✅ DONE (historial reciente)

| US | Título | Commit | Fecha |
|---|---|---|---|
| US-NEW-001 | Setup inicial — análisis de gaps v1→v2 | `docs: gap analysis v2` | 2026-04-20 |
| US-NEW-002 | Tablas business_units + departments + FKs | `feat(org): US-NEW-002 — tablas BU y departments con FK` | 2026-04-20 |
| US-NEW-003 | CRUD Business Units API | `feat(org): US-NEW-003 — CRUD Business Units API` | 2026-04-20 |
| US-NEW-004 | CRUD Departments API | `feat(org): US-NEW-004 — CRUD Departments API` | 2026-04-20 |
| US-NEW-005 | Sidebar org tree nav (Frontend) | `feat(web): US-NEW-005 — sidebar org tree nav` | 2026-04-20 |
| US-NEW-006 | Vista paneles de organizaciones (cards + métricas) | `feat(web): US-NEW-006 — paneles de organizaciones` | 2026-04-20 |
| US-BUG-001 | Fix 404 en página de Programas | `fix(web): US-BUG-001 — crea /admin/programs` | 2026-04-20 |
| US-NEW-007 | Toggle dark/light mode en dropdown usuario | `feat(web): US-NEW-007 — toggle dark/light en user dropdown` | 2026-04-20 |
| US-NEW-008 | Toggle de idioma (ES/EN) en dropdown usuario | `feat(web): US-NEW-008 — toggle idioma en user dropdown` | 2026-04-20 |
| US-NEW-010 | Color chrome #182e4e + Senior PMO como admin | `feat(auth): US-NEW-010 — chrome #182e4e + Senior PMO admin` | 2026-04-20 |
| US-NEW-009 | Página /account (perfil + cambiar password) | `feat(web): US-NEW-009 — página /account perfil + password` | 2026-04-20 |
| US-NEW-011 | Campos adicionales en solicitud + FK BU/Depto | `feat(requests): US-NEW-011 — campos adicionales en solicitud` | 2026-04-20 |
| US-NEW-012 | Project Charter: tabla + generación al aprobar | `feat(requests): US-NEW-012 — project_charters + auto-gen` | 2026-04-20 |
| US-NEW-013 | Charter aparece como documento del proyecto | `feat(requests): US-NEW-013 — charter como documento` | 2026-04-20 |
| US-NEW-014 | Filtro de organización en dashboard | `feat(dashboard): US-NEW-014 — filtro organización` | 2026-04-20 |
| US-BUG-002 | Fix distorsión en gráficas de barra | `fix(dashboard): US-BUG-002 — distorsión gráficas barra` | 2026-04-20 |
| US-NEW-015 | KPIs respetan jerarquía de roles | `feat(dashboard): US-NEW-015 — KPIs respetan jerarquía roles` | 2026-04-20 |
| US-BUG-003 | Fix layout Plan vs Real + columna PM | `fix(dashboard): US-BUG-003 — layout Plan vs Real` | 2026-04-20 |
| US-NEW-016 | Unificar Plan + Gantt en una pestaña | `feat(projects): US-NEW-016 — unificar plan + gantt` | 2026-04-20 |
| US-NEW-018 | Módulo Áreas/Organigrama del proyecto | `feat(projects): US-NEW-018 — módulo áreas del proyecto` | 2026-04-20 |
| US-NEW-019 | Consolidar RAID (vista unificada) | `feat(projects): US-NEW-019 — consolidar RAID` | 2026-04-20 |
| US-NEW-020 | Categorías de documentos actualizadas | `feat(projects): US-NEW-020 — categorías de documentos` | 2026-04-20 |
| US-NEW-021 | Consolidar pestañas de Minutas | `feat(projects): US-NEW-021 — consolidar minutas` | 2026-04-20 |
| US-NEW-022 | Módulo Reportes dentro del proyecto | `feat(projects): US-NEW-022 — módulo reportes` | 2026-04-20 |
| US-NEW-023 | Gestión de Tenant (info + stats + editar) | `feat(admin): US-NEW-023 — gestión de tenant` | 2026-04-20 |
| US-NEW-024 | Gestión jerarquía org (BU + Depto) en Admin | `feat(admin): US-NEW-024 — jerarquía org en admin` | 2026-04-20 |
| US-NEW-025 | Iconos en paneles de tenant + jerarquía | `feat(superadmin): US-NEW-025 — iconos en paneles` | 2026-04-20 |
| US-NEW-026 | Visión General = Tenants + Health unificados | `feat(superadmin): US-NEW-026 — visión general unificada` | 2026-04-20 |

---

## 📋 Backlog ordenado por prioridad

### Bloque 1 — Jerarquía org (EP002) — BLOQUEANTE para todo lo demás
- [x] US-NEW-002 — Migración BD: tablas BU + Depto + FKs ✅
- [x] US-NEW-003 — CRUD Business Units (API) ✅
- [x] US-NEW-004 — CRUD Departments (API) ✅
- [x] US-NEW-005 — Sidebar org nav (Frontend) ✅
- [x] US-NEW-006 — Vista paneles de organizaciones (Frontend) ✅
- [x] US-BUG-001 — Fix 404 en Programas ✅

### Bloque 2 — Topbar y UX base (EP001)
- [x] US-NEW-007 — Toggle dark/light en dropdown usuario ✅
- [x] US-NEW-008 — Toggle idioma en dropdown usuario ✅
- [x] US-NEW-009 — Página administrar cuenta (perfil + cambiar password) ✅
- [x] US-NEW-010 — Color chrome #182e4e + Senior PMO = admin ✅

### Bloque 3 — Project Charter (EP003)
- [x] US-NEW-011 — Campos adicionales en solicitud (correos, personas clave, etc.) ✅
- [x] US-NEW-012 — Project Charter: tabla + generación al aprobar ✅
- [x] US-NEW-013 — Charter aparece como documento en el proyecto ✅

### Bloque 4 — Dashboard fixes (EP004)
- [x] US-BUG-002 — Fix distorsión gráficas de barra ✅
- [x] US-NEW-014 — Filtro organización en dashboard ✅
- [x] US-NEW-015 — KPIs respetan jerarquía de roles ✅
- [x] US-BUG-003 — Fix layout Plan vs Real (filtros horizontales + columna PM) ✅

### Bloque 5 — Proyecto detalle (EP005)
- [x] US-NEW-016 — Unificar Plan + Gantt en una pestaña ✅
- [~] US-NEW-017 — Tabs inline para módulos del proyecto → **SUPERSEDED** por US-NEW-035 (EP013, bloque 9)
- [x] US-NEW-018 — Módulo Área/Organigrama del proyecto ✅

### Bloque 6 — RAID y módulos (EP006)
- [x] US-NEW-019 — Consolidar RAID (Riesgos+Acciones+Incidentes+Decisiones) ✅
- [x] US-NEW-020 — Categorías de documentos actualizadas ✅
- [x] US-NEW-021 — Consolidar pestañas de Minutas en 1 ✅
- [x] US-NEW-022 — Módulo Reportes dentro del proyecto ✅

### Bloque 7 — Admin (EP007)
- [x] US-NEW-023 — Gestión de tenant (propuesta de acciones) ✅
- [x] US-NEW-024 — Gestión jerarquía org completa (BU + Depto) ✅

### Bloque 8 — SuperAdmin (EP010)
- [x] US-NEW-025 — Iconos en paneles de tenant ✅
- [x] US-NEW-026 — Visión General = Tenants + Health unidos ✅

---

### Bloque 9 — Refactor de navegación (EP013) — issue #17
**Orden de ejecución** (1 US por commit, en este orden):
- [ ] US-NEW-031 — Upload y display del logo del tenant en chrome
- [ ] US-NEW-032 — Restructurar sidebar principal (drill-down real; quitar "Módulos de proyecto" y duplicado de Organizaciones)
- [ ] US-NEW-033 — Panel de organización → página de recursos reales (fix bug + enhancement)
- [ ] US-NEW-034 — Página resumen de programa (KPIs + lista de proyectos)
- [ ] US-NEW-035 — Tabs inline en detalle de proyecto (supersede US-NEW-017)
- [ ] US-NEW-036 — Restructurar sidebar Admin (fusionar Mi Tenant + Panel + Configuración; 4 ítems raíz)

### Bloque 10 — Entregables operativos (EP014) — issue #18
- [ ] US-NEW-037 — Infra compartida de exportación a PDF (WeasyPrint)
- [ ] US-NEW-038 — Reporte de Avance de Proyecto (Python, BD, PDF)
- [ ] US-NEW-039 — Reporte de Seguimiento de Actividades (Python, BD, PDF)
- [ ] US-NEW-040 — Formato estandarizado + export (.docx/.md/.txt/.pdf) de Minuta IA

### Bloque 11 — Notificaciones (EP011) — POST-MVP
- [ ] US-NEW-027 — Tabla notifications + in-app center
- [ ] US-NEW-028 — Email notifications via Resend

### Bloque 12 — Instalación productivo Hostgator MySQL (EP012) — release v1.0
- [ ] US-NEW-029 — Compatibilidad MySQL del código (dialect-agnostic; reemplazar PG-específicos)
- [ ] US-NEW-030 — Setup Hostgator MySQL + pipeline de deploy productivo (fresh install)

> EP012 **no es migración desde un productivo previo**: staging se queda en
> Railway Postgres y productivo arranca directamente como instalación
> fresca en Hostgator MySQL. Ver DEC-017/018/019 en EP012 y DECISIONS.md.

---

## Instrucción para Claude Code

Al iniciar sesión, lee este archivo y los epics relevantes para las US en cola.
Trabaja el backlog en orden sin parar entre US. Por cada US:
1. Implementa la US completa.
2. Haz commit con el mensaje indicado antes de tocar la siguiente.
3. Mueve la US de IN-PROGRESS a DONE con fecha de hoy.
4. Mueve la primera US de QUEUE a IN-PROGRESS.
5. Arranca la siguiente US de inmediato.

Continúa hasta que no queden US en QUEUE o el contexto se agote.
Si el contexto se agota a mitad de una US, haz commit del avance con prefijo `wip:` y anota aquí dónde quedó.
