---
tipo: archivo
responsable: propietario
estado: archivado
revisado: 2026-08-29
revisar_cada: nunca
---

# Draft — Plan de mejoras: feedback cliente 16-jul-2026

> **Fase A/B — triage del PDF** `PMO_AAS_feedback_16jul.pdf` (8 págs,
> texto + capturas anotadas). Estado: **pendiente OK del owner** para
> arrancar. IDs contra próximo libre: US-190, BUG-091, ENH-195.

---

## 0. Ya resuelto por el batch Plan Import Revamp (2026-07-18)

El feedback es del 16-jul; el batch del 18-jul ya resolvió los items
1 y 2 del PDF — **pedir al cliente que re-pruebe con la versión nueva**:

| Item PDF | Resuelto por |
|---|---|
| 1. Import con plantilla no actualiza estados ni avances | ENH-191 (`a39b3dc`) estados end-to-end + BUG-089 (`48b33c3`) % por celda |
| 2. WBS 1.30 confundido con 1.3, hijos huérfanos | BUG-088 (`37c66ae`) WBS fiel + warnings de huérfanos |

## 1. Items nuevos — triage propuesto

### Bloque A — RAID quick fixes (dolor alto, scope chico)

**BUG-091 — Editar riesgo no graba (status legacy rechazado).** EP006.
Captura pág. 4: `status: Input should be 'open', 'in_progress',
'on_hold' or 'resolved'`. Causa raíz (diagnosticada): riesgos con
status **legacy pre-US-179** (`identified`, `mitigating`, …) en DB; el
form (`raid-edit-fields.tsx:82`) inicializa el Select con ese valor —
el browser MUESTRA "Abierto" pero el state manda el legacy → 422.
Fix: normalizar legacy→canónico al abrir el form + backend tolera y
normaliza legacy en update + barrido de datos para remapear leftovers.

**ENH-195 — Alta de acción con Responsable + vista resumen fiel.** EP006.
Pág. 5: el modal "Registrar acción" no tiene campo Responsable (debe
tomar el pool completo: PMs + gente de negocio) y la lista muestra
"—" en Área/Responsable. Fix: campo owner_actor en el create-modal
(mismo picker de la edición) + asegurar que la vista resumen refleje
área/responsable al crear.

**ENH-196 — Lista RAID sin scroll: layout 2 líneas + edición directa.**
EP006. Pág. 6: la vista requiere scroll vertical y horizontal. Cambio:
cada item en 2 líneas (línea 1: título + chips estado/prioridad;
línea 2: área · responsable · fechas), todo visible sin scroll
horizontal, con la edición inline existente accesible directo.

### Bloque B — Plan / WBS

**ENH-197 — Jerarquía WBS visible y consistente.** EP009/EP006.
Item 3 del PDF: "todos los que inicien con 1.x deben ser hijos de 1,
pero no se refleja". Gap-analysis del agrupado actual (ENH-180
groupByWbs) + indentación clara por nivel, y colgar hijos bajo su
prefijo aunque falte el padre exacto (hoy el rollup los trata como
raíces). Evaluar asignar `parent_id` real al importar.

**US-190 — Revisión de calidad del plan ("plan linter").** EP009.
Item 4: al cargar el plan y con botón "Revisar calidad": checks de
(a) estructura WBS (huecos, huérfanos, profundidad), (b) cada sección
cierra con hito, (c) actividades críticas registradas, (d) duraciones
> 21 días (regla US-090), (e) tareas sin fechas/responsable, (f) %
inconsistentes. Salida: lista de observaciones accionables (severidad
+ fila/tarea) — habilita un buen look-ahead. Reusa la infra de
warnings del import; candidato natural a sumar la IA (resumen de
calidad en lenguaje del PM).

### Bloque C — Salud 5+1 con historial (diseño primero)

**US-191 — Evaluación de salud por dimensión con historia.** EP004/EP005.
Pedido central del PDF: botón para editar la salud POR dimensión
(cronograma, presupuesto, riesgos, decisiones, recursos) + la **sexta**
= salud global del proyecto (la del cuadro grande), con **Fecha de
Evaluación**, guardando las evaluaciones anteriores para ver la
evolución (ej. "15 Jul: Cronograma=🟡, Presupuesto=🟢 … / 1 Jul: …").
También cubre "edición de proyecto no permite cambiar el status
general" (la 6ª es el override global existente, mejor expuesto).
Requiere schema (tabla `project_health_evaluations` o extender los
snapshots semanales existentes) → **migración Alembic**.

**US-192 — Salud editable desde el portafolio + reporte.** EP004/EP020.
Pág. 8: para portafolios de ~30 proyectos, editar la salud 5+1 desde
la vista de portafolio SIN abrir cada proyecto (candidato: el heatmap
`/dashboard/health-matrix` que ya pinta Proyecto×Dimensión, + acceso
desde /pmo/projects) y generar desde ahí un **reporte de salud del
portafolio**. Depende de US-191.

### Bloque D — Recursos

**ENH-198 — Análisis de asignación: teórica vs FTE real.** EP017.
Pág. 7: reporte/pantalla con recursos "usados" en proyectos,
asignación teórica (capacidad disponible) vs FTE asignado, drill por
área y sub-área (teams), alertas de sobreasignación. **Gap-analysis
contra `/pmo/resources` (US-183)** que ya calcula saturación: falta la
comparación explícita teórica-vs-real por persona, el drill por
sub-área y verificar que el flujo sea visible para el cliente (nav).

## 2. Orden sugerido

1. **Bloque A** (BUG-091 → ENH-195 → ENH-196): fixes chicos, dolor
   diario del cliente.
2. **Bloque B** (ENH-197 → US-190): continúa el momentum del plan.
3. **Bloque C** (US-191 → US-192): requiere cerrar diseño + migración;
   el resto no lo bloquea.
4. **Bloque D** (ENH-198): gap-analysis primero — puede resultar más
   chico de lo que parece.

## 3. Preguntas de diseño para el owner (bloquean C y D)

1. **US-191:** ¿la evaluación manual por dimensión CONVIVE con el
   motor automático (recomendado: cada dimensión muestra el auto y el
   PM puede fijar su evaluación del período; el historial guarda
   ambas) o lo REEMPLAZA?
2. **US-191:** ¿evaluaciones con fecha libre (cada guardado = un punto
   en la historia) o períodos fijos (semanal/quincenal)?
3. **US-192:** ¿la edición masiva vive en el heatmap health-matrix
   (recomendado — ya existe la matriz) o en la lista /pmo/projects?
4. **ENH-198:** ¿el cliente ya vio `/pmo/resources` (Revamp 1.0,
   mergeado 9-jul)? Si no estaba deployado al 16-jul, parte del pedido
   puede estar cubierto — confirmar antes de construir de más.

---

**Última actualización:** 2026-07-18 · sesión `claude/plan-import-wbs-fixes-nwotng`
