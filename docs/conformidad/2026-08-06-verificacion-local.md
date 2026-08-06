---
responsable: propietario
estado: historico
revisado: 2026-08-06
revisar_cada: nunca
---

# Verificación local — los trabajos que GitHub Actions no pudo correr

| Campo | Valor |
|---|---|
| Fecha | 2026-08-06 |
| Motivo | Caída de GitHub Actions durante el PR #582 |
| Rama | `claude/remediacion-ola-2-2kg36x` |
| Alcance | Los cuatro trabajos de CI que no reportaron |

---

## Qué pasó

La ejecución `31119280553` del PR #582 levantó cinco trabajos y **cuatro
murieron en «Set up job»** con `Failed to resolve action download info. Error:
Service Unavailable`, con **0 ms facturables**. No llegaron a ejecutar un solo
paso. Solo corrió `contraste-wcag`, que pasó —incluido el gate nuevo de DIS-01—.

`rerun_failed_jobs` devolvió `403 Resource not accessible by integration`: el
token de la sesión no tiene `actions:write`. githubstatus confirmaba el impacto
sin actualización.

Con el owner necesitando cerrar y sin fecha de vuelta, se corrieron a mano.

> **Esto no sustituye al trinquete.** Una verificación local la corre quien
> quiere que pase; el CI la corre siempre. Sirve para decidir con dato mientras
> el CI está caído, no para declarar el requisito verificado. Al mergear, el CI
> debe correr de verdad.

---

## Resultado

| Trabajo | Cómo se corrió | Resultado |
|---|---|---|
| `api-migrations-postgres` | Postgres 16.13 local, rol y base como el servicio del workflow | ✅ ver abajo |
| `web-build` | `pnpm --filter @pmoaas/web build` | ✅ salida 0 |
| `seguridad` · bandit | `bandit -r apps/api/app -ll` | ✅ 0 medias, 0 altas (26 bajas) sobre 38.043 líneas |
| `seguridad` · pip-audit | con `.pip-audit-ignore` aplicado | ✅ 0 vulnerabilidades nuevas, 8 pasivo declarado |
| `seguridad` · pnpm audit | `pnpm audit --prod --audit-level high` | ✅ salida 0 (1 moderada, bajo el umbral) |
| `seguridad` · gitleaks | `gitleaks detect --source .` | ✅ **478 commits**, sin fugas |
| Suite API · ruff · mypy · tsc | como la skill `verificar` | ✅ |

**Diferencia con el CI, declarada:** Postgres **16.13** en local contra
**15-alpine** en el workflow. Para lo que se ejerce aquí —tipos `json` y
conversión implícita desde `unknown`— el comportamiento es el mismo en ambas.

---

## Los dos hallazgos

Ninguno estaba en el producto. Los dos estaban en el **aparato de verificación**,
que es donde más caro sale no mirar.

### 1. `api-migrations-postgres` no ejercía la migración 0101

El trabajo corre `upgrade head`, `downgrade base`, `upgrade head` sobre una base
**limpia**. Se comprobó que **ninguna migración del árbol inserta filas en
`tenants`**. La 0101 es una migración de **datos**: recorre los inquilinos y
reescribe una llave dentro de `settings`. Sobre una base sin inquilinos, el
bucle recorre **cero filas** y su cuerpo nunca se ejecuta.

O sea: el trabajo que se había señalado como «el que importa» para esta
migración **habría dado verde con la migración rota**.

Un `upgrade head` sobre base limpia prueba que el **esquema** se construye y que
las migraciones son reversibles en su forma estructural. No prueba que una
migración de datos haga lo suyo. Son dos garantías distintas y solo una estaba
cubierta.

**Remediado:** `apps/api/tests/test_dat06_migracion_0101.py` siembra los tres
casos que la base limpia no tiene —el inquilino con la llave vieja, uno ya
migrado y uno sin el bloque—, corre `upgrade()` y `downgrade()` de verdad contra
el motor, y **cuenta los `UPDATE`**. Corre siempre contra SQLite y contra
Postgres cuando `DATABASE_URL_POSTGRES` está definida; el workflow la define, y
un tercer caso vigila que siga definiéndola —un `skip` silencioso se lee igual
que un verde—.

El conteo de `UPDATE` no es adorno: quitar la guarda `de not in umbrales`
sobrevive a **cualquier** aserción sobre el contenido, porque reescribe las
filas ajenas con exactamente lo mismo. Se comprobó mutándolo.

### 2. La justificación del encabezado de la 0101 era falsa

El docstring afirmaba que la primera versión, con `sa.text` y el diccionario ya
serializado, «habría fallado en Postgres» con *column settings is of type json
but expression is of type text*, y lo daba como un caso de BUG-039.

**Se mutó la migración de vuelta a esa versión y la suite pasó.** Contra
Postgres 16 + psycopg3 el parámetro viaja como `unknown` y el motor lo convierte
a `json` sin quejarse. Comprobado además de forma aislada: `json.dumps(dict)`
por `sa.text` es **aceptado**; lo que Postgres rechaza es pasar el `dict` crudo,
y eso falla antes, en el adaptador.

La tabla tipada se queda —es la forma correcta: no serializa a mano y aguanta
que la columna pase a `jsonb`—, pero **no por el motivo que estaba escrito**.

Corregido en el docstring, dejando la corrección visible. Una justificación
falsa en un encabezado es peor que ninguna: la siguiente persona la cita, y en
este expediente el motivo escrito es lo que sostiene cada cierre.

---

## Lo que esto dice del método

Las tres lecciones del [índice](README.md) se repitieron aquí, aplicadas al
verificador en vez de al producto:

- **Medir contra el texto, no contra el nombre.** «Hay un trabajo de migraciones
  contra Postgres» era cierto y no cubría lo que se creía.
- **Una prueba que no se ve fallar no es una prueba.** El hallazgo 2 salió de la
  mutación, no de leer.
- **La cobertura se demuestra, no se supone.** Un trabajo verde sobre un sujeto
  vacío es un trabajo verde sobre nada.
