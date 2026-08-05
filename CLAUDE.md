# CLAUDE.md — Reglas de trabajo para Claude Code

> Este archivo define **cómo trabajo** en este repo. Se lee al inicio de
> cada sesión junto con `SPRINT.md`, `HANDOFF.md` y el índice de epics.
> Si algo aquí contradice otro doc, **este archivo gana** hasta que el
> owner lo actualice.

---

## 0. Principios rectores

> **Decisión owner 2026-04-29 + 2026-05-22:** estos principios mandan sobre todo lo demás.

### 0.1 Solucionar > documentar (issues / tracking)

El proceso de issue tracking, triage, bloques y SPRINT.md existe para
**ordenar** el trabajo, no para reemplazarlo. Si una sesión gasta más
ronda en mover items entre INBOX/Bloques que en escribir código,
algo está mal. Más enfoque en solucionar, menos en documentar issues.

### 0.2 Documentación del producto pristina

> **Nuevo 2026-05-22.** Co-principio que NO compite con 0.1.

Las **epics (`docs/epics/EP0XX-*.md`) describen la funcionalidad del
producto**, no el plan de trabajo. Cuando un commit cambia el
comportamiento descrito en una epic, **la epic debe actualizarse en el
mismo bloque de trabajo**, no después.

Distinción clave:
- **Epic** = qué hace la plataforma, descripción funcional, viva.
- **Issue** = instrucción técnica para implementar un cambio puntual.
- **SPRINT.md** = orden y estado del trabajo en curso.

Cuando una US/ENH/BUG modifica:
- Comportamiento descrito en la epic → actualizar epic.
- Schema descrito en la epic → actualizar epic (+ DB-CHANGES.md).
- Endpoint nuevo / removido / renombrado → actualizar epic.
- Decisión arquitectónica → además actualizar `DECISIONS.md`.

Si el cambio NO afecta la descripción del producto (refactor interno,
fix de typo, optimización transparente), no hay nada que actualizar.

**Implementación práctica:** usa un sub-agente con modelo Haiku
(rápido + barato) para redactar/refinar la edición del epic doc
después del commit principal. El patrón está en la skill `delegar`.

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

## 0.3 Verificación, contexto y acciones irreversibles

**Cómo se comprueba que algo funciona aquí: skill `verificar`.** Stack,
preparación del entorno, los siete comandos con su criterio, los gates de CI y
las rutas que no se editan a mano. Vive en una skill porque se consulta **al
verificar**, no en cada turno.

**Definición de terminado (MCA FLU-02).** Lint, typecheck y tests de API en
verde, criterio `exit 0` y nunca un conteo. Sin excepciones ni fallos
«esperados». Si algo sale rojo, es tuyo. El DoD de `cerrar-item` se marca
**después**, no en su lugar.

**El contexto permanente tiene techo y CI lo hace cumplir.** Si tu cambio
engorda `CLAUDE.md`, `SPRINT.md` o `HANDOFF.md`, `scripts/check_contexto.py`
falla. Umbrales y razones en `conformidad.yaml`; no se suben sin escribir por
qué, y recortar es la respuesta por defecto.

**Lo que el modelo devuelve pasa por un conjunto de evaluación con umbral** (MCS
IA-07/08/09), job `evaluacion-ia`. Un fallo de IA que llegue a un usuario entra
al conjunto **antes** de arreglarse: `apps/api/evaluacion/README.md`.

**Las amenazas y sus controles** viven en `docs/architecture/modelo-amenazas.md`.
Una ruta sin autenticación o un destino externo nuevo rompen su trinquete a
propósito: obligan a pasar por el modelo antes de declararlos.

