---
tipo: runbook
responsable: propietario
estado: vigente
revisado: 2026-05-08
revisar_cada: 180d
---

# Runbook · Import MPP nativo (MPXJ + OpenJDK 21)

> **Scope:** correr, verificar y reversar el soporte de import `.mpp`
> (formato binario propietario de MS Project) entregado en **US-069
> (#122)** del Sprint 5. El parser corre como subprocess Java contra
> [MPXJ](https://www.mpxj.org/) desde los contenedores de `api` y
> `worker` — ambos comparten el `apps/api/Dockerfile`.

Tiempo estimado: **15–20 min** para smoke local; Railway redeploy
automático al mergear a `main`.

---

## 0. Arquitectura (US-069)

```
apps/api/app/api/v1/endpoints/tasks.py  (POST /projects/{id}/tasks/import)
        │
        ▼ .mpp o application/vnd.ms-project
apps/api/app/services/msproject/mpp_parser.py   (Python)
        │
        ▼ subprocess.run(["java", "-cp", ..., "MpxjCli", tmp_path, output_path])
apps/api/app/services/msproject/mpxj_cli/MpxjCli.java   (wrapper)
        │
        ▼ net.sf.mpxj.reader.UniversalProjectReader
/opt/mpxj/lib/*.jar   (MPXJ + deps POI/SLF4J)
```

- El wrapper `MpxjCli` recibe 2 argumentos: `<input-file>` (.mpp) y
  `<output-file>` (donde escribir el JSON). Escribe el JSON a archivo
  (no a stdout) para evitar contaminación con logs que MPXJ/POI/SLF4J
  emiten al stdout durante el read del .mpp. El JSON tiene la misma
  forma que produce `xlsx_task_parser.parse_xlsx` (`XlsxParseResult`
  + `ParsedTask`), reusando el adaptador `_TaskShim` del endpoint sin
  tocar la lógica de persistencia.
- Timeout por defecto: **60 s** (`MPP_PARSE_TIMEOUT_SECONDS`). Cuando
  se cumple, el subprocess se mata y el endpoint devuelve `422`.

---

## 1. Pre-requisitos

- MPXJ **13.7.0** pinned en `apps/api/Dockerfile` (ARG `MPXJ_VERSION`).
  Upgrade: re-testar contra fixtures reales + bumpear el ARG.
- OpenJDK **21 JRE headless** copiado desde la imagen oficial
  `eclipse-temurin:21-jre-jammy` (el `python:3.12-slim` base no trae
  JDK 21 en los repos de Bookworm).
- Tamaño incremental vs baseline del contenedor api/worker:
  - JRE 21 headless: **~180 MB**
  - MPXJ + deps (POI, SLF4J, log4j): **~45 MB**
  - Total: **~225 MB** sobre la imagen Python slim.

---

## 2. Build local + smoke test

Desde `apps/api/`:

```bash
# Build con la versión actualmente pinned.
docker build -t pmo-aas-api:mpp-smoke .

# Smoke 1 — Java resuelve la clase.
docker run --rm pmo-aas-api:mpp-smoke \
    java -cp "/opt/mpxj/lib/*:/opt/mpxj/cli" MpxjCli

# Salida esperada en stderr:  "usage: MpxjCli <input-file>"
# Exit code: 2

# Smoke 2 — Parser Python arranca (Java debe estar en PATH).
docker run --rm pmo-aas-api:mpp-smoke \
    python -c "import shutil; assert shutil.which('java'), 'java missing'; print('OK')"
```

Si Smoke 1 falla con `Error: Could not find or load main class MpxjCli`,
revisar que `/opt/mpxj/cli/MpxjCli.class` existe en la imagen
(`docker run --rm pmo-aas-api:mpp-smoke ls /opt/mpxj/cli`). La causa
típica es un error silencioso en `javac` durante la etapa
`mpxj-build` — revisar el output del build.

Si Smoke 1 falla con `NoClassDefFoundError: net/sf/mpxj/...`, el zip de
MPXJ cambió de estructura — revisar `/opt/mpxj/lib/` y ajustar el
classpath en el Dockerfile o en `mpp_parser.DEFAULT_CLI_CP`.

---

## 3. Smoke con un archivo .mpp real

Colocar un `.mpp` chico en `/tmp/plan.mpp` del host. Luego:

```bash
docker run --rm -v /tmp/plan.mpp:/tmp/plan.mpp pmo-aas-api:mpp-smoke \
    sh -c 'java -cp "/opt/mpxj/lib/*:/opt/mpxj/cli" MpxjCli /tmp/plan.mpp /tmp/out.json && cat /tmp/out.json'
```

Salida esperada en `/tmp/out.json`: JSON `{"tasks":[{...}]}` con los
campos `row_number`, `name`, `wbs`, `start_date`, `end_date`,
`duration_days`, `progress`, `is_milestone`, `predecessors_raw`,
`resources_raw`.

**Nota:** stdout puede contener warnings de MPXJ/POI durante el read
(p. ej. "WARN: deprecated API"); por eso el wrapper escribe el JSON
a archivo, no a stdout. No te preocupes por logs en stdout.

Si el JSON se ve con caracteres raros (ej. `á` en vez de `á`),
el CLI ya escribe UTF-8 explícito; revisar que el cliente/terminal no
esté en `C` locale (`LANG=C.UTF-8`).

---

## 4. Env vars

| Variable | Default | Propósito |
|---|---|---|
| `MPXJ_CLI_CP` | `/opt/mpxj/lib/*:/opt/mpxj/cli` | Classpath pasado a `java -cp`. Solo tocar si movemos los jars a otra ruta. |
| `MPP_PARSE_TIMEOUT_SECONDS` | `60` | Timeout del subprocess. Subir solo si tenés archivos >10k tareas y se confirmó que no es por un bug de MPXJ. |
| `JAVA_HOME` | `/opt/java/openjdk` | Set por el Dockerfile. No debería necesitar override. |
| `PATH` | incluye `/opt/java/openjdk/bin` | idem. |

En Railway las variables del Dockerfile ya se heredan — no hace falta
setearlas en la UI, salvo que quieras un timeout distinto por servicio.

---

## 5. Troubleshooting

### El endpoint devuelve 422 con "Java runtime no disponible"

`shutil.which("java")` no encontró el binario dentro del contenedor. Causas:

1. El build stage `mpxj-build` o la copia `COPY --from=temurin-jre ...`
   falló silenciosamente. Forzar rebuild sin cache:
   `docker build --no-cache -t pmo-aas-api:debug .`
2. El `PATH` fue sobrescrito por un ENV posterior en el Dockerfile.
   Revisar que `/opt/java/openjdk/bin` siga estando al principio del
   `PATH` en el runtime final.

### El endpoint devuelve 422 con "archivo MPP corrupto o versión no soportada"

- El archivo puede ser **válido** pero de una versión de MS Project que
  MPXJ 13.7.0 no soporta (muy raro — MPXJ cubre 98/2000/2003/2007/2010/
  2013/2016/2019/365). Subir la versión pinned: ver §7.
- El archivo puede ser **.xlsx renombrado** a `.mpp` — en ese caso el
  usuario debe elegir el formato correcto en el wizard (US-070).
- Para diagnóstico detallado, correr el CLI manualmente con el archivo
  (§3) y leer el stderr del `java`.

### Parseos lentos (>30 s)

MPXJ carga el proyecto completo en memoria. Para archivos >5k tareas
el cold start del JVM puede costar 2–3 s adicionales. Opciones:

1. Aumentar `MPP_PARSE_TIMEOUT_SECONDS` en Railway (hasta 120).
2. Pasar el parseo al worker vía Celery (ver follow-up en el issue
   #122 — "async dispatch" está out of scope de la US-069 MVP).

### `OutOfMemoryError` durante parseo

Archivos realmente grandes pueden exceder el heap default del JVM
(256 MB en el binario de Temurin). Ajustar con `-Xmx`:

```python
# mpp_parser.py, parámetro al subprocess:
["java", "-Xmx512m", "-cp", _classpath(), "MpxjCli", tmp_path]
```

Si ocurre de forma recurrente, convertirlo en env var (`MPXJ_JVM_OPTS`).

---

## 6. Rollback

Si la ruta `.mpp` necesita desactivarse de urgencia (ej. CVE en MPXJ):

1. **Quick disable (1 commit):** en `endpoints/tasks.py`, eliminar la
   detección `is_mpp` en el check de content-type y dejar solo XLSX/XML.
   El usuario recibe `415 UNSUPPORTED_MEDIA_TYPE` para `.mpp`.
2. **Full rollback:** revertir el commit de US-069 (`git revert`). El
   Dockerfile recupera la base `python:3.12-slim` sin Java. Railway
   reconstruye la imagen más liviana en el siguiente deploy.

No hay datos persistidos específicos de `.mpp` que limpiar — el campo
`Task.source = "mpp"` es solo auditoría; tareas importadas siguen siendo
válidas aunque se desactive el parser.

---

## 7. Upgrade de MPXJ

1. Revisar [releases](https://github.com/joniles/mpxj/releases) — buscar
   patch notes con cambios breaking en `UniversalProjectReader`,
   `Task.getPredecessors()` o `Duration.convertUnits()`.
2. Bumpear `ARG MPXJ_VERSION` en `apps/api/Dockerfile`.
3. Recompilar wrapper: `docker build --target mpxj-build`. Si `javac`
   falla con errores de API incompatible, ajustar `MpxjCli.java` y
   documentar el cambio aquí.
4. Correr los tests `test_us069_mpp_parser.py` — todos deben pasar.
5. Smoke con `.mpp` real (§3) contra un archivo que ya funcionaba
   antes. Comparar el JSON de salida campo por campo.
6. Actualizar la versión en el encabezado de este runbook.

---

## 8. Tests relacionados

- `apps/api/tests/test_us069_mpp_parser.py` — unit tests mockean
  `subprocess.run`. Cubren: parseo OK, archivo corrupto, timeout,
  archivo vacío, Java ausente, contrato de shape, endpoint 200 + 422.
- El test `TC-069.4_mpxj_cli_smoke` se salta automáticamente cuando
  `java` no está en `PATH` o `/opt/mpxj/cli` no existe (útil en dev
  local). En CI corre dentro del contenedor.

---

**Última actualización:** 2026-04-24 — entrega inicial US-069.
**MPXJ pinned:** `13.7.0`. **JRE:** `Eclipse Temurin 21 (headless)`.
