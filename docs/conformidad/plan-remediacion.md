# Plan de remediación de conformidad — MCS

| Campo | Valor |
|---|---|
| Fecha | 2026-08-05 |
| Objetivo declarado | **N2** (`conformidad.yaml`) |
| Nivel hoy | **N0** |
| Distancia a N1 | **44 requisitos** — ver la verificación contra `MCS-CORE` |
| Distancia a N2 | **95 requisitos** (todo lo abierto) |
| Base | Registro reconciliado de los cuatro informes fechados |

---

## Cómo se construyó, y qué le falta

**`MCS-CORE` llegó al repositorio el 2026-08-05** y vive en
`marco/MCS-CORE.md`. Este plan se construyó **sin él**, reconstruyendo el
registro desde los informes fechados; al llegar el marco se verificaron las dos
primeras olas y **tres de seis cierres no se sostuvieron**
([verificación](2026-08-05-verificacion-con-marco.md)). El resto del plan sigue
en pie: lo que cambió son estados, no el orden del trabajo.

Reconcilia. La tabla detallada del 2026-08-03 trae 117 filas con
`ID · Estado · Evidencia · Gravedad`; el cuadro por dominio cuadra en 126 sobre
17 dominios; el §5 enumera los bloqueantes de N1 uno a uno; y los informes del
08-04, R1 y la remediación del 08-05 aportan los cambios de estado. Aplicados
todos, salen **126 requisitos, 31 cerrados, 95 abiertos, 45 bloqueando N1** —
contra los «50» del ledger, diferencia explicada por lo cerrado el 2026-08-05.

**Lo único que la reconstrucción no da es el criterio de aceptación por
requisito.** Se tiene el hueco medido («77 puntos», «73 de 75 pantallas»), no la
vara con la que el marco lo da por cerrado. Consecuencia práctica: para los
requisitos mecánicos el hueco **es** la vara y no hay ambigüedad; para los de
juicio —CON, REQ, DOC— habrá que declarar el criterio al cerrarlos y aceptar que
una reauditoría con el catálogo en mano podría discrepar. Se prefiere avanzar
declarando el criterio a esperar el documento.

**Nivel por requisito:** conocido para 53 (los enumerados en §5 más los 13 con
columna de nivel en el seguimiento). Los otros 73 se tratan como N2, que es la
lectura conservadora: si alguno resultara ser N1, aparece al reauditar y suma a
la ola correspondiente, no invalida el plan.

---

## La regla que ordena todo esto

**Remedir antes de construir.** El expediente ya tiene cuatro errores de
recuento documentados, y esta misma sesión encontró un quinto: `OPS-02` figuraba
como «el requisito más barato que queda, solo falta la variable de entorno», y
la variable era necesaria pero no suficiente — el worker no reportaba nada
porque su proceso nunca importaba el módulo que inicializaba la captura.

El patrón se repite en la otra dirección: **el trabajo de producto de esta
sesión cerró bloqueantes de N1 sin que nadie los remidiera.** `ARQ-02` y
`GOB-02` decían «cero ADR reales en `docs/adr/`»; hoy hay **24**. `LEN-01` decía
«el glosario declara borrador, nada adoptado»; hoy está aprobado y completo.

Por eso la Ola 0 no construye nada.

---

## Ola 0 — ✅ Hecha el 2026-08-05

**Resultado: de 45 a 41 bloqueantes de N1**, sin escribir una línea de producto.
Informe: [`2026-08-05-ola0-recuento.md`](2026-08-05-ola0-recuento.md).

Cerraron `ARQ-02`, `GOB-02`, `LEN-01` y `DAT-05` — los cuatro estaban cerrados
desde hacía horas o días y el registro no se había enterado. `DAT-06` y `DIS-01`
siguen abiertos pero **acotados**, y `DAT-06` trajo una sorpresa que justifica
sola la ola: parecía un `sed` sobre cuatro literales y esconde un **cambio de
contrato** (`amber_max` es una llave guardada en `tenant.settings`).

De los seis nunca medidos, cuatro quedaron medidos y **dos no se pudieron
medir**: `DAT-08` y `DAT-16` llegan sin evidencia escrita, así que sin el
catálogo no se sabe qué preguntarles. Se dejan declarados sin medir en vez de
suponerles un estado — suponerlo es lo que produjo los cinco errores de recuento
del expediente.

<details>
<summary>El planteo original de la ola</summary>

### Lo que se midió

Dos grupos, y ninguno es trabajo de construcción:

