---
tipo: guia
responsable: propietario
estado: vigente
revisado: 2026-08-12
revisar_cada: 90d
---

# CLAUDE.md — Reglas de trabajo para Claude Code

> Define cómo se trabaja en este repo. Si contradice otro doc, este archivo
> gana hasta que el owner lo actualice.

## 0. Principios rectores

### 0.1 Solucionar > documentar

El tracking (issues, bloques, SPRINT.md) ordena el trabajo; no lo reemplaza.
Dedica la ronda a escribir código, no a mover items entre listas.

### 0.2 Documentación del producto pristina

Las epics (`docs/epics/EP0XX-*.md`) describen la funcionalidad del producto,
no el plan de trabajo. **Epic** = qué hace la plataforma (viva). **Issue** =
instrucción técnica puntual. **SPRINT.md** = orden y estado del trabajo.

Si un commit cambia comportamiento, schema o endpoints descritos en una epic,
actualiza la epic **en el mismo bloque**. Schema: además `DB-CHANGES.md`.
Decisión arquitectónica: además `DECISIONS.md`. Redacta la edición con un
sub-agente Haiku (skill `delegar`). Un cambio interno (refactor, typo) no
actualiza nada.

Reglas blandas (no anulan 1 US = 1 commit ni la revisión del owner):

- `status:ready` aprobado → implementar y demostrar, sin re-justificar scope.
- Issue ya implementado en otro branch → cherry-pick + verificar + cerrar.
- AC de más de 1 día → MVP + el resto «diferido (no bloqueante)» en el cierre.
- Tests + typecheck verdes = terminado. Rojo → iterar, sin batchear.
- El comment de cierre demuestra que funciona (TC ejecutados). No es opcional.
- Council de 3 agentes: interno por default; sub-agentes solo si la decisión
  lo amerita (>1 día de ETA o blast radius alto).
- Un batch del owner salta reglas de bloques; 1 issue = 1 commit no se salta.

## 0.3 Verificación, contexto y acciones irreversibles

- **Cómo se verifica**: skill `verificar` (stack, entorno, comandos, gates de
  CI, rutas que no se editan a mano).
- **Terminado (MCA FLU-02)**: lint, typecheck y tests de API con `exit 0`,
  nunca un conteo. Rojo = tuyo. El DoD de `cerrar-item` va después.
- **El contexto permanente tiene techo**; `scripts/check_contexto.py` lo hace
  cumplir en CI. Umbrales y razones en `conformidad.yaml`; no se suben sin
  escribir por qué. Recortar es la respuesta por defecto.
- **La salida del modelo pasa por el conjunto de evaluación** (MCS IA-07/08/09,
  job `evaluacion-ia`). Un fallo que llegó a un usuario entra al conjunto antes
  del fix: `apps/api/evaluacion/README.md`.
- **Amenazas y controles**: `docs/architecture/modelo-amenazas.md`. Ruta sin
  autenticación o destino externo nuevo → primero el modelo, después el código.
- **Lo irreversible se bloquea** (MCA AUT-01): `scripts/guard_irreversible.py`,
  hook `PreToolUse`. Bloquea `--force` sin lease, `--no-verify`, push a `main`,
  `alembic upgrade`/`downgrade`, `DROP`/`TRUNCATE`, `rm -rf`,
  `reset --hard`/`clean -f` y `branch -D`. Pregunta ante `--force-with-lease`,
  `gh issue close` y `commit --amend`. Un `ask` no frena con permisos
  relajados; un `deny` sí. Trinquete: `apps/api/tests/test_mca_aut01_guard.py`.

## 1. Qué se carga siempre, y qué bajo demanda

**Siempre**, en este orden:

1. `docs/project-management/HANDOFF.md` — puente de la sesión anterior.
2. `CLAUDE.md` (este archivo).
3. `docs/project-management/SPRINT.md` — IN-PROGRESS e INBOX.
4. `docs/epics/README.md` — índice de epics.
5. `docs/project-management/LESSONS.md` — patrones aprendidos (§14).

**Bajo demanda**, cuando el trabajo lo pide y no antes:

| Se abre | Cuándo |
|---|---|
| `docs/epics/EP0XX-*.md` | Al tocar ese epic; el índice dice cuál |
| `docs/project-management/SPRINT-BACKLOG.md` | Al planear, no al ejecutar |
| `docs/epics/DECISIONS.md` | Ante duda arquitectónica |
| `docs/epics/DB-CHANGES.md` | Si el cambio toca esquema |
| Skill `verificar` | Al comprobar que algo funciona |
| `docs/architecture/modelo-amenazas.md` | Si se cruza una frontera de confianza |

No se explora fuera de estas listas: el contexto es finito y el CI hace cumplir
el techo (MCA CTX-04; mediciones fechadas en `conformidad.yaml`).

## 2. Numeración de identificadores

| Prefijo | Uso | Contador |
|---|---|---|
| `US-###` | Historia de usuario | Global, auto-incremento |
| `BUG-###` | Bug del owner | Propio, auto-incremento |
| `ENH-###` | Enhancement sobre US | Propio, auto-incremento |
| `EP0XX` | Épica | Manual |
| `DEC-###` | Decisión arquitectónica | `DECISIONS.md` |
| `ADR-###` | Architecture Decision Record | `docs/adr/` |
| `TC-###` | Test case | El epic que lo cubre |

El próximo ID libre **se deriva, no se almacena** (MCA CTX-03):

```bash
git fetch origin main            # siempre contra main actualizado
python scripts/proximo_id.py     # --detalle muestra el máximo por fuente
```

Une GitHub, `git log` y los docs, y toma el máximo. `gh issue list` solo no
basta: hubo batches por chat sin issue. Porqué: docstring del script.

