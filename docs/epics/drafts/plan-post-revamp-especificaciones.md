---
tipo: gestion
responsable: propietario
estado: borrador
revisado: 2026-08-27
revisar_cada: 30d
---

# Post-revamp · Especificaciones de implementación — bloques R1, R2, R3, R4

> Nivel «ejecutable sin explorar»: cada US trae endpoint, modelo, migración,
> archivos a tocar (rutas reales verificadas contra `mapa-backend.md` y el
> código el 2026-08-27) y criterios de aceptación. La sesión que implemente
> NO necesita abrir nada fuera de lo listado + los mapas de arquitectura.
>
> Convenciones que aplican a TODO: 1 US = 1 commit = 1 migración (si toca
> esquema); scoping por `effective_tenant_id` no aplica a rutas superadmin
> (van con el guard de superadmin existente en `superadmin_panel.py`);
> respuesta de error = el formato de `ApiError` vigente; todo endpoint nuevo
> se declara en `docs/architecture/modelo-amenazas.md` (rutas autenticadas
> superadmin: impacto bajo, pero se declara); epic afectada: EP010
> (superadmin) salvo indicación. Migraciones: la próxima libre es **0116** —
> confirmar con `ls apps/api/alembic/versions | tail -1` antes de crear.

## Estado de grounding (verificado 2026-08-27)

- `login_failed` **ya se audita** en `endpoints/auth.py` (líneas ~132–181,
  `write_audit(action="login_failed", module="auth", …)`) → US-231 es solo
  agregación, sin instrumentar nada.
- `refresh_tokens` (models/auth.py) tiene `user_id`, `revoked`,
  `expires_at` → US-232 se resuelve contando tokens vivos de superadmins,
  **sin tabla nueva**.
- `users` tiene `failed_login_attempts` + `locked_until` (models/user.py
  ~31–32) → US-229 es un SELECT cross-tenant + reutilizar el unlock.
- Celery: **una sola cola** (la default `celery`; no hay `task_queues`),
  6 módulos de tareas (`ai`, `notifications`, `respaldo`,
  `scheduled_minutes`, `scheduled_reports`, `snapshots`), beat ya corre
  4 entradas (`workers/celery_app.py`) → el desglose «por cola» del mockup
  6f se implementa **por módulo de tarea**, y la profundidad es un solo
  `LLEN celery` en Redis.
- La UI ya tiene los huecos marcados: `superadmin/page.tsx` (PendingKpi
  MRR/Uptime + card incidentes), `superadmin/security/page.tsx` (3 KPIs +
  tabla bloqueadas + auditoría sin filtro), `superadmin/health/page.tsx`
  (4 KPIs + tabla colas + incidentes), `superadmin/tenants/[id]/page.tsx`
  (Facturación/Flags/Seguridad en SIN_DATO), `admin/plan/page.tsx`.

---

## R1 — Observabilidad superadmin

### US-227 · Versión y última migración — S

- **Endpoint**: `GET /api/v1/superadmin/version` →
  `{"version": str|null, "commit": str|null, "alembic_head": str, "desplegado_en": str|null}`.
  `version`/`commit`/`desplegado_en` de env (`APP_VERSION`, `GIT_SHA`,
  `DEPLOYED_AT` — Railway los inyecta o quedan null y la UI conserva
  `SIN_DATO` con leyenda); `alembic_head` = `SELECT version_num FROM
  alembic_version`.
- **Archivos**: `endpoints/superadmin_panel.py` (+ruta), sin modelo, sin
  migración. Front: `lib/api/superadmin-panel.ts` (+fetcher/tipo),
  `superadmin/health/page.tsx` (KPIs «Versión desplegada» y «Última
  migración» dejan `SIN_DATO` cuando el dato llega).
- **AC**: TC-1 con envs seteadas devuelve los 4 campos; TC-2 sin envs
  devuelve null y la UI muestra `SIN_DATO` (no «null»); TC-3 usuario no
  superadmin → 403.

### US-228 · Instrumentación del worker (cola + fallos) — M

