---
responsable: propietario
estado: vigente
revisado: 2026-08-06
revisar_cada: 30d
---

# HANDOFF.md — Estado para la próxima sesión

**Branch activa:** `claude/remediacion-ola-2-2kg36x` — 12 commits, sin PR todavía
**Generado por:** `/handoff`

---

## 🎯 Dónde estamos parados

**La Ola 2 está ejecutada: de 41 a 32 bloqueantes de N1.** Once requisitos
cerrados y dos que bajan de cifra sin cerrar, uno por commit, todos con prueba
propia y verificación por mutación.

MCA sigue en **N2**, su objetivo. MCS sigue en **N0** — el nivel no se mueve
hasta que caigan los 32, y los que quedan **no son mecánicos**.

## 📍 Dónde retomar

**Abrir el PR y esperar CI.** Dos verificaciones nuevas necesitan que el owner
las añada a las exigidas de `main` (ver Cleanup).

Después: la Ola 3 **necesita postura del owner antes de tocar código**. Las
preguntas están al final del resumen de la sesión; las tres primeras —alcance
de competencia, escenarios de calidad, inventario de datos personales—
desbloquean nueve requisitos entre ellas.

## ✅ Hecho en esta sesión

| SHA | Requisito | Qué |
|---|---|---|
| `9e21f61` | `SEG-05` | `SECURITY.md`: canal privado, plazos, alcance, puerto seguro |
| `3fb5835` | `OPS-01` | structlog formatea el `logging` estándar → JSON a `stdout`, los dos procesos |
| `b876e79` | `DEV-04` | `mypy --strict` en CI con línea base de 1.163 que solo encoge |
| `0c7b329` | `CFG-04` | job `commits` sobre el rango del PR + hook en `.githooks/` |
| `528209f` | `DIS-01`·`CFG-14` | cero literales de color y espaciado; el token citado tiene que existir |
| `b1fcc15` | `DAT-06` | 0 restos de `amber` en código (PARCIAL: queda `amber_max`) |
| `b2febff` | `DAT-05` | quinta paleta de salud, en el acta que se firma |
| `25e7a81` | `DOC-01` | 127 documentos con encabezado |
| `5f0fe1a` | `DOC-03` | el ER se genera de `Base.metadata` |
| `65494af` | `DAT-04`·`DAT-08` | 26 conversiones a `core/unidades.py` |
| `d657b1b` | `LEN-02` | `errors.mensaje()` hace estructural el requisito; 177→169 |
| `058dfef` | `DAT-12` | 17 sitios de presentación distinguen el hueco del cero |

## 🔄 PRs abiertos o en flight

Ninguno. La branch está pusheada y **sin PR: una branch sin PR no tiene CI**.

## ⚠️ Gotchas y decisiones recientes

- **Medir contra el texto del requisito destapa lo que la evidencia anotada
  esconde.** Cuatro hallazgos así: el acta `.docx` se firmaba con la paleta
  anterior a DIS-02; once citas a tokens inexistentes hacían que la página de
  documentos pintara tema claro en modo oscuro y la tabla de permisos saliera
  sin fondo; el gate de tipos daba verde sin analizar nada; el worker no
  configuraba su registro y Celery se lo llevaba por delante.
- **Un control que da verde cuando no corre es peor que no tenerlo.** Sustituye
  una ausencia visible por una garantía falsa. Pasó con `check_tipos.py`: sin
  mypy instalado el proceso devuelve 1, igual que «encontré errores».
- **Una lista escrita a mano no puede probar «uno solo».** Prueba «uno solo
  entre los que me acordé de listar». Los trinquetes nuevos **derivan** del
  árbol y lo que se declara son las excepciones, con razón escrita.
- **La mutación cazó cuatro pruebas que no podían fallar**, y ninguna se veía
  leyendo el código: una derivaba su caso de la constante que vigilaba, otra
  comprobaba `set(X) <= rutas` con `X` vacío, otra buscaba dos cadenas por
  separado en vez de una dentro de la otra.
- **El trinquete de contexto disparó al actualizar `SPRINT.md`**, y se recortó
  en vez de subir el techo — que es la regla.

## 📋 Lo que sigue

Detalle en `SPRINT.md` → INBOX y en `plan-remediacion.md`.

- **Ola 3** — necesita postura del owner. Se le suman tres de la Ola 2 que
  resultaron no ser mecánicas: `DAT-02` (8 renombres con migración y ventana,
  como `wbs`), `DIS-03` y `DAT-11` (épica de producto).
- **`SEG-04`** aparte: CRÍTICA, autorización sobre el objeto.
- **`DAT-06` y `LEN-02`** cierran sin decisión: el primero con la ventana de
  `amber_max`, el segundo escribiendo las tres partes al tocar cada endpoint.

## 📚 Estado de las epics docs

| Epic | Sincronizada | Notas |
|---|---|---|
| EP004 | sí | US-020: el hueco se ve distinto del cero (DAT-12) |
| EP014 · EP020 | sin cambios | no describen el vocabulario del semáforo; lo hace el glosario, ya al día |

Al día también: glosario (`amber` a 0 restos), `plan-remediacion.md`,
`design-system/tokens.md` (declarado **reemplazado**, con aviso en el cuerpo),
`database.md` y el nuevo `er-generado.md`.

## 🧹 Acciones del owner

- [ ] **Añadir `tipos-python` y `commits` a las verificaciones exigidas de
      `main`.** Sin eso, los gates existen y no bloquean.
- [ ] **Activar el hook local**: `git config core.hooksPath .githooks`.
- [ ] **Correr las migraciones `0097`-`0100`.** Sigue pendiente de antes.
- [ ] **Confirmar Sentry en Railway:** dos líneas, `proceso=api` y
      `proceso=worker`. Con las dos, `OPS-02` cierra.
- [ ] Smoke de la web: tablero (KPI sin dato → «—»), detalle de proyecto, y la
      página de documentos en **tema oscuro** (llevaba meses mal).
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
