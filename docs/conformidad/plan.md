# Plan de conformidad — pmo_aas

| Campo | Valor |
|---|---|
| Última auditoría | **2026-08-04** · [MCA](2026-08-04-mca.md) · [MCS](2026-08-04-mcs.md) |
| Anteriores | 2026-08-03 · [MCA](2026-08-03-mca.md) · [seguimiento](2026-08-03-mca-seguimiento.md) · [MCS](2026-08-03-mcs.md) |
| Próxima evaluación | 2026-11-03 |

| Marco | Objetivo | Alcanzado | Estado |
|---|---|---|---|
| MCA | N2 | **N0** | 9 de 11 CONFORME. Bloquean **AUT-01** (owner, 2 min) y **CAP-01** (10 min) |
| MCC | no_aplica | no_aplica | Producto propio, sin encargo (`AUDITORIA.md` §1.3) |
| MCS | N2 | **N0** | **21 de 126 CONFORME** (eran 9). Distancia a N1: **54** — no 43, ver abajo |

> **La distancia a N1 nunca fue 43.** El informe del 2026-08-03 omitió de su
> tabla de bloqueantes los 14 requisitos de N1 en NO VERIFICABLE, que bloquean
> igual (`MCS-CORE` §6.2 exige CONFORME **o** NO APLICABLE). Era 60; hoy es 54.
> Detalle en [2026-08-04-mcs.md](2026-08-04-mcs.md) §1.

---

## Tanda A — ejecutada 2026-08-03

Cuatro de cinco hechas. La quinta (A1) queda a la espera por decisión del owner.

| # | Acción | Estado |
|---|---|---|
| **A1** | Proteger `main` | **PENDIENTE — decisión del owner.** Esperar a cerrar #570 y abrir los dos PR que faltan. Comando abajo |
| ~~A2~~ | Escáneres en CI | **HECHA** — job `seguridad`: gitleaks (historial completo), bandit, pip-audit, pnpm audit |
| ~~A3~~ | Cabeceras de seguridad | **HECHA** — middleware en `main.py` + 5 pruebas |
| ~~A4~~ | ¿La IA calcula cifras? | **HECHA — sí lo hacía.** Corregido |
| ~~A5~~ | Captura de errores | **HECHA** — sentry-sdk, inerte sin `SENTRY_DSN` |

### Lo que los escáneres encontraron el primer día

Ninguno de estos hallazgos era visible antes, porque nada los buscaba.

**bandit — B314, vulnerabilidad real.** `parse_ms_project_xml` recibía bytes de
un archivo **subido por el usuario** y los pasaba a `xml.etree.ElementTree`, que
no resiste bombas de entidades. Sustituido por `defusedxml`; comprobado que un
XML válido sigue parseando y que una bomba se rechaza con un 400 limpio, sin
revelar qué defensa saltó. Los 31 tests del importador siguen verdes.

**pip-audit — 23 vulnerabilidades en 7 paquetes.** Cerradas **10** subiendo las
directas, y no son menores:

| Paquete | De → a | CVE | Por qué importa |
|---|---|---|---|
| `python-multipart` | 0.0.12 → 0.0.31 | 6 | Maneja la subida de minutas y planes |
| `python-jose` | 3.3.0 → 3.4.0 | 2 | JWT: toda la autenticación |
| `jinja2` | 3.1.4 → 3.1.6 | 3 | Render de los PDF |
| `python-dotenv` | 1.0.1 → 1.2.2 | 1 | — |

Suite completa tras el cambio: **778 passed · 1 skipped · exit 0**, sin
regresiones. Efecto lateral: los avisos de deprecación bajaron de 2.312 a 698.

Las 13 restantes están **bloqueadas, no ignoradas**, y cada una con su causa en
`apps/api/.pip-audit-ignore`: `starlette` (7) exige subir FastAPI; `pyasn1` (4)
tiene arreglo pero `python-jose` fija `<0.5.0` —comprobado: uv lo declara
insatisfacible—; `ecdsa` y `weasyprint` no tienen versión con arreglo.

> **El gate es un trinquete**, igual que el de contexto: falla ante cualquier
> vulnerabilidad **nueva**. Probado en ambos sentidos, incluida una dependencia
> vulnerable añadida a propósito.

### A4 — la IA sí calculaba cifras, y había un segundo hallazgo

