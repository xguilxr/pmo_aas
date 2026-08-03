---
name: handoff
description: Genera/actualiza docs/project-management/HANDOFF.md con el estado de la sesión actual (dónde quedamos, qué sigue, contexto para la próxima sesión), y de paso limpia SPRINT.md archivando lo completado a SPRINT-DONE-HISTORY.md. Úsalo al cierre de cualquier sesión donde quieras dejar un puente claro para retomar después.
---

# /handoff — Cierre de sesión + bridge para la próxima

Cuando el usuario invoca `/handoff`, ejecuta en orden las siguientes
acciones. Si algún paso no aplica (ej. no hubo cambios), anótalo y
sigue al siguiente. Todo el trabajo debe terminar con un commit + push
sobre la branch activa.

---

## Paso 1 — Recopila el contexto de la sesión

Antes de escribir nada, junta esta información:

- **Branch activa** (`git branch --show-current`).
- **Commits de la sesión** (`git log --oneline origin/main..HEAD` o
  equivalente para la branch activa).
- **Estado de PRs abiertos** que se tocaron en la sesión (numero,
  título, CI status). Usa `mcp__github__list_pull_requests` o
  `mcp__github__pull_request_read` cuando aplique.
- **SPRINT.md actual** — qué quedó en IN-PROGRESS, qué pasó a DONE,
  qué nuevos items entraron a INBOX.
- **Decisiones / pivotes** importantes que el owner tomó esta sesión.
- **Errores o gotchas** detectados (CI rojo, dependencias rotas,
  collisions de migraciones, etc.).

## Paso 1.5 — Verificar epic docs pendientes de actualización (§0.2)

Antes del cleanup, repasa los commits de la sesión y pregúntate:
- ¿Algún commit cambió comportamiento descrito en `docs/epics/EP0XX-*.md`?
- ¿Algún schema, endpoint o flow cambió y la epic todavía describe el
  comportamiento viejo?

Si SÍ → **delega a sub-agente Haiku** para actualizar el epic doc antes
de cerrar la sesión (ver CLAUDE.md §10 patrón). El HANDOFF.md final
debe poder afirmar que no quedan epics desactualizadas.

Si NO aplica → continúa al paso 2.

## Paso 2 — Limpieza obligatoria de SPRINT.md

### Estructura esperada del archivo

`docs/project-management/SPRINT.md`:

```
🔴 IN-PROGRESS    (la US/bloque que Claude está tocando ahora,
                   o "Sin US activa" + próximo paso accionable)
📥 INBOX / TRIAGE (issues recién creados + sprints planeados con
                   sus bloques en orden de ejecución)
⏸️ Deferred       (issues sin asignación de versión, esperan decisión)
✅ DONE           (tabla resumen — detalle en SPRINT-DONE-HISTORY.md)
📋 Backlog v2.0
```

**Separación de histórico:** `SPRINT.md` lleva solo el sprint actual + INBOX +
Deferred + backlog v2.0. `SPRINT-DONE-HISTORY.md` lleva el detalle de los
bloques cerrados.

**Flujo de un item:** al crear issue → INBOX · al arrancar implementación →
IN-PROGRESS · al cerrar bloque → DONE (tabla resumen), con el detalle a
SPRINT-DONE-HISTORY.md.

### Cuándo se actualiza SPRINT.md (decisión owner 2026-05-22)

| Evento | ¿Actualizar? |
|---|---|
| Cada commit individual | NO (sobrecarga) |
| Al crear ≥ 1 issue nuevo | SÍ (entra a INBOX) |
| Al cerrar BLOQUE completo | SÍ (items pasan a DONE) |
| Al cerrar SPRINT | SÍ + cleanup obligatorio |
| Al cerrar SESIÓN (`/handoff`) | SÍ siempre — lo hace esta skill |

> Cuanto más actualizado, mejor para que otra sesión lo retome sin sorpresas,
> pero **no a costa de detenerse en cada commit**. El equilibrio: actualizar en
> segmentos grandes (bloque, sprint, sesión).

### Cleanup al cierre de sprint

Cuando un sprint termina y el owner confirma el cierre, antes de arrancar el
siguiente:

1. **Mover** las secciones `🗂️ Sprint N (vX.Y) — CERRADO` y el contexto
   IN-PROGRESS narrativo a `SPRINT-DONE-HISTORY.md`, preservando bloques, SHAs,
   migraciones y diferidos.
2. **Reemplazar** la sección DONE por una tabla resumen
   `Sprint | Versión | Cerrado | Items`, una fila por sprint.
3. **Limpiar** IN-PROGRESS para que apunte solo al sprint activo.
4. **Truncar** «Notas y cambios» a las entradas del sprint actual + la del cierre.
5. **Commit** `docs(sprint): cierre Sprint N — archiva a SPRINT-DONE-HISTORY.md`.

### Antes de redactar el handoff

1. Mueve a `docs/project-management/SPRINT-DONE-HISTORY.md` cualquier
   sprint / bloque completado que aún viva en `SPRINT.md`. Preserva
   commits SHA, migraciones agregadas y diferidos.
