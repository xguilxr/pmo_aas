# HANDOFF.md — Estado para la próxima sesión

**Última actualización:** 2026-08-03
**Branch activa:** `claude/auditoria-conformidad-mca-mcs` · **PR #573** (abierto, CI verde)
**Generado por:** `/handoff` — sesión de auditoría de conformidad

---

## 🎯 Dónde estamos parados

Sesión **de conformidad, no de producto**. Se auditó el repositorio contra MCA
(entorno agéntico) y MCS (calidad de software), y se ejecutó la primera tanda de
remediación. PR #573 con 18 commits, los ocho jobs de CI en verde.

| Marco | Objetivo | Alcanzado | Evaluados |
|---|---|---|---|
| MCA | N2 | **N0** | 11/11 · 10 conformes |
| MCS | N2 | **N0** | 126/126 · 9 conformes |

**MCA está a un requisito de N2** y ese requisito no necesita código: solo que
alguien verifique el guard desde una sesión abierta dentro del repo.

**MCS no alcanza N1**: 43 requisitos lo bloquean. El producto está
funcionalmente maduro y estructuralmente desprotegido — la calidad vive en el
código y en la cabeza del owner, no en controles que sobrevivan a un mal día.

## 📍 Dónde retomar

**Lo más barato y de mayor impacto son dos acciones del owner**, no de Claude:

1. Abrir Claude Code con el repo como directorio de trabajo y comprobar que el
   guard intercepta (`echo "prueba: git push --force"`). Cierra AUT-01 y MCA
   llega a **N2**.
2. Proteger `main` — hoy cualquiera escribe directo en productiva.

Después, **B3** (conjunto de evaluación de IA, dependía de B2) y **B5** (modelo
de amenazas, dependía de B1). Las dos están desbloqueadas.

## ✅ Hecho en esta sesión

Todo en PR #573. Detalle por requisito en `docs/conformidad/plan.md`.

**Entorno (MCA)** — contexto permanente de 87.623 a ~51.000 caracteres
(**−43 %**): `SPRINT.md` de 521 a 227 líneas, procedimientos de `CLAUDE.md` a
`.claude/skills/`, contador de IDs derivado en vez de almacenado. Tres controles
nuevos en CI y comandos de verificación declarados **y ejecutados**.

**Producto (MCS)** — Tanda A cerró tres de las cuatro críticas. Los escáneres,
su primer día: vulnerabilidad real de XML en el importador (archivo del usuario
a un parser sin defensa), 10 de 23 CVE de Python cerradas (6 de subida, 2 de
JWT), la crítica de Next.js, y la IA que calculaba cifras para informes
ejecutivos con `float()` en ruta monetaria.

**B1** — aislamiento entre inquilinos **verificado por mutación**: quitar un
filtro `tenant_id` la hace fallar en lectura, modificación y borrado.

**B2** — el contenido de terceros ya no llega al modelo como instrucción. El
informe nombraba las minutas; los puntos de entrada eran **diez**. Los dos que
faltaban pesan más: la memoria del proyecto (un resumen envenenado se antepone
a *toda* generación futura) y el importador de planes (decide el mapeo de
columnas). Verificada por mutación en tres puntos.

También se corrigió el stub de renderers del `conftest`, que cubría 3 de 6
módulos y hacía fallar 4 tests sin GTK/Pango.

## 🔄 PRs en flight

| PR / branch | Acción pendiente |
|---|---|
| **#573** · `claude/auditoria-conformidad-mca-mcs` | Revisar y mergear. **CI verde** |
| #570 · `claude/pmo-portfolio-architecture-6hbuen` | Verificar + mergear · `alembic upgrade head` (0091-0094) |
| `claude/plan-import-wbs-fixes-nwotng` | Falta abrir PR · migs 0095-0096 |
| `claude/gantt-areas-fixes` | Falta abrir PR (ENH-149/BUG-075/ENH-154/ENH-152) |

## ⚠️ Gotchas

- **`main` no está protegida.** Verificado contra la API de GitHub. La regla de
  `CLAUDE.md` §8 existe solo en prosa.
- **Tres gates nuevos en CI** funcionan como **trinquete**: fallan ante
  crecimiento nuevo, no por el pasivo heredado, que está documentado con fecha.
  Frenaron seis intentos de engordar el contexto en esta misma sesión.
- **No hay tests de frontend.** El salto de Next 15.0 a 15.5 lo respaldan solo
  typecheck y build. Un smoke manual antes de mergear sería prudente.
- **Python 3.12 no es negociable**: `psycopg[binary]` no tiene wheel para 3.13+.
- Los requisitos que tocó la Tanda A **siguen figurando como NO CONFORME**:
  arreglarlos no es medirlos, y eso exige reauditar.

## 📋 Lo que sigue

- **Tanda B:** B3 (3-4 d, ya desbloqueada) → B5 (2 d). B1, B2 y B4 hechas.
- **Producto:** ENH-202 (Helvetica en exports) es el siguiente batch. US-168
  sigue `in-progress`.

## 📚 Epics

EP008 actualizada (el modelo ya no calcula cifras, y hay tope de coste). El
resto no cambió de comportamiento: la sesión fue de entorno y seguridad.

## 🧹 Acciones del owner

- [ ] Verificar el guard desde una sesión dentro del repo (cierra AUT-01 → N2).
- [ ] Proteger `main` tras cerrar los PR abiertos.
- [ ] Revisar y mergear **PR #573**.
- [ ] Fijar `permanente_max_chars` en `conformidad.yaml`.
- [ ] Revisar `docs/dominio/02-GLOSARIO.md` término por término.
- [ ] Smoke manual de la web tras el salto de Next 15.0 → 15.5.
- [ ] `SENTRY_DSN` en Railway para encender la captura de errores.
- [ ] Los tres PR pendientes de las ramas anteriores.

## 🔮 Sin issue todavía

- **Calidad de cronograma DCMA 14-point.** El importador ya deja el insumo
  exacto y no exige costos. Ver `docs/dominio/01-DIAGNOSTICO.md` §4.
- **Línea base.** Brecha keystone: sin ella no existe «desviación».
- **Migrar de `python-jose` a PyJWT** — cerraría 5 CVE bloqueadas hoy por su
  restricción `pyasn1<0.5.0`.
- **Re-medir INT-04**: `api-tests-smoke` tarda 3 m en el runner, no los 13 de
  una máquina local. El requisito puede estar más cerca de conforme de lo que
  estimó el informe.

---

## Cómo retomar

1. Este archivo primero.
2. Luego `CLAUDE.md` (§0.3 = comandos de verificación) + `SPRINT.md` + el epic
   en flight.
3. Continúa desde "Dónde retomar".
