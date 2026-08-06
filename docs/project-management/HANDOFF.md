---
tipo: gestion
responsable: propietario
estado: vigente
revisado: 2026-08-06
revisar_cada: 30d
---

# HANDOFF.md — Estado para la próxima sesión

**Branch activa:** `claude/remediacion-ola-2-2kg36x`, rebasada sobre `main` · **PR #582 abierto**
**Generado por:** `/handoff`

---

## 🎯 Dónde estamos parados

**Ola 2 entera, más `SEG-04`, `DAT-06` y `DOC-02`: de 41 a 29 bloqueantes de
N1.** Uno por commit, todos con prueba propia y verificación por mutación.

`SEG-04` era la única CRÍTICA viva y el hueco era explotable: la autorización
de objeto se aplicaba al listado y a ningún detalle.

MCA sigue en **N2**, su objetivo. MCS sigue en **N0**: MCS-CORE §6.2 no da
crédito parcial —un solo PARCIAL bloquea el nivel—, así que el número no se
mueve hasta que caigan los 29. Orden de ataque en
[`runbook-cierre-n1.md`](../conformidad/runbook-cierre-n1.md).

## 📍 Dónde retomar

**Mergear #582.** Lleva `SEG-04` —la única CRÍTICA— y `DAT-06`, y ninguno de los
dos está en `main`.

Su CI **no reportó**, y no es el código: GitHub Actions tuvo una caída y cuatro
de los cinco trabajos murieron en «Set up job» con 0 ms facturables. Los cuatro
se corrieron a mano el 2026-08-06 y están en verde. Aun así, al mergear conviene
dejar que el CI corra de verdad: **la verificación local no sustituye al
trinquete**, lo suple mientras está caído.

Después, el **runbook** manda: fases, qué necesita postura tuya y qué es solo
trabajo.

## ✅ Hecho en esta sesión

Quince commits, uno por requisito. **Cierran** `SEG-05`, `OPS-01`, `DEV-04`,
`CFG-04`, `DIS-01`+`CFG-14`, `DOC-01`, `DOC-03`, `DAT-04`+`DAT-08`, `DAT-12`,
**`SEG-04`** y **`DAT-06`**; `DAT-05` vuelve a cerrar. `LEN-02` baja de 177 a
166 sin cerrar. `git log --oneline origin/main..HEAD` los tiene con su porqué.

**Verificación local de los cuatro trabajos caídos: todo verde** — suite 1377,
build de web, bandit, pip-audit, pnpm audit, gitleaks sobre 478 commits, y la
0101 contra Postgres real. Salieron **dos correcciones que el CI no habría
dado**, las dos en el aparato de verificación y ninguna en el producto (Gotchas).
Informe:
[`2026-08-06-verificacion-local.md`](../conformidad/2026-08-06-verificacion-local.md).

## 🔄 PRs

**#581 — MERGEADO** (13 commits, hasta `47eb7b8`). **#582 — ABIERTO** con el
resto: `SEG-04` (`32b56b7`), `DAT-06` (`18c30f1`), la portabilidad del hook
`commit-msg` (`61770ef`), los puentes y —nuevo— la suite de la 0101 contra
Postgres más la limpieza del expediente. El merge de #581 cayó a mitad de la
ronda; un PR mergeado no rastrea trabajo nuevo, así que la rama se rebasó.

## ⚠️ Gotchas y decisiones recientes

- **Medir contra el texto del requisito destapa lo que la evidencia anotada
  esconde.** Seis hallazgos así: el acta `.docx` se firmaba con la paleta
  anterior a DIS-02; once citas a tokens inexistentes pintaban tema claro en
  modo oscuro; el gate de tipos daba verde sin analizar nada; el worker no
  configuraba su registro; nueve copias del resolvedor de proyecto dejaban
  entrar a proyectos ajenos; y la etiqueta de ajustes decía «Ámbar».
- **Un trabajo verde sobre un sujeto vacío es un trabajo verde sobre nada.**
  `api-migrations-postgres` corre sobre base limpia y ninguna migración inserta
  inquilinos: el bucle de la 0101 recorría cero filas, así que habría pasado con
  la migración rota. Remediado con `test_dat06_migracion_0101.py`.
- **Corrección: `sa.text` sobre JSON *no* falla en Postgres.** El puente anterior
  afirmaba lo contrario. Se mutó la 0101 de vuelta a esa versión y **pasó**: el
  parámetro viaja como `unknown` y Postgres lo convierte. La tabla tipada se
  queda por ser lo correcto, no por aquel motivo.
- **`SEG-04` cambió comportamiento:** un usuario `role_type='user'` **sin
  ninguna asignación** deja de alcanzar cualquier proyecto. Es lo que
  `user_scope_assignments` dice desde que se escribió y lo que el listado ya
  hacía; se cerró la puerta de la URL directa.

## 📋 Lo que sigue

Detalle en `SPRINT.md` → INBOX y en `plan-remediacion.md`.

- **Ola 3** — necesita postura del owner. Se le suman `DAT-02` (8 renombres,
  ADR + migración por campo), `DIS-03` y `DAT-11`.
- **`LEN-02`**: 166 mensajes con texto suelto; el mecanismo ya obliga a las
  tres partes al tocar cada endpoint.
- **Cuatro ventanas de compatibilidad abiertas** (`phase=support`,
  `portfolio_function`, `wbs`, `amber_max`). Se cierran con dato a los dos meses.

## 📚 Estado de las docs

**EP004** sincronizada (US-020: el hueco se ve distinto del cero). **EP014** y
**EP020** sin cambios: no describen el vocabulario del semáforo, lo hace el
glosario.

`ADR-030` y `DB-CHANGES.md` (0101) al día. El modelo de amenazas suma **AM-15**
—acceso a un proyecto ajeno dentro del mismo inquilino—, hermana de AM-02. Al
día también: glosario, `design-system/tokens.md` (declarado **reemplazado**),
`database.md` y el nuevo `er-generado.md`.

**Expediente de conformidad limpiado.** `plan-remediacion.md` se declaraba
`historico`/`nunca` siendo el plan **activo**; ahora es `vigente` y trae las
cifras de hoy. `docs/conformidad/` estrena
[`README.md`](../conformidad/README.md) — eran trece documentos sin forma de
saber cuál estaba vivo. Los informes fechados **no se tocaron**: son el
expediente, y el índice explica por qué no se editan.

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

- **`DOC-07`** — el gate solo informa, y hoy hay **cero vencidos**: los tres que
  había eran registro marcado como vigente, ya corregidos a `historico`. Hacerlo
  fallar ya no arrastra pasivo.
- **`DAT-07`** — tipos propios de magnitud. Hoy nada impide pasar un porcentaje
  donde se espera una fracción.
- Línea base (D-6) y DCMA: épica propia. El owner tiene además cambios de
  diseño de producto pendientes.

---

## Cómo retomar

1. Lee este `HANDOFF.md` primero.
2. Luego `CLAUDE.md` + `SPRINT.md` + `docs/conformidad/plan-remediacion.md`.
3. `python scripts/registro_conformidad.py` da el estado real.