2. La sección DONE de `SPRINT.md` queda como **tabla resumen**
   (`Sprint | Versión | Cerrado | Items`), no como listado largo.
3. La sección `IN-PROGRESS` debe apuntar **solo** a la US/bloque
   activa (o "Sin US activa" si recién arranca).
4. La sección `Notas y cambios recientes` se trunca a las entradas
   del sprint actual + la entrada del cierre. Lo viejo migra al
   archivo histórico.
5. **Objetivo:** `SPRINT.md` nunca pasa de ~250 líneas. Si crece más,
   sigue limpiando.

## Paso 3 — Genera / actualiza `docs/project-management/HANDOFF.md`

Sobreescribe el archivo con esta estructura (en español, conciso):

```markdown
# HANDOFF.md — Estado para la próxima sesión

**Última actualización:** YYYY-MM-DD HH:MM
**Branch activa:** `claude/...`
**Generado por:** /handoff

---

## 🎯 Dónde estamos parados

<2-4 oraciones que resumen el estado del proyecto AHORA. Foco en
qué está corriendo en CI, qué está mergeado a main, qué queda
abierto y bloqueando.>

## 📍 Dónde retomar (próximo paso accionable)

<Bullet único o muy corto con la primera acción concreta que
debería tomar la próxima sesión. Ej. "Verificar CI verde de PR
#408 y mergear", "Arrancar US-123 sobre branch nueva", etc.>

## ✅ Hecho en esta sesión

- <bullet 1: cambio + commit SHA + branch>
- <bullet 2: cambio + commit SHA + branch>
- ...

Si la sesión cerró sprints, lista cuáles e indica que ya están
archivados en SPRINT-DONE-HISTORY.md.

## 🔄 PRs abiertos o en flight

| # | Branch | Estado CI | Acción pendiente |
|---|---|---|---|
| #XXX | claude/... | green / failing / pending | merge / fix / wait |

## ⚠️ Gotchas y decisiones recientes

- <gotcha 1: ej. "alembic puede colisionar revision IDs si dos lanes
  paralelos tocan migraciones; lección: secuencial puro">
- <decisión 1: ej. "snapshots históricos fuera de scope v1.0">

## 📋 Lo que sigue (resumen ejecutivo del backlog activo)

Referenciar la sección INBOX de SPRINT.md sin duplicar. 3-5 bullets
máximo. Detalle completo en SPRINT.md.

- Sprint N Bloque M: <items + foco>
- Sprint N+1: <items + foco>
- ...

## 📚 Estado de las epics docs

Lista de epics que la sesión tocó (commits con cambios funcionales) y
si están sincronizadas con el código:

| Epic | Sincronizada | Notas |
|---|---|---|
| EP0XX | sí / pendiente | <razón si pendiente> |

Si alguna queda pendiente, anotarlo como acción para la próxima
sesión.

## 🧹 Cleanup técnico pendiente

Items que el owner debería hacer fuera de Claude (UI de GitHub,
panel de Railway, decisiones de negocio, etc.). Marcar con `- [ ]`
para que sirvan de checklist.

- [ ] <acción 1>
- [ ] <acción 2>

## 🔮 Para sesiones futuras (sin issue todavía)

Items que el owner mencionó tangencialmente y vale la pena no
perder. No son INBOX porque no tienen issue creado.

- <idea 1: ej. "sesión de revisión completa de diseño y navegación
  cuando termine EP020">
- ...

---

## Cómo retomar

Para la próxima sesión:

1. Lee este `HANDOFF.md` primero.
2. Luego `CLAUDE.md` + `docs/project-management/SPRINT.md` + el
   epic en flight referenciado.
3. Continúa desde el "próximo paso accionable" arriba.
```

## Paso 4 — Commit + push

Un solo commit con header:

```
docs(handoff): <YYYY-MM-DD> — <resumen 1 línea de la sesión>
```

Body breve con bullets de lo que cambió en SPRINT.md / SPRINT-DONE-HISTORY.md / HANDOFF.md.

Push a la branch activa (no a main directamente).

## Paso 5 — Resumen al owner

Termina con el resumen estándar de CLAUDE.md sección 11. Bullets:

- Hecho: actualicé HANDOFF.md + limpié SPRINT.md (de X a Y líneas) +
  archivé sprints cerrados.
- Próximo paso accionable: <copia el bullet "dónde retomar">.
- PRs en flight (si los hay): tabla compacta.
- Acciones externas para el owner: solo las nuevas; las que ya
  estaban antes apuntar a HANDOFF.md.

---

## Reglas duras

- **No inventes** lo que se hizo en la sesión. Si no estás seguro,
  consulta `git log`, `gh pr view`, o pregunta al owner antes de
  escribir.
- **No dejes** SPRINT.md sin limpiar. Aunque el handoff parezca
  rápido, el cleanup es obligatorio.
- **No crees PR** ni mergeas; solo commit + push de la branch
  activa.
- **No borres** HANDOFF.md previo — sobreescribe completo. Cada
  sesión deja su versión propia.
- Si la sesión NO produjo commits ni cambios, igual genera HANDOFF.md
  con un breve "sesión de discusión/planeación, sin código" y deja
  registrado el plan que se discutió.
