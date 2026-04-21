# CLAUDE.md — Reglas de trabajo para Claude Code

> Este archivo define **cómo trabajo** en este repo. Se lee al inicio de
> cada sesión junto con `docs/epics/SPRINT.md` y el epic relevante.
> Si algo aquí contradice otro doc, **este archivo gana** hasta que el
> owner lo actualice.

---

## 1. Archivos de contexto obligatorios

Antes de tocar código o crear issues, leer en este orden:

1. `CLAUDE.md` (este archivo) — reglas y mecanismo.
2. `docs/epics/SPRINT.md` — tarea activa, QUEUE, INBOX y bloques.
3. El o los archivos de epic relevantes en `docs/epics/EP0XX-*.md`.
4. `docs/epics/DECISIONS.md` — solo si hay duda arquitectónica.
5. `docs/epics/DB-CHANGES.md` — solo si la US toca schema.

**No** leer código ni docs por exploración abierta si no están en la
lista anterior. El contexto es finito.

---

## 2. Numeración de identificadores

| Prefijo | Uso | Contador | Próximo libre |
|---|---|---|---|
| `US-###` | Historia de usuario viva del diseño | Global, auto-incremento | **US-055** (US-054 cerrada en Bloque 22) |
| `BUG-###` | Bug reportado por el owner | Propio, auto-incremento | **BUG-023** |
| `ENH-###` | Enhancement sobre US existente | Propio, auto-incremento | **ENH-012** (ENH-011 cerrada en Bloque 22) |
| `EP0XX` | Épica (3 dígitos) | Asignado manualmente | — |
| `DEC-###` | Decisión arquitectónica | Ver `DECISIONS.md` | — |
| `ADR-###` | Architecture Decision Record | Ver `docs/adr/` | — |
| `TC-###` | Test case | Ver epic relevante | — |

**Reglas:**
- El próximo ID libre se calcula mirando el último registrado en
  `SPRINT.md` (DONE + QUEUE + INBOX + bloques activos).
- Si una US ya no aplica, queda tachada en el sprint pero **no** se
  reusa su número.
- Los **ENH no crean US nueva**: actualizan la US afectada y quedan como
  referencia/lineage. Ej.: `ENH-003 (afecta US-042)` se documenta en el
  issue y en `SPRINT.md` como enhancement a la US existente.
- Los commits históricos del repo todavía referencian `US-NEW-###` y
  `US-BUG-###` (prefijos antiguos). No se reescribe historia; buscar
  con `git log --grep=042` funciona vía substring.

---

## 3. Ciclo feedback → issue → fix → comment

Flujo que arranca cuando el owner pega un comment con uno o varios
items (bugs, enhancements o ideas nuevas).

### Paso 1 — Intake
- El owner pega el comment tal cual, crudo.
- Claude parsea y clasifica **cada item** como:
  - `BUG` — algo no funciona como se esperaba
  - `ENH` — mejora sobre US existente
  - `US` — historia nueva del diseño

### Paso 2 — Triage
- Para cada item: identifico epic afectado (`EP0XX`), US afectada (si
  aplica), y propongo ID auto-incremento.
- Presento resumen al owner con:
  - Tipo + ID propuesto
  - Epic + US afectada
  - Desc corta (1 línea)
  - Bloque sugerido (existente que calza, o "Bloque X+1" nuevo)
- **Espero OK explícito** antes de crear issues.

### Paso 3 — Crear issue en GitHub

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
  - Epic: `EP0XX` (uno solo)
  - Status: `status:triage`
  - Extras si aplica: `post-mvp`, `v1.0`, etc.

### Paso 4 — Integrar a SPRINT.md

Heurística (corresponde a la opción 7c del acuerdo):

1. ¿El item calza en un **Bloque activo** (mismo epic/flujo)?
   Si sí → agrégalo al bloque existente.
2. Si no → propone **"Bloque X+1"** nuevo y espera confirmación del
   owner antes de moverlo de INBOX a QUEUE.
3. Si es urgente (BUG crítico) → propon "reabrir hotfix block" como
   hicimos con Bloque 13.

Sección **📥 INBOX / TRIAGE** al inicio de `SPRINT.md`: aquí viven los
issues recién creados hasta que el owner decide en qué bloque entran.

### Paso 5 — Implementación

- **1 US/BUG/ENH = 1 commit.** Sin mezclar en el mismo commit.
- Mover la US de INBOX/QUEUE → **IN-PROGRESS** antes de empezar.
- Cambiar label `status:triage` → `status:in-progress` en el issue.
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

### Paso 6 — Comment al commit

Cuando el commit está pusheado:

1. Cambiar label `status:in-progress` → `status:fix-committed` en el issue.
2. Dejar comment con esta plantilla:

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

3. Mover la US en `SPRINT.md` a **DONE** con fecha y SHA del commit.
4. **No cerrar** el issue. El owner lo cierra cuando verifica.

### Paso 7 — Cierre (owner)

El owner:
- Verifica que el fix funciona.
- Si OK → cierra el issue con `completed`.
- Si no OK → comenta, cambia label a `status:needs-rework`, y Claude
  retoma desde paso 5 en el **mismo** issue (no crear issue nuevo).

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
| `EP001` … `EP016` | #0e8a16 | Epic al que pertenece |
| `status:triage` | #fbca04 | Recién creado, pendiente de plan |
| `status:in-progress` | #0075ca | Claude está trabajando |
| `status:fix-committed` | #5319e7 | Commit pusheado, esperando review del owner |
| `status:needs-rework` | #b60205 | Owner rechazó el fix, retomar |
| `post-mvp` | #cccccc | Fuera del scope v1.0 |
| `v1.0` | #006b75 | Blocking release v1.0 |

**Flujo de transición de status:**

```
status:triage ──▶ status:in-progress ──▶ status:fix-committed
                                                │
                        ┌───────────────────────┘
                        ▼
               (owner verifica)
                        │
                ┌───────┴───────┐
                ▼               ▼
           [close]      status:needs-rework
                                │
                                └───▶ status:in-progress (reabre)
```

---

## 6. SPRINT.md — estructura esperada

```
🔴 IN-PROGRESS    (la US que Claude está tocando ahora, o "Sin US activa")
📥 INBOX / TRIAGE (issues recién creados, pendientes de asignar a bloque)
⏳ QUEUE          (próximas 5, en orden)
✅ DONE           (historial reciente)

📋 Backlog por prioridad
  Bloque 1, 2, 3... (por orden histórico)
```

Reglas:
- Al crear un issue nuevo, se agrega a **📥 INBOX** primero.
- El owner (o Claude por propuesta) lo mueve a un **Bloque** existente
  o propone **"Bloque X+1"** nuevo.
- De ahí entra a **QUEUE** cuando le toca el turno.
- De QUEUE → **IN-PROGRESS** cuando Claude empieza a trabajarlo.
- De IN-PROGRESS → **DONE** cuando el commit está pusheado.

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
  en `SPRINT.md` antes de terminar la sesión.

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

**Última actualización:** 2026-04-21
**Responsable:** Claude Code (owner: xguilxr)