`REPORT_SYSTEM` recibía `budget_plan` y `budget_actual` y le pedía al modelo un
`budget_status`. El modelo derivaba la desviación por su cuenta: es exactamente
lo que IA-05 prohíbe, y esa cifra iba a un informe ejecutivo.

Y al mirarlo apareció algo que la auditoría no había visto: el contexto hacía
`float(p.budget or 0)`. El modelo guarda `Decimal` —DAT-03 conforme— pero **se
convertía a coma flotante justo en el camino al informe**.

Corregido: la desviación y el porcentaje consumido se calculan en Python con
`Decimal`, viajan como cadena, y el prompt lleva una regla innegociable de no
calcular. El modelo redacta; no computa.

### A1 — el comando, para cuando cierren los PR

```bash
gh api -X PUT repos/xguilxr/pmo_aas/branches/main/protection   -H "Accept: application/vnd.github+json"   -f "required_pull_request_reviews[required_approving_review_count]=0"   -F "enforce_admins=false"   -F "restrictions=null"   -f "required_status_checks[strict]=true"   -f "required_status_checks[contexts][]=lint"   -f "required_status_checks[contexts][]=api-tests-smoke"   -f "required_status_checks[contexts][]=web-typecheck"   -f "required_status_checks[contexts][]=web-build"
```

**Deja fuera `seguridad` y `contexto-permanente` a propósito:** GitHub no puede
exigir un check que nunca ha corrido, y los PR quedarían esperando para siempre.
Se añaden después del primer PR que los ejecute.

---

## Tanda B — ejecutada 2026-08-03

| # | Acción | Cierra | Estado |
|---|---|---|---|
| ~~B1~~ | Suite de aislamiento entre inquilinos | SEG-08, T-4 | **HECHA** — 8 casos, verificada por mutación |
| ~~B2~~ | Contenido de minutas como dato no confiable | IA-11, T-5 | **HECHA** — ver abajo |
| ~~B3~~ | Conjunto de evaluación de IA en la canalización | IA-07, IA-08, IA-09 | **HECHA** — 45 casos, umbral eliminatorio, job propio en CI. Ver abajo |
| ~~B4~~ | Límites de iteraciones y de coste por ejecución | IA-03 | **HECHA** — `AI_MAX_PROMPT_CHARS` |
| ~~B5~~ | Modelo de amenazas sobre la arquitectura | SEG-06 | **HECHA** — 14 amenazas, trinquete de revisión en la suite. Ver abajo |

### B2 — el informe nombraba las minutas; los vectores eran diez

El informe describe IA-11 como «las minutas las sube el usuario y se procesan
con IA». Es cierto y es el vector más visible, pero al recorrer **todas** las
llamadas a `generate_for_tenant` aparecieron diez puntos por los que entra
texto que no escribió la plataforma. Cerrar solo las minutas habría dejado el
requisito marcado como conforme con el problema abierto en otros nueve sitios.

Dos merecen mención aparte:

- **La memoria del proyecto (`auto_summary_md`)** es el vector *indirecto*, y es
  peor que el directo. Lo escribe el modelo resumiendo minutas de cualquiera, y
  luego se antepone a **toda** generación posterior del proyecto. Una minuta
  envenenada deja de ser un incidente y se vuelve una instrucción permanente.
- **El importador de planes** (`import_ai.py`, `import_mapping_suggest.py`)
  manda al modelo cabeceras, filas y estados de la hoja que sube el usuario. No
  estaba en el informe. Y lo que el modelo devuelve ahí decide a qué campo se
  mapea cada columna del plan importado.

**La delimitación por sí sola no vale.** Si el contenido puede escribir la
etiqueta de cierre, sale del bloque y lo que escriba detrás se lee con la
autoridad de la plataforma. Por eso hay tres capas y las tres son obligatorias:
neutralizar las etiquetas estructurales y los marcadores de rol, envolver con
la procedencia, y la regla de precedencia en el mensaje de sistema.

**Lo que NO se envuelve, a propósito:** las instrucciones permanentes del PM y
del tenant, y las notas libres que el operador teclea en esa misma petición. Son
canales de instrucción legítimos; degradarlos a dato rompería el producto sin
cerrar nada. Se neutralizan igual, para que no puedan falsificar delimitadores.

**Verificada por mutación**, en tres puntos distintos:

| Mutación | Efecto |
|---|---|
| La envoltura deja de neutralizar | **11 pruebas** caen, en todos los puntos de entrada |
| El system prompt pierde la regla de precedencia | **6 pruebas** caen |
| Un solo punto de entrada deja de envolver | **1 prueba** cae, exactamente la suya |

Y dos trinquetes que evitan que caduque: una prueba falla si aparece una llamada
nueva al proveedor sin la regla, y otra si un prompt usa una etiqueta
estructural que no está declarada.

> **Lo que esto NO es.** No es una garantía: un modelo puede desobedecer, y
> ninguna prueba unitaria puede afirmar lo contrario. Reduce la superficie. La
> contención real la dan los límites de lo que el sistema deja hacer al modelo
> —el copiloto solo navega, las cifras se calculan en Python, ninguna salida
> ejecuta nada—, y eso ya estaba. **B3 (conjunto de evaluación) es lo que
> convertiría esto en algo medible**, y es la siguiente.

### B3 — la pregunta que nadie estaba haciendo

B2 comprueba que el contenido ajeno no llegue al modelo **como instrucción**.
Nada comprobaba la otra mitad: *suponiendo que el modelo desobedezca de todas
formas* —cosa que ninguna defensa de prompt puede impedir, y así lo dice el
docstring de `untrusted.py`—, **qué sale por el otro lado**.

Esa es la pregunta que el conjunto de evaluación hace, y por eso puede ser un
gate: no mide al modelo, que exigiría un proveedor vivo, dinero por ejecución y
un resultado distinto cada vez. Mide al sistema, y eso es determinista, tarda
segundos y no necesita ni clave de API ni red. Cada caso es una salida de modelo
ya rota que se hace pasar por el mismo código que corre en producción.

**45 casos, cuatro superficies** —minuta, merge entre fragmentos, copiloto,
mapeo de columnas del importador—, cada una llamando a funciones de producto de
verdad. **Umbral: seguridad 100 % eliminatoria, calidad ≥ 90 %.** El umbral de
calidad no es 100 % a propósito: IA-09 pide que un fallo de producción entre al
conjunto **el día que se detecta**, no el día que se arregla.

Lo que de verdad se mide no son las expectativas de cada caso sino los
**invariantes de superficie**, que se aplican a todos los casos la enumere quien
la enumere. Un caso nuevo hereda el contrato entero. El más útil rehace, sobre
toda minuta, el viaje `summary` → memoria del proyecto → prompt de mañana: es
el vector indirecto que B2 señaló como el peor, y ahora cada caso lo ejercita de
paso.

**Los fallos de producción ya conocidos entraron como casos permanentes.**
BUG-063, BUG-068, BUG-069, BUG-070, BUG-073, ENH-102 y ENH-147 vivían dispersos
en el arreglo que los cerró; ahora vive cada uno en el conjunto, con la salida de
modelo que lo provocó. Una prueba de trinquete falla si alguno desaparece.

#### Qué encontró el primer día

Dos cosas que ninguna prueba miraba, ninguna reportada por un usuario:

**Una navegación fuera del sitio desde el copiloto.** El guardia era «empieza por
`/` y no por `//`». Cinco formas lo pasaban y resuelven a otro origen, porque el
parser de URL del navegador trata `\` como `/` y **borra** tabuladores y saltos
de línea antes de leer: `/\evil.example`, `/\/evil.example`, y las variantes con
TAB, LF y CR entre las barras. El frontend hace `router.push(a.path)` sin
comprobar nada más. La cadena completa existía: minuta envenenada → memoria del
proyecto → contexto de página del copiloto → botón ofrecido al usuario
autenticado. Verificado contra el parser de Node, no contra la especificación de
memoria.

**Un «no lo sé» del modelo borrando un acierto de la heurística.** En el mapeo de
columnas, `field: null` con confianza 0,99 pisaba el `name` que la heurística
resolvió con 0,8, y la columna llegaba sin asignar al asistente de importación.

Las dos corregidas en commits propios, con su prueba de regresión.

#### Verificado por mutación

Un conjunto de evaluación que sigue verde con la defensa quitada no mide nada.

| Mutación | Casos que caen |
|---|---|
| Un constructor de acciones ingenuo (el modelo manda) | **8** |
| La heurística del mapeo deja de opinar | **6** |
| El guardia de rutas acepta cualquier ruta | **5** |
| El parser tolerante vuelve a `json.loads` a secas | **3** |
| El validador acepta cualquier tipo de RAID | **2** |
| El guardia de rutas vuelve al filtro anterior | **2** |
| El envoltorio deja de neutralizar | **1** |
| Sin mutar | **0** |

#### Lo que NO cubre

Escrito aquí para que no se lea como cobertura que no existe:

- **El informe ejecutivo no tiene superficie.** Su contención es de otra
  naturaleza —las cifras se calculan en Python antes de llamar (IA-05), así que
  no hay salida que validar— y el ensamblado del contexto está en línea dentro
  de `_run_report`, sin función a la que llamar. Sacarlo y evaluarlo queda
  pendiente.
- **La exfiltración del prompt de sistema no está contenida**, y no hay caso que
  finja lo contrario. Si el modelo copia su mensaje de sistema en un `summary`,
  sale. El daño está acotado porque el destino es el mismo usuario del mismo
  inquilino que subió el archivo —no cruza la frontera que SEG-08 protege—, pero
  un prompt no es un secreto y queda escrito que no lo tratamos como tal.
- **El modelo mismo no se evalúa.** Un conjunto que ejerza al proveedor de verdad
  es otra cosa y otra decisión: mediría el modelo, no el sistema, y no puede ser
  un gate.

### B5 — el marco pide el modelo y no dice cómo hacerlo

Primero, una advertencia sobre el método. `MCS-CORE.md §5.14` **enuncia SEG-06 y
no trae procedimiento**: el identificador aparece una sola vez en todo `marcos/`,
en la tabla de requisitos. La skill `modelado-amenazas` enruta a §5.14 esperando
encontrar allí un procedimiento que no está. Su propia puerta de calidad dice
que en ese caso hay que parar y decirlo en vez de reconstruirlo de memoria, así
que queda dicho: **el método lo elegí yo** —descomposición por flujos, fronteras
de confianza numeradas, STRIDE sobre cada una— y el documento lo declara en su
§0 para que nadie lo lea como prescrito por el marco. Es un defecto de la skill,
no del requisito, y merece issue en el repositorio del kit.

El modelo vive en `docs/architecture/modelo-amenazas.md`: **ocho fronteras de
confianza y catorce amenazas**, cada una con control actual, evidencia abrible,
riesgo residual y estado.

**Y de paso destapó un error de la propia auditoría.** SEG-06 pide un modelo
«derivado de la arquitectura», así que lo primero fue buscarla. El informe deja
`ARQ-01` en PARCIAL con la evidencia «no se encontraron diagramas de contexto ni
de contenedores», y eso **no es exacto**: `docs/architecture/README.md` los
tiene, en mermaid, y su propio índice los anuncia en la fila 7. El auditor listó
`database.md`, `navigation.md` y `api-conventions.md` y no abrió el README.

No cambio el estado de ARQ-01 por mi cuenta —arreglar no es medir, y esto ni
siquiera es arreglar— pero queda anotado: **la razón escrita para ese PARCIAL no
se sostiene**, y hay que volver a mirarlo en la reauditoría en vez de arrastrarlo.

El modelo de amenazas no repite esos diagramas: aporta la vista que ellos no dan,
que es la misma arquitectura mirada por dónde se cruza una frontera de confianza.

#### Qué encontró

**AM-01, corregida en commit propio.** El modo BYO deja al administrador de un
inquilino fijar `base_url`, y `POST /admin/ai/provider/test` la usaba para hacer
una petición **desde dentro de la red privada de Railway**, devolviendo estado,
120 caracteres del cuerpo y latencia. Comprobado contra servidores locales antes
de tocar nada: puerto abierto, puerto cerrado y nombre inexistente daban tres
respuestas distinguibles. Era un oráculo de red completo en manos de cualquier
administrador de cliente. Cerrada en las tres puertas y verificada por mutación.

Y cuatro que **no** tenían control y ahora están escritas en vez de ignoradas:

| ID | Amenaza | Por qué importa |
|---|---|---|
| AM-08 | El registro de auditoría es una tabla ordinaria | AM-06 se apoya en él como único control. Un control que se apoya en otro que no existe no es un control |
| AM-09 | `/auth/login` no tiene límite por IP | El bloqueo por usuario para de adivinar una contraseña, no un intento por cuenta contra miles |
| AM-10 | El bloqueo por usuario es a su vez una denegación de servicio | Con una lista de usuarios se bloquea al inquilino entero |
| AM-14 | `main` sin proteger | Ya estaba en la lista del owner; ahora tiene ficha |

Ninguna se arregla aquí: B5 es el modelo, no la remediación. AM-01 fue la
excepción porque estaba viva y el arreglo cabía en un módulo.

#### Cómo se revisa, que es la mitad que suele faltar

SEG-06 pide «revisado ante cambios significativos», y eso ningún documento lo
cumple solo. Lo cumple `tests/test_seg06_modelo_amenazas.py`, que recalcula desde
el código dos cosas y falla si aparece algo que `amenazas.yaml` no declara:

- **rutas que no exigen identidad** — hoy siete, cada una con su motivo escrito;
- **destinos externos** en `app/`, separados en `egreso` y `referencia`.

Verificado por mutación: publicar un endpoint sin autenticación tira 2 pruebas;
añadir un destino externo sin declararlo, 1.

Deliberadamente **no** se vigila una huella del código entero. Un gate que se
pone rojo con cada edición se desactiva en dos días, y entonces no vigila nada.
Por el mismo motivo la ventana de 12 meses **avisa y no falla**: que pase el
tiempo no hace el código menos seguro hoy; superficie nueva sin evaluar, sí.

> Contar las rutas abiertas costó dos intentos. El primero miraba solo el primer
> nivel de dependencias y daba **37** rutas públicas, incluido el panel de
> superadministrador — `get_superadmin` no es `get_current_user`, pero depende de
> él. Las abiertas de verdad son **siete**. Queda anotado porque el susto es
> instructivo: una comprobación de seguridad mal escrita asusta o tranquiliza,
> y las dos cosas son igual de caras.

### Discrepancia: IA-12 no existe en el alcance evaluado

La tabla de acciones del informe atribuye a B2 «IA-11, IA-12», y el resumen
ejecutivo también cita las dos. Pero la evaluación detallada solo tiene **once**
requisitos de IA (IA-01..IA-11) y el cuadro de mando declara «0 / 11». **IA-12
no se evaluó**, muy probablemente porque es de N3 y el objetivo es N2.

Se deja anotado sin inventar: B2 cierra **IA-11** y el hallazgo **T-5**. Si
IA-12 existe en MCS-CORE y aplica a N2, hay que evaluarlo, no darlo por cerrado
de rebote.

---

## Tanda 1b — lo único que separa al entorno de N2

La Tanda 1 cerró **diez de once** requisitos y bajó el contexto permanente un
43 % (87.623 → ~50.400 caracteres). Queda **uno**, y con él caen N1 y N2 juntos,
porque los cinco de N2 ya están CONFORME.

**Y es tuyo, no mío:** la auditoría corrió desde `C:/Users/David Aguilar`, no desde el
repo, así que su `.claude/settings.json` nunca llegó a cargarse. Probado dos veces, la
segunda tras abrir `/hooks`: el guard no intercepta desde fuera del proyecto.

| # | Acción | Cierra | Esfuerzo | Quién |
|---|---|---|---|---|
| ~~10~~ | ~~Sacar las cifras vivas de `CLAUDE.md` §0.3~~ · **HECHA 2026-08-03** — criterio `exit 0` en la tabla, mediciones fechadas en `conformidad.yaml`. Además el check ahora **vigila CTX-03 automáticamente**, probado en 4 escenarios | **CTX-03** | — | — |
| 11 | **Abrir Claude Code con `pmo_aas` como directorio de trabajo** y comprobar que el guard intercepta (`echo "prueba: git push --force"`). Abrir `/hooks` no basta: `.claude/settings.json` es config **del proyecto** y no se carga en una sesión enraizada fuera de él | **AUT-01** | 2 min | **Owner** |
| 12 | Reejecutar `MCA-P02`. Con 10 y 11 hechas, el entorno alcanza **N2** | — | 20 min | Claude |

> **La acción 10 corrige un error mío.** Escribí esas cifras en las acciones 3 y
> 3b como evidencia de ejecución. Eran ciertas el día que las medí y dejan de
> serlo sin que nadie lo note — que es exactamente lo que CTX-03 prohíbe.

### Acción 13 — el objetivo de contexto, alcanzado (2026-08-04)

**De 51.298 a 31.552 caracteres: −39 %.** El objetivo de 40.000 estaba declarado
desde la Tanda 1 y no se había alcanzado nunca.

La medición anterior daba la brecha por cerrada de dos maneras posibles: cambiar
el método, o subir el objetivo a ~50.000 «que es lo que este entorno cuesta de
verdad». Se eligió lo primero, y resultó ser lo correcto por una razón que la
medición ya insinuaba: **la partida más grande no era un archivo grande, era una
regla.**

`CLAUDE.md` §1.4 obligaba a leer «el epic relevante» antes de empezar. Eso metía
un documento funcional completo en el contexto de cada sesión **antes de saber
siquiera si se iba a abrir** — el 31 % del presupuesto, gastado en una apuesta.

| Qué se movió | A dónde | Ahorro |
|---|---|---|
| El epic entero | `docs/epics/README.md`, que ya era el índice. El epic se abre **al tocarlo** | ~9.700 |
| `CLAUDE.md` §0.3 | Skill `verificar`: stack, entorno, los siete comandos, gates, rutas protegidas | ~2.800 |
| Deferred, DONE y backlog de `SPRINT.md` | `SPRINT-BACKLOG.md`, que se abre al planear y no al ejecutar | ~5.000 |

> **Un tropiezo que vale la pena contar.** La primera versión creó un
> `docs/epics/INDICE.md` nuevo… existiendo ya `docs/epics/README.md`, que **era
> el índice de epics** y con más información (dependencias, epics canceladas).
> Era un duplicado: exactamente el CTX-06 que este mismo trabajo hace cumplir en
> otros. Se borró y se consolidó en el README, quitándole de paso la columna
> «Cambios v2», un marcador de una migración de mayo que ya no ayuda a decidir
> qué epic abrir. Cuesta ~3.400 caracteres más que el índice duplicado y no
> tener dos versiones de la misma tabla los vale.

**Lo que NO se movió, a propósito.** La numeración de identificadores (§2) y las
convenciones de commit (§4) se usan en **cada** turno. Sacarlas bajaría la cifra
y obligaría a cargar una skill por commit: más contexto, no menos. Reducir la
medición sin reducir lo que se lee es falsear el control, no ejercerlo — y es la
trampa evidente de este requisito, porque `check_contexto.py` mide **la política
declarada en §1**, no lo que hay en disco.

Por eso `medir_contexto()` se actualizó en el mismo cambio, y `_epics()` lleva
escrito que si algún día §1 vuelve a exigir el epic de arranque, esta función
tiene que volver a la mediana. El medidor y la política se mueven juntos o la
cifra miente.

**El techo bajó de 51.300 a 31.900** (actual + 1 %). Sin eso la ganancia se
erosiona en silencio, que es exactamente lo que el trinquete existe para evitar.

> El techo anterior había quedado saturado: el 2026-08-04 el margen era de **dos
> caracteres**, y dos veces esa misma sesión obligó a recortar documentación en
> vez de subirlo. Funcionó como debía, pero ya no dejaba escribir un handoff.

---

## Por qué solo hay una tanda

`AUDITORIA.md` §2.1 fija el orden de subida. El punto 1 —gravedad crítica— **no aplica**:
no hay credenciales expuestas ni alcance externo suelto (HER-01 CONFORME, con evidencia en
el informe §3). El punto 2 es *«MCA hasta N2, si no está»*, y no está: está en N0.

MCS no entra en el plan porque todavía no se sabe qué le falta. Auditarlo hoy costaría de 2
a 4 horas para producir hallazgos que este entorno no puede comprobar: sin comandos de
verificación declarados, cualquier cobertura o resultado que MCS reporte no significa nada
(`AUDITORIA.md` §1.1).

**La Tanda 1 es una tarde.** Once requisitos, ninguna clase de fallo nueva (MCA-CORE §4.3),
y desbloquea la auditoría de software.

---

## Tanda 1 — MCA de N0 a N2

| # | Acción | Cierra | Esfuerzo | Qué riesgo elimina |
|---|---|---|---|---|
| ~~1~~ | ~~Renombrar `pmoaasconformidad.yaml` → `conformidad.yaml`~~ · **HECHA 2026-08-03** | H-5 | — | — |
| ~~2~~ | ~~Declarar el presupuesto de contexto permanente~~ · **HECHA 2026-08-03** — `max: 40000`. Sigue EXCEDIDO y el máximo es propuesta mía, no tuya | **CTX-02** | — | — |
| ~~3~~ | ~~Declarar y ejecutar los comandos de verificación~~ · **HECHA 2026-08-03** — `CLAUDE.md` §0.3. Tres de cinco ejecutados con salida registrada. **Abrió FLU-01 como PARCIAL:** ver 3b | **CTX-01** | — | — |
| ~~3b~~ | ~~Arreglar los 4 tests de render que fallan en Windows~~ · **HECHA 2026-08-03** — no se marcaron `heavy` (habría perdido cobertura en PR): se corrigió la causa raíz en `tests/conftest.py`. **778 passed · 1 skipped · exit 0** | **FLU-01** | — | — |
| ~~4~~ | ~~Comprobación en CI del presupuesto y del largo de `SPRINT.md`~~ · **HECHA 2026-08-03** — `scripts/check_contexto.py` + job `contexto-permanente`. Probado en ambos sentidos. **Techos como trinquete**, no como objetivo: ver nota abajo | **CTX-05**, **FLU-03**, H-3 | — | — |
| ~~5~~ | ~~Ejecutar `/handoff` y bajar `SPRINT.md` a ≤250 líneas~~ · **HECHA 2026-08-03** — **521 → 219 líneas**, por debajo del objetivo. Lo cerrado se archivó íntegro en `SPRINT-DONE-HISTORY.md` (749 → 1.092 líneas). Contexto permanente **87.623 → 68.055 (−22,3 %)**. Techos apretados detrás | H-2, alimenta CTX-03 | — | — |
| ~~6~~ | ~~Mover procedimientos de `CLAUDE.md` a skills invocables~~ · **HECHA 2026-08-03** — 4 skills nuevas (`triage`, `cerrar-item`, `delegar`, `resumen-ronda`) + §6 incorporada a `handoff`. `CLAUDE.md` **36.506 → 16.853 (−54 %)**. Contexto **68.055 → 49.944** | **CAP-01**, **CTX-04** | — | — |
| ~~7~~ | ~~Sacar el contador «Próximo libre» del contexto permanente~~ · **HECHA 2026-08-03** — `scripts/proximo_id.py`. **No se derivó de `gh issue list` como decía el plan**: GitHub va por US-170 cuando el máximo real es US-193, porque muchos batches se ejecutaron sin crear issues. Une GitHub + `git log` + docs | **CTX-03** | — | — |
| ~~8~~ | ~~Declarar qué acciones exigen confirmación humana~~ · **HECHA 2026-08-03, pero AUT-01 queda PARCIAL** — no se declaró: se *implementó* con `.claude/settings.json` + hook `PreToolUse` (`scripts/guard_irreversible.py`), probado en 15 casos. **Parcial porque no se pudo demostrar que dispare**: el vigilante de configuración no toma un settings creado a mitad de sesión | AUT-01 (parcial) | — | Ver 8b |
| **8b** | Abrir `/hooks` o reiniciar sesión, y reconfirmar que el guard intercepta. Es acción del owner: no puedo abrir `/hooks` yo | **AUT-01** | 2 min | Que el control exista y no se ejecute — MCA-CORE §6.1 |
| ~~9~~ | ~~Reejecutar `MCA-P02` y registrar el nivel alcanzado~~ · **HECHA 2026-08-03** — [informe de seguimiento](2026-08-03-mca-seguimiento.md). **11/11 evaluados: 9 CONFORME, AUT-01 PARCIAL, CTX-03 NO CONFORME.** Nivel: **sigue N0** | — | — | — |

**Lo que bajó el contexto permanente:** acciones **5, 6 y 7**. Resultado real: de 87.623 a
~50.400 caracteres (−43 %), sin perder ninguna capacidad. No se llegó a los 40.000 estimados:
ver `conformidad.yaml` → `distancia_al_objetivo`.

### Nota sobre los techos de la acción 4

Los techos que CI hace cumplir **no son el objetivo**: son el valor actual más 1 % de
tolerancia, y viven en `conformidad.yaml` con su `historial`. El control falla si el
contexto **crece**, que es el riesgo real; no bloquea por el estado heredado.

Poner el objetivo (40.000) como techo habría dejado el CI en rojo en cada PR, y un control
que bloquea todo se desactiva en dos días.

**Cada vez que una acción baje el contexto hay que bajar el techo detrás.** Se apretó tres
veces (88.500 → 68.500 → 50.400) y el control frenó cuatro intentos míos de engordar el
contexto. Un trinquete que no se aprieta es un número decorativo.

### Medición: caracteres, no bytes

Las cifras de la auditoría (88.180 → 91.501) se tomaron con `wc -c`, que cuenta **bytes**;
en UTF-8 cada acento ocupa dos. La medición correcta la produce `scripts/check_contexto.py`
y da **87.623 caracteres**. La conclusión de la auditoría no cambia —el orden de magnitud es
el mismo y el hallazgo era la ausencia de presupuesto, no su valor— pero la cifra que manda
de aquí en adelante es la del script.

---

## Tanda 2 — MCS, después de la Tanda 1

Ejecutar `MCS-P01` contra **N2**, el objetivo de `conformidad.yaml`. Nunca contra N3.

`conformidad.yaml` ya lo argumenta y el argumento es correcto: auditar hoy contra N3 un
producto sin usuarios externos devuelve decenas de no conformidades reales e irrelevantes,
y consume la capacidad que hace falta para publicarlo.

Estimación: 2–4 h. Ya no está bloqueada por falta de comandos de verificación: existen,
corren y dan exit 0. Arranca cuando MCA llegue a N2 (acción 11).

---

## Tanda 3 — Dominio PMO (frente nuevo, 2026-08-03)

Fuera del alcance de MCA/MCC/MCS: ninguno de los tres marcos audita si la **semántica de
gestión de proyectos** del producto es correcta. Abierto a pedido del owner.

Diagnóstico entregado en `docs/dominio/`:

| Documento | Qué es |
|---|---|
| `00-RUNDOWN-estandares.md` | Mapa de PMI, ISO, AXELOS e IPMA. **Para revisar, no compromete a nada** |
| `01-DIAGNOSTICO.md` | Brecha medida entre el producto y el núcleo del dominio |
| `02-GLOSARIO.md` | Glosario canónico. **Borrador: nada adoptado hasta aprobación** |

**Hallazgo principal:** la brecha no es de cobertura sino de definición. El producto ya
modela RAID, acta de constitución, interesados, control de cambios, programas y EDT. Lo que
falta es que cada concepto tenga un término único y una regla de cálculo.

| # | Acción | Cierra | Esfuerzo | Estado |
|---|---|---|---|---|
| D-1 | Owner revisa `02-GLOSARIO.md` término por término | — | 1–2 h | **Bloqueante del resto** |
| D-2 | Decidir umbral de RAG (§2.4) y método de avance (§2.3) | B-3, B-5 | Criterio de negocio | Pendiente |
| D-3 | Unificar las dos paletas de salud en una definición | B-3 | 1 h | Pendiente |
| D-4 | Migrar `phase` a las cinco fases del ciclo de vida; retirar `support` | B-2 | 4–6 h | Pendiente |
| D-5 | Normalizar `yellow` → `amber` y retirar literales en español del código | B-2, B-3 | 2 h | Pendiente |
| D-6 | Introducir línea base | B-1 | 1–2 días | Pendiente |
| D-7 | Decidir: EVM completo o calidad de cronograma DCMA 14-point | B-4 | Decisión | Pendiente |

**El plan de remediación detallado no se escribe hasta que D-1 esté hecha.** Planificar
sobre vocabulario que todavía puede cambiar es trabajo que se tira.

**Recomendación sobre D-7:** calidad de cronograma, no EVM. DCMA 14-point se alimenta de
`task_dependencies`, `predecessors`, `successors` e `is_critical`, que ya existen por el
importador de MS Project. EVM exige antes línea base **y** costo por tarea, que no existe.
Más barato y más diferenciador.

---

## Puerta de lanzamiento — sin cambios

`conformidad.yaml` la declara y sigue **NO EVALUADA**. Exige MCA N2 + MCS N3, más
aislamiento entre usuarios con prueba automatizada, modelado de amenazas hecho, plan de
respuesta ante incidente y restauración probada.

Se evalúa **antes** de abrir el registro público. Hoy, con MCA en N0, la puerta está a dos
niveles de distancia en un marco y sin medir en el otro.

---

## Nota sobre MCC

No aplica y está correctamente declarado, con razón y con disparador de revisión
(*«aparece un cliente que financie o condicione el desarrollo»*). No es un hallazgo
negativo: `AUDITORIA.md` §1.3 exige declararlo, y declararlo es el requisito.
