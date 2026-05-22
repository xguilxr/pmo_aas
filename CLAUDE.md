# CLAUDE.md — Reglas de trabajo para Claude Code

> Este archivo define **cómo trabajo** en este repo. Se lee al inicio de
> cada sesión junto con `docs/epics/SPRINT.md` y el epic relevante.
> Si algo aquí contradice otro doc, **este archivo gana** hasta que el
> owner lo actualice.

---

## 0. Principio rector — solucionar > documentar

> **Decisión owner 2026-04-29:** se prioriza por encima de todo lo demás.

El proceso de issue tracking, triage, bloques y SPRINT.md existe para
**ordenar** el trabajo, no para reemplazarlo. Si una sesión gasta más
ronda en mover items entre INBOX/QUEUE/Bloques que en escribir código,
algo está mal. Más enfoque en solucionar, menos en documentar issues.

Reglas blandas (no son atajos para saltarse 1 US = 1 commit ni la
revisión del owner, pero sí relajan el ceremonial):

- **El gate `status:ready` se respeta**, pero una vez aprobado no
  hay que volver a justificar el scope: implementar y demostrar que
  funciona.
- **Si un issue ya está implementado** en otro commit/branch →
  cherry-pick + verificar + cerrar. No re-triagear ni re-asignar
  bloque.
- **Si el AC tiene scope grande** (>1 día), entregar el **MVP
  funcional** + documentar el resto como "diferido (no bloqueante)"
  en el comment de cierre. Mejor cerrar 80% que dejar abierto al 20%.
- **Tests + typecheck verdes son la única condición** para considerar
  un fix terminado. Si pasan, se commitea. Si no, se itera hasta que
  pasen — sin batchear.
- **El comment de cierre demuestra** que funciona (TC ejecutados +
  verificación). No es opcional. Es la diferencia entre "fix
  submitted" y "fix delivered".
- **Council de 3 agentes (mini consejo):** se hace **internamente**
  por default (3 perspectivas en el reasoning). Solo se delega a
  sub-agents cuando la decisión arquitectónica lo amerita (>1 día de
  ETA o blast radius alto).
- **Saltarse las reglas de bloques** está permitido cuando el owner
  pide ejecutar un batch de issues. La regla **1 issue = 1 commit**
  no se salta.

Si terminar una ronda implica saturar memoria/context con lectura de
docs auxiliares, prefiere ejecutar y demostrar; el doc se actualiza
al final del bloque, no en cada paso.

---

## 1. Archivos de contexto obligatorios

Antes de tocar código o crear issues, leer en este orden:

1. `docs/project-management/HANDOFF.md` — bridge de la sesión anterior. Indica dónde retomar.
2. `CLAUDE.md` (este archivo) — reglas y mecanismo.
3. `docs/project-management/SPRINT.md` — tarea activa, QUEUE, INBOX y bloques.
4. El o los archivos de epic relevantes en `docs/epics/EP0XX-*.md`.
5. `docs/epics/DECISIONS.md` — solo si hay duda arquitectónica.
6. `docs/epics/DB-CHANGES.md` — solo si la US toca schema.

**Nota (Sprint 2+):** Desde Sprint 2 (2026-04-22), `SPRINT.md` y `SPRINT-DONE-HISTORY.md` viven en `docs/project-management/` (ver sección 6 para estructura).

**No** leer código ni docs por exploración abierta si no están en la
lista anterior. El contexto es finito.

---

## 2. Numeración de identificadores

| Prefijo | Uso | Contador |
|---|---|---|
| `US-###` | Historia de usuario viva del diseño | Global, auto-incremento |
| `BUG-###` | Bug reportado por el owner | Propio, auto-incremento |
| `ENH-###` | Enhancement sobre US existente | Propio, auto-incremento |
| `EP0XX` | Épica (3 dígitos) | Asignado manualmente |
| `DEC-###` | Decisión arquitectónica | Ver `DECISIONS.md` |
| `ADR-###` | Architecture Decision Record | Ver `docs/adr/` |
| `TC-###` | Test case | Ver epic relevante |

**Fuente de verdad del contador "próximo libre":** la sección IN-PROGRESS
de `SPRINT.md` siempre lleva la línea `Próximo libre: US-###, BUG-###,
ENH-###`. Ese es el único lugar canónico — este CLAUDE.md no lo replica
para evitar desincronización.

