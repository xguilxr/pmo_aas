# HANDOFF.md — Estado para la próxima sesión

**Última actualización:** 2026-08-03
**Branch activa:** ninguna — árbol local sobre `main`, **sin commitear**
**Generado por:** sesión de auditoría de conformidad MCA

---

## 🎯 Dónde estamos parados

Sesión **de entorno, no de producto**: auditoría contra los marcos MCA/MCC/MCS.
No se tocó funcionalidad; sí se corrigió un defecto de tests que destapó.

**MCA salió N0.** Sin presupuesto de contexto declarado, `MCA-P02` Etapa 1
ordena N0 «sin más análisis». Por eso **MCS no se auditó**. MCC no aplica
(producto propio) y está bien declarado.

Ejecutadas las **acciones 1-5** del plan (`docs/conformidad/plan.md`). Queda
**una no conformidad abierta**: `CTX-02`, y solo porque el presupuesto de
40.000 caracteres lo propuso la auditoría y necesita decisión del owner.

## 📍 Dónde retomar

**Decidir `permanente_max_chars` en `conformidad.yaml`** (hoy 40.000). Cierra
CTX-02 y el repo pasa de N0 a nivel medible. Después: acción 6 (mover
procedimientos de `CLAUDE.md` a skills), que es la que más contexto libera.

## ✅ Hecho en esta sesión

Sin commits: todo en el árbol de trabajo.

- Auditoría en `docs/conformidad/` (informe MCA + plan consolidado).
- `conformidad.yaml` en la raíz (renombrado desde `pmoaasconformidad.yaml`, que
  el procedimiento no encontraba): presupuesto, límites y conformidades.
- **`CLAUDE.md` §0.3**: stack, preparación del entorno, cinco comandos de
  verificación **ejecutados** con su salida real, y rutas protegidas.
- **Defecto de tests corregido** (`apps/api/tests/conftest.py`): el stub de
  renderers parcheaba `render_pdf` en 3 módulos escritos a mano cuando los
  importan 6, y `html_to_pdf` no se stubeaba. 4 tests ejercían WeasyPrint real
  y fallaban sin GTK/Pango. Ahora barre `sys.modules`. La suite pasó de rojo a
  **exit 0**; las cifras fechadas están en `conformidad.yaml` → `mediciones`.
  Cobertura preservada: 2 casos heavy nuevos para `html_to_pdf`.
- **`scripts/check_contexto.py`** + job `contexto-permanente` en CI. Probado en
  ambos sentidos.
- **`SPRINT.md` de 521 a 219 líneas**; lo cerrado se archivó íntegro en
  `SPRINT-DONE-HISTORY.md`.
- **Diagnóstico de dominio PMO** en `docs/dominio/`.

**Contexto permanente: de 87.623 a ~68.000 caracteres.**

## 🔄 PRs en flight (sin cambios)

| PR / branch | Acción pendiente |
|---|---|
| #570 · `claude/pmo-portfolio-architecture-6hbuen` | verificar + mergear · `alembic upgrade head` (0091-0094) |
| `claude/plan-import-wbs-fixes-nwotng` | verificación owner + PR · migs 0095-0096 |
| `claude/gantt-areas-fixes` | owner crea PR (ENH-149/BUG-075/ENH-154/ENH-152) |

## ⚠️ Gotchas

- **Los techos del CI son un trinquete, no el objetivo.** Están en el valor
  actual + 1 %: fallan si el contexto **crece**. Cada vez que una acción lo
  baje, **hay que bajar el techo detrás** — si no, es un número decorativo.
  Ver `historial` en `conformidad.yaml`.
- **Python 3.12 no es negociable**: `psycopg[binary]==3.2.3` no tiene wheel
  para 3.13+. `uv venv --python 3.12`.
- **Las cifras de contexto son caracteres, no bytes.** Manda el script.
- Los 2 tests heavy nuevos no corrieron localmente (exigen GTK/Pango); corren
  en `api-tests-heavy`.

## 📋 Lo que sigue

- **Producto:** ENH-202 (Helvetica en exports) es el siguiente batch. US-168
  sigue `in-progress`.
- **Entorno:** acciones 6-9 del plan.
- **Dominio:** revisar `docs/dominio/02-GLOSARIO.md` término por término. El
  plan de remediación no se escribe hasta que esté aprobado.

## 📚 Epics

La sesión no cambió comportamiento de producto: `CLAUDE.md` §0.2 no aplica.

## 🧹 Acciones del owner

- [ ] **Decidir `permanente_max_chars`** (cierra CTX-02).
- [ ] Decidir cómo commitear el árbol: `main` es productiva, va en branch.
- [ ] Verificar + mergear PR #570 · `alembic upgrade head` (0091-0094).
- [ ] Crear PR de `claude/plan-import-wbs-fixes-nwotng` (migs 0095-0096).
- [ ] Crear PR de `claude/gantt-areas-fixes`.
- [ ] Revisar `docs/dominio/02-GLOSARIO.md`.

## 🔮 Sin issue todavía

- **Calidad de cronograma DCMA 14-point.** El importador de MS Project ya deja
  `predecessors`, `successors`, `is_critical` y `outline_level`: es el insumo
  exacto. No exige costos ni línea base. Ver `docs/dominio/01-DIAGNOSTICO.md` §4.
- **Línea base.** Brecha keystone: sin ella no existe «desviación» ni EVM.
- Import CSV del pool de recursos; persistir desglose de salud en tendencias.

---

## Cómo retomar

1. Este archivo primero.
2. Luego `CLAUDE.md` (§0.3 = comandos de verificación) + `SPRINT.md` + el epic
   en flight.
3. Continúa desde "Dónde retomar".