**a) Los que nuestro propio trabajo pudo cerrar.** Se miden contra el código de
hoy, no contra la evidencia de hace tres días:

| ID | Lo que decía la auditoría | Lo que hay hoy |
|---|---|---|
| `ARQ-02`, `GOB-02` | «cero ADR reales» | 24 ADR (`ADR-001`…`ADR-023`) |
| `LEN-01` | «glosario borrador, nada adoptado» | Aprobado y completo, nueve decisiones ejecutadas |
| `DAT-05`, `DAT-06` | «dos paletas de salud, dos vocabularios de fase», «`yellow`/`amber`», «`support`» | D-1, D-2, D-7 y ADR-023 ejecutadas |
| `OPS-02` | «sin Sentry» | Cableado en los dos procesos; falta confirmar en Railway |
| `DIS-01` | «25 literales `#rrggbb`, dos paletas divergentes» | Las paletas divergentes ya no están; **siguen 25 literales** — no cierra, queda acotado |

**b) Los seis que nunca se midieron.** `CON-04`, `DAT-08`, `DAT-16`, `DES-04`,
`DIS-05`, `DIS-06`. Es medición, no construcción, y hay precedente de que vale
la pena: `IA-05` estaba sin medir, se midió, y el modelo **sí** calculaba cifras
que iban a informes ejecutivos.

**Salida de la ola:** la cifra de distancia a N1 deja de ser una estimación.

---

</details>

---

## Ola 1 — ✅ Cerrada entera el 2026-08-05

`CFG-03` y `INT-03` eran **el mismo hecho**: `main` no estaba protegida. El
owner la protegió: 8 verificaciones exigidas en modo `strict`, sin `force-push`
ni borrado de rama. Los dos cierran, y con ellos **la distancia a N1 baja de 47
a 45**.

**Residual aceptado por el owner (2026-08-05):** `enforce_admins` se queda en
`false`. Un administrador —hoy, el único que trabaja en el repo— puede saltarse
las dos cosas. Se decidió a sabiendas: con un solo desarrollador, la salida de
emergencia vale más que el trinquete, y el control sigue cumpliendo su función
principal, que es proteger del mal día y no de la voluntad.

**No es un pendiente, es una decisión** — y por eso se escribe. Se revisa cuando
entre alguien más al repositorio, que es el momento en que «administrador» deja
de significar «el owner».

**El hueco de `contraste-wcag` quedó tapado el 2026-08-05.** La lista de
exigidos tenía ocho de los diez trabajos reales del CI, y el que faltaba era el
gate de `DIS-02` —cerrado esta misma sesión—, así que una regresión de contraste
podía integrarse: el control existía, corría, y no bloqueaba. Ahora son nueve.

(`api-tests-heavy` queda fuera con razón y no por olvido: solo corre en push a
`main`, nunca en un PR, y exigirlo bloquearía todas las integraciones.)

    gh api -X PATCH repos/xguilxr/pmo_aas/branches/main/protection/required_status_checks \
      -f 'contexts[]=contexto-permanente' -f 'contexts[]=seguridad' \
      -f 'contexts[]=lint' -f 'contexts[]=api-tests-smoke' \
      -f 'contexts[]=evaluacion-ia' -f 'contexts[]=api-migrations-postgres' \
      -f 'contexts[]=web-typecheck' -f 'contexts[]=web-build' \
      -f 'contexts[]=contraste-wcag'

---

## Ola 2 — Mecánicos, y se pueden disparar solos

Tienen el hueco medido y verificable por prueba: el criterio es el conteo. No
necesitan decisión, así que se pueden lanzar sin supervisión, uno por commit.

| ID | Trabajo | Tamaño medido |
|---|---|---|
| `DAT-12` | Distinguir «sin dato» de cero | 77 puntos |
| `DIS-03` | Cinco estados por pantalla | 73 de 75 pantallas |
| `DIS-01` | Literales de color a tokens | 25 literales |
| `DAT-04` | Conversión de unidades solo en fronteras | 6 sitios |
| `DAT-02` | Unidad en el nombre del campo | `budget` y los que aparezcan |
| `OPS-01` | `structlog` está declarado y no se importa en ningún sitio | Cablearlo |
| `DEV-04` | Sin verificación de tipos en Python | Añadir `mypy` al gate |
| `CFG-04` | Sin `commitlint` ni hook | 37 de 40 commits ya cumplen |
| `SEG-05` | No existe `SECURITY.md` | Un archivo |
| `DOC-01` | 0 de 64 documentos declaran responsable, estado y revisión | 64 encabezados |
| `DOC-03` | El ER se mantiene a mano pudiendo generarse | Un generador |
| `LEN-02` | 152 de 159 mensajes dicen solo qué pasó | Ya es norma; se aplica al tocar cada endpoint |
| `DAT-11` | Cada número indica periodo y actualización | Transversal — medir primero |
| `DAT-06` | Retirar `amber`: 3 sitios mecánicos (motor de informes, plantilla, CSS) | **El cuarto no entra aquí** — ver Ola 3 |