**Reglas:**
- El próximo ID libre se calcula mirando el último registrado en
  `SPRINT.md` (DONE + INBOX + bloques activos).
- Si una US ya no aplica, queda tachada en el sprint pero **no** se
  reusa su número.
- Los **ENH no crean US nueva**: actualizan la US afectada y quedan como
  referencia/lineage. Ej.: `ENH-003 (afecta US-042)` se documenta en el
  issue y en `SPRINT.md` como enhancement a la US existente.
- Los commits históricos del repo todavía referencian `US-NEW-###` y
  `US-BUG-###` (prefijos antiguos). No se reescribe historia; buscar
  con `git log --grep=042` funciona vía substring.

---

## 3. Ciclo de trabajo — de la idea al fix entregado

El flujo completo tiene 4 fases. Cada item nuevo de trabajo pasa por
todas, pero los items pequeños (BUG simple) pueden saltar de Fase A a
Fase B directo si el owner los pega ya formados.

```
Fase A — Planeación / Diseño   →   Fase B — Triage e issues   →
Fase C — Implementación        →   Fase D — Cierre (owner)
```

---

### Fase A — Planeación / Diseño (solo cuando aplica)

Para frentes grandes (epic nuevo, redesign, módulo nuevo, refactor con
blast radius alto) NO se crean issues primero. Se hace una sesión de
discovery con el owner siguiendo este patrón:

1. **Discovery activo** — Claude pregunta, propone, refina con el
   owner en rondas. Mini-consejo de 3 perspectivas interno por default.
2. **Draft doc vivo** — el output se escribe en `docs/epics/drafts/<tema>.md`
   y se itera con el owner (no en GitHub, no en SPRINT.md todavía).
3. **Owner cierra scope** — confirma alcance, descarta secciones,
   marca opcionales / diferidos. El draft queda como referencia
   normativa.
4. **Promoción a epic oficial** — solo cuando el draft está cerrado,
   se crea `docs/epics/EP0XX-<tema>.md` con US numeradas + AC + TC +
   dependencias + plan de sprints.
5. **Acuerdo final** — owner confirma orden de sprints/bloques y
   damos paso a Fase B.

Ejemplos de cuándo Fase A es obligatoria:
- Epic nuevo (EP020 — Report Builder, EP017 — Directorio).
- Restructure de un módulo existente.
- Cambio que toca > 10 archivos o > 1 día de implementación.
- Cualquier US/ENH cuyo scope no está claro en una línea.

Cuándo se puede saltar Fase A:
- Bug puntual con AC obvio.
- ENH pequeño sobre código existente.
- Owner pega un dump corto donde el triage es directo.

---

### Fase B — Triage e issues

#### Paso 1 — Intake
- El owner pega el comment tal cual, crudo.
- Claude parsea y clasifica **cada item** como:
  - `BUG` — algo no funciona como se esperaba
  - `ENH` — mejora sobre US existente
  - `US` — historia nueva del diseño

#### Paso 2 — Triage
- Para cada item: identifico epic afectado (`EP0XX`), US afectada (si
  aplica), y propongo ID auto-incremento.
- Presento resumen al owner con:
  - Tipo + ID propuesto
  - Epic(s) + US afectada
  - Desc corta (1 línea)
  - Bloque sugerido (existente que calza, o "Bloque X+1" nuevo)
- **Espero OK explícito** antes de crear issues.

#### Paso 3 — Crear issue en GitHub

> **Delegación a sub-agentes:** si hay que crear ≥ 5 issues en una
> tanda, usa un sub-agente con la lista completa de specs en el prompt.
> Si son ≤ 4, créalos directo desde main con el tool mcp__github__
> apropiado.

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

- **Título del issue:** `[BUG-006] — <desc corta>` (la US afectada y el
  epic viven en el body, no en el título).
- **Labels obligatorias al crear:**
  - Tipo: `bug` / `enhancement` / `user-story`
  - Epic: `EP0XX` (uno principal). Si el item toca varios epics, se
    pueden añadir labels adicionales para los secundarios.
  - Status: `status:triage`
  - Extras si aplica: `post-mvp`, `v1.0`, etc.

#### Paso 4 — Integrar a SPRINT.md

Heurística (corresponde a la opción 7c del acuerdo):

