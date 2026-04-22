# SPRINT.md — Tarea activa

> **Regla:** Claude Code lee SOLO este archivo + el epic relevante. 1 US = 1 commit. Al terminar, marcar DONE y mover la siguiente a IN-PROGRESS.

---

## 🔴 IN-PROGRESS

```
2026-04-22 23:58 — US-055 (Export tareas CSV/Excel opción A)

BUG-026 completado (77dc093). Avanzando Bloque 1.
```

---

## 📥 INBOX / TRIAGE

> Issues recién creados que todavía no han sido asignados a un Bloque.
> El owner (o Claude por propuesta) decide a qué bloque entran antes de
> pasar a QUEUE. Ver `CLAUDE.md` §3 paso 4 y §6.

```
— Vacío — (intake del comment del owner del 2026-04-21 ya asignado a Bloque 20 y Bloque 18)
```

---

## ⏳ QUEUE (próximas 20 — Sprint 2)

| # | ID | Epic | Título | Bloque |
|---|---|---|---|---|
| 71 | US-055 | EP005 | Export tareas (CSV/Excel) — Opción A: botón descarga instantánea | Bloque 1 |
| 72 | ENH-012 | EP013 | Sidebar: reorganizar con módulo "Módulos de Proyecto" | Bloque 1 |
| 73 | ENH-013 | EP002 | Botón "Nuevo Programa" abre modal en Organizaciones | Bloque 1 |
| 74 | BUG-023 | EP003 | Project Charter: link a editor cuando no hay archivo (404) | Bloque 1 |
| 75 | BUG-024 | EP006 | Lógica de uploads no configurada | Bloque 1 |
| 76 | BUG-025 | EP007 | Rol "Reportes" sin módulo de permisos | Bloque 1 |
| 87 | BUG-026 | EP001 | Auth: timeout de inactividad a 15 minutos | Bloque 1 |
| 77 | ENH-014 | EP014 | Reportes: renombrar archivo con datetime + preview PDF | Bloque 2 |
| 78 | US-056 | EP014 | Calendarizar envío automático de reportes vía Resend | Bloque 2 |
| 80 | ENH-015 | EP004 | Dashboard: expandir barra de navegación | Bloque 2 |
| 82 | ENH-017 | EP006 | RAID: filtros en línea horizontal | Bloque 2 |
| 81 | ENH-016 | EP003 | Solicitudes: permitir reabrir si proyecto no existe | Bloque 2 |
| 85 | ENH-019 | EP006 | RAID: gestión avanzada consolidada en principal | Bloque 3 |
| 84 | ENH-018 | EP006 | RAID: agregar toggle Kanban | Bloque 3 |
| 83 | US-058 | EP006 | RAID: preview panel editable con comentarios | Bloque 3 |
| 86 | ENH-020 | EP002 | Áreas: permitir múltiples recursos/contactos | Bloque 3 |
| 91 | US-062 | EP002 | Áreas/Recursos: Area Leader + recursos asignados (Sprint 2, no v1.2) | Bloque 3 |
| 79 | US-057 | EP008 | IA: permitir tenants propia instancia + docs configuración + rollback | Bloque 4 |
| 88 | US-059 | EP002 | v1.2 Recursos: usuarios sin roles jerárquicos | v1.2 |
| 89 | US-060 | EP002 | v1.2 Roles: tipos usuario (Viewer/User/Admin) | v1.2 |
| 90 | US-061 | EP002 | v1.2 Aprobaciones: jerarquía directa + permisos | v1.2 |

> **Sprint 2 intake (2026-04-22):** 21 issues nuevos clasificados en 4 bloques.
> Bloques 1-3 para Sprint 2 v1.1 (navegación + RAID + reportes + IA).
> Bloque 4 para IA avanzada (tenants propia instancia).
> v1.2: 3 issues post-MVP de recursos + roles + aprobaciones (US-062 movida a Bloque 3 por owner).

---

## ✅ DONE (historial Sprint 1)

**Ver SPRINT-DONE-HISTORY.md para tabla completa de 94 items del Sprint 1 v1.0 MVP (US-001 a US-054).**

> Sprint 1 completado 2026-04-21. 22 bloques (+ hotfixes) con all features bloqueantes de v1.0.

---

## 📋 Backlog Sprint 2 (v1.1 — en ejecución)

### Bloque 1 — Sprint 2 Setup: navegación + bugs + permisos (7 items)
- [x] BUG-026 — Auth: timeout de inactividad a 15 minutos — #87 ✅ 77dc093
- [ ] US-055 — Export tareas (CSV/Excel) — Opción A: botón descarga instantánea — #71
- [ ] ENH-012 — Sidebar: reorganizar con módulo "Módulos de Proyecto" — #72
- [ ] ENH-013 — Botón "Nuevo Programa" abre modal en Organizaciones — #73
- [ ] BUG-023 — Project Charter: link a editor cuando no hay archivo (404) — #74
- [ ] BUG-024 — Lógica de uploads no configurada — #75
- [ ] BUG-025 — Rol "Reportes" sin módulo de permisos — #76

### Bloque 2 — Sprint 2 Reportes + Dashboard (5 items)
- [ ] ENH-014 — Reportes: renombrar archivo con datetime + preview PDF — #77
- [ ] US-056 — Calendarizar envío automático de reportes vía Resend — #78
- [ ] ENH-015 — Dashboard: expandir barra de navegación — #80
- [ ] ENH-017 — RAID: filtros en línea horizontal — #82
- [ ] ENH-016 — Solicitudes: permitir reabrir si proyecto no existe — #81

### Bloque 3 — Sprint 2 RAID + Áreas (5 items)
- [ ] ENH-019 — RAID: gestión avanzada consolidada en principal — #85
- [ ] ENH-018 — RAID: agregar toggle Kanban — #84
- [ ] US-058 — RAID: preview panel editable con comentarios — #83
- [ ] ENH-020 — Áreas: permitir múltiples recursos/contactos — #86
- [ ] US-062 — Áreas/Recursos: Area Leader + recursos asignados (moved from v1.2) — #91

### Bloque 4 — Sprint 2 IA avanzada (1 item)
- [ ] US-057 — IA: permitir tenants propia instancia + docs config + rollback — #79

### Bloque v1.2 (Post-MVP — no implementar en Sprint 2)
- [ ] US-059 — v1.2 Recursos: usuarios sin roles jerárquicos — #88
- [ ] US-060 — v1.2 Roles: tipos usuario (Viewer/User/Admin) — #89
- [ ] US-061 — v1.2 Aprobaciones: jerarquía directa + permisos — #90
- [ ] US-062 — v1.2 Áreas/Recursos: Area Leader + recursos asignados — #91

---

**Notas Sprint 2:**
- Total: 21 issues (18 Sprint 2 v1.1 + 3 v1.2).
  - Sprint 2: 7 BUGs + 10 ENHs + 4 USs (US-055, US-056, US-057, US-058, US-062).
  - v1.2: US-059, US-060, US-061 (no implementar en este sprint).
- Bloques 1-4: ejecución Sprint 2.
  - Bloque 1: Setup (navegación, bugs, permisos).
  - Bloque 2: Reportes + Dashboard.
  - Bloque 3: RAID + Áreas (incluye US-062 movida del v1.2).
  - Bloque 4: IA avanzada (tenants propia instancia + docs).
- Bloque v1.2: documentado pero NO ejecutar.

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