- **Diseño**: dos fuentes. (a) Profundidad: `LLEN celery` contra el broker
  Redis (la URL ya está en la config del worker; leerla del mismo sitio,
  no duplicar env). (b) Fallos: señal `task_failure` de Celery en
  `workers/celery_app.py` → `write_audit(action="task_failed",
  module="worker", detalle: task name + excepción truncada)`. Agregación
  24h por prefijo de task (`ai.*`, `notifications.*`, …) desde `audit_log`.
- **Endpoint**: `GET /api/v1/superadmin/worker` →
  `{"broker_ok": bool, "profundidad": int|null, "modulos": [{"modulo": str,
  "fallidos_24h": int}], "fallidos_24h_total": int}`. Si Redis no responde:
  `broker_ok: false`, profundidad null — nunca 500.
- **Archivos**: `workers/celery_app.py` (señal), `endpoints/
  superadmin_panel.py` (+ruta), `services/audit.py` solo si `write_audit`
  no acepta actor sistema (revisar firma). Sin migración (audit_log ya
  existe). Front: `superadmin/health/page.tsx` (KPIs jobs
  pendientes/fallidos + tabla por módulo), `superadmin/page.tsx` y
  `superadmin-health-section.tsx` (el health card «Worker: sin
  instrumentar» pasa a real).
- **AC**: TC-1 tarea que lanza excepción deja fila de audit y aparece en el
  conteo; TC-2 broker caído → `broker_ok:false` y UI en `SIN_DATO` con
  aviso, no error; TC-3 la tabla lista los 6 módulos aunque tengan 0.

### US-229 · Cuentas bloqueadas a nivel plataforma — S

- **Endpoint**: `GET /api/v1/superadmin/security/locked-accounts` →
  `[{"user_id", "email", "tenant_id", "tenant_slug", "failed_attempts",
  "locked_until"}]` — solo `locked_until > now()`. Acción:
  `POST /api/v1/superadmin/security/locked-accounts/{user_id}/unlock`
  reutilizando la lógica de `admin_users.py::unlock` (extraer helper si
  está inline; el endpoint tenant-side no cambia de contrato).
- **Archivos**: `endpoints/superadmin_panel.py`, posible helper en
  `services/` o import directo. Sin migración. Front:
  `lib/api/superadmin-panel.ts`, `superadmin/security/page.tsx` (KPI
  «Cuentas bloqueadas» pasa a real; tabla se llena; botón unlock por fila
  con `confirmarDestructivo` NO — no es destructivo, botón normal).
- **AC**: TC-1 usuario con `locked_until` futuro aparece, con pasado no;
  TC-2 unlock resetea `failed_login_attempts` y `locked_until` y escribe
  audit; TC-3 audit del unlock nombra tenant y actor.

### US-230 · Auditoría por actor — S

- **Cambio**: `GET` de logs de plataforma (el que sirve `getPlatformLogs`
  en `superadmin_panel.py`) acepta `?actor_user_id=` y
  `?solo_superadmins=true` (join a users por `is_superadmin`).
- **Archivos**: `endpoints/superadmin_panel.py`, `lib/api/
  superadmin-panel.ts`, `superadmin/security/page.tsx` (usa
  `solo_superadmins=true` y retira la nota «sin filtro en el backend»),
  `superadmin/logs/page.tsx` (gana el filtro opcional).
- **AC**: TC-1 filtro devuelve solo acciones de superadmins; TC-2 sin
  filtro el contrato actual no cambia (snapshot de respuesta).

### US-231 · Intentos fallidos agregados — S

- **Endpoint**: `GET /api/v1/superadmin/security/failed-logins?horas=24` →
  `{"total": int, "por_tenant": [{"tenant_id", "slug", "conteo"}],
  "top_usuarios": [{"email_enmascarado", "conteo"}]}` — agrega
  `audit_log(action='login_failed')` por ventana. Email enmascarado
  (`d***@dominio`) porque la pantalla la puede ver soporte por encima del
  hombro; el dato completo ya está en logs.
- **Archivos**: `endpoints/superadmin_panel.py`, front
  `superadmin/security/page.tsx` (KPI «Intentos fallidos (24h)» real).
- **AC**: TC-1 tres fallos seguidos suman 3 al total y al tenant; TC-2
  ventana respeta `horas`; TC-3 email nunca viaja completo.

### US-232 · Sesiones activas de superadmin — S

- **Endpoint**: `GET /api/v1/superadmin/security/sessions` →
  `{"activas": int, "detalle": [{"user_id", "email", "creada", "expira"}]}`
  = `refresh_tokens` con `revoked=false AND expires_at > now()` join users
  `is_superadmin=true`. Es un proxy honesto (sesión = refresh vivo) y la UI
  lo dice en el caption.
- **Archivos**: `endpoints/superadmin_panel.py`, front
  `superadmin/security/page.tsx` (KPI «Sesiones de superadmin»).
- **AC**: TC-1 login de superadmin sube el conteo, logout/revocación lo
  baja; TC-2 tokens expirados no cuentan.

### US-233 · Incidentes de plataforma — M·**migración 0116**

- **Modelo** `models/incident.py`: `incidents(id, severity
  ENUM('critica','mayor','menor'), title, description TEXT, started_at,
  resolved_at NULL, created_by, TimestampMixin)` +
  `incident_tenants(incident_id FK CASCADE, tenant_id)` — sin FK a tenants
  para poder registrar incidentes de tenants ya borrados (misma convención
  que audit).
- **Endpoints**: CRUD superadmin en `endpoints/superadmin_panel.py`
  (`GET/POST /superadmin/incidents`, `PATCH /superadmin/incidents/{id}`
  para resolver/editar). Banner tenant-side:
  `GET /api/v1/incidents/active` (autenticado normal) devuelve los abiertos
  que incluyan al tenant efectivo o que no tengan tenants (= global);
  respuesta solo `{severity,title,started_at}` — **texto plano, la
  descripción no viaja al banner** (frontera: contenido de superadmin
  renderizado en tenants; declararlo en `modelo-amenazas.md`).
- **Archivos**: modelo + migración 0116 + `DB-CHANGES.md`; endpoints;
  front: `superadmin/health/page.tsx` (tabla real + «Declarar incidente»
  se habilita con modal de creación), `superadmin/page.tsx` (card
  incidentes recientes), `components/app-shell.tsx` o layout `(app)` para
  el `Banner variant="warning"` global cuando hay incidente activo del
  tenant (montarlo en `app/(app)/layout.tsx`, no en cada página).
- **AC**: TC-1 incidente con tenants X,Y solo banner en X,Y; TC-2 sin
  tenants → banner en todos; TC-3 resuelto desaparece; TC-4 el banner
  escapa HTML (título con `<script>` se pinta literal); TC-5 downgrade de
  0116 limpio (lección 2026-08-19: índices de bajada).

### US-234 · Uptime 30d — M·**migración 0117**

- **Modelo** `health_snapshots(id, capturado_en, ok BOOL, detalle JSON)` —
  fila cada 5 min desde beat: entrada nueva
  `platform-health-snapshot` (300 s) en `workers/celery_app.py` que llama
  al mismo servicio que `getPlatformHealth` y persiste. Retención: task
  borra >35 días (misma pasada).
- **Endpoint**: `GET /api/v1/superadmin/uptime?dias=30` →
  `{"pct": float|null, "desde": date, "muestras": int}`; `pct=null` con
  <1 día de muestras y la UI dice «acumulando desde <fecha>».
- **Archivos**: modelo + migración 0117 + `DB-CHANGES.md`; task en
  `workers/tasks/snapshots.py` (convive con metric_snapshots); endpoint en
  `superadmin_panel.py`; front `superadmin/page.tsx` (PendingKpi Uptime →
  real). **Nota beat**: el intervalo de 5 min define la resolución; caídas
  más cortas no se ven y el caption lo dice.
- **AC**: TC-1 10 muestras ok + 2 fail → 83.3%; TC-2 sin muestras → null;
  TC-3 la retención no borra dentro de la ventana.

## R2 — Monetización (desbloqueado — **DEC-034**, owner 2026-08-27)

Registro manual del plan por tenant ahora; Stripe después como escritor
sobre el mismo modelo. Detalle y rationale en `DECISIONS.md` §DEC-034.
R2 puede arrancar sin más preguntas.

### US-235 · Suscripción por tenant — M·**migración 0118**

- **Modelo** `models/subscription.py`: `subscriptions(id, tenant_id UNIQUE,
  plan ENUM('starter','business','enterprise'), estado
  ENUM('al_corriente','pago_pendiente','suspendido'), renovacion DATE NULL,
  metodo_pago VARCHAR NULL, notas TEXT NULL, TimestampMixin)`. Un registro
  por tenant; tenants sin fila = sin plan asignado (UI: `SIN_DATO`). Los
  topes siguen en `settings.plan` (US-221) — esta tabla es la comercial, no
  la de límites; unificarlos es una DEC futura, no de esta US.
- **Endpoints**: `GET/PUT /api/v1/superadmin/tenants/{id}/subscription`
  (superadmin_panel). `admin/plan` (tenant, solo lectura) suma
  `plan`/`estado`/`renovacion` a su respuesta actual.
- **Front**: `superadmin/tenants/[id]/page.tsx` (card Facturación pasa de
  `SIN_DATO` a real + edición inline superadmin),
  `superadmin/tenants/page.tsx` (chip de plan en la tarjeta — el que la
  barrida omitió por falta de campo), `admin/plan/page.tsx`,
  `lib/api/superadmin-panel.ts` y `lib/api/admin.ts`.
- **AC**: TC-1 PUT crea o actualiza (upsert) y audita; TC-2 tenant sin fila
  → UI `SIN_DATO`, no error; TC-3 tenant-side es solo lectura (PUT → 403).

### US-236 · MRR — S (tras US-235)

- Tarifa por plan vive en `core/` como constante con moneda
  (`PLAN_PRICING`), no en DB — cambiarla es un deploy consciente.
- **Endpoint**: `GET /api/v1/superadmin/mrr` → `{"mrr": Decimal, "moneda",
  "por_plan": [{"plan","tenants","subtotal"}], "sin_plan": int}` — solo
  `estado='al_corriente'`.
- **Front**: `superadmin/page.tsx` (PendingKpi MRR → real, cifra
  `formatearImporte`).
- **AC**: TC-1 2×business+1×starter = suma exacta; TC-2 suspendido no
  suma; TC-3 `sin_plan` cuenta tenants sin fila.

### US-237 · Feature flags — M·**migración 0119**

- **Diseño**: flags declarados en código
  (`core/feature_flags.py::FLAGS = {nombre: {default, descripcion}}`) +
  tabla de overrides `tenant_feature_overrides(id, tenant_id, flag,
  enabled BOOL, UNIQUE(tenant_id, flag))`. Un flag no declarado en código
  no se puede overridear (el endpoint valida contra FLAGS). Primer flag
  real: `ai_assistant` (consultado por el endpoint del assistant al
  resolver si responde) — para que el sistema nazca con un consumidor.
- **Endpoints**: `GET/PUT /api/v1/superadmin/tenants/{id}/flags`;
  helper `flag_activo(db, tenant_id, nombre)` en `core/feature_flags.py`
  usado por el assistant.
- **Front**: `superadmin/tenants/[id]/page.tsx` (card Feature flags: lista
  real con `Switch` por flag, default marcado como tal).
- **AC**: TC-1 override false apaga el assistant para ese tenant (el
  endpoint devuelve el error de deshabilitado ya existente de AI_DISABLED);
  TC-2 PUT de flag inexistente → 422; TC-3 sin override rige el default.

## R3 — Dark theme (US-238 — M/L)

- **Alcance**: reescribir el bloque `.dark, [data-theme="dark"]` de
  `apps/web/app/globals.css` con los pasos del mockup 1a §02b: canvas
  `oklch(16% .006 250)`, superficie 21%, riel/cabecera 26%, filete
  `#33363C` + luz `#454850`, acento `oklch(58% 0.15 258)`, semáforo fondos
  ~30% / fg ~80%, texto primario `oklch(92% .004 250)`.
- **Los tokens de profundidad se invierten** — la «luz» blanca no existe en
  oscuro: `--linea-surco: 0 1px 0 <luz oscura #454850-ish>`;
  `--relieve-*`/`--hundido` con sombras más marcadas y luz tenue. Definir
  los 6 (`--linea-surco`, `--linea-surco-arriba`, `--relieve-control`,
  `--relieve-isla`, `--hundido`, `--relieve-hito`) dentro del bloque dark.
