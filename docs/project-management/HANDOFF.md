# HANDOFF.md — Estado para la próxima sesión

**Última actualización:** 2026-07-09
**Branch activa:** `claude/pmo-portfolio-architecture-6hbuen` · **PR #570** (abierto)
**Generado por:** sesión Revamp 1.0 (retro socio + ejecución end-to-end)

---

## 🎯 Dónde estamos parados

**Batch "Revamp 1.0" COMPLETO (11/11)** en PR #570. Nace de la retro del
socio (portafolio ejecutivo multi-proyecto + recursos/capacidad) + 9
decisiones del owner en chat. Diseño completo en
`docs/epics/drafts/portfolio-recursos-capacidad.md`.

Qué cambió (por bloque):
1. **Salud única híbrida** (US-180 `0f96dec` / US-181 `0c0ad7d`): UN solo
   semáforo — motor de reglas por dimensión (cronograma/presupuesto/
   riesgos/decisiones/recursos, `services/project_health.py`) + override
   manual del PM con razón obligatoria en 🟡/🔴. `status_rag` absorbido y
   dropeado (mig 0091). Drill-down "¿por qué?" + foco PM + heatmap
   Proyecto×Dimensión en N1 (`/dashboard/health-matrix`).
2. **Tablas** (ENH-185 `9bb3338`, ENH-186 `acf8d46`, ENH-187 `8114214`,
   ENH-188 `d735e76`): Cambios y Lecciones heredan estructura RAID (sort,
   filtros, chips, inline, export XLSX propio); Plan con chips de color
   de estado; filtros programa/prioridad en /pmo/projects.
3. **Recursos/capacidad** (US-182 `c3fdf7e` / US-183 `4aec20c` / US-184
   `595dc4f`): `actors` = resource_pool (tipo/función/seniority/escasez/
   capacidades, mig 0092); participations con FTE% + status (mig 0093);
   motor de saturación por ventana (`services/capacity.py`) vs
   `project_capacity_pct`; página nueva **/pmo/resources** (personas/
   roles/áreas/conflictos); dimensión recursos del health activa; 3
   alertas de capacidad (in-app, dedupe 7d, sweep semanal + fast-path).
4. **IA** (US-185 `9770161` / ENH-189 `a440efa`): memoria de proyecto
   (`project_ai_contexts`, mig 0094): contexto curado + instrucciones +
   resumen acumulativo que la IA actualiza por minuta (task
   `ai.update_project_context`); bloque `<CONTEXTO_DEL_PROYECTO>`
   inyectado en minutas y reportes; instrucciones permanentes por tenant
   (`/admin/ai`) compuestas vía `prompt_builder`.

Verificación final del batch: **728 pytest + 1 skip · ruff limpio ·
tsc + next build verdes**.

## 📍 Dónde retomar (próximo paso accionable)

1. **Owner verifica y mergea PR #570.**
2. Tras merge: `alembic upgrade head` en Railway (migraciones **0091-0094**).
3. Decisión pendiente del owner: **rename "Organizaciones" → "Portafolios"**
   (recomendación: solo labels de UI, no schema — ver resumen de la sesión).
4. Ideas futuras sin issue: import CSV del pool de recursos (onboarding
   35 proyectos), persistir desglose salud en tendencias UI, evaluar
   auto_summary también con actividades del plan (hoy solo minutas).

## ⚠️ Gotchas

- **Container fresco**: API requiere Python **3.12** (`python3.12 -m pip
  install --break-system-packages -r requirements-dev.txt`); 3.11 truena
  con sintaxis PEP 695 en `app/workers/db.py`. Web: `pnpm install
  --frozen-lockfile`.
- Salud auto se recalcula en: detalle de proyecto, health-detail,
  health-matrix y snapshot semanal — los agregados SQL pueden tener
  staleness acotada entre recálculos (documentado en el draft §4).
- La saturación solo considera participations `status='activa'` con
  `allocation_pct` NOT NULL; las vistas muestran cobertura ("Sin FTE").
- Las alertas de capacidad son in-app only (sin email) con dedupe de 7
  días por (tipo, actor).
- Editar salud desde el form de proyecto ya NO existe — solo la tarjeta
  de Salud (declarar con razón / volver a auto).

## 📚 Estado de epics

Actualización delegada a sub-agente al cierre de esta sesión (commit
`docs(epics)` en la misma branch): EP004 (salud dimensiones + matrix),
EP005 (salud única), EP006 (cambios/lecciones RAID + exports), EP008
(memoria IA + prompts composables), EP009 (chips plan), EP017 (pool de
recursos + FTE% + saturación + /pmo/resources + alertas). Si ese commit
no aparece en la branch, re-lanzar la actualización.

## 🧹 Cleanup / acciones del owner

- [ ] Verificar + mergear **PR #570**.
- [ ] `alembic upgrade head` en Railway (0091-0094).
- [ ] Decidir rename Organizaciones→Portafolios (labels UI).
- [ ] Smoke visual de las vistas nuevas: /pmo/resources, heatmap N1,
  Memoria IA, /admin/ai instrucciones, Cambios/Lecciones revamp.
