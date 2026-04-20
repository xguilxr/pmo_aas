# SPRINT.md — Tarea activa

> **Regla:** Claude Code lee SOLO este archivo + el epic relevante. 1 US = 1 commit. Al terminar, marcar DONE y mover la siguiente a IN-PROGRESS.

---

## 🔴 IN-PROGRESS

```
US: US-NEW-018
Epic: EP005-projects.md
Título: Módulo Área/Organigrama del proyecto
Tipo: Backend + Frontend — CRUD project_areas
Commit esperado: "feat(projects): US-NEW-018 — módulo áreas del proyecto"
Precondición: ver DB-CHANGES.md sección EP005.
```

---

## ⏳ QUEUE (próximas 3)

| # | US | Epic | Título | Tipo |
|---|---|---|---|---|
| 1 | US-NEW-017 | EP005 | Tabs inline para módulos del proyecto | Frontend (diferida) |
| 2 | US-NEW-019 | EP006 | Consolidar RAID (vista unificada) | Frontend |
| 3 | US-NEW-020 | EP006 | Categorías de documentos actualizadas | Backend |

> **Nota:** US-NEW-017 (tabs inline) implica refactor grande del shell
> de detalle de proyecto; se difiere hasta que el módulo de áreas esté
> completo para evitar cambios concurrentes en esas rutas.

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
- [ ] US-NEW-017 — Tabs inline (sin cambio de página) para módulos del proyecto
- [ ] US-NEW-018 — Módulo Área/Organigrama del proyecto

### Bloque 6 — RAID y módulos (EP006)
- [ ] US-NEW-019 — Consolidar RAID (Riesgos+Acciones+Incidentes+Decisiones)
- [ ] US-NEW-020 — Categorías de documentos actualizadas
- [ ] US-NEW-021 — Consolidar pestañas de Minutas en 1
- [ ] US-NEW-022 — Módulo Reportes dentro del proyecto

### Bloque 7 — Admin (EP007)
- [ ] US-NEW-023 — Gestión de tenant (propuesta de acciones)
- [ ] US-NEW-024 — Gestión jerarquía org completa (BU + Depto)

### Bloque 8 — SuperAdmin (EP010)
- [ ] US-NEW-025 — Iconos en paneles de tenant
- [ ] US-NEW-026 — Visión General = Tenants + Health unidos

### Bloque 9 — Notificaciones (EP011) — POST-MVP
- [ ] US-NEW-027 — Tabla notifications + in-app center
- [ ] US-NEW-028 — Email notifications via Resend

### Bloque 10 — Migración BD (EP012) — AL FINAL
- [ ] US-NEW-029 — Plan de migración + compatibilidad MySQL
- [ ] US-NEW-030 — Ejecución migración zero-downtime

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