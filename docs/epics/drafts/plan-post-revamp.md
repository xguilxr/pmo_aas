---
tipo: gestion
responsable: propietario
estado: borrador
revisado: 2026-08-27
revisar_cada: 30d
---

# Plan post-revamp — backend pendiente, operación eficiente y generación de documentos

> Plan de trabajo derivado del revamp de diseño v2 (2026-08-27, branch
> `claude/platform-design-revamp-y8rpqw`) y de las instrucciones del owner:
> (1) terminar el backend que el diseño dejó marcado «pendiente», (2) montar
> las skills y tools para operar la plataforma con modelos pequeños a bajo
> costo sin sacrificar calidad, y (3) preparar la fase de generación de
> reportes HTML y minutas a partir de especificaciones.
>
> **Los IDs de US son propuestos** — se confirman con
> `scripts/proximo_id.py` contra `origin/main` al crear cada issue
> (MCA CTX-03). Punto de partida al escribir esto: US-227 / ENH-203.

> **Especificaciones ejecutables** (2026-08-27, segunda pasada): el detalle
> por US —endpoints, DDL, migraciones, archivos reales, ACs y guía de la
> ronda— vive en tres documentos hermanos:
> `plan-post-revamp-especificaciones.md` (R1–R4),
> `plan-post-revamp-operacion.md` (bloque O: CLI `pmo` + skills) y
> `plan-post-revamp-generacion.md` (bloque G: schemas de report-spec y
> minuta + renderer). Este documento queda como el índice y el porqué.

## Norte

1. Que ninguna cifra de la UI diga «pendiente de backend»: todo lo que el
   diseño muestra existe o se retira.
2. Que un modelo pequeño (Haiku) pueda operar la plataforma —consultar,
   crear, reportar— con scripts deterministas y skills auto-contenidas, sin
   exploración de código ni contexto grande.
3. Que reportes HTML y minutas se generen desde una especificación con un
   renderer determinista: el modelo solo produce JSON estructurado y
   validado; el layout nunca se re-genera.

## Orden de ejecución sugerido

```
R1 (observabilidad superadmin)  →  R2 (monetización — DEC-034, desbloqueado)
O  (operación eficiente)        →  G  (reportes HTML + minutas)
R3 (dark theme) y R4 (deuda visual) — cuando quepan, sin dependencias
```

R1 y O pueden correr en paralelo (lanes sin migraciones compartidas). G
depende de O (usa sus tools). R2 quedó desbloqueado el 2026-08-27:
**DEC-034** (facturación manual primero; Stripe después sobre el mismo
modelo). Adiciones del mismo día en `-especificaciones.md`: **US-239**
(clave de proyecto estilo Jira en la URL, migración 0120) y el bloque
**QA-iPad** (BUG-093+ reservados; gate: la lista de bugs visuales que el
owner está levantando en iPad/PC).

---

## Bloque R1 — Plataforma observable (superadmin con datos reales)

Cierra los ítems #1, #3, #6, #7, #8, #9 del backlog de la especificación de
revamp más los tres «ya reales, solo falta exponerlos». Pantallas: 6a, 6e,
6f, 1b. Todo endpoint nuevo pasa antes por `modelo-amenazas.md` (son rutas
superadmin: autenticadas, sin destino externo — impacto bajo, pero se
declara).

| US | Qué | Tamaño | Detalle |
|---|---|---|---|
| US-227 | **Versión y última migración** vía `GET /api/v1/superadmin/version` | S | Ya viven en README/CI; exponer versión desplegada (env/build arg) + `alembic_version` leída de la DB. Sin migración. UI: KPIs de 6f dejan `SIN_DATO`. |
| US-228 | **Instrumentación de colas Celery** | M | Endpoint que lee del broker (Redis) profundidad de cola y jobs fallidos por nombre (`notifications`, `ai`, `scheduled_reports`), con ventana 24h para fallidos (persistir resultado de tarea o usar backend de resultados). Alimenta 1b (tendencias), 6a y 6f. El health card «Worker: sin instrumentar» pasa a real. |
| US-229 | **Cuentas bloqueadas a nivel plataforma** | S–M | Listado cross-tenant de `failed_login_attempts`/`locked_until` (ya en el modelo `User`) + acción de unlock reutilizando la lógica de `admin_users.py`. Llena la tabla de 6e. Sin tabla nueva. |
| US-230 | **Auditoría filtrada por actor** | S | Parámetro `actor`/`is_superadmin` en `getPlatformLogs`; la tabla de 6e deja de rotularse «sin filtro». Sin migración. |
| US-231 | **Intentos fallidos de login agregados** | M | Endpoint que agrega conteos por tenant/usuario/ventana. Decidir fuente: contador vivo en `User` (barato, sin historia) vs registrar cada intento en el audit log y agregar de ahí (historia real). Propuesta: audit log — el evento ya existe o es un insert más en el flujo de login fallido. |
| US-232 | **Sesiones activas de superadmin** | M | Requiere decisión: hoy no hay tabla de sesiones (JWT sin registro). Opciones: (a) tabla `sessions` liviana escrita en login/refresh — habilita además «cerrar sesión remota» a futuro; (b) diferir y retirar el KPI de 6e. Propuesta: (a), es la misma tabla que pedirá cualquier auditoría seria. Migración. |
| US-233 | **Modelo `incidents` + CRUD + banner** | M–L | Tabla (severidad, descripción, inicio/fin, tenants afectados), CRUD superadmin, «Declarar incidente» de 6f se habilita, banner opcional visible en tenants afectados (frontera de confianza: contenido escrito por superadmin renderizado en tenants — texto plano, sin HTML). Migración. |
| US-234 | **Uptime 30d** | M | Job periódico (Celery beat) que persiste el resultado de `getPlatformHealth` en una tabla `health_snapshots`; endpoint de agregación 30 días. El KPI de 6a pasa a real recién con historia acumulada — la UI dice «acumulando desde <fecha>» mientras tanto. Migración. |

DoD del bloque: las marcas «pendiente de backend» de 6a/6e/6f y el health
card del worker desaparecen de la UI en el mismo commit que entrega cada
endpoint (regla §0.2: la pantalla es parte del slice).

## Bloque R2 — Monetización (bloqueado por una decisión)

Ítems #2, #4, #5 del backlog. **Gate: DEC del owner** — ¿billing real
(Stripe u otro) o registro manual del plan por tenant mientras tanto?
Propuesta: manual primero (una tabla, cero integración) y Stripe como fase
aparte; el modelo de datos se diseña para que Stripe solo *escriba* en él.

| US | Qué | Tamaño | Detalle |
|---|---|---|---|
| US-235 | **Plan y estado de facturación por tenant** | M | Tabla `subscriptions` (tenant, plan, estado de pago, próxima renovación, método, notas), endpoint superadmin de lectura/escritura. `admin/plan` (tenant-side, solo lectura) se conecta a la misma fuente. Llena las tarjetas de 6b/6d. Migración. |
| US-236 | **MRR agregado** | S | Suma de `subscriptions` activas → KPI de 6a. Depende de US-235. |
| US-237 | **Feature flags por tenant** | M | Tablas `feature_flags` + `tenant_feature_overrides`, endpoint lectura/escritura, la UI de toggles de 6d (hoy placeholder) se cablea. Definir el primer flag real consumido (p. ej. `ai_assistant`) para que no nazca decorativo. Migración. |

## Bloque R3 — Dark theme completo

Punto 7 del orden de la especificación: mismos tokens, **pasos propios** (no
un volteo del claro — la banda de luminosidad válida es más estrecha sobre
fondo oscuro). El mockup 1a §02b trae la paleta objetivo: canvas
`oklch(16% .006 250)`, superficie 21%, cabecera/riel 26%, filete `#33363C`
con luz `#454850`, acento `oklch(58% 0.15 258)`, semáforo con fondos 30% y
fg ~80%. Una US (M–L): reescribir el bloque `.dark` de `globals.css`
(incluye los tokens de profundidad — la «luz» blanca de `--linea-surco` no
existe en oscuro, se invierte), verificar `check_contraste.py` en los dos
temas y recorrer las 30 pantallas. El chrome oscuro hoy conserva el navy
viejo a propósito (nota en `globals.css`).

## Bloque R4 — Deuda visual menor del revamp (ENH batch)

Desviaciones anotadas por los agentes durante la implementación; ninguna
bloquea. Un solo issue batch o ENHs individuales a criterio del triage:

- `TrendPill` (kpi-card) no tiene tono `warning`: un atraso de plan se
  pintaría rojo (alarma) — por eso 1b quedó sin el icono de tendencia.
- Columna «Programa» en `/pmo/projects` (mockup 1c): requiere el nombre del
  programa resuelto en la fila del API, no solo `program_id`.
- Conteos por estado en las pestañas de Solicitudes (4b): hoy solo se
  conoce el conteo de la pestaña activa; falta un endpoint de counts.
- Zebra striping (`#FCFCFB` en los mockups): decidir si se adopta como
  token o se descarta — hoy unas pantallas lo aproximan con
  `--color-subtle` y otras no lo llevan.
- Iconos sin equivalente Keyline (`sparkles`, `brain`, `lightbulb`,
  `flag`, `send`, `log-out`, `external-link`, `plug`, `crown`, `scale`):
  hoy hay sustitutos razonados (`info`, `star`, `arrow-up-right`, …).
  Decidir si se piden al set upstream o se fijan los sustitutos como
  definitivos en el mapa de la especificación.
- `PreviewPane` del builder quedó en 480px (mockup: 420) para no arriesgar
  su layout interno — ajustar cuando se toque ese componente.
- Chip de plan en tarjeta de tenant (6b): bloqueado por US-235.

---

## Bloque O — Operación eficiente con modelos pequeños

Objetivo: que operar la plataforma (consultar cartera, cargar datos, cerrar
ciclos, generar documentos) cueste una fracción de tokens y pueda correr en
Haiku. La estrategia es una sola: **mover trabajo del modelo al código**.
El modelo decide y redacta; los scripts navegan, autentican, paginan,
validan y formatean.

### O1 — CLI de operación (`tools/pmo/`) — la pieza central

Un CLI Python delgado sobre el API (no sobre la DB), pensado para ser
invocado por un agente:

- `pmo login` (guarda token), `pmo ctx` (tenant/org activos).
- Lecturas: `pmo proyectos [--salud red] [--json]`, `pmo proyecto <folio>`,
  `pmo raid <folio>`, `pmo capacidad`, `pmo cartera` (el resumen ejecutivo
  del dashboard en texto plano).
- Escrituras acotadas: `pmo riesgo nuevo --json <archivo>`,
  `pmo tarea avanzar <id> <pct>`, `pmo importar <xlsx>` (reusa US-216).
- Reglas de diseño que hacen el ahorro real:
  1. **Salida JSON compacta por defecto**, campos mínimos; `--full` para
     todo. Nada de HTML ni tablas anchas hacia el modelo.
  2. **Errores accionables en una línea** («falta X, corré Y») — un error
     críptico quema una ronda entera de contexto en diagnóstico.
  3. **Idempotencia y `--dry-run`** en toda escritura.
  4. Sin estado oculto: todo lo que el comando necesita va en flags o en el
     archivo de contexto (`~/.pmo/ctx.json`).
- Tamaño: M. Sin cambios de API salvo huecos que el propio CLI revele.

### O2 — Skills de operación (`.claude/skills/`)

Skills auto-contenidas (la skill trae TODO lo que la tarea necesita — cero
exploración del repo). Propuestas:

| Skill | Cubre | Sustituye |
|---|---|---|
| `operar` | El contrato del CLI `pmo`: comandos, flags, formato de salida, errores comunes. | Explorar `lib/api/*` o el backend para saber cómo consultar algo. |
| `sembrar-datos` | Alta masiva de demo/arranque: plantillas XLSX de US-216, orden correcto (org → portafolio → programa → proyecto → plan → recursos). | Re-descubrir el flujo de importación cada vez. |
| `reporte-html` | La fase G: especificación → JSON → renderer (ver abajo). | Generar HTML a mano. |
| `minuta` | Transcript → JSON del gold standard → renderer. | Redactar minutas en prosa libre. |

Las skills existentes (`verificar`, `cerrar-item`, …) son de *desarrollo*;
estas son de *operación* — conviven.

### O3 — Política de enrutamiento de modelos

Extender la skill `delegar` con la matriz de operación: qué corre en Haiku
(ejecución de CLI, extracción a esquema, llenado de plantillas), qué pide
Sonnet (síntesis de minuta compleja, redacción ejecutiva) y qué nunca se
delega (decisiones de scope). Regla de presupuesto: una tarea de operación
estándar debe caber en <10k tokens de contexto; si no cabe, falta un tool,
no un modelo más grande.

### O4 — Contratos que protegen el ahorro

- `evaluacion-ia` (MCS IA-07/08/09) cubre también las salidas de O/G: un
  JSON de minuta o reporte mal formado entra al conjunto de evaluación
  antes del fix.
- Test trinquete: el `--help` del CLI y la skill `operar` no divergen (el
  test compara comandos declarados vs documentados).

Tamaño del bloque O: M–L total; O1 primero, O2 detrás (la skill documenta
lo que O1 ya entrega), O3/O4 al cierre.

---

## Bloque G — Generación de reportes HTML y minutas

La fase que el owner anuncia: reportes HTML «con base en ciertas
especificaciones» y minutas, generados eficientemente. Principio de diseño:
**el layout se escribe una vez; cada generación solo aporta datos.**

### G1 — Formato de especificación de reporte

Un YAML/JSON versionado (`report-spec`) que declara: audiencia, secciones
(de un catálogo cerrado: KPI band, semáforo, tabla de proyectos, matriz de
riesgos, narrativa, gantt-resumen…), scope (tenant/org/portafolio/programa/
proyecto), ventana temporal y branding. Es la evolución natural del report
builder (EP020): sus secciones ya son datos; aquí se les da forma textual
versionable que un agente puede escribir y validar con JSON Schema. S–M.

### G2 — Renderer determinista de HTML

Plantillas (Jinja2 en `apps/api`, junto al PDF renderer existente) que
consumen `report-spec` + datos del API y emiten HTML autocontenido con los
tokens del revamp (mismo lenguaje visual que la plataforma: DM Sans,
semáforo, `--relieve-*`; paleta de gráficos ADR-023 con SVG estático).
El modelo **nunca** escribe HTML: escribe la spec y los textos narrativos
(campos `narrativa` del spec). Salida: HTML para compartir y el mismo HTML
al pipeline PDF existente. M–L.

### G3 — Minutas eficientes

El gold standard (`minute-gold-standard.md`, 6 secciones) ya define la
estructura. Falta separar redacción de presentación:

1. **Esquema JSON de minuta** (encabezado, participantes, resumen, temas
   con bullets, RAID unificado, próximos pasos) con JSON Schema estricto.
2. **Extracción con modelo pequeño**: transcript → JSON validado (retry
   sobre el error de schema, no sobre prosa). Los TC de ENH-102/105 se
   vuelven casos del conjunto de evaluación.
3. **Renderer** de minuta: JSON → HTML (mismo sistema de plantillas de G2)
   → guardado como minuta del proyecto por el flujo existente.

Ahorro esperado: el costo por minuta pasa de «modelo grande redactando
formato + contenido» a «modelo pequeño extrayendo a esquema»; el formato es
gratis. M.

### G4 — Cierre

- Los reportes generados quedan en Artefactos del proyecto (EP018).
- Casos de evaluación para spec inválida, transcript pobre, datos vacíos
  (`SIN_DATO`, DAT-12 aplica también a documentos generados).

Dependencias: G2/G3 usan el CLI de O1 para datos en generación offline;
dentro del API llaman servicios directo.

---

## Riesgos y gates

- **Migraciones**: R1/R2 suman ~4 migraciones (0116+). Sesiones
  secuenciales, una lane con migraciones a la vez (§8).
- **DEC pendientes**: billing (R2), fuente de intentos fallidos (US-231),
  tabla de sesiones (US-232), zebra/iconos (R4). Cada una es un `DEC-###`
  en `DECISIONS.md` al resolverse.
- **Frontera de confianza**: banner de incidentes (US-233) y HTML generado
  (G2) renderizan contenido generado/escrito por terceros → pasan por
  `modelo-amenazas.md` antes del código.
- **EP021** (catálogo de IA) no está en este plan a propósito: tiene su
  propia epic decidida y desbloquea US-223–226 por su lado.
