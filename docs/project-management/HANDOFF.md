---
responsable: propietario
estado: vigente
revisado: 2026-08-06
revisar_cada: 30d
---

# HANDOFF.md — Estado para la próxima sesión

**Branch activa:** `claude/remediacion-ola-2-2kg36x` — **rebasada sobre `main`**; #581
mergeó los 13 primeros commits y quedan **4 fuera**, que necesitan PR nuevo
**Generado por:** `/handoff`

---

## 🎯 Dónde estamos parados

**Ola 2 entera más `SEG-04` y el cierre de `DAT-06`: de 41 a 30 bloqueantes de
N1.** Uno por commit, todos con prueba propia y verificación por mutación.

`SEG-04` era la única CRÍTICA viva y el hueco era explotable: la autorización
de objeto se aplicaba al listado y a ningún detalle.

MCA sigue en **N2**, su objetivo. MCS sigue en **N0** — el nivel no se mueve
hasta que caigan los 30, y lo que queda necesita postura del owner.

## 📍 Dónde retomar

**Abrir un PR nuevo con los cuatro commits que quedaron fuera de #581** — entre
ellos `SEG-04`, que es la única CRÍTICA y **todavía no está en `main`**.

Después, añadir las dos verificaciones nuevas a las exigidas de `main` (ver
Cleanup): eso sí va tras el merge, porque GitHub no deja exigir un check que
nunca ha reportado.

Después: **Ola 3**, que el owner dejó para otra sesión. Las tres primeras
—alcance de competencia (`CON-01/03/05`), escenarios de calidad con medida
(`REQ-02`) e inventario de datos personales (`REQ-03`)— desbloquean nueve
requisitos entre ellas, y las tres necesitan una decisión antes de tocar
código.

## ✅ Hecho en esta sesión

Quince commits, uno por requisito. **Cierran** `SEG-05`, `OPS-01`, `DEV-04`,
`CFG-04`, `DIS-01`+`CFG-14`, `DOC-01`, `DOC-03`, `DAT-04`+`DAT-08`, `DAT-12`,
**`SEG-04`** y **`DAT-06`**; `DAT-05` vuelve a cerrar. `LEN-02` baja de 177 a
166 sin cerrar. `git log --oneline origin/main..HEAD` los tiene con su porqué.

## 🔄 PRs abiertos o en flight

**#581 — MERGEADO**, con los 13 primeros commits (hasta `47eb7b8`).

**Quedan cuatro fuera y necesitan PR nuevo.** El merge cayó justo en el handoff
que cerraba la Ola 2, y `SEG-04` y `DAT-06` se hicieron después. Un PR mergeado
no puede seguir rastreando trabajo, así que la rama se **rebasó sobre `main`** y
lleva solo esos cuatro:

| SHA | Qué |
|---|---|
| `32b56b7` | **`SEG-04`** — la única CRÍTICA. **No está en `main`** |
| `18c30f1` | `DAT-06` — `amber_max` → `yellow_max` (ADR-030, migración **0101**) |
| `4671227` | Este puente + el plan |
| `61770ef` | El hook `commit-msg` suponía `python3`; en Windows no existe |

## ⚠️ Gotchas y decisiones recientes

- **Medir contra el texto del requisito destapa lo que la evidencia anotada
  esconde.** Seis hallazgos así: el acta `.docx` se firmaba con la paleta
  anterior a DIS-02; once citas a tokens inexistentes pintaban tema claro en
  modo oscuro; el gate de tipos daba verde sin analizar nada; el worker no
  configuraba su registro; nueve copias del resolvedor de proyecto dejaban
  entrar a proyectos ajenos; y la etiqueta de ajustes decía «Ámbar».
- **`SEG-04` cambió comportamiento:** un usuario `role_type='user'` **sin
  ninguna asignación** deja de alcanzar cualquier proyecto. Es lo que
  `user_scope_assignments` dice desde que se escribió y lo que el listado ya
  hacía; se cerró la puerta de la URL directa.
- **Una migración sobre JSON no se escribe con `sa.text`** y el diccionario ya
  serializado: funciona en SQLite y falla en Postgres. Forma de BUG-039.

## 📋 Lo que sigue

Detalle en `SPRINT.md` → INBOX y en `plan-remediacion.md`.

- **Ola 3** — necesita postura del owner, y el owner la dejó para otra sesión.
  Se le suman tres de la Ola 2 que resultaron no ser mecánicas: `DAT-02` (8
  renombres con migración y ventana, como `wbs`), `DIS-03` y `DAT-11`.
- **`LEN-02`** es el único que cierra sin decisión: 166 mensajes con texto
  suelto, y el mecanismo ya obliga a las tres partes al tocar cada endpoint.
- **Cuatro ventanas de compatibilidad abiertas** (`phase=support`,
  `portfolio_function`, `wbs`, `amber_max`). Se cierran con dato: a los dos
  meses se mira `compat.nombre_viejo`.

## 📚 Estado de las epics docs

| Epic | Sincronizada | Notas |
|---|---|---|
| EP004 | sí | US-020: el hueco se ve distinto del cero (DAT-12) |
| EP014 · EP020 | sin cambios | no describen el vocabulario del semáforo; lo hace el glosario, ya al día |

`ADR-030` y `DB-CHANGES.md` (0101) al día. El modelo de amenazas suma **AM-15**
—acceso a un proyecto ajeno dentro del mismo inquilino—, hermana de AM-02.

Al día también: glosario (`amber` a 0 restos), `plan-remediacion.md`,
`design-system/tokens.md` (declarado **reemplazado**, con aviso en el cuerpo),
`database.md` y el nuevo `er-generado.md`.

## 🧹 Acciones del owner

- [ ] **Añadir `tipos-python` y `commits` a las verificaciones exigidas de
      `main`.** Sin eso, los gates existen y no bloquean.
- [ ] **Activar el hook local**: `git config core.hooksPath .githooks`.
- [ ] **Correr las migraciones `0097`-`0101`.** Las cuatro primeras venían de
      antes; la `0101` renombra una llave dentro de `tenants.settings`.
- [ ] **Confirmar Sentry en Railway:** dos líneas, `proceso=api` y
      `proceso=worker`. Con las dos, `OPS-02` cierra.
- [ ] Smoke de la web: tablero (KPI sin dato → «—»), detalle de proyecto, la
      página de documentos en **tema oscuro** (llevaba meses mal) y los
      umbrales de carga en ajustes («Amarillo hasta», antes «Ámbar»).
- [ ] Contrastar los umbrales de D-4 contra cartera real.

## 🔮 Para sesiones futuras (sin issue todavía)

- **`DOC-07`** — tres documentos con la revisión vencida; el gate solo informa.
  Hacerlo fallar exige decidir qué pasa con lo que nadie va a revisar.
- **`DAT-07`** — tipos propios de magnitud. Hoy nada impide pasar un porcentaje
  donde se espera una fracción.
- Línea base (D-6) y DCMA 14-point: épica propia.
- El owner tiene cambios de diseño de producto pendientes.

---

## Cómo retomar

1. Lee este `HANDOFF.md` primero.
2. Luego `CLAUDE.md` + `SPRINT.md` + `docs/conformidad/plan-remediacion.md`.
3. `python scripts/registro_conformidad.py` da el estado real.
