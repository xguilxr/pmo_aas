---
name: verificar
description: Stack, preparación del entorno y los comandos de verificación del repo — lint, tests de API, typecheck y build de web, migraciones, presupuesto de contexto y conjunto de evaluación de IA — con su criterio de aprobación y las rutas que no se editan a mano. Úsala antes de dar por terminado un cambio, al montar el entorno por primera vez, o cuando necesites saber cómo se comprueba algo en este repo. NO la uses para el ceremonial de cierre de un issue (eso es cerrar-item).
---

# Verificación — cómo se comprueba que algo funciona aquí

> **MCA CTX-01.** Todo lo de abajo se ejecutó el **2026-08-04** y esta skill
> registra la salida real. Si un comando deja de correr, se arregla el comando o
> se corrige esta skill. Un comando declarado que no corre es peor que no
> declarar ninguno: el asistente confía en él y da por terminado lo que no lo está.

Vive en una skill y no en `CLAUDE.md` porque se consulta **al verificar**, no en
cada turno. El presupuesto de contexto permanente lo hace cumplir el CI, y esta
sección eran ~4.500 caracteres que se cargaban siempre para usarse al final.

---

## Stack

Monorepo pnpm 9.12 · `apps/api` FastAPI + SQLAlchemy + Alembic, Python **3.12**
(fijado en `apps/api/runtime.txt`) · `apps/web` Next.js + TypeScript ·
`packages/sdk` escrito a mano · Postgres · Celery + Redis.

## Preparar el entorno

Python 3.12 no es opcional: `psycopg[binary]==3.2.3` no publica wheel para
3.13+ y la instalación falla entera.

```bash
uv venv --python 3.12 apps/api/.venv
uv pip install --python apps/api/.venv/Scripts/python.exe -r apps/api/requirements-dev.txt
pnpm install --frozen-lockfile
```

## Comandos de verificación

Los mismos que corre `.github/workflows/ci.yml`; esa es la fuente de verdad y
esta tabla la refleja.

| Ámbito | Comando | Criterio | Dura |
|---|---|---|---|
| Lint API | `cd apps/api && .venv/Scripts/python.exe -m ruff check .` | exit 0 | segundos |
| Tests API | `cd apps/api && .venv/Scripts/python.exe -m pytest -q -n auto -m "not heavy"` | exit 0 | ~15 min |
| Typecheck web | `pnpm --filter @pmoaas/web exec tsc --noEmit` | exit 0 | ~1 min |
| Contexto | `python scripts/check_contexto.py` | exit 0 | segundos |
| Evaluación IA | `cd apps/api && .venv/Scripts/python.exe -m evaluacion.runner` | exit 0 | segundos |
| Build web | `pnpm --filter @pmoaas/web build` | exit 0 | — |
| Migraciones | `cd apps/api && alembic upgrade head && alembic downgrade base && alembic upgrade head` | exit 0 · exige Postgres levantado | — |

> **El criterio es `exit 0`, nunca un conteo.** Aquí no se anota «N tests
> pasaron»: esa cifra deriva del contenido real, queda obsoleta con el siguiente
> test y no debe vivir en un documento de referencia (MCA CTX-03). Las
> mediciones fechadas de cada auditoría viven en `conformidad.yaml`.

## Definición de terminado (MCA FLU-02)

Los tres comandos ejecutables en verde: **lint exit 0, typecheck exit 0, tests
API exit 0**. Sin excepciones ni fallos «esperados». Si algo sale rojo, es tuyo.
El DoD de la skill `cerrar-item` se marca **después** de que estos pasen, no en
su lugar.

## El smoke suite no necesita WeasyPrint

`tests/conftest.py::_stub_heavy_renderers` stubea `render_pdf` y `html_to_pdf`
—los dos símbolos que cargan las librerías nativas GTK/Pango— y propaga el stub
a todo módulo de `app.` que los haya importado, barriendo `sys.modules` en vez
de una lista escrita a mano. Por eso corre verde en Windows sin instalar nada más.

> Si añadís un módulo que importe un renderer, **no hay que registrarlo en
> ningún sitio**: el barrido lo cubre. La lista manual anterior se había quedado
> corta y hacía fallar 4 tests (auditoría MCA 2026-08-03).

El render real se ejerce a propósito en `tests/test_us037_pdf_renderer.py`,
marcado `heavy`, que corre en el job `api-tests-heavy` del CI (solo push a
`main`). **Ese archivo está excluido del stub**: si tocás `pdf_renderer.py`, es
el que te cubre.

`conftest.py` stubea además los proveedores de IA y `_ping_byo_provider`. Dos
suites están excluidas de ese stub a propósito, porque con él puesto medirían el
stub y pasarían en verde con el agujero abierto: `test_bug030_groq_no_metadata`
y `test_seg06_am01_ssrf_base_url`. Si escribís una suite que compruebe el
comportamiento real de un proveedor, añadila a `_AI_STUB_EXCLUDE_PREFIXES`.

## Gates de CI que son trinquetes

Fallan ante crecimiento **nuevo**, no por el pasivo heredado, que está
documentado con fecha:

| Job | Qué frena |
|---|---|
| `contexto-permanente` | Que `CLAUDE.md`, `SPRINT.md` o `HANDOFF.md` engorden. Umbrales en `conformidad.yaml` |
| `seguridad` | Secretos en el historial, SAST, dependencias vulnerables nuevas |
| `evaluacion-ia` | Que la salida del modelo deje de estar contenida. Umbral en `apps/api/evaluacion/casos.yaml` |
| `test_seg06_modelo_amenazas` | Una ruta sin autenticación o un destino externo que el modelo de amenazas no declara |

## Rutas que no se modifican a mano

| Ruta | Regla |
|---|---|
| `apps/api/alembic/versions/` | Solo vía `alembic revision`. Nunca editar una migración ya mergeada a `main` |
| `pnpm-lock.yaml` · `apps/api/uv.lock` | Los regenera el gestor. No se editan |
| `landing/` | Se despliega a mano a HostGator, no por Railway. Un cambio aquí no llega solo a producción (ver `docs/runbooks/infra/landing-hostgator.md`) |