**Lo irreversible se bloquea; preguntar no alcanzaba** (MCA AUT-01). Lo hace
`scripts/guard_irreversible.py` como hook `PreToolUse`. Se **bloquea** `--force`
sin lease, `--no-verify`, push a `main`, `alembic upgrade`/`downgrade`,
`DROP`/`TRUNCATE`, `rm -rf`, `reset --hard`/`clean -f` y `branch -D`. Se
**pregunta** solo ante `--force-with-lease`, `gh issue close` y `commit --amend`.
Con los permisos de la sesión relajados, un `ask` no abre diálogo y el comando
corre igual; `deny` frena en cualquier modo. Motivos en el docstring del guard,
trinquete en `apps/api/tests/test_mca_aut01_guard.py`.

---

## 1. Qué se carga siempre, y qué bajo demanda

**Siempre**, en este orden:

1. `docs/project-management/HANDOFF.md` — puente de la sesión anterior. Dice dónde retomar.
2. `CLAUDE.md` (este archivo) — lo que manda en cada turno.
3. `docs/project-management/SPRINT.md` — IN-PROGRESS e INBOX.
4. `docs/epics/README.md` — índice de epics: qué cubre cada uno y de qué depende.

**Bajo demanda**, cuando el trabajo lo pide y no antes:

| Se abre | Cuándo |
|---|---|
| `docs/epics/EP0XX-*.md` | Al **tocar** ese epic. El índice basta para decidir cuál |
| `docs/project-management/SPRINT-BACKLOG.md` | Al planear, no al ejecutar |
| `docs/epics/DECISIONS.md` | Ante duda arquitectónica |
| `docs/epics/DB-CHANGES.md` | Si el cambio toca esquema |
| Skill `verificar` | Al comprobar que algo funciona |
| `docs/architecture/modelo-amenazas.md` | Si el cambio cruza una frontera de confianza |

> **Por qué el epic ya no se carga entero.** La regla anterior obligaba a leer
> «el epic relevante» antes de empezar, y eso metía un documento funcional
> completo en el contexto permanente antes de saber siquiera si se iba a abrir.
> El índice cuesta una fracción y sirve para lo único que hacía falta al
> arrancar: decidir cuál abrir. Es MCA CTX-04 — y bajar la cifra sin partir de
> verdad el documento sería falsear la medición, no reducirla. Las mediciones
> fechadas están en `conformidad.yaml`.

**No** leer código ni docs por exploración abierta fuera de estas listas. El
contexto es finito y el techo lo hace cumplir el CI.

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
| `TC-###` | Test case | Ver el epic que lo cubre |

**El próximo ID libre se deriva, no se almacena** (MCA CTX-03):

```bash
git fetch origin main            # SIEMPRE contra main actualizado
python scripts/proximo_id.py     # --detalle muestra el máximo por fuente
```

Une GitHub, `git log` y los docs, y toma el máximo. **No basta `gh issue list`:**
muchos batches se ejecutaron por chat sin crear issues. El porqué y el incidente
de IDs duplicados de 2026-06-06 —cuyos IDs canónicos son **ENH-155..158 /
BUG-077**— están en el docstring del script.

**Reglas:**
- Si una US ya no aplica, queda tachada en el sprint pero **no** se reusa su
  número.
- Los **ENH no crean US nueva**: actualizan la US afectada y quedan como
  referencia/lineage. Ej.: `ENH-003 (afecta US-042)` se documenta en el issue y
  en `SPRINT.md` como enhancement a la US existente.
- Los commits históricos todavía referencian `US-NEW-###` y `US-BUG-###`
  (prefijos antiguos). No se reescribe historia; `git log --grep=042` funciona
  vía substring.

---

## 3. Ciclo de trabajo

De la idea al fix entregado, en cuatro fases:

```
Fase A — Planeación / Diseño   →   Fase B — Triage e issues   →
Fase C — Implementación        →   Fase D — Cierre (owner)
```

| Fases | Qué cubren | Dónde vive el procedimiento |
|---|---|---|
| **A y B** | Discovery, draft en `docs/epics/drafts/`, clasificación BUG/ENH/US, plantilla de issue, labels, integración a SPRINT.md | skill **`triage`** |
| **C y D** | Slice end-to-end, commit, comment de cierre con evidencia, DoD, cierre de bloque | skill **`cerrar-item`** |