- **Chrome oscuro**: deja el navy heredado y toma canvas 16%/riel 21% con
  pill activo claro invertido (`--chrome-active` claro + texto tinta) — el
  mockup no lo dibuja; criterio: mismo contraste relativo que el claro.
- **Gate**: `check_contraste.py` ya mide ambos temas — es el DoD duro.
  Recorrido visual de las 30 pantallas con `data-theme="dark"`.
- **AC**: TC-1 36/36 pares AA en ambos temas; TC-2 ninguna pantalla queda
  con fondo claro heredado (grep de tokens sólo-claros en el bloque dark);
  TC-3 gráficos usan los pasos dark ya existentes de ADR-023 (no se tocan).

## R4 — Deuda visual menor (ENHs, batch)

| ENH | Qué | Archivos |
|---|---|---|
| a | `TrendPill` gana tono `warning` (goodWhenUp con delta adverso leve ≠ alarma); reponer icono de tendencia en «Avance plan vs real» | `components/kpi-card.tsx`, `dashboard/page.tsx` |
| b | Columna «Programa» en `/pmo/projects`: API agrega `program_name` a la fila de listado (join barato) y la tabla la pinta con ancho fijo | `endpoints/projects.py`, `lib/api/projects.ts`, `pmo/projects/page.tsx` |
| c | Counts por estado en Solicitudes: `GET /project-requests/counts` → pastilla en cada pestaña | `endpoints/project_requests.py`, `pmo/requests/page.tsx` |
| d | DEC: zebra striping — adoptar token (`--color-zebra: #FCFCFB`) o retirarlo de los mockups; hoy es inconsistente | `globals.css` + 3–4 tablas |
| e | DEC: fijar sustitutos de iconos sin equivalente Keyline como definitivos (tabla en el plan padre) o pedir alta upstream | doc de especificación |
| f | `PreviewPane` del builder 480→420px | `reports/builder/page.tsx` |

---

## Adiciones 2026-08-27 — feedback del owner (iPad, slug de proyecto)

### US-239 · Clave de proyecto estilo Jira en la URL — M·**migración 0120** · EP005

Pedido del owner: «que los proyectos tengan un código de algún slug del
proyecto estilo Jira para que las URLs lo porten también».

- **Modelo**: `projects.clave` VARCHAR(10) NULL, patrón `^[A-Z][A-Z0-9]{1,9}$`,
  **única por tenant** (índice único parcial `(tenant_id, clave) WHERE clave
  IS NOT NULL`). No sustituye al folio (`PRJ-2026-004` sigue siendo el
  identificador documental); la clave es el identificador **memorable y de
  URL** (`HLD`, `EAMBNF`). Migración 0120: columna + índice + **backfill**:
  iniciales del nombre (mayúsculas, sin stopwords, máx 6) con sufijo
  numérico ante colisión; el registro de la migración lista las claves
  generadas para revisión del owner (mismo patrón que 0110/0111).
- **Resolución dual** (API): helper `resolver_proyecto(db, tenant_id,
  id_o_clave)` — si casa el regex UUID → por id; si no → `upper()` y por
  clave. Aplicarlo en `endpoints/projects.py` (GET detalle) y en los
  endpoints anidados que reciben `project_id` de path vía la dependencia
  común de `api/deps.py` si existe, o en cada router que hoy haga
  `get(Project, id)` — la implementación localiza los puntos con grep de
  `project_id` en path params; el criterio: **toda URL que hoy acepta UUID
  acepta clave**, con el mismo scoping por tenant.
- **Front**: las rutas Next siguen siendo `[id]` (aceptan ambos valores —
  cero renombres de carpetas). Helper `hrefProyecto(p)` en
  `lib/api/projects.ts` que prefiere `clave` y cae a `id`; sustituir los
  literales `` `/pmo/projects/${id}` `` por el helper (grep;
  ~15 sitios: tablas, tops, board, breadcrumbs, tabs). `project-form.tsx`:
  campo «Clave» con sugerencia automática desde el nombre, validación del
  patrón y error claro en colisión; editable después con aviso («las URLs
  viejas con la clave anterior dejan de resolver») — v1 no guarda
  histórico de claves.