**Cómo dispararlos:** uno por commit, con prueba propia y verificación por
mutación, igual que todo lo de esta sesión. `DAT-11` y `DIS-03` conviene
acotarlos con una medición previa antes de lanzarlos enteros.

---

## Ola 3 — Necesitan una decisión tuya antes de tocar código

No son caros por volumen sino porque **fijan una postura del producto**, y esa
no la puede tomar quien implementa:

| ID | La decisión que hace falta |
|---|---|
| `CON-01`, `CON-03`, `CON-05` | Hasta dónde llega la competencia del producto en materia de gestión de proyectos, qué fuente normativa se declara, y a quién se deriva lo que queda fuera |
| `REQ-02` | Qué escenarios de calidad tienen medida numérica (hoy: ninguno) |
| `REQ-03` | Inventario de datos personales — qué guarda el producto y con qué base |
| `DAT-01`, `DAT-10` | Unidades canónicas y fichas de indicador: qué métricas se declaran y quién las firma |
| `SEG-02` | Si los secretos siguen en variables de Railway o se adopta un almacén |
| `DAT-06` (parte) | `task_load_thresholds.amber_max` es una **llave guardada en `tenant.settings`**: renombrarla es cambio de contrato sobre datos existentes y necesita ventana de compatibilidad, como `wbs` |
| `DEV-02`, `DEV-03` | Estrategia de pruebas: Postgres en la suite, pruebas de frontend (hoy **cero**), extremo a extremo |
| `SUM-01` | Si la canalización produce un artefacto en vez de que Railway construya desde la rama |
| `INF-02`, `INF-03`, `DES-02` | Paridad de entornos, copias de seguridad declaradas y probadas, y procedimiento de reversión |

**`SEG-04` es aparte y merece atención:** CRÍTICA, N1, y el hueco es
autorización verificada en el punto de acceso y no sobre el objeto. Es trabajo
real de seguridad, no una declaración.

---

## Ola 4 — De N1 a N2

Los 50 restantes. **No se planifican todavía**, y es deliberado: el propio
expediente estima **3–4 semanas persona a N1 y 8–12 a N2**, y planificar la
segunda mitad sobre estados que la primera va a mover repite el error que este
plan existe para no repetir. Se replanifica al alcanzar N1, con el registro ya
remedido.

---

## Registro completo — los 97 abiertos

`⚠` marca los que **nunca se midieron**: su estado es una ausencia de dato, no
un diagnóstico.

