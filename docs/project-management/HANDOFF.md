# HANDOFF.md — Estado para la próxima sesión

**Última actualización:** 2026-05-26
**Branch activa:** `claude/laughing-carson-stUJu`
**Generado por:** /handoff

---

## 🎯 Dónde estamos parados

Sprint 33 (v1.28) entregado completo en la branch `claude/laughing-carson-stUJu`:
**Dashboards N1/N2 ricos + reportes derivados + revamp v1 + 4 follow-ups** (19
commits, `status:fix-committed`). La branch está rebaseada sobre `main` (que ya
tiene el rediseño V1 de project detail, #511). Tests backend 583 passed/1
skipped; ruff + tsc + next build verdes; render real de PDF (WeasyPrint)
validado. **Nada mergeado aún** de esta sesión: la branch espera merge + QA
visual del owner. Cero PRs abiertos (no se creó PR).

## 📍 Dónde retomar (próximo paso accionable)

**Owner primero:** mergear `claude/laughing-carson-stUJu` a `main`, correr
`alembic upgrade head` en Railway (migraciones 0079/0080/0081) y hacer QA visual
(4 páginas + 3 PDF). Una vez mergeado, la próxima sesión arranca limpio desde
INBOX (no hay US activa). Próximo libre: **US-164, BUG-068, ENH-142.**

## ✅ Hecho en esta sesión

Sprint 33 (v1.28) — branch `claude/laughing-carson-stUJu`. Detalle completo en
`SPRINT-DONE-HISTORY.md`. Resumen:

- **Fundación datos:** US-151 (`metric_snapshots`, mig. 0079) `77f977c`, US-152 (endpoints analytics) `ab40c73`.
- **Dashboards:** US-153 primitivos SVG `a6f0ba5`; US-154 `/dashboard` `af41833`; US-155 `/pmo` `44bcac6`; US-156 org `5f9913d`; US-157 programa `0c9ff4d`.
- **Reportes derivados:** US-158 S-05/S-15 (mig. 0080) `647795a`; US-160 reportes N1/N2 PDF `3451eeb`; US-161 S-07 Curva-S (mig. 0081) `ffbb38b`; US-163 heatmap/treemap en PDF `6e61149`.
- **Revamp + follow-ups:** US-159 revamp v1 `411a44b`; US-162 acceso PM scoped `360e5ee`; ENH-141 consolidar gauge `9a669c6`.
- **Docs:** EP004/EP020/DB-CHANGES actualizados en los mismos bloques.

## 🔄 PRs abiertos o en flight

Ninguno. La branch `claude/laughing-carson-stUJu` no tiene PR creado (el owner
abre/mergea). #511 ya está mergeado a main.

## ⚠️ Gotchas y decisiones recientes

- **Snapshots históricos reactivados** (estaban diferidos a v2.0): ahora v1.x, cadencia semanal por scope. El dashboard es fuente de verdad; los reportes se derivan.
- **S-07 Curva-S reactivada** (estaba "descartada"): planeado lineal `start_date`→`end_date`, capturado en `metric_snapshots.extras.avg_progress_plan`.
- **Reportes N1/N2 viven fuera del Report Builder** (project-only por mig. 0078): generación on-demand vía endpoints dedicados, **sin persistir** `Report` rows (persistencia sigue en backlog v2.0).
- **Vistas agregadas accesibles a PMs** (decisión owner 2026-05-26), scoped a sus proyectos vía `scoped_project_ids`. Capturar snapshots sigue admin-only.
- **Capture button**: en `/dashboard` se muestra cuando cargan las analíticas; para un PM no-admin devuelve 403 con banner informativo (accept. menor).
- **Verificación visual pendiente**: tests + build + render real de PDF cubren correctitud, pero NO el aspecto visual en navegador (sin display en el entorno remoto).

## 📋 Lo que sigue (resumen ejecutivo del backlog activo)

Detalle en INBOX/Deferred de `SPRINT.md`.

- **INBOX:** ENH-115 #434 (breadcrumbs cross `/pmo/**/reports`, `status:ready` diferido).
- **Deferred:** chat IA global (US-102 + ENH-074/075/076); paquete Áreas/Recursos EP017 (ENH-109 bloquea US-119/ENH-110; US-133/134 RBAC); admin UI settings (ENH-111/112/113).
- **Backlog v2.0:** persistencia histórica de reportes L1/L2 (la generación ya existe); KPIs custom por tenant; S-10 entregables formales; cleanup carpetas redirect post-Sprint 32.

## 📚 Estado de las epics docs

| Epic | Sincronizada | Notas |
|---|---|---|
| EP004 (dashboard) | sí | Documenta US-151…163 + ENH-141 (Fase 1-5 + follow-ups). |
| EP020 (report-builder) | sí | S-05/S-07/S-15 implementadas; nota L1/L2 fuera del builder. |
| DB-CHANGES.md | sí | Migración 0079 documentada (0080/0081 son seeds de datos). |

## 🧹 Cleanup técnico pendiente

- [ ] Mergear `claude/laughing-carson-stUJu` → `main`.
- [ ] `alembic upgrade head` en Railway (aplica 0079 + 0080 + 0081).
- [ ] Tras deploy, capturar snapshot (botón en `/dashboard`) para sembrar tendencias/curva-S; si no, el primer punto llega con el job del lunes 02:00 UTC.
- [ ] QA visual: `/dashboard`, `/pmo`, org y programa (+ dark mode) y los 3 PDF (status N1/N2 + secciones S-05/S-07/S-15 en el builder de proyecto).

## 🔮 Para sesiones futuras (sin issue todavía)

- Scoping fino del **botón "Capturar snapshot"** para ocultarlo a no-admins (hoy 403 con banner).
- Persistencia del histórico de reportes N1/N2 (Report rows con `generator` + `project_id` nullable).
- Heatmap/treemap como SVG más rico (squarified) si se quiere más fidelidad en el PDF.

---

## Cómo retomar

Para la próxima sesión:

1. Lee este `HANDOFF.md` primero.
2. Luego `CLAUDE.md` + `docs/project-management/SPRINT.md` + el epic en flight (EP004 / EP020).
3. Continúa desde el "próximo paso accionable" arriba (merge + QA del owner; luego INBOX).