1. ¿El item calza en un **Bloque activo** (mismo epic/flujo)?
   Si sí → agrégalo al bloque existente.
2. Si no → propone **"Bloque X+1"** nuevo y espera confirmación del
   owner antes de moverlo de INBOX a QUEUE.
3. Si es urgente (BUG crítico) → propon "reabrir hotfix block" como
   hicimos con Bloque 13.

Sección **📥 INBOX / TRIAGE** al inicio de `SPRINT.md`: aquí viven los
issues recién creados hasta que el owner decide en qué bloque entran.

**Cuándo actualizar SPRINT.md (regla práctica):**
- **Al crear issues nuevos** → agregar al INBOX (1 commit doc).
- **Al cerrar un BLOQUE completo** → mover items de INBOX/IN-PROGRESS
  a DONE. Esto evita actualizar SPRINT.md por cada commit pequeño.
- **Al cerrar SESIÓN** → ejecutar `/handoff` que limpia SPRINT.md
  archivando lo cerrado a `SPRINT-DONE-HISTORY.md` y reescribe
  `HANDOFF.md`.
- **Al cerrar SPRINT completo** → cleanup más profundo (ver §6).

---

### Fase C — Implementación

#### Paso 5 — Antes de tocar código

- **Gate `status:ready`** — el issue debe tener este label antes de
  empezar. Si está en `triage`, ese label es del owner (no de Claude).
  Pedirle al owner que apruebe el gate.
- **1 US/BUG/ENH = 1 commit.** Sin mezclar en el mismo commit.
- Mover la US de INBOX → **IN-PROGRESS** en SPRINT.md antes de empezar.
- **Cambiar label** del issue: `status:ready` → `status:in-progress`.
  (Si por alguna razón viene de `status:triage` directo — owner pasó por
  alto el gate — pedir confirmación antes de saltarlo.)

#### Paso 6 — Commit + push

- Header de commit:
  ```
  fix(scope): BUG-006 — desc corta (refs #42)
  feat(scope): US-051 — desc corta (refs #42)
  feat(scope): ENH-003 — desc corta (refs #42)
  ```
- **Nunca** usar `fix #N` / `closes #N` / `resolves #N` en el commit.
  El owner cierra manualmente.
- Si toca schema, crear migración Alembic en el mismo commit y
  referenciarla en `DB-CHANGES.md` al final.
- **Push obligatorio inmediato** tras el commit. No acumular commits
  locales que no se han pusheado.

#### Paso 7 — Comment al issue + actualizar label

> **Esto NO es opcional.** Cada push de un commit que resuelve un
> issue obliga a 2 acciones inmediatas en GitHub:

1. **Cambiar label** del issue: `status:in-progress` → `status:fix-committed`.
2. **Dejar comment** en el issue con esta plantilla:

```markdown
## Resuelto en commit <SHA corto>

- **Tipo:** BUG-006 (o US-051 / ENH-003)
- **Resuelve:** <qué del reporte original queda arreglado>
- **No resuelve** (si aplica): <scope fuera de este commit>

### Archivos tocados
- `apps/api/app/api/v1/endpoints/foo.py`
- `apps/web/components/bar.tsx`

### Cómo verificar
1. <pasos de smoke test>
2. <endpoint / URL / acción en UI>

### Follow-ups detectados
<si encontré algo durante el fix que abre otro issue, lo listo aquí>
```

3. Mover la US en `SPRINT.md` IN-PROGRESS → DONE (solo si es el
   último item del bloque; si no, esperar al cierre del bloque).
4. **No cerrar** el issue. El owner lo cierra cuando verifica.

> Si hay que actualizar labels o comments en N issues a la vez
> (cierre de un bloque grande), delega a un sub-agente con la lista
> completa para no quemar contexto haciéndolo manual.

---

### Fase D — Cierre

#### Paso 8 — Verificación del owner

El owner:
- Verifica que el fix funciona.
- Si OK → cierra el issue con `completed`.
- Si no OK → comenta, cambia label a `status:needs-rework`, y Claude
  retoma desde Fase C paso 5 en el **mismo** issue (no crear issue nuevo).

#### Paso 9 — Cierre de bloque (Claude)

