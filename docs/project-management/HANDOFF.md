# HANDOFF.md — Estado para la próxima sesión

**Última actualización:** 2026-08-04
**Branch activa:** `claude/auditoria-conformidad-mca-mcs` · **PR #573** (abierto)
**Generado por:** sesión de conformidad — Tanda B, acción B3

---

## 🎯 Dónde estamos parados

Sesión **de conformidad, no de producto**. Se auditó el repo contra MCA (entorno
agéntico) y MCS (calidad de software) y se ejecutó la remediación. De la Tanda B
quedan B1, B2, B3 y B4 hechas; falta **B5**.

| Marco | Objetivo | Alcanzado | Evaluados |
|---|---|---|---|
| MCA | N2 | **N0** | 11/11 · 10 conformes |
| MCS | N2 | **N0** | 126/126 · 9 conformes |

**MCA está a un requisito de N2** y ese requisito no necesita código: solo que
alguien verifique el guard desde una sesión abierta dentro del repo.

Los requisitos que tocó la remediación **siguen figurando como NO CONFORME**:
arreglarlos no es medirlos, y eso exige reauditar.

## 📍 Dónde retomar

**Lo más barato y de mayor impacto son dos acciones del owner**, no de Claude:

1. Abrir Claude Code con el repo como directorio de trabajo y comprobar que el
   guard intercepta (`echo "prueba: git push --force"`). Cierra AUT-01 y MCA
   llega a **N2**.
2. Proteger `main` — hoy cualquiera escribe directo en productiva.

Después, **B5** (modelo de amenazas, 2 d, desbloqueada por B1).

## ✅ Hecho en esta sesión — B3, conjunto de evaluación de IA

Cierra **IA-07, IA-08 e IA-09**. Vive en `apps/api/evaluacion/`; el detalle está
en `docs/conformidad/plan.md` §B3 y el porqué en `evaluacion/README.md`.

B2 comprobaba que el contenido ajeno no llegue al modelo como instrucción. Nadie
comprobaba la otra mitad: **si el modelo desobedece igualmente, qué sale**. Esa
es la pregunta que el conjunto hace, y por eso puede ser un gate — mide al
sistema, no al modelo: corre sin clave de API, sin red y en segundos, con job
propio en CI (`evaluacion-ia`) y umbral eliminatorio en seguridad.

Los fallos de IA que ya llegaron a un usuario (BUG-063/068/069/070/073,
ENH-102, ENH-147) entraron como **casos permanentes**, con la salida de modelo
que los provocó. Una prueba de trinquete falla si alguno desaparece.

**Encontró dos defectos el primer día**, ninguno reportado por usuarios, los dos
corregidos en commits propios:

- **Navegación fuera del sitio desde el copiloto.** El guardia era «empieza por
  `/` y no por `//`»; cinco formas lo pasaban porque el parser de URL del
  navegador trata `\` como `/` y **borra** TAB/LF/CR. El frontend hace
  `router.push(a.path)` sin comprobar nada más.
- **Un `field: null` del modelo** con confianza alta borraba el mapeo que la
  heurística había acertado, en el importador de planes.

Verificado por mutación: quitar cada defensa tira entre 1 y 8 casos; sin mutar,
0.

## 🔄 PRs en flight

| PR / branch | Acción pendiente |
|---|---|
| **#573** · `claude/auditoria-conformidad-mca-mcs` | Revisar y mergear |
| #570 · `claude/pmo-portfolio-architecture-6hbuen` | Verificar + mergear · `alembic upgrade head` (0091-0094) |
| `claude/plan-import-wbs-fixes-nwotng` | Falta abrir PR · migs 0095-0096 |
| `claude/gantt-areas-fixes` | Falta abrir PR (ENH-149/BUG-075/ENH-154/ENH-152) |

## ⚠️ Gotchas

- **`main` no está protegida.** Verificado contra la API de GitHub. La regla de
  `CLAUDE.md` §8 existe solo en prosa. Al protegerla, añadir `evaluacion-ia` a
  los checks requeridos.
- **Los gates de CI funcionan como trinquete:** fallan ante crecimiento nuevo, no
  por el pasivo heredado. El de contexto frenó esta misma sesión y hubo que
  recortar en vez de subir el techo — que es lo que debe pasar.
- **No hay tests de frontend.** El salto de Next 15.0 a 15.5 lo respaldan solo
  typecheck y build. Un smoke manual antes de mergear sería prudente.
- **Python 3.12 no es negociable**: `psycopg[binary]` no tiene wheel para 3.13+.

## 📋 Lo que sigue

- **Tanda B:** solo queda **B5** (modelo de amenazas, 2 d).
- **Evaluación de IA:** falta superficie para el **informe ejecutivo** — hay que
  sacar el ensamblado del contexto fuera de `_run_report` primero.
- **Producto:** ENH-202 (Helvetica en exports) es el siguiente batch. US-168
  sigue `in-progress`.

## 🧹 Acciones del owner

- [ ] Verificar el guard desde una sesión dentro del repo (cierra AUT-01 → N2).
- [ ] Proteger `main` tras cerrar los PR abiertos, con `evaluacion-ia` incluido.
- [ ] Revisar y mergear **PR #573**.
- [ ] Fijar `permanente_max_chars` en `conformidad.yaml`.
- [ ] Revisar `docs/dominio/02-GLOSARIO.md` término por término.
- [ ] Smoke manual de la web tras el salto de Next 15.0 → 15.5.
- [ ] `SENTRY_DSN` en Railway para encender la captura de errores.
- [ ] Los tres PR pendientes de las ramas anteriores.

## 🔮 Sin issue todavía

- **Calidad de cronograma DCMA 14-point.** Ver `docs/dominio/01-DIAGNOSTICO.md` §4.
- **Línea base.** Brecha keystone: sin ella no existe «desviación».
- **Migrar de `python-jose` a PyJWT** — cerraría 5 CVE bloqueadas hoy por su
  restricción `pyasn1<0.5.0`.
- **Re-medir INT-04**: `api-tests-smoke` tarda 3 m en el runner, no los 13 de una
  máquina local. El requisito puede estar más cerca de conforme de lo estimado.

---

## Cómo retomar

1. Este archivo primero.
2. Luego `CLAUDE.md` (§0.3 = comandos de verificación) + `SPRINT.md` + el epic
   en flight.
3. Continúa desde "Dónde retomar".