- **AC**: TC-1 `/pmo/projects/HLD` y `/pmo/projects/<uuid>` cargan el
  mismo proyecto; TC-2 clave de otro tenant → 404 (scoping); TC-3
  colisión al crear → 422 con sugerencia; TC-4 backfill genera claves
  únicas y las registra; TC-5 minúsculas en URL resuelven
  (case-insensitive); TC-6 proyecto sin clave (pre-backfill fallido o
  borrada) sigue accesible por UUID.
- **Nota CLI/G**: `pmo proyecto <folio>` (bloque O) acepta también la
  clave — mismo resolver expuesto; actualizar el contrato en
  `-operacion.md` al implementar.

### QA-iPad · Bugs visuales del revamp en tablet — BUG-093+ (reservados) · gate: lista del owner

El owner detectó bugs visuales en iPad (2026-08-27); la lista llega al
terminar su revisión (iPad + PC). Al llegar: un BUG por hallazgo vía
`triage`, bloque propio «QA revamp». Sospechosos probables para acelerar
la revisión (el revamp se implementó contra artboards de 1440px):

1. Tablas `table-fixed` con anchos fijos que suman >768px sin
   `overflow-x-auto` en el contenedor (proyectos, usuarios, plan).
2. `KpiBand` en cortes intermedios (`sm:grid-cols-3` deja la banda de 6 en
   3×2 con filetes verticales que no cierran la retícula).
3. Topbar: buscador de 260px + switchers de inquilino/organización
   compitiendo por ancho en 768–1024px.
4. Sidebar táctil: el colapso a 68px depende de hover/click fino; en
   touch el breakpoint `lg` deja el sidebar off-canvas y el botón de menú
   es de 36px (objetivo táctil justo).
5. Vistas anchas sin `max-w` (vista maestra, gantt, heatmap): scroll
   horizontal correcto pero sticky de primera columna + `-webkit-overflow-
   scrolling` en Safari iPad es el clásico que se rompe.
6. Modales `max-h-[calc(100dvh-2rem)]`: `dvh` + teclado en pantalla en
   Safari.

1. **Arranque**: leer `HANDOFF.md`, `CLAUDE.md`, `SPRINT.md`, este doc y
   los dos hermanos (`-operacion`, `-generacion`). El OK del owner por chat
   a «desarrollar el plan» sustituye los labels `status:ready` (§0.2 de
   CLAUDE.md); los issues se crean con la skill `triage` usando estas
   especificaciones como cuerpo, o se omiten si el owner prefiere
   solo commits.
2. **Lanes** (sesiones secuenciales si comparten migraciones):
   - Lane 1 (con migraciones, secuencial): US-233 → US-234 → US-235 →
     US-236 → US-237 → US-239. Migraciones 0116–0120 en ese orden
     (R2 desbloqueado por DEC-034).
   - Lane 2 (sin migraciones, paralelizable con 1): US-227 → US-230 →
     US-231 → US-232 → US-229 → US-228.
   - Lane 3 (solo web): R3 dark theme (US-238); después R4; el bloque
     «QA revamp» (BUG-093+) entra aquí cuando el owner entregue la lista.
   - Lane 4 (independiente): bloque O; después bloque G (usa O).
3. **Por US**: branch de trabajo único de la ronda; commit
   `feat(scope): US-XXX — …`; actualizar epic (EP010 para R1/R2) +
   `DB-CHANGES.md` si hay migración; UI del slice en el mismo commit
   (§13 end-to-end: la marca «pendiente de backend» muere junto con el
   endpoint que la resuelve).
4. **Verificación por US** (skill `verificar`): ruff + pytest `-m "not
   heavy"` + tsc + build web con exit 0; para migraciones, el ciclo
   upgrade/downgrade/upgrade contra Postgres local.
5. **Cierre de ronda**: skill `resumen-ronda`; `SPRINT.md` actualizado al
   cerrar bloque, no por commit.
