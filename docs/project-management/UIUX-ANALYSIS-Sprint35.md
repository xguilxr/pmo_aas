---
responsable: propietario
estado: historico
revisado: 2026-06-28
revisar_cada: nunca
---

# Análisis UI/UX + alineación de campos RAID — Sprint 35 (2026-06-28)

> **Histórico.** Entregable del Sprint 35 (2026-06-28), conservado como
> registro del análisis. Lo que de aquí sigue pendiente vive en
> [`SPRINT-BACKLOG.md`](SPRINT-BACKLOG.md), no en este documento.

> Entregable de cierre del batch "Plan page + RAID mejoras". Cubre el análisis
> UI/UX pedido por el owner y **ENH-169** (alinear/complementar campos RAID).
> Las recomendaciones marcadas **[requiere OK]** tocan schema o cambian
> comportamiento descrito en epics → esperar confirmación del owner antes de
> ejecutar (CLAUDE.md §9).

---

## 1. ENH-169 — Alineación de campos RAID

### 1.1 Estado actual (campos por tipo)

| Campo | Riesgo | Acción | Incidente | Decisión |
|---|---|---|---|---|
| folio, title, description, status, area_id, owner_id, owner_actor_id | ✅ | ✅ | ✅ | ✅ |
| Prioridad/Severidad | severity (P×I) | priority (1-4) | priority | priority |
| Fecha de creación (negocio) | identified_at | reported_at | reported_at | reported_at |
| Fecha compromiso | due_date | committed_date | committed_date | committed_date |
| Cierre/resolución | closure_note | resolution | resolution | resolution |
| category | ✅ | — | — | — |
| probability / impact / mitigation_strategy | ✅ | — | — | — |
| type (action/issue/decision) | — | ✅ | ✅ | ✅ |

### 1.2 Inconsistencias detectadas

1. **Etiqueta de fecha de creación**: las listas muestran "F. Creación" para
   todos, pero internamente es `identified_at` (risk) vs `reported_at` (issue).
   Alineado a nivel de UI; OK.
2. **Responsable no se muestra en las listas**: existe `owner` (User) +
   `owner_actor_id` (Actor) pero ninguna lista RAID muestra una columna
   Responsable. El export sí resuelve Actor→nombre (fallback User). La lista
   sólo trae `owner` (User), por lo que items asignados a un Actor saldrían
   vacíos sin un cambio backend. **[requiere OK]**: ¿agregar columna
   Responsable resolviendo Actor en el read (como el export)?
3. **`resolution` (issues) y `closure_note` (risks)** cumplen el mismo rol
   ("nota de cierre") con nombres distintos. No bloqueante; alinear el LABEL en
   UI a "Nota de cierre" para ambos sería consistente. **[seguro]**
4. **Riesgo `due_date` vs issue `committed_date`**: mismo concepto (fecha
   compromiso), columnas distintas en DB. Ya alineado en UI ("F. Compromiso").

### 1.3 Recomendaciones ENH-169 (para confirmar scope)

- **[seguro, UI]** Unificar el label de la nota de cierre a "Nota de cierre"
  en el detalle de issues (hoy "Resolución") y risks.
- **[requiere OK]** Columna Responsable en las listas R/A/I/D + resolución
  Actor→nombre en `listRisks`/`listIssues` (hoy sólo en el export).
- **[requiere OK]** ¿Severidad editable inline en riesgos? Hoy severity = P×I
  (derivada); editar inline implicaría editar probability/impact (2 selects).
- **[requiere OK]** ¿`category` también para issues (acciones/incidencias/
  decisiones)? Hoy es exclusiva de riesgos.

> Implementado en Sprint 35 sin tocar schema: ENH-166 (ocultar finalizados +
> orden por fase), ENH-167 (filtro de área), ENH-168 (export por tipo),
> US-174 (Kanban + drag), US-175 (estado inline). La "alineación" restante son
> decisiones de producto → se listan arriba para el owner.

---

## 2. Análisis UI/UX general (Plan + RAID)

### 2.1 Mejoras de alto valor (bajo riesgo)

- **Plan — densidad de la lista con edición inline (US-173):** ahora cada fila
  tiene selects/inputs/checkboxes. En proyectos grandes esto agrega ruido
  visual y muchos nodos DOM. Sugerencia: edición inline "on click" (la celda
  muestra el valor y se vuelve control al enfocar) en vez de controles
  siempre-on para área/estado. **[mejora futura]**
- **Plan — flicker de controles controlados:** los selects/inputs inline
  reflejan el valor sólo tras confirmar el PATCH (estado controlado por el
  server). En redes lentas se percibe lag. Sugerencia: update optimista local
  + revert on error. **[mejora futura]**
- **RAID Kanban — columna de finalizados:** el board muestra todas las fases;
  bien. Pero la lista oculta finalizados por default y el board no — es
  intencional pero conviene un hint visual de que el board ignora ese toggle.
- **RAID Kanban — accesibilidad del drag:** el DnD nativo no es operable por
  teclado. Para a11y completa, una alternativa con botones "← / →" por tarjeta
  o @dnd-kit con sensores de teclado. **[mejora futura]**

### 2.2 Aprovechamiento de espacio

- **Plan — toolbar:** tras mover acciones al header (ENH-162) y el configurador
  de columnas (ENH-164), la toolbar quedó más limpia. Con muchas columnas
  opcionales activas la tabla scrollea horizontal; el configurador mitiga esto.
- **RAID — header:** ahora hay 3 botones (Nuevo, Exportar {tipo}, Exportar RAID
  4 hojas) + toggle Lista/Kanban + barra de filtros. En viewport angosto se
  apilan (flex-wrap) — OK, pero considerar agrupar los 2 export en un menú
  "Exportar ▾". **[mejora futura]**

### 2.3 Styling / design-system

- Los controles inline nuevos usan tokens del DS (`--border-default`,
  `--color-surface`, etc.) y bordes transparentes con hover — consistente.
- El badge de Hito (ENH-163) usa `--color-info-bg/fg`; coherente con el resto.
- El emoji 🔷 para hito convive con el badge; aceptable, pero un ícono del DS
  (lucide `Diamond`) sería más consistente. **[mejora futura, menor]**

### 2.4 Documentación

- Epics actualizadas en el mismo batch: **EP009** (closed_at, atraso, auto-WBS)
  y **EP006** (export por tipo, listas, Kanban, inline). **DB-CHANGES** con la
  migración 0086.
- `navigation.md`: **sin cambios necesarios** — no se agregaron rutas nuevas
  (Kanban es un toggle `?view=`, no una página; renumber-wbs es endpoint).
- No quedan epics desactualizadas por los commits de Sprint 35.

### 2.5 Deuda / follow-ups sugeridos (sin issue aún)

1. Edición inline "on-click" + optimista (Plan y RAID).
2. A11y del Kanban (teclado).
3. Columna Responsable en RAID + resolución Actor en el read.
4. Auto-WBS: hoy preserva orden por WBS natural; para listas totalmente
   planas/contradictorias el resultado es secuencial. Evaluar una columna
   `position` explícita si se quiere un orden manual estable.
5. Menú "Exportar ▾" para agrupar los exports de RAID.