Cuando todos los issues de un bloque están en `status:fix-committed`
(esperando verificación del owner) o `closed completed`:
- Actualizar SPRINT.md: mover los items del bloque a DONE.
- Si el bloque cierra el sprint, ejecutar el cleanup completo de §6.

---

## 4. Convenciones de commit

```
<tipo>(<scope>): <ID> — <desc corta> (refs #<issue>)
```

**Tipos:** `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `wip`.

**Scopes comunes:**
- `api` — backend FastAPI
- `web` — frontend Next.js
- `worker` — worker Railway
- `org`, `auth`, `dashboard`, `projects`, `admin`, `superadmin`,
  `requests`, `branding`, `ai`, `ops`, `infra`, `epics`, `sprint`,
  `landing`, `decisions`, `db`, `archive`, `rename`

**Ejemplos:**
```
fix(web): BUG-006 — sidebar muestra items admin a usuarios plain (refs #42)
feat(api): US-051 — endpoint /exports/minutes con filtro por período (refs #43)
docs(sprint): mueve BUG-006 de INBOX a Bloque 18 (refs #42)
```

**Reglas de commit:**
- Si el contexto se agota a mitad, `wip(scope): US-051 — avance parcial (refs #N)`
  y anotar en `SPRINT.md` dónde quedó.
- **No** hacer `--amend` a commits ya pusheados.
- **No** usar `--no-verify` para saltar hooks.

---

## 5. Labels de GitHub

Set requerido. Si falta alguna, la crea el owner (UI o gh CLI):

| Label | Color sugerido | Uso |
|---|---|---|
| `bug` | #d73a4a | Tipo: reporte de fallo |
| `enhancement` | #a2eeef | Tipo: mejora sobre US existente |
| `user-story` | #7057ff | Tipo: historia nueva |
| `EP001` … `EP02X` | #0e8a16 | Epic al que pertenece (uno o varios) |
| `status:triage` | #fbca04 | Recién creado, pendiente de aprobación del triage |
| `status:ready` | #0e8a16 | **Owner aprobó el triage — Claude puede arrancar** |
| `status:in-progress` | #0075ca | Claude está trabajando |
| `status:fix-committed` | #5319e7 | Commit pusheado, esperando review del owner |
| `status:needs-rework` | #b60205 | Owner rechazó el fix, retomar |
| `post-mvp` | #cccccc | Fuera del scope v1.0 |
| `v1.0` / `v1.1` / `v1.2` / `v1.3` / `v2.0` | #006b75 | Release target |

**Flujo de transición de status:**

```
status:triage ──▶ status:ready ──▶ status:in-progress ──▶ status:fix-committed
                    ↑ (owner)                                    │
                    │                                            ▼
                    │                                    (owner verifica)
                    │                                            │
                    │                                    ┌───────┴───────┐
                    │                                    ▼               ▼
                    └──────(status:needs-rework)────────────      [close issue]
                                                                  completed / not_planned
```

**Gate de arranque:** Claude **no** puede empezar una US/BUG/ENH hasta que el
issue tenga `status:ready`. La transición `triage → ready` la hace el owner
(o por propuesta explícita del owner en el chat). Esta separación evita que
Claude arranque con un scope que el owner todavía no ha validado.

**`needs-rework`:** cuando el owner rechaza el fix, el issue vuelve a
`status:triage` (no directo a `in-progress`). Claude reevalúa el scope con
el owner y espera de nuevo el `status:ready` antes de tocar código.

---

## 6. SPRINT.md — estructura esperada

Archivo vive en `docs/project-management/SPRINT.md` (desde Sprint 2).

```
🔴 IN-PROGRESS    (la US/bloque que Claude está tocando ahora,
                   o "Sin US activa" + próximo paso accionable)
📥 INBOX / TRIAGE (issues recién creados + Sprints planeados con
                   sus bloques en orden de ejecución)
⏸️ Deferred       (issues sin asignación de versión, esperan decisión)
✅ DONE           (tabla resumen — detalle en SPRINT-DONE-HISTORY.md)

📋 Backlog v2.0
```

**Separación de histórico:**
- `SPRINT.md` → solo items del sprint actual + INBOX + Deferred + backlog v2.0.
- `SPRINT-DONE-HISTORY.md` → detalle de bloques cerrados de sprints anteriores.

**Flujo de un item en SPRINT.md:**
1. Al crear issue → entra al **INBOX** (sección del sprint correspondiente).
2. Al arrancar implementación → mover a **IN-PROGRESS**.
3. Al cerrar bloque → mover los items a **DONE** (tabla resumen);
   el detalle del bloque va a SPRINT-DONE-HISTORY.md.

> **NO mover items por cada commit individual.** Solo al cerrar
> bloque completo o al cierre de sesión vía `/handoff`.

### Limpieza al cierre de sprint (obligatoria)

Cuando un sprint termina (todos sus bloques en DONE y el owner confirma cierre), antes de arrancar el siguiente sprint Claude debe:

1. **Mover** todas las secciones `🗂️ Sprint N (vX.Y) — CERRADO` y el contexto IN-PROGRESS narrativo de ese sprint desde `SPRINT.md` a `SPRINT-DONE-HISTORY.md` (preservando bloques, commits SHA, migraciones agregadas y diferidos).
2. **Reemplazar** la sección DONE de `SPRINT.md` con una tabla resumen `Sprint | Versión | Cerrado | Items` (1 fila por sprint cerrado) que apunte a `SPRINT-DONE-HISTORY.md`.
3. **Limpiar** `IN-PROGRESS` para que apunte solo al nuevo sprint activo (o "Sin US activa" si recién arranca).
4. **Truncar** la sección `Notas y cambios` a entradas del sprint actual + la entrada del cierre; el histórico narrativo vive en `SPRINT-DONE-HISTORY.md`.
5. **Commit** con mensaje `docs(sprint): cierre Sprint N — archiva a SPRINT-DONE-HISTORY.md`.

Objetivo: `SPRINT.md` nunca debe pasar de ~250 líneas. Si crece más, es señal de que falta limpiar.

---

## 7. Regla sagrada: 1 US = 1 commit

No acumular cambios de varias US en un solo commit, nunca.

Excepciones permitidas:
- Commits de **docs puros** que tocan SPRINT.md y moviendo dos US al
  mismo tiempo (ej.: cerrar bloque completo).
- Commits de **housekeeping** (`docs(rename)`, `chore(cleanup)`) que no
  están atados a una US específica.

---

## 8. Branch policy

- `main` — productivo. No se pushea directo.
- `claude/<tema>-<sufijo>` — branch de trabajo de Claude. Todas las US
  se hacen aquí; el PR lo abre el owner o Claude (según quién esté
  manejando la sesión).
- Cada sesión de Claude tiene asignada una branch específica; ver
  `SPRINT.md` → IN-PROGRESS para la activa.

### Rebase + force-push

Cuando una branch abierta queda atrás respecto a `main` (CI falla
porque main agregó migraciones / cambios que la branch no tiene):

1. `git fetch origin main`
2. `git rebase origin/main` (sobre la branch local).
3. Resolver conflictos si los hay.
4. `git push --force-with-lease origin <branch>` — **siempre con
   `--force-with-lease`, nunca con `--force` solo**. El flag protege
   contra pisar trabajo del owner si modificó la branch remota.

Esto aplica también cuando hay collisions de migraciones Alembic
(revision IDs duplicados al mergear lanes paralelos a main).

### Sesiones secuenciales > paralelas (decisión owner 2026-05-22)

Tras múltiples collisions de migraciones por paralelizar lanes en el
mismo sprint, la metodología por default es:

- **1 sesión activa = 1 lane = 1 branch.**
- Migraciones consecutivas, sin paralelización.
- Esperar CI verde + merge antes de arrancar la siguiente US.
- La paralelización solo se justifica si los lanes son completamente
  independientes (sin migraciones, sin schemas compartidos).

---

## 9. Cuando dudar

- Si un item no calza claramente en BUG/ENH/US → **preguntar**.
- Si no hay Bloque activo razonable → **proponer** "Bloque X+1" y esperar.
- Si la US requiere tocar schema sin migración clara → **parar** y
  consultar `DB-CHANGES.md` + `DECISIONS.md`.
- Si un fix toca más de 10 archivos → **parar** y validar con el owner
  antes de seguir.

---

## 10. Memoria y contexto

- **No** leer archivos grandes completos cuando basta una sección.
- Para rename/refactor masivo, preferir `sed` vía Bash (no carga
  contenido a memoria) sobre `Edit` con `replace_all`.
- Al abrir un archivo, anotar qué se necesita y descartarlo después.
- Si el contexto se agota, commit con `wip:` y documentar dónde quedó
  en `docs/project-management/SPRINT.md` (sección IN-PROGRESS) antes de terminar la sesión.

### Delegación a sub-agentes

Usa sub-agentes (con la herramienta `Agent`) cuando:

- **Crear ≥ 5 issues** en GitHub: pasa la lista completa al agente.
- **Aplicar labels en ≥ 10 issues**: agente con tabla `# → labels`.
- **Audit de codebase**: sub-agente explorer cuando hay que mapear
  varios módulos antes de planear.
- **Búsquedas multi-archivo** que exceden 3 queries directas.

Mantén la sesión principal para discusión + diseño + commits propios.
Los agentes ahorran contexto del thread principal.

---

## 11. Resumen de ronda (obligatorio al cerrar cada turno)

> Una "ronda" = un prompt del owner + la acción que Claude ejecuta en
> respuesta. Al terminar cada ronda, **siempre** entrego el siguiente
> resumen antes de quedar a la espera del próximo prompt.

### Plantilla

```markdown
## Resumen de la ronda

**Hecho:**
- <bullet 1: qué decisión se tomó / qué se implementó>
- <bullet 2: qué se movió en SPRINT.md / qué label cambió>
- <bullet 3: commits nuevos con SHA corto>

**Archivos modificados:**
- `path/a/archivo.ext` — <razón 1 línea>
- `path/a/otro.ext` — <razón 1 línea>
(o referencia a `git diff --stat HEAD~N..HEAD` si son muchos)

**Acciones externas para el owner:**
- [ ] Crear PR de `<branch>` → `main` (o merge directo si aplica)
- [ ] Crear label `<nombre>` en GitHub UI (si falta)
- [ ] Correr migración Alembic en Railway (`alembic upgrade head`)
- [ ] Subir landing/ a HostGator (o cualquier otro paso manual)
- [ ] Cerrar issue #N tras verificar el fix
- [ ] (ninguna, si todo quedó autoejecutable)
```

### Reglas

- **Bullets concisos**, 1 línea cada uno. Si una acción necesita más
  explicación, que viva en el commit message o en el comment del issue.
- **Lista de archivos** siempre presente; si hay más de 15, uso
  `git diff --stat <rango>` en vez de listarlos uno por uno.
- **Acciones externas** marcadas con `- [ ]` (checkbox) para que el
  owner las marque conforme las ejecuta. Si no hay ninguna, escribir
  explícitamente "ninguna" — nunca omitir el bloque.
- Si la ronda terminó con un **commit + push**, siempre incluir el
  SHA corto y el nombre de la branch.
- Si la ronda fue puramente de **discusión/propuesta** (no hubo
  cambios), el bloque "Archivos modificados" dice `— ninguno —` y
  "Acciones externas" lista lo que el owner debe responder/decidir.

---

## 12. Handoff entre sesiones — `/handoff`

> El skill `/handoff` (en `.claude/skills/handoff/SKILL.md`) genera y
> mantiene `docs/project-management/HANDOFF.md` con el estado para la
> próxima sesión.

### Flujo obligatorio

1. **Al abrir una sesión:** Claude lee `HANDOFF.md` **antes que
   SPRINT.md**. Es el puente que la sesión anterior dejó. Si está
   vacío o desactualizado, pídeselo al owner antes de retomar.

2. **Al cerrar una sesión:** owner invoca `/handoff`. El skill:
   - Limpia `SPRINT.md` archivando lo completado a `SPRINT-DONE-HISTORY.md`.
   - Trunca `Notas y cambios` a las del sprint actual.
   - Reescribe `HANDOFF.md` con: dónde estamos, dónde retomar, hecho
     en la sesión, PRs en flight, gotchas, cleanup pendiente, ideas
     futuras sin issue.
   - Hace 1 commit + push (sin crear PR).

3. **Regla dura:** SPRINT.md nunca supera ~250 líneas. Si crece más,
   `/handoff` es el momento de limpiarlo.

4. **Si la sesión no produjo commits**, `/handoff` igual escribe un
   resumen breve ("sesión de discusión/planeación") para que la
   próxima sesión retome el hilo.

---

**Última actualización:** 2026-05-22 (post-Sprint 26)
**Responsable:** Claude Code (owner: xguilxr)