Lo que no se delega a una skill porque manda siempre:

- **1 US/BUG/ENH = 1 commit.** Sin excepciones (ver §7).
- **Claude no arranca sin OK explícito del owner**, por label `status:ready` o
  por chat.
- **Claude nunca cierra un issue.** Lo cierra el owner al verificar.
- **El comment de cierre demuestra que funciona** (TC ejecutados +
  verificación). Es la diferencia entre «fix submitted» y «fix delivered».
- Si un fix toca **más de 10 archivos**, parar y validar con el owner.
- Si la US toca schema sin migración clara, parar y consultar `DB-CHANGES.md` +
  `DECISIONS.md`.

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

Set de labels, colores y el diagrama de transición de status: skill **`triage`**.

**Gate de arranque:** Claude **no** empieza una US/BUG/ENH sin `status:ready`, o
sin un OK explícito del owner por chat. La transición `triage → ready` la hace
el owner, nunca Claude.

---

## 6. SPRINT.md

Vive en `docs/project-management/SPRINT.md`. Secciones: IN-PROGRESS · INBOX /
TRIAGE · Deferred · DONE (tabla resumen) · Backlog v2.0. El detalle de lo
cerrado va a `SPRINT-DONE-HISTORY.md`.

**No se actualiza en cada commit** — se actualiza al crear issues, al cerrar
bloque, al cerrar sprint y al cerrar sesión.

**Nunca pasa de 250 líneas.** Lo hace cumplir el CI (§0.3). La estructura
completa, la tabla de frecuencia y el cleanup de cierre de sprint viven en la
skill **`handoff`**, que es quien los ejecuta.

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
- Para rename/refactor masivo, preferir `sed` vía Bash (no carga contenido a
  memoria) sobre `Edit` con `replace_all`.
- Al abrir un archivo, anotar qué se necesita y descartarlo después.
- Si el contexto se agota: commit `wip:` y documentar dónde quedó en
  `SPRINT.md` (IN-PROGRESS) antes de terminar la sesión.
- El contexto permanente tiene techo y lo hace cumplir el CI (§0.3).

**Delegar a sub-agentes** es la forma principal de no quemar contexto en trabajo
mecánico. Cuándo hacerlo, con qué modelo y el modelo de orquestación: skill
**`delegar`**.

---

## 11. Resumen de ronda

Al cerrar **cada turno** se entrega un resumen al owner: qué se hizo, qué
archivos cambiaron y qué acciones externas le quedan. Nunca se omite el bloque
de acciones externas: si no hay ninguna, se escribe «ninguna».

Plantilla y reglas en la skill **`resumen-ronda`**.

---

## 12. Handoff entre sesiones — `/handoff`

- **Al abrir sesión:** leer `HANDOFF.md` **antes que `SPRINT.md`**. Es el puente
  que dejó la sesión anterior. Si está vacío o desactualizado, pedírselo al
  owner antes de retomar.
- **Al cerrar sesión:** el owner invoca `/handoff`. Limpia `SPRINT.md`, archiva
  lo cerrado y reescribe `HANDOFF.md`. Aunque la sesión no haya producido
  commits, igual deja el puente.

Procedimiento completo en la skill **`handoff`**.

---

## 13. Mentalidad end-to-end

> **Decisión owner 2026-05-23.** Cada cambio de funcionalidad se piensa como
> **slice completo** (backend → worker → DB → UX → UI → docs), no como rebanada
> técnica suelta. Si la funcionalidad no es alcanzable desde la UI, no existe.

El checklist por capa, las anclas concretas (qué obliga a qué) y el DoD viven en
la skill **`cerrar-item`**. Se cargan al cerrar un item, que es cuando se usan.

---

**Última actualización:** 2026-08-03 — auditoría MCA acción 6: los procedimientos
repetibles salieron a `.claude/skills/` (`triage`, `cerrar-item`, `delegar`,
`resumen-ronda`, `handoff`). Este archivo queda con lo que manda siempre.
**Responsable:** Claude Code (owner: xguilxr)
