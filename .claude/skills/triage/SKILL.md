---
name: triage
description: Convierte un comentario crudo del owner en issues de GitHub bien formados — clasifica cada punto como BUG/ENH/US, asigna epic e ID, propone bloque de sprint y crea los issues con labels. Úsala cuando el owner pegue feedback sin procesar, pida "crea un issue para X", o abras un frente nuevo que necesite diseño previo. NO la uses para implementar (eso es cerrar-item) ni para un cambio que el owner ya pidió ejecutar directo.
---

# Triage — de comentario crudo a issues

Cubre las **Fases A y B** del ciclo de trabajo. La Fase C (implementar) y la D
(cerrar) viven en la skill `cerrar-item`.

---

## Fase A — Planeación / Diseño (solo cuando aplica)

Arranca de dos formas: una sesión de diseño explícita («vamos a diseñar X»), o
un comentario suelto del owner que abre un frente nuevo o redefine algo.

### Cuándo es obligatoria

- Funcionalidad **nueva** que requiere epic doc (módulo nuevo, flujo end-to-end).
- Redesign o restructure de funcionalidad existente.
- Cambio que toca > 10 archivos o > 1 día de implementación.
- Cualquier US/ENH cuyo scope no esté claro en una línea.

### Cuándo se salta

- Bug puntual con AC obvio.
- ENH pequeño sobre código existente.
- Cambio puntual que el owner pide directo → Fase B paso 1.

### Flujo

1. **Discovery activo** — preguntar, proponer, refinar con el owner en rondas.
   Mini-consejo de 3 perspectivas interno por default.
2. **Draft doc vivo** — el output va a `docs/epics/drafts/<tema>.md` y se itera
   con el owner. No en GitHub, no en SPRINT.md todavía.
3. **Owner cierra scope** — confirma alcance, descarta secciones, marca
   opcionales y diferidos. El draft queda como referencia normativa.
4. **Epic nueva o existente:**
   - Funcionalidad **nueva** → crear `docs/epics/EP0XX-<tema>.md`.
   - **Afecta una epic existente** → actualizar `docs/epics/EP0YY-*.md`
     directamente. No crear epic nueva.
   - Cambio **estrictamente puntual** → saltar a Fase B.
5. **Acuerdo final** — owner confirma orden de sprints/bloques.

> **Las epics son documentación funcional viva, no plan de trabajo.** Epic = qué
> hace la plataforma. Issue = instrucción técnica. SPRINT.md = estado del
> trabajo. No confundir los tres roles.

---

## Fase B — Triage e issues

### Paso 1 — Intake

El owner pega el comentario crudo. Parsear y clasificar **cada item**:

- `BUG` — algo no funciona como se esperaba
- `ENH` — mejora sobre US existente
- `US` — historia nueva del diseño

### Paso 2 — Triage

Para cada item: identificar epic afectado (`EP0XX`), US afectada si aplica, y
proponer ID auto-incremento.

Presentar al owner: tipo + ID propuesto · epic(s) + US afectada · desc de una
línea · bloque sugerido (existente que calce, o «Bloque X+1» nuevo).

**Esperar OK explícito antes de crear issues.**

### Paso 3 — Crear issue en GitHub

> **Delegación:** si hay ≥ 5 issues en una tanda, usa un sub-agente con la lista
> completa de specs en el prompt (ver skill `delegar`). Si son ≤ 4, créalos
> directo.

Template obligatorio:

```markdown
## Contexto
<qué estaba pasando / comportamiento esperado vs actual>

## Tipo y alcance
- Tipo: BUG / ENH / US
- ID: BUG-### / ENH-### / US-###
- Epic: EP0XX
- US afectada (si ENH): US-### — <título>
- Sprint bloque propuesto: Bloque N

## Criterios de aceptación
- [ ] CA1
- [ ] CA2

## Test cases
- [ ] TC-###: <descripción>

## Fix propuesto
<hipótesis / archivos a tocar / riesgo>
```

**Título:** `[BUG-006] — <desc corta>`. La US afectada y el epic van en el body,
no en el título.

**Labels obligatorias al crear:**
- Tipo: `bug` / `enhancement` / `user-story`
- Epic: `EP0XX` (uno principal; añadir secundarios si toca varios)
- Status: `status:triage`
- Extras si aplica: `post-mvp`, `v1.0`, etc.

**Formato canónico de referencia en docs:** `<ID> #<issue>` juntos —
`US-120 #378`, `BUG-061 #391`, `ENH-097 #373`. El ID es estable en el tiempo; el
`#issue` lleva al detalle técnico.

### Paso 4 — Integrar a SPRINT.md

1. ¿Calza en un **Bloque activo** (mismo epic/flujo)? → agregarlo ahí.
2. Si no → proponer **«Bloque X+1»** y esperar confirmación antes de moverlo de
   INBOX a QUEUE.
3. Si es urgente (BUG crítico) → proponer reabrir un hotfix block.

La sección **📥 INBOX / TRIAGE** de `SPRINT.md` es donde viven los issues recién
creados hasta que el owner decide su bloque.

---

## Labels de GitHub — set requerido

Si falta alguna, la crea el owner (UI o `gh` CLI).

| Label | Color | Uso |
|---|---|---|
| `bug` | #d73a4a | Tipo: reporte de fallo |
| `enhancement` | #a2eeef | Tipo: mejora sobre US existente |
| `user-story` | #7057ff | Tipo: historia nueva |
| `EP001` … `EP020` | #0e8a16 | Epic al que pertenece |
| `status:triage` | #fbca04 | Recién creado, pendiente de aprobación |
| `status:ready` | #0e8a16 | **Owner aprobó — Claude puede arrancar** |
| `status:in-progress` | #0075ca | Claude está trabajando |
| `status:fix-committed` | #5319e7 | Commit pusheado, esperando review |
| `status:needs-rework` | #b60205 | Owner rechazó el fix, retomar |
| `post-mvp` | #cccccc | Fuera del scope v1.0 |
| `v1.0` … `v2.0` | #006b75 | Release target |

**Transición de status:**

```
status:triage ──▶ status:ready ──▶ status:in-progress ──▶ status:fix-committed
                    ↑ (owner)                                    │
                    │                                    (owner verifica)
                    │                                    ┌───────┴───────┐
                    └──(status:needs-rework)─────────────      [close issue]
```

**Gate de arranque:** Claude **no** empieza una US/BUG/ENH hasta que el issue
tenga `status:ready`. La transición `triage → ready` la hace el owner, por label
o por chat.

**`needs-rework`:** cuando el owner rechaza un fix, el issue vuelve a
`status:triage` — no directo a `in-progress`. Se reevalúa el scope con el owner
y se espera de nuevo el `status:ready`.

---

## Cuando dudar

- Si un item no calza claramente en BUG/ENH/US → **preguntar**.
- Si no hay bloque activo razonable → **proponer** «Bloque X+1» y esperar.
