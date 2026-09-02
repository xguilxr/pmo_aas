---
tipo: informe
responsable: propietario
estado: vigente
revisado: 2026-09-01
revisar_cada: 90d
---

# Seguimiento 2026-09-01 — «Claudio, arranca»

Repositorio ya auditado (`conformidad.yaml`, `evaluado: 2026-08-04`; próxima evaluación
formal agendada `2026-11-03`). Estado detectado: **ya auditado** → modo seguimiento
(OPERACION.md §1.1): solo lo NO CONFORME del plan anterior más regresiones nuevas.

## Alcanzado, vs. la última medición

No se movió: MCA sigue N2/N2 (11/11 conformes), MCS sigue N0 (objetivo N2, 25/126
conformes). No hay nada NUEVO que corregir bajo este alcance — ver "Qué se comprobó" y
"Qué queda abierto" abajo.

## Qué se comprobó (regresiones desde la entrada de 2026-08-12 en `conformidad.yaml`)

Main avanzó 283 commits / 8 PRs mergeados (`#587, #593, #594, #595, #596, #597, #598,
#602`) desde la última entrada. Nada de ese rango toca seguridad, arquitectura o el guard
de acciones irreversibles por título; se verificó igual con evidencia ejecutada:

| Comprobación | Comando | Resultado |
|---|---|---|
| CI en `main` | `gh run list --branch main --limit 5` | 5/5 `success` (hasta PR #602, 2026-08-29) |
| Guard de irreversibles (AUT-01) | `uv run pytest apps/api/tests/test_mca_aut01_guard.py -q` | **24/24 passed** |
| Lint | `uv run ruff check .` (apps/api) | **All checks passed** |
| Tipos vs. línea base | `python scripts/check_tipos.py` | `892 errores heredados, 892 tolerados` — sin regresión |
| Presupuesto de contexto (CTX-01/02) | `python scripts/check_contexto.py` | `TOTAL 19,865` bajo el techo `23,000` |
| Metadata de documentos (DOC-01) | `python scripts/check_docs.py` | `158 documentos` con tipo/responsable/estado/revisión |
| Hook y skill de CAP-01/AUT-01 siguen presentes | `test -f scripts/guard_irreversible.py` · `test -f .claude/skills/rebasear/SKILL.md` | ambos presentes |

Nota de entorno: el `.venv` local de este checkout estaba desincronizado de
`requirements.txt`/`requirements-dev.txt` (`uv sync` resuelve contra
`[dependency-groups]` de `pyproject.toml`, que no es lo que usa CI). Se corrigió con
`uv pip install -r requirements.txt -r requirements-dev.txt` antes de medir. No es un
hallazgo del repo — es higiene de este checkout.

La suite completa (`pytest -m "not heavy"`, ~382 archivos) se lanzó pero no terminó en
la ventana de esta sesión, probablemente por falta de una Postgres local — la señal de
regresión ya la da CI (verde) más los checks puntuales de la tabla. Queda pendiente
correrla completa si se quiere evidencia de esa suite específica.

## Qué queda abierto (ya estaba declarado, no es nuevo)

Ambos ítems siguen exactamente como los dejó la entrada del 2026-08-05 en
`conformidad.yaml`, y ambos están fuera del alcance de un seguimiento correctivo
(no son mecánicos ni reversibles en minutos):

1. **13 requisitos NO VERIFICABLE de MCS** — medición, 1-2 días. Recomendado antes de
   comprometer las Tandas C/D/E.
2. **Tandas C/D/E** — remediación de fondo hacia N1/N2 de MCS, 6-9 semanas.

Ninguno se ejecuta en esta sesión: forzar una evaluación apurada de los 13 NO VERIFICABLE
sin las fuentes que exige cada uno (p. ej. OPS-02 necesita confirmar en los logs de
Railway, que no son accesibles desde acá) repetiría el error que el propio expediente ya
documentó dos veces (auditorías previas que declararon cifras sin la evidencia de
primera mano). Se mantiene la fecha `proxima_evaluacion: 2026-11-03` para la evaluación
formal completa.

## Conclusión

Seguimiento sin hallazgos: 0 regresiones, 0 correcciones aplicadas al código o los
requisitos. El plan vigente (13 NO VERIFICABLE → Tandas C/D/E, ambos multi-día) no
cambia.
