# SPRINT.md — Tarea activa

> **Regla:** Claude Code lee SOLO este archivo + el epic relevante. 1 US = 1 commit. Al terminar, marcar DONE y mover la siguiente a IN-PROGRESS.

---

## 🔴 IN-PROGRESS

```
2026-04-24 — Sprint 4 v1.3 en curso.

Bloque 1 Sprint 4 — 2/8 items completos:
- BUG-030 (#118) hotfix Groq metadata → 400. ✅ 8495dc8
- BUG-015 (#40) rework botón CSV en dashboard. ✅ d3523bb
- BUG-029 (#105) upload documentos funcional + styling. ✅ 3f6ac90

Reshuffle 2 (2026-04-24, tras revisión de runbooks Railway):
- US-066 (#113) PROMOVIDA a prioridad inmediata (antes de
  terminar Bloque 1). Owner reporta que los docs de Railway
  Volume están incorrectos — Railway NO permite compartir
  volumes entre servicios. Sin US-066 los uploads se pierden
  en cada redeploy, bloquea el resto del testing de features.
- Nueva estrategia: object storage S3-compatible (Cloudflare R2).
- Runbook completo entregado en docs/runbooks/infra/uploads-
  storage.md + SETUP.md y DEPLOYMENT.md corregidos.
- Bloque 1 restante (ENH-003, 024, 025, 026, 027, 028) espera
  tras US-066.

Próximo item: US-066 (#113). Owner ejecuta el runbook §2-§5
(bucket R2 + env vars + smoke test) y agrega status:ready al
issue. Luego Claude implementa el refactor de código.
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

### 🔥 Priority immediate — US-066 (promovida del Bloque 2)

| # | ID | Epic | Título |
|---|---|---|---|
| 1 | **US-066** | EP007 | **Uploads: object storage S3-compatible (Cloudflare R2) + runbook + código** — #113 |

> Runbook entregado en commit ca5dd0c. Código (boto3 + selector
> backend + StreamingResponse + tests con moto) entregado en
> commit e0f9c2e. Owner termina la config R2 + redeploy →
> verifica end-to-end → `status:fix-committed`.

### Bloque 1 (continuación) — Reworks del review (6 items restantes)

| # | ID | Epic | Título |
|---|---|---|---|
| 2 | ENH-003 | EP002 | Modal directo "Nuevo programa" en `/admin/organizations` y `/admin/programs` (sub-A) — #50 |
| 3 | ENH-024 | EP014 | Reporte: filename correcto al descargar — #106 |
| 4 | ENH-025 | EP006 | Filtros RAID siguen apilados (rework definitivo) — #107 |
| 5 | ENH-026 | EP006 | Consolidar "Gestión Avanzada" en `/admin/raid` — #108 |
| 6 | ENH-027 | EP006 | Panel editable RAID en `/admin/projects/[id]/raid` — #109 |
| 7 | ENH-028 | EP005 | Export tareas: Excel MPP-like + PLAN naming + CSV BOM — #110 |

### Bloque 2 — RAID robusto + fix completo charter (4 items restantes)

> **Orden obligatorio:** US-066 primero (ya promovida arriba), luego BUG-028 (charter real usa storage).

| # | ID | Epic | Título |
|---|---|---|---|
| 8 | BUG-028 | EP003 | Charter vacío: generar PDF real al aprobar solicitud (depende US-066+BUG-029) — #104 |
| 9 | US-064 | EP006 | RAID: área + responsable + fechas + ordenamiento — #111 |
| 10 | US-065 | EP006 | RAID: página dedicada por ítem (deep link + historial + adjuntos) — #112 |
| 11 | US-068 | EP002 | Página PMO de organización (paneles programas + proyectos, separada de admin) — #116 |

### Bloque 3 — Import Project/Excel (1 item)

| # | ID | Epic | Título |
|---|---|---|---|
| 12 | US-067 | EP009 | Importar XLSX + MPP nativo → generar tareas — #114 |

### Bloque 4 — Auth simplificada post-DEC-020 (2 items)

> **Contexto:** DEC-020 (2026-04-24) redefine la plataforma como
> "herramienta de apoyo y visualización", **sin aprobaciones
> jerárquicas**. Las US-059/060 salen de v2.0 con scope reducido.
> US-061 (#90) se cancela.

| # | ID | Epic | Título |
|---|---|---|---|
| 13 | US-059 | EP001+EP002 | Roles simplificados: Admin / User / Viewer (reemplaza jerarquías) — #88 |
| 14 | US-060 | EP001+EP002 | Permisos fijos por rol + rol `Reportes` absorbido en `User` (fix BUG-025 residual) — #89 |

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
> el owner. Scope: **reworks del review + infra + RAID robusto + import
> project/excel + página PMO de organización**. Los 3 items de v2.0
> (US-059/060/061) siguen diferidos por DEC-018.
>
> **Reshuffle 2026-04-24:** BUG-028 movido a Bloque 2 (depende de
> US-066 + BUG-029). #40 y #50 reintegrados. US-068 creada para sub-B
> de #50. Total 14 items.

### Bloque 1 — Reworks del review (8 items)
- [x] BUG-015 — Dashboard: botón "Exportar CSV" en 2 líneas (rework) — #40 ✅ d3523bb
- [x] BUG-029 — Upload de Excel falla + botón "Choose file" sin styling — #105 ✅ 3f6ac90
- [x] ENH-003 — Modal directo "Nuevo programa" en `/admin/organizations` y `/admin/programs` (sub-A) — #50 ✅ b47f19a (ya resuelto por ENH-013 Sprint 2; owner re-valida en deploy actual)
- [x] ENH-024 — Reporte: filename correcto al descargar — #106 ✅ 33c043c
- [x] ENH-025 — Filtros RAID siguen apilados (rework definitivo horizontales) — #107 ✅ ca9dc1d
- [ ] ENH-026 — Consolidar "Panel de Gestión Avanzada" RAID en `/admin/raid` — #108
- [ ] ENH-027 — Panel editable RAID (US-058) debe funcionar en `/admin/projects/[id]/raid` — #109
- [ ] ENH-028 — Export tareas: Excel MPP-like + naming PLAN-{Proyecto}-{Fecha} + CSV BOM UTF-8 — #110

### Bloque 2 — Infra + RAID robusto + PMO page (5 items)

> **Orden:** US-066 → BUG-028 → US-064 → US-065 → US-068.

- [ ] US-066 — Uploads: Railway persistent volume + runbook — #113
- [ ] BUG-028 — Charter vacío: generar PDF real al aprobar solicitud — #104
- [ ] US-064 — RAID: área (nullable legacy, obligatoria en nuevos) + responsable + fechas + ordenamiento — #111
- [ ] US-065 — RAID: página dedicada por ítem (deep link + historial + adjuntos) — #112
- [ ] US-068 — Página PMO de organización (paneles programas + proyectos, separada de admin) — #116

### Bloque 3 — Import Project/Excel (1 item)
- [ ] US-067 — Importar XLSX + MPP nativo → generar tareas (requiere Java 21 + MPXJ en worker) — #114

### Bloque 4 — Auth simplificada post-DEC-020 (2 items)
- [ ] US-059 — Roles simplificados: Admin / User / Viewer (reemplaza jerarquías, sin aprobaciones) — #88
- [ ] US-060 — Permisos fijos por rol + rol `Reportes` absorbido en `User` (fix residual BUG-025) — #89

---

## 📋 Backlog v2.0 (post-v1.3)

> **Contexto (DEC-020, 2026-04-24):** los 3 items originales de v2.0
> fueron recuperados o cancelados tras la decisión de no implementar
> aprobaciones jerárquicas. US-059 (#88) + US-060 (#89) bajaron a
> Sprint 4 v1.3 Bloque 4 con scope simplificado. US-061 (#90) está
> cancelada.

- [ ] (posibles items futuros: 2FA, SSO, magic-link login)

---

## Notas y cambios

- **2026-04-24 (reshuffle #2 — US-066 promovida):** owner reporta que
  los docs de Railway Volume (`SETUP.md` §4.1, `DEPLOYMENT.md` §4)
  están incorrectos — Railway no permite compartir volumes entre
  servicios. Sin storage persistente los uploads se pierden en cada
  redeploy, bloqueando el resto del testing. **US-066 (#113)
  promovida a prioridad inmediata** antes de seguir el Bloque 1.
  Nueva estrategia: **object storage S3-compatible (Cloudflare R2)**,
  cero egress fees + free tier 10 GB. Runbook completo entregado en
  `docs/runbooks/infra/uploads-storage.md` con 12 secciones
  (bucket + token + env vars + smoke + código + backup + rollback +
  troubleshooting). SETUP.md y DEPLOYMENT.md corregidos.
- **2026-04-24 (DEC-020 mid-Sprint 4):** owner redefine la plataforma
  como herramienta de apoyo/visualización — sin aprobaciones
  jerárquicas. Consecuencia: US-059 (#88) + US-060 (#89) bajan de v2.0
  al Bloque 4 del Sprint 4 v1.3 con scope reducido (3 roles fijos:
  Admin/User/Viewer + permisos estáticos por rol). US-061 (#90)
  cancelada. El permiso `reports` pendiente de BUG-025 se absorbe en
  US-060 como parte del rol `User`. Total Sprint 4: 16 items (8+5+1+2).
- **2026-04-24 (Sprint 4 reshuffle):** owner revisa el plan inicial
  y pide considerar #40, #50, #103 + mover BUG-028 al Bloque 2 por
  dependencia con US-066 + BUG-029 (charter real requiere storage
  persistente + upload funcional). Acciones:
  - BUG-015 #40 y ENH-003 #50 reintegrados al Bloque 1 con scope
    clarificado en comentarios.
  - BUG-028 #104 re-scoped a "generar PDF real del charter" + movido
    a Bloque 2 después de US-066.
  - Nueva US-068 #116 para sub-problema B de #50 (página PMO de
    organización separada de admin) en Bloque 2.
  - #103 identificado como pending-merge (no requiere issue nuevo;
    documentado en comentario).
  - US-060 (#89) y US-061 (#90) documentados con contexto DEC-018
    para que owner pueda cerrarlos con `not_planned`.
  - Introducido label `status:ready` en CLAUDE.md §5 como gate de
    arranque: Claude espera `status:ready` antes de tocar código.
  - Total Sprint 4: 14 items (8+5+1).
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
