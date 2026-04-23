# SPRINT.md — Tarea activa

> **Regla:** Claude Code lee SOLO este archivo + el epic relevante. 1 US = 1 commit. Al terminar, marcar DONE y mover la siguiente a IN-PROGRESS.

---

## 🔴 IN-PROGRESS

```
2026-04-23 — Sprint 2 v1.1 CERRADO. Próximo: Sprint 3 v1.2 (arranca tras merge + deploy verde en Railway).

Hotfix Railway 2026-04-23:
- 40c4176: migraciones 0021/0022 removieron filtro `deleted_at IS NULL`
  (tenants no tiene esa columna) — Railway bloqueaba deploy.

Sprint 3 v1.2 (próximo): ver §"Backlog Sprint 3" más abajo. Arranca
  cuando el owner configure GROQ_API_KEY + FERNET_KEY y apruebe el
  arranque.

v2.0 (major overhaul, post-v1.2): 4 items diferidos — ver §"Backlog v2.0".
```

---

## 📥 INBOX / TRIAGE

> Issues recién creados que todavía no han sido asignados a un Bloque.
> El owner (o Claude por propuesta) decide a qué bloque entran antes de
> pasar a QUEUE. Ver `CLAUDE.md` §3 paso 4 y §6.

```
— Vacío —
```

---

## ⏳ QUEUE (Sprint 3 v1.2)

| # | ID | Epic | Título | Bloque |
|---|---|---|---|---|
| 96 | ENH-021 | EP008 | Superadmin AI: quitar defaults editables de Ollama | Bloque 1 |
| 95 | US-063 | EP001 + EP011 | Recuperación y cambio de contraseña con envío por correo | Bloque 1 |

---

## ✅ DONE

**Ver `SPRINT-DONE-HISTORY.md` para el historial completo de Sprint 1 (v1.0 MVP, 94 items) y Sprint 2 (v1.1, 18 items).**

Sprint 2 v1.1 cerrado 2026-04-23. 4 bloques completos + hotfix Railway.

---

## 📋 Backlog Sprint 2 (v1.1 — CERRADO)

### Bloque 1 — Sprint 2 Setup: navegación + bugs + permisos (7 items) ✅ COMPLETO
- [x] BUG-026 — Auth: timeout de inactividad a 15 minutos — #87 ✅ 77dc093
- [x] US-055 — Export tareas (CSV/Excel) — Opción A: botón descarga instantánea — #71 ✅ 023a99c
- [x] ENH-012 — Sidebar: reorganizar con módulo "Módulos de Proyecto" — #72 ✅ e2e420f
- [x] ENH-013 — Botón "Nuevo Programa" abre modal en Organizaciones — #73 ✅ b47f19a
- [x] BUG-023 — Project Charter: link a editor cuando no hay archivo (404) — #74 ✅ d81d036
- [x] BUG-024 — Lógica de uploads no configurada — #75 ✅ 3cd997d
- [x] BUG-025 — Rol "Reportes" sin módulo de permisos — #76 ✅ b1954c7

### Bloque 2 — Sprint 2 Reportes + Dashboard (5 items) ✅ COMPLETO
- [x] ENH-014 — Reportes: renombrar archivo con datetime + preview PDF — #77 ✅ 02cfaa6
- [x] US-056 — Calendarizar envío automático de reportes vía Resend — #78 ✅ 51947ef
- [x] ENH-015 — Dashboard: expandir barra de navegación — #80 ✅ 55956f9
- [x] ENH-017 — RAID: filtros en línea horizontal — #82 ✅ 6832199
- [x] ENH-016 — Solicitudes: permitir reabrir si proyecto no existe — #81 ✅ ade6ee7

### Bloque 3 — Sprint 2 RAID + Áreas (5 items) ✅ COMPLETO
- [x] ENH-019 — RAID: filtros avanzados (status + severidad/prioridad) — #85 ✅ fe3b001
- [x] ENH-018 — RAID: agregar toggle Kanban — #84 ✅ c894f12
- [x] US-058 — RAID: preview panel editable con comentarios (parcial — ver issue) — #83 ✅ e239caa
- [x] ENH-020 — Áreas: permitir múltiples recursos/contactos — #86 ✅ 009c0f2
- [x] US-062 — Áreas/Recursos: Area Leader + recursos asignados (moved from v1.2) — #91 ✅ 009c0f2

### Bloque 4 — Sprint 2 IA multi-modo (1 item) ✅ COMPLETO
- [x] US-057 — IA multi-modo por tenant: disabled / platform (Groq) / byo — #79 ✅ (9 commits, 8e4c385…be2a2ac; hotfix 40c4176)

---

## 📋 Backlog Sprint 3 (v1.2 — próximo)

> Scope reducido por decisión del owner el 2026-04-23: los 3 items
> grandes de "roles/recursos/aprobaciones jerárquicas" (US-059,
> US-060, US-061, US-062-duplicado) **se mueven a v2.0** — son un
> major overhaul que no encaja en un sprint incremental. v1.2 queda
> acotado a lo que el owner pidió tras cerrar v1.1.

### Bloque 1 — Sprint 3 Limpieza post-v1.1 + Auth self-service (2 items)
- [ ] ENH-021 — Superadmin AI: quitar defaults editables de Ollama — #96
  - UI change ya implementada junto con el hotfix Railway; pendiente owner cierre formal del issue.
- [ ] US-063 — Recuperación y cambio de contraseña con envío por correo — #95

---

## 📋 Backlog v2.0 (Major Overhaul — post-v1.2)

> **Contexto (DEC-018):** estos items requieren repensar el modelo de
> roles/permisos/áreas a nivel plataforma. No son incrementales: tocan
> auth + multi-tenancy + UX transversal. Se ejecutan como v2.0 con su
> propio sprint dedicado cuando v1.2 esté estable.

- [ ] US-059 — Recursos: usuarios sin roles jerárquicos (replantear Auth) — #88
- [ ] US-060 — Roles: tipos de usuario (Viewer/User/Admin) — #89
- [ ] US-061 — Aprobaciones: jerarquía directa + permisos — #90
- [ ] (posibles items futuros: 2FA, SSO, magic-link login)

---

## Notas y cambios

- **2026-04-23 (post-v1.1):** owner define scope de Sprint 3 v1.2:
  solo limpieza Ollama + password reset (ENH-021 + US-063). Los 3
  items originales de v1.2 (#88/#89/#90) pasan a v2.0 por ser un
  major overhaul de Auth/Roles/Aprobaciones. Ver **DEC-018**.
- **2026-04-22 (Sprint 2 intake):** 21 issues clasificados en 4
  bloques v1.1 + 3 items v1.2 (luego reclasificados a v2.0 el
  2026-04-23).

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