Reglas: un número de US retirada no se reusa. Un ENH no crea US nueva:
actualiza la afectada y queda como lineage (`ENH-003 (afecta US-042)`). Los
commits históricos usan prefijos viejos (`US-NEW-###`, `US-BUG-###`); no se
reescribe historia.

## 3. Ciclo de trabajo

```
Fase A — Planeación / Diseño   →   Fase B — Triage e issues   →
Fase C — Implementación        →   Fase D — Cierre (owner)
```

Fases A y B: skill **`triage`**. Fases C y D: skill **`cerrar-item`**.

Manda siempre:

- **1 US/BUG/ENH = 1 commit** (§7).
- Claude no arranca sin OK del owner: label `status:ready` o chat.
- **Claude nunca cierra un issue.** Lo cierra el owner al verificar.
- El comment de cierre demuestra que funciona (TC + verificación).
- Fix de más de 10 archivos → parar y validar con el owner.
- Schema sin migración clara → parar; `DB-CHANGES.md` + `DECISIONS.md`.

## 4. Convenciones de commit

```
<tipo>(<scope>): <ID> — <desc corta> (refs #<issue>)
```

Tipos: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `wip`.
Scopes comunes: `api`, `web`, `worker`, `org`, `auth`, `dashboard`, `projects`,
`admin`, `superadmin`, `requests`, `branding`, `ai`, `ops`, `infra`, `epics`,
`sprint`, `landing`, `decisions`, `db`, `archive`, `rename`.

Ejemplo: `fix(web): BUG-006 — sidebar muestra items admin a usuarios plain (refs #42)`

Reglas: contexto agotado a mitad → `wip(scope): US-051 — avance parcial` y
anotar en `SPRINT.md` dónde quedó. **No** hacer `--amend` a commits ya
pusheados. **No** usar `--no-verify` para saltar hooks.

## 5. Labels de GitHub

Set de labels y transiciones: skill **`triage`**. Sin `status:ready` (o OK del
owner por chat) no se empieza. La transición `triage → ready` es del owner.

## 6. SPRINT.md

Vive en `docs/project-management/SPRINT.md`. Secciones: IN-PROGRESS ·
INBOX/TRIAGE · Deferred · DONE · Backlog v2.0. El detalle de lo cerrado va a
`SPRINT-DONE-HISTORY.md`. Se actualiza al crear issues y al cerrar bloque,
sprint o sesión — no en cada commit. Techo de líneas: §0.3. Estructura y
cleanup: skill **`handoff`**.

## 7. Regla sagrada: 1 US = 1 commit

Nunca se acumulan cambios de varias US en un commit. Excepciones: docs puros
que mueven varias US en `SPRINT.md` (cerrar bloque) y housekeeping
(`docs(rename)`, `chore(cleanup)`) sin US específica.

## 8. Branch policy

- `main` — productivo. No se pushea directo.
- `claude/<tema>-<sufijo>` — branch de trabajo de Claude. El PR lo abre el
  owner o Claude. La branch activa está en `SPRINT.md` → IN-PROGRESS.
- Branch atrás de `main` (CI rojo por cambios de `main`, colisión de revisiones
  de Alembic): skill **`rebasear`**.

Sesiones secuenciales > paralelas (owner 2026-05-22): 1 sesión = 1 lane =
1 branch; migraciones consecutivas; CI verde + merge antes de la siguiente US.
Paralelizar solo lanes sin migraciones ni schemas compartidos.

## 9. Cuando dudar

- Item que no calza en BUG/ENH/US → **preguntar**.
- Sin bloque activo razonable → **proponer** «Bloque X+1» y esperar.
- Schema sin migración clara → **parar**; `DB-CHANGES.md` + `DECISIONS.md`.
- Fix de más de 10 archivos → **parar** y validar con el owner.

## 10. Memoria y contexto

- No leer archivos completos cuando basta una sección.
- Rename/refactor masivo: `sed` vía Bash antes que `Edit` con `replace_all`.
- Contexto agotado → commit `wip:` y anotar en `SPRINT.md` dónde quedó.
- El techo del contexto permanente: §0.3.
- Delegar trabajo mecánico a sub-agentes: skill **`delegar`**.

## 11. Resumen de ronda

Cada turno cierra con un resumen al owner: qué se hizo, qué archivos cambiaron
y qué acciones externas le quedan («ninguna» si no hay). Plantilla: skill
**`resumen-ronda`**.

## 12. Handoff entre sesiones — `/handoff`

Al abrir: leer `HANDOFF.md` **antes** que `SPRINT.md`; si está vacío o viejo,
pedirlo al owner. Al cerrar: el owner invoca `/handoff` (limpia `SPRINT.md`,
archiva y reescribe `HANDOFF.md`), haya o no commits. Skill **`handoff`**.

## 13. Mentalidad end-to-end

Cada cambio es un slice completo: backend → worker → DB → UX → UI → docs
(owner 2026-05-23). Si no es alcanzable desde la UI, no existe. Checklist y
DoD: skill **`cerrar-item`**.

## 14. Flujo de trabajo

- **Plan mode** para toda tarea no trivial (3+ pasos): plan corto, aprobación,
  ejecución.
- **Sub-agentes solo para research amplio** (explorar, buscar, inventariar).
  Nunca para verificar trabajo propio: la verificación se ejecuta directo.
- **Simplicidad primero**: el cambio más pequeño que resuelve, con impacto
  mínimo sobre lo que ya funciona.
- **Loop de auto-mejora**: tras cualquier corrección del owner, registrar el
  patrón en `docs/project-management/LESSONS.md` (máx. 40 líneas; una lección
  se poda al volverse regla o gate). Se lee al abrir ronda (§1).
