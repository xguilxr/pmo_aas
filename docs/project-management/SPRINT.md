# SPRINT.md — Tarea activa

> **Regla:** Claude Code lee SOLO este archivo + el epic relevante. 1 US = 1 commit. Al terminar, marcar DONE y mover la siguiente a IN-PROGRESS.

---

## 🔴 IN-PROGRESS

```
2026-04-24 — Sprint 4 v1.3 kickoff.

Sprint 3 v1.2 CERRADO — Bloque 2 (BUG-027 + ENH-022 + ENH-023)
esperando merge de la branch claude/update-admin-ai-config-EyClx.
Post-merge + redeploy Railway limpia los warnings de tailscaled
que el owner ve en logs.

Sprint 4 v1.3 arranca ahora con 11 items en 3 bloques (ver QUEUE):
- Bloque 1 (7 reworks del review 2026-04-23).
- Bloque 2 (3 items RAID robusto + uploads persistentes).
- Bloque 3 (1 item import XLSX + MPP).

Primera US en IN-PROGRESS: BUG-028 (#104) charter vacío abre
editor en vez de URL placeholder example.local.
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

## ⏳ QUEUE (Sprint 4 v1.3)

| # | ID | Epic | Título | Bloque |
|---|---|---|---|---|
| 1 | BUG-028 | EP003 | Charter vacío abre URL placeholder example.local | 1 |
| 2 | BUG-029 | EP006 | Upload Excel falla + botón Choose File sin styling | 1 |
| 3 | ENH-024 | EP014 | Reporte: filename correcto al descargar | 1 |
| 4 | ENH-025 | EP006 | Filtros RAID siguen apilados (rework horizontales) | 1 |
| 5 | ENH-026 | EP006 | Consolidar Gestión Avanzada en /admin/raid | 1 |
| 6 | ENH-027 | EP006 | Panel editable RAID en /admin/projects/[id]/raid | 1 |
| 7 | ENH-028 | EP005 | Export tareas: Excel MPP-like + PLAN naming + CSV BOM | 1 |
| 8 | US-064 | EP006 | RAID: área + responsable + fechas + ordenamiento | 2 |
| 9 | US-065 | EP006 | RAID: página dedicada por ítem (deep link) | 2 |
| 10 | US-066 | EP007 | Uploads: Railway volume + runbook | 2 |
| 11 | US-067 | EP009 | Importar XLSX + MPP nativo → tareas | 3 |

---

## ✅ DONE

**Ver `SPRINT-DONE-HISTORY.md` para el historial completo de Sprint 1 (v1.0 MVP, 94 items) y Sprint 2 (v1.1, 18 items).**

Sprint 2 v1.1 cerrado 2026-04-23. 4 bloques completos + hotfix Railway.

Sprint 3 v1.2 cerrado 2026-04-24 — 2 bloques:
- Bloque 1 (2 items): ENH-021 #96 + US-063 #95.
- Bloque 2 (3 items): BUG-027 #100 + ENH-022 #102 + ENH-023 #103.

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

## 📋 Backlog Sprint 3 (v1.2 — CERRADO)

### Bloque 1 — Sprint 3 Limpieza post-v1.1 + Auth self-service (2 items) ✅ COMPLETO
- [x] ENH-021 — Superadmin AI: quitar defaults editables de Ollama — #96 ✅ b70c887
- [x] US-063 — Recuperación y cambio de contraseña con envío por correo — #95 ✅ (6 commits, af4c9c3…7222dac)

### Bloque 2 — Sprint 3 Cleanup IA legacy post-DEC-017 (3 items) ✅ COMPLETO (pending merge)
- [x] BUG-027 — /admin/tenant config: retirar dropdown "Modo IA" + form Ollama Tailscale + endpoint backend + runbooks archivados + runbook BYO nuevo — #100 ✅ 1b62045
- [x] ENH-022 — Housekeeping docs/ai/ (4 archivos legacy a archive) + archivar EP016 + actualizar refs cruzadas — #102 ✅ 6315d19
- [x] ENH-023 — Retirar sidecar Tailscale del worker (start-worker.sh + Dockerfile custom + env vars TS_AUTHKEY/HOSTNAME + tailscale-setup.md archivado) — #103 ✅ f541171

---

## 📋 Backlog Sprint 4 (v1.3 — ACTIVO)

> Sprint arranca 2026-04-24 tras cerrar el review post-Sprint 2/3 con
> el owner. Scope: **reworks del review + RAID robusto + import de
> project/excel**. Los 3 items de v2.0 (US-059/060/061) siguen diferidos
> por DEC-018.

### Bloque 1 — Reworks del review (7 items) 🔴 EN CURSO
- [ ] BUG-028 — Charter vacío abre URL placeholder `example.local` (DNS_PROBE fail) — #104
- [ ] BUG-029 — Upload de Excel falla + botón "Choose file" sin styling — #105
- [ ] ENH-024 — Reporte: filename correcto al descargar (hoy baja como "reporte" genérico) — #106
- [ ] ENH-025 — Filtros RAID siguen apilados (rework definitivo horizontales) — #107
- [ ] ENH-026 — Consolidar "Panel de Gestión Avanzada" RAID en `/admin/raid` — #108
- [ ] ENH-027 — Panel editable RAID (US-058) debe funcionar en `/admin/projects/[id]/raid` — #109
- [ ] ENH-028 — Export tareas: Excel MPP-like + naming PLAN-{Proyecto}-{Fecha} + CSV BOM UTF-8 — #110

### Bloque 2 — RAID robusto + uploads persistentes (3 items)
- [ ] US-064 — RAID: área (nullable legacy, obligatoria en nuevos) + responsable + fechas + ordenamiento área/fecha/prioridad — #111
- [ ] US-065 — RAID: página dedicada por ítem (deep link + historial + adjuntos) — #112
- [ ] US-066 — Uploads: Railway persistent volume + runbook de configuración — #113

### Bloque 3 — Import Project/Excel (1 item)
- [ ] US-067 — Importar XLSX + MPP nativo → generar tareas (requiere Java 21 + MPXJ en worker) — #114

---

## 📋 Backlog v2.0 (Major Overhaul — post-v1.3)

> **Contexto (DEC-018):** estos items requieren repensar el modelo de
> roles/permisos/áreas a nivel plataforma. No son incrementales: tocan
> auth + multi-tenancy + UX transversal. Se ejecutan como v2.0 con su
> propio sprint dedicado cuando v1.3 esté estable.

- [ ] US-059 — Recursos: usuarios sin roles jerárquicos (replantear Auth) — #88
- [ ] US-060 — Roles: tipos de usuario (Viewer/User/Admin) — #89
- [ ] US-061 — Aprobaciones: jerarquía directa + permisos — #90
- [ ] (posibles items futuros: 2FA, SSO, magic-link login)

---

## Notas y cambios

- **2026-04-24 (Sprint 4 kickoff):** owner revisa Sprint 2/3 y reporta
  7 items con `needs-rework` + pide RAID robusto (área obligatoria,
  fechas, página dedicada, ordenamiento) + import XLSX/MPP. Se crean
  11 issues (#104-#114) en 3 bloques. Scope completo confirmado por
  owner (ningún corte). Import MPP requiere Java 21 + MPXJ en worker
  (flag de riesgo dentro del issue US-067).
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