| ID | Nivel | Estado | Gravedad | El hueco, como lo dejó medido la auditoría |
|---|---|---|---|---|
| `GOB-02` | **N1** | PARCIAL | MEDIA | `docs/epics/DECISIONS.md` tiene 25 entradas `DEC-`, pero `docs/adr/` solo contiene `README.md`: cero ADR reales. Las exclusiones de requisitos no e… |
| `GOB-03` | ? | PARCIAL | BAJA | `conformidad.yaml` fija `proxima_evaluacion: 2026-11-03`. Es la primera revisión; no hay serie |
| `CFG-01` | **N1** | PARCIAL | MEDIA | Código, migraciones, `railway.json`/`railway.toml`, prompts, docs y bloqueos están versionados. Falta glosario adoptado y fichas de métrica |
| `CFG-03` | **N1** | NO CONFORME | CRÍTICA | `gh api repos/xguilxr/pmo_aas/branches/main/protection` → 404 «Branch not protected». `CLAUDE.md` §8 dice «main no se pushea directo»: es prosa sin… |
| `CFG-04` | **N1** | PARCIAL | BAJA | 37 de los últimos 40 commits siguen Conventional Commits. Sin `commitlint` ni hook que lo imponga |
| `CFG-06` | **N1** | PARCIAL | BAJA | `package.json` declara `0.1.0`. No hay etiquetas ni releases que evidencien disciplina SemVer |
| `CFG-07` | ? | NO CONFORME | ALTA | Sin etiquetas inmutables. Railway despliega desde rama |
| `CFG-08` | ? | NO CONFORME | MEDIA | No existe `CHANGELOG.md` |
| `CFG-09` | ? | NO CONFORME | MEDIA | PR #570 abierto desde 2026-07-09; `claude/plan-import-wbs-fixes-nwotng` sin PR desde 2026-07-18. Ramas de semanas, no de dos días |
| `CFG-10` | ? | PARCIAL | ALTA | La interfaz está versionada en la ruta (`app/api/v1/`). Sin política documentada de compatibilidad ni de retirada |
| `CFG-11` | ? | PARCIAL | MEDIA | El job `api-migrations-postgres` ejecuta `upgrade → downgrade → upgrade`: la reversibilidad sí se verifica. No hay evidencia del patrón de expansió… |
| `CFG-13` | ? | NO CONFORME | ALTA | No existen fichas de métrica |
| `CFG-14` | ? | PARCIAL | MEDIA | `apps/web/app/globals.css` centraliza tokens, pero hay 25 literales hexadecimales en componentes |
| `REQ-01` | **N1** | PARCIAL | MEDIA | La plantilla de issue exige «Criterios de aceptación». Pero varios batches se ejecutaron por chat sin crear issues («0.1 solucionar > documentar»),… |
| `REQ-02` | **N1** | NO CONFORME | MEDIA | No se encontró ningún escenario de calidad con medida de respuesta numérica |
| `REQ-03` | **N1** | PARCIAL | ALTA | `docs/architecture/security-multitenant.md` menciona datos personales. No hay inventario dedicado |
| `REQ-04` | ? | PARCIAL | MEDIA | Los nombres de test referencian IDs (`test_us191_…`), lo que da trazabilidad de hecho. No hay trazado formal AC → prueba |
| `ARQ-02` | **N1** | PARCIAL | MEDIA | 25 decisiones en `DECISIONS.md`; ningún ADR en `docs/adr/` |
| `ARQ-04` | **N1** | PARCIAL | MEDIA | Configuración en entorno (`.env.example`, Railway) ✓. Registros a salida estándar: no — ver OPS-01 |
| `ARQ-05` | ? | NO CONFORME | MEDIA | Sin escenarios de calidad (REQ-02), no hay nada que respaldar |
| `ARQ-06` | ? | NO CONFORME | MEDIA | `DECISIONS.md` registra la decisión adoptada, no las descartadas |
| `DIS-01` | **N1** | NO CONFORME | ALTA | 25 literales `#rrggbb` en `apps/web/components` y `apps/web/app`. Incluye las dos paletas divergentes de salud (`HEALTH_DONUT_COLOR` verde `#1F8A5B… |
| `DIS-03` | **N1** | NO CONFORME | — | No se auditaron los estados de pantalla |
| `DIS-04` | **N1** | PARCIAL | MEDIA | `change_approval` y los borrados de RAID confirman. No se verificó cobertura completa |
| `DIS-05` | ? | NO VERIFICABLE ⚠ | — | Sin pruebas de teclado |
| `DIS-06` | ? | NO VERIFICABLE ⚠ | — | Sin auditoría de patrones WAI-ARIA |
| `DIS-07` | ? | NO CONFORME | ALTA | Cero verificación de accesibilidad en CI |
| `LEN-01` | **N1** | PARCIAL | ALTA | `docs/dominio/02-GLOSARIO.md` existe pero declara explícitamente «borrador, nada adoptado». `docs/archive/initial-epics-es/glossary.md` está archivado |
| `LEN-02` | **N1** | PARCIAL | — | No se auditaron los mensajes de error |
| `LEN-03` | **N1** | NO CONFORME | MEDIA | No existe guía de estilo |
| `LEN-04` | ? | NO CONFORME | MEDIA | Sin verificación automática de terminología |
| `DAT-01` | **N1** | NO CONFORME | ALTA | Sin unidades canónicas: el glosario es borrador |
| `DAT-02` | **N1** | PARCIAL | MEDIA | `duration_days`, `allocation_pct`, `progress` llevan unidad en el nombre. `budget` no |
| `DAT-04` | **N1** | NO CONFORME | — | — |
| `DAT-05` | **N1** | NO CONFORME | ALTA | Dos paletas de salud y dos vocabularios de fase conviviendo. Ver `docs/dominio/01-DIAGNOSTICO.md` B-2 y B-3 |
| `DAT-06` | **N1** | NO CONFORME | ALTA | `yellow`/`amber`/`Amarillo` para el mismo valor; `support` como fase inexistente |
| `DAT-07` | ? | NO CONFORME | MEDIA | Sin tipos propios para magnitudes |
| `DAT-08` | ? | NO VERIFICABLE ⚠ | — | — |
| `DAT-09` | **N1** | PARCIAL | MEDIA | La salud se calcula en `services/project_health.py`, una sola vez ✓. Otros indicadores no auditados |
| `DAT-10` | **N1** | NO CONFORME | indicador\ | Cero fichas de indicador. Búsqueda en `docs/` de `metric\ |
| `DAT-11` | **N1** | NO CONFORME | — | — |
| `DAT-12` | **N1** | NO CONFORME | — | — |
| `DAT-13` | ? | NO CONFORME | ALTA | Sin pruebas de reconciliación |
| `DAT-14` | ? | NO CONFORME | ALTA | Sin pruebas de estructura, frescura ni volumen |
| `DAT-15` | ? | NO CONFORME | MEDIA | Los números no ofrecen acceso a su definición |
| `DAT-16` | ? | NO VERIFICABLE ⚠ | — | — |
| `DEV-02` | **N1** | PARCIAL | MEDIA | Las pruebas usan SQLite en memoria (`tests/conftest.py`): rápido, pero la lógica de dominio sí necesita base de datos |
| `DEV-03` | **N1** | PARCIAL | ALTA | 132 archivos de prueba en `apps/api` (unitarias + integración). Cero pruebas en `apps/web`. Cero extremo a extremo |
| `DEV-04` | **N1** | PARCIAL | ALTA | `ruff` con `E,F,I,N,UP,B,A,C4,RUF` y `tsc --noEmit` ✓. Sin verificación de tipos en Python (no hay mypy ni pyright) |
| `DEV-05` | ? | NO CONFORME | ALTA | `pytest-cov` instalado, pero ningún umbral de cobertura en CI ni declarado |
| `DEV-06` | ? | PARCIAL | MEDIA | Muchos AC están cubiertos, pero sin trazado formal |
| `INT-03` | **N1** | PARCIAL | CRÍTICA | El CI falla ante error, pero `main` no está protegida: nada impide integrar con verificaciones en rojo |
| `INT-04` | ? | NO CONFORME | MEDIA | `api-tests-smoke` tarda ~13 minutos por sí solo |
| `INT-05` | ? | NO CONFORME | ALTA | No hay hallazgos de seguridad que puedan bloquear: no se generan |
| `INT-06` | ? | NO CONFORME | ALTA | Sin actualización automatizada de dependencias |
| `SUM-01` | **N1** | NO CONFORME | ALTA | Railway construye desde la rama; no hay artefacto producido por la canalización |
| `SUM-03` | ? | NO CONFORME | MEDIA | Sin inventario de componentes (SBOM) |
| `SUM-04` | ? | NO CONFORME | ALTA | Sin análisis de vulnerabilidades de imagen |
| `INF-02` | **N1** | PARCIAL | ALTA | Existe desarrollo local y producción en Railway. Paridad de versiones de datos no verificada; el CI usa Postgres 15, y la versión de producción no … |
| `INF-03` | **N1** | NO VERIFICABLE | ALTA | Railway ofrece copias, pero no hay documento que lo declare ni evidencia de configuración. Las menciones de «backup» en `docs/runbooks/` son de cla… |
| `INF-04` | ? | NO CONFORME | ALTA | Sin entorno de preproducción |
| `INF-05` | ? | NO CONFORME | CRÍTICA | La restauración nunca se ha probado. La puerta de lanzamiento de `conformidad.yaml` ya lo identifica como pendiente |
| `INF-06` | ? | NO CONFORME | ALTA | Sin objetivos de punto ni de tiempo de recuperación |
| `DES-02` | **N1** | PARCIAL | ALTA | `docs/runbooks/ai/groq-setup.md` §7 documenta reversión del proveedor de IA. No hay procedimiento de reversión de la aplicación |
| `DES-04` | ? | NO VERIFICABLE ⚠ | MEDIA | Sin medición de tiempo de reversión |
| `DES-05` | ? | PARCIAL | MEDIA | Las migraciones se ejecutan a mano (`alembic upgrade head` figura como acción del owner en `HANDOFF.md`), luego sí están separadas del código — per… |
| `DES-06` | ? | NO CONFORME | BAJA | Sin métricas de rendimiento de entrega |
| `OPS-01` | **N1** | NO CONFORME | ALTA | `structlog==24.4.0` está en `requirements.txt` pero no se importa en ningún archivo de `apps/api/app/`. Dependencia declarada y sin usar |
| `OPS-02` | **N1** | PARCIAL | CRÍTICA | Sin Sentry ni equivalente. Un error en producción no notifica a nadie |
| `OPS-04` | ? | NO CONFORME | MEDIA | Sin instrumentación OpenTelemetry |
| `OPS-05` | ? | NO CONFORME | ALTA | Sin objetivos de nivel de servicio |
| `OPS-06` | ? | NO CONFORME | ALTA | Sin alertas |
| `OPS-07` | ? | NO CONFORME | MEDIA | Sin identificador de petición propagado |
| `SEG-01` | **N1** | NO VERIFICABLE | ALTA | Sin evaluación ASVS |
| `SEG-02` | **N1** | PARCIAL | ALTA | `.gitignore` cubre `.env`; los secretos viven en variables de Railway. No hay almacén dedicado ni verificación automática |
| `SEG-04` | **N1** | PARCIAL | CRÍTICA | `core/permissions.py` resuelve capacidades por rol (`capabilities_for(role_type)`); `core/visibility.py` y `services/area_visibility.py` acotan alc… |
| `SEG-05` | **N1** | NO CONFORME | MEDIA | No existe `SECURITY.md` |
| `IA-02` | **N1** | PARCIAL | MEDIA | Existe `models/ai.py` con `ai_jobs`. No se verificó que la acción sea distinguible de una humana en el registro de auditoría |
| `IA-06` | ? | NO CONFORME | MEDIA | Sin rúbrica de autonomía ni ADR |
| `IA-10` | ? | NO CONFORME | ALTA | Sin confirmación humana para acciones de IA con efecto |
| `DOC-01` | **N1** | NO CONFORME | MEDIA | 0 de 64 documentos de `docs/` declaran responsable, estado o fecha de revisión |
| `DOC-02` | **N1** | NO CONFORME | MEDIA | Sin esquema de tipos documentales |
| `DOC-03` | **N1** | PARCIAL | MEDIA | El ER de `database.md` se mantiene a mano pudiendo generarse del modelo |
| `DOC-04` | ? | NO CONFORME | MEDIA | Sin declaración de dependencias documentales |
| `DOC-05` | ? | NO CONFORME | BAJA | Sin índice de dependencias |
| `DOC-06` | ? | PARCIAL | MEDIA | `CLAUDE.md` §0.2 exige actualizar la epic en el mismo bloque, y el DoD lo incluye. Es instrucción, no control: nada lo verifica en CI |
| `DOC-07` | ? | NO CONFORME | MEDIA | Sin ventana de revisión ni señalización |
| `CON-01` | **N1** | NO CONFORME | ALTA | Sin declaración de alcance de materia ni frontera de competencia |
| `CON-02` | **N1** | PARCIAL | PRINCE2\ | Los 10 chequeos de calidad del plan están en código, no en un prompt: bien. Pero cero anclaje a estándar — búsqueda de `PMBOK\ |
| `CON-03` | **N1** | NO CONFORME | ALTA | Ninguna afirmación normativa declara fuente ni vigencia |
| `CON-04` | ? | NO VERIFICABLE ⚠ | — | — |
| `CON-05` | **N1** | NO CONFORME | MEDIA | Sin derivación a persona cualificada |
| `CON-06` | ? | NO CONFORME | MEDIA | Sin responsable ni periodicidad por elemento |
| `CON-07` | ? | NO CONFORME | MEDIA | Sin jerarquía de autoridad |
| `CON-08` | ? | NO CONFORME | ALTA | Sin conjunto de evaluación del dominio |
| `CON-09` | ? | NO CONFORME | MEDIA | Sin periodo de vigencia |
| `CON-10` | ? | NO CONFORME | ALTA | La regla que deriva la salud del proyecto no está declarada como rúbrica: `health_status` es un campo almacenado con `health_source` y `health_reas… |

---

## Qué NO cubre este plan

- **El criterio de aceptación por requisito.** Ver arriba: se declara al cerrar.
- **Los 73 requisitos de nivel desconocido**, tratados como N2 por prudencia.
- **La puerta de lanzamiento**, que exige MCS N3 y sigue NO EVALUADA.
