---
tipo: epica
responsable: propietario
estado: vigente
revisado: 2026-08-05
revisar_cada: 90d
---

# DECISIONS.md — Decisiones arquitectónicas

> Claude Code: antes de proponer soluciones alternativas, verifica que no contradiga una decisión aquí registrada. Si necesitas contradecirla, documenta el cambio con fecha y rationale.

> **Dónde vive cada cosa (2026-08-05).** MCS `ARQ-02` exige que **toda decisión
> irreversible** esté en un ADR, así que las cinco de esta lista que lo eran
> —DEC-003, DEC-007, DEC-008, DEC-022 y DEC-024— se promovieron a `ADR-024` a
> `ADR-028` y conservan aquí su enlace.
>
> La regla para lo que venga: **si deshacerla exige migrar datos productivos o
> rompe un contrato público, va a `docs/adr/`**. Si cuesta una decisión y no una
> migración —proceso, presentación, alcance de sprint— se queda aquí.

---

## DEC-001 — Tracking multi-sesión con GitHub Issues + archivos MD
**Fecha:** 2026-04-20  
**Decisión:** Issues GitHub para tracking público + archivos MD en repo para contexto de Claude Code.  
**Rationale:** Claude Code puede leer MD del repo directamente. GitHub Issues da visibilidad y búsqueda.  
**Alternativa descartada:** Solo Notion (Claude Code no tiene acceso directo).

## DEC-002 — ❌ SUPERSEDED por DEC-013
**Fecha original:** 2026-04-20
**Revocada:** 2026-04-21 (ver DEC-013).
**Decisión original:** EP012 era la última épica para migrar a MySQL al final del roadmap.
**Estado actual:** EP012 queda CANCELADO. Productivo v1.0 corre en Railway Postgres sin plan de migrar. El archivo original del epic se conserva en `docs/archive/cancelled-epics/EP012-db-migration.md`.

## DEC-003 — Jerarquía org con tablas separadas (no JSONB)

> **Promovida a [ADR-024](../adr/README.md#adr-024) el 2026-08-05.** Es
> irreversible —deshacerla exige migrar datos productivos o rompe un contrato
> público—, y MCS `ARQ-02` exige que toda decisión irreversible viva en un ADR.
> Esta entrada se conserva por la relación bidireccional que pide `CFG-18`.
**Fecha:** 2026-04-20  
**Decisión:** `business_units` y `departments` son tablas con FK reales, no campos JSONB en organizations.  
**Rationale:** Permite FK desde programs/projects, filtros eficientes, y RLS por nivel.  
**Alternativa descartada:** `organizations.settings JSONB` con BU/Depto embebidos (no permite FK).

## DEC-004 — 1 US = 1 commit = 1 sesión de Claude Code
**Fecha:** 2026-04-20  
**Decisión:** Cada user story se implementa en una sesión independiente con su propio commit.  
**Rationale:** Evita exceder contexto/memoria de Claude Code. Permite rollback granular.  
**Regla:** Si una US es muy grande, dividirla en US-XXXa y US-XXXb antes de ejecutar.

## DEC-005 — Admin Y Senior PMO tienen permisos de administrador
**Fecha:** 2026-04-20  
**Decisión:** El middleware de rutas `/admin` acepta roles `Administrador` Y `PMO Manager` (nivel senior).  
**Implementación:** `user.roles` debe incluir permiso `is_admin_equivalent: true` en el JWT o verificar por nombre de rol.  
**Afecta:** EP001 (middleware auth), EP007 (rutas admin).

## DEC-006 — Color primario chrome: #182e4e
**Fecha:** 2026-04-20  
**Decisión:** El sidebar y topbar usan `#182e4e` como color de fondo (no el `#0E164F` anterior).  
**Afecta:** `docs/design-system/style.md`, variable CSS `--chrome-bg`.

## DEC-007 — RAID no es una tabla nueva, es una vista de risks + issues

> **Promovida a [ADR-025](../adr/README.md#adr-025) el 2026-08-05.** Es
> irreversible —deshacerla exige migrar datos productivos o rompe un contrato
> público—, y MCS `ARQ-02` exige que toda decisión irreversible viva en un ADR.
> Esta entrada se conserva por la relación bidireccional que pide `CFG-18`.
**Fecha:** 2026-04-20  
**Decisión:** RAID = tabla `risks` (R) + tabla `issues` con types: action(A), incident(I), decision(D).  
**No se crea** una tabla `raid` nueva. Solo se agrega UI que agrupe las 4 fuentes bajo el tab RAID.  
**Rationale:** Schema existente ya soporta los 4 tipos, evita duplicación de datos.

## DEC-008 — Project Charter es una tabla separada (no documento PDF guardado)

> **Promovida a [ADR-026](../adr/README.md#adr-026) el 2026-08-05.** Es
> irreversible —deshacerla exige migrar datos productivos o rompe un contrato
> público—, y MCS `ARQ-02` exige que toda decisión irreversible viva en un ADR.
> Esta entrada se conserva por la relación bidireccional que pide `CFG-18`.
**Fecha:** 2026-04-20  
**Decisión:** `project_charters` es una tabla estructurada cuyos datos de "Gestión" se sincronizan dinámicamente desde `projects`.  
**Rationale:** Permite editar campos, generar PDF on-demand, y actualizar datos de gestión sin regenerar documento.  
**PDF del charter:** se genera on-demand desde los datos de la tabla, no se guarda como archivo estático.

## DEC-009 — Áreas/Organigrama del proyecto: sin acceso a plataforma
**Fecha:** 2026-04-20  
**Decisión:** `project_areas` registra actores y áreas solo como referencia (nombre, contacto). No son usuarios del sistema.  
**Uso:** Se referencian en asignación de tareas, RAIDs y minutas como texto, no como FK a `users`.  
**Rationale:** Muchos stakeholders no tendrán cuenta en la plataforma.

## DEC-010 — Reportes automáticos: módulo dentro del proyecto (EP006), generación IA en EP008
**Fecha:** 2026-04-20  
**Decisión:** El módulo de Reportes vive en EP006 (UI dentro del proyecto). EP008 solo maneja la generación con IA.  
**Separación:** EP006 = CRUD de reportes + UI. EP008 = motor de generación IA que EP006 invoca.

## DEC-011 — Ollama local vía Tailscale (reemplaza CF Tunnel + Access)
**Fecha:** 2026-04-21
**Decisión:** El canal de acceso del worker Railway al Ollama local es **Tailscale tailnet privado**. Se retira Cloudflare Tunnel + Cloudflare Access (Service Token).
**Rationale:** El setup real de CF Tunnel + Access se bloqueó de forma reproducible por managed rulesets de CF (AI bot blocking) que devuelven 403 invisibles al WAF; la UI de Cloudflare One fragmenta el flujo y tiene bugs de estado; y exponer Ollama públicamente con token es innecesariamente amplia para un endpoint que solo ve el worker. Tailscale elimina la exposición pública, centraliza auth en admin console, y simplifica el runbook a 2 comandos + sidecar.
**Afecta:** EP016 (US-044/045 quedan SUPERSEDED); ADR-014 reemplazada por ADR-015; subdominio `ollama.pmo-aas.com` se retira de DNS; worker Dockerfile gana sidecar `tailscaled`.
**Alternativa descartada:** CF Tunnel sin Access + Basic Auth via Caddy local — sigue exponiendo el endpoint. ngrok paid — misma exposición, peor precio.
**Plan B:** Self-host Headscale si Tailscale sube precios o limita free tier.
**Referencia:** ADR-015.

## DEC-012 — Base de datos productiva v1.0 en Railway Postgres; HostGator solo para landing `www`
**Fecha:** 2026-04-21
**Decisión:** En v1.0 productiva, `DATABASE_URL` sigue apuntando a **Railway Postgres**. HostGator hostea **exclusivamente el landing/marketing** en `www.pmo-aas.com` (estático). MySQL remoto en HostGator queda **fuera de alcance v1.0**.
**Rationale:** La migración a MySQL HostGator (EP012) tiene blockers operacionales no resueltos: (1) Railway Hobby **no tiene IP estática**, impidiendo whitelist en cPanel Remote MySQL; (2) exposición del puerto MySQL a internet en shared hosting es riesgo alto; (3) queries JSONB/GENERATED/citext en el código requieren rework; (4) HostGator shared no tiene backups automáticos comparables a Railway Pro. Costo Railway prod (~$30-40/mes) vs riesgo operacional HostGator shared justifica mantener Postgres.
**Supersede parcial:** DEC-002 ("Migración PG→MySQL al final del roadmap") se recorta a "MySQL HostGator pasa a v1.1+ solo si los blockers se resuelven con infra dedicada (VPS/RDS); EP012 queda deprioritizado".
**Afecta:** EP012 US-029/030 pasan de "Bloque 14 productivo" a backlog v1.1 con scope revisado; SPRINT.md reordenado.
**Alternativa descartada:** Mover todo (API + BD) a HostGator — pierde escalabilidad Railway; VPN Railway↔HostGator — complejidad desproporcionada para MVP.
**DNS en Cloudflare (plan de rutas):**
- `app.pmo-aas.com` → CNAME Railway `web` (DNS only / nube gris).
- `api.pmo-aas.com` → CNAME Railway `api` (DNS only / nube gris).
- `www.pmo-aas.com` → A/CNAME HostGator (proxy naranja, Full SSL).
- `pmo-aas.com` (apex) → redirect 301 a `app.pmo-aas.com` (o CNAME flattening).
- `ollama.pmo-aas.com` → **retirado** (ver DEC-011).

## DEC-013 — Productivo v1.0 corre 100% en Railway; EP012 (MySQL HostGator) CANCELADO
**Fecha:** 2026-04-21
**Decisión:** Productivo v1.0 (y v1.x) corren íntegramente en **Railway**, incluyendo BD Postgres. El owner sube el tier del plan Railway (Hobby → Pro u otro con más recursos) y absorbe el costo marginal con las licencias cobradas a clientes. **EP012 (migración a MySQL HostGator) queda CANCELADO**, no deprioritizado: no hay plan futuro de mover la BD a MySQL. HostGator sigue sirviendo únicamente el landing estático `www.pmo-aas.com` (ver DEC-012).
**Rationale:**
- El tier superior de Railway cubre compute + Postgres con backups automáticos y throughput suficiente para cargas esperadas del MVP + primeros clientes.
- El costo incremental del upgrade se cubre con el ingreso de licencias → no hay presión económica para migrar a shared hosting.
- Los blockers técnicos de EP012 (JSONB, GENERATED, citext, RLS, ausencia de IP estática Railway Hobby) ya no se invierten en resolver — el valor del negocio está en entregar features y arrancar pruebas masivas, no en migrar infra.
- Mantener un solo dialecto (Postgres) elimina deuda técnica permanente: no hay que mantener el código dialect-agnostic ni duplicar CI matrix.
**Supersede:**
- **DEC-002** (migración PG→MySQL al final del roadmap) queda totalmente revocada.
- **DEC-012** se refuerza: la parte de "MySQL HostGator pasa a v1.1+ solo si los blockers se resuelven" también se revoca. No se reabre.
**Afecta:**
- EP012 se marca `CANCELLED` en `docs/epics/EP012-db-migration.md`; US-029/030 se cierran como CANCELADAS (no se ejecutarán).
- SPRINT.md: se elimina Bloque 17 de la lista de bloques priorizados.
- Roadmap antes de v1.0 productivo / pruebas masivas: solo queda terminar Bloque 14 (EP016 v2 Tailscale para habilitar IA) y Bloque 15 (DNS + landing).
**Alternativa descartada:** VPS dedicado con MySQL — complejidad operativa alta para un beneficio nulo vs Railway Postgres en escala MVP/v1.
**Plan B:** Si Railway sube precios de forma insostenible en el futuro, re-evaluar Supabase o Neon (ambos Postgres, sin rework de código).


---

## DEC-017 — IA multi-modo por tenant: disabled / platform (Groq) / byo (US-057)

**Contexto:** US-057 replantea el modelo de IA del MVP. Anteriormente
(US-048) había un sólo endpoint Ollama tailnet compartido por todos los
tenants, con un cascade global controlado por env (`AI_MODE`). Eso
funcionaba para pilotar, pero no escalaba a una oferta productiva
multi-tenant donde cada cliente decide:

- No usar IA en absoluto (plan barato / políticas de compliance).
- Usar IA "included" que hostea la plataforma, sin configurar nada.
- Traer su propio proveedor (OpenAI / Claude / Perplexity / Gemini /
  Ollama interno) con sus credenciales y llevarse el costo a su cuenta.

**Decisión:** se establecen **tres modos** como campo `mode` en
`tenants.settings.ai`:

1. `disabled` — el endpoint `/ai/*` responde 409 `AI_DISABLED`. Default
   del migración 0021 para todos los tenants existentes (opt-in).
2. `platform` — usa **Groq** (`llama-3.1-70b-versatile`) como proveedor
   compartido con la `GROQ_API_KEY` de plataforma (cifrada en
   `platform_ai_settings.groq_api_key_encrypted`). **Scope limitado a
   minutas** para controlar el consumo en el free tier. Los draft de
   reportes IA (EP008) **no** están disponibles en este modo — el
   endpoint responde 409 `AI_PLATFORM_SCOPE_LIMITED`. Cada llamada
   manda `metadata.tenant_id` + `metadata.job_id` para trazabilidad
   cross-tenant en el dashboard del superadmin.
3. `byo` — el admin del tenant configura un proveedor propio en
   `/admin/ai`. Las credenciales se cifran con **Fernet**
   (`AI_SECRETS_FERNET_KEY`, reactivada tras deprecación por US-047).
   Proveedores BYO soportados: `openai`, `claude`, `perplexity`,
   `gemini`, `ollama` (absorbe el flujo US-048 como sub-caso).

**Reglas:**
- **Sin fallback entre modos**. Si `platform` (Groq) falla tras 3
  reintentos (backoff 1s/3s/8s), el job se marca `failed` y se
  **notifica al superadmin** (tipo `platform_ai_alert`, email vía
  Resend). No cae a proveedores externos: preservar privacidad y costo.
- Cada cambio de `mode` requiere confirmación explícita del admin del
  tenant (modal en UI) — puede romper jobs en vuelo.
- `ai_jobs.provider` se rellena para alimentar el dashboard de uso
  Groq (`/superadmin/ai`).

**Supersede / afecta:**
- **US-048** queda absorbida: el endpoint `/admin/ai/ollama` persiste
  para retro-compat, pero la migración `20260423_0022` traslada los
  tenants con Ollama tailnet activo al shape `byo` con
  `provider="ollama"`. El nuevo `/admin/ai/provider` es la fuente de
  verdad para el worker (`load_tenant_ai()`).
- **DEC-011** (Ollama tailnet como canal IA principal) se relaja:
  Tailscale sigue disponible para tenants que quieran Ollama BYO,
  pero ya no es "el único camino a IA".

**Alternativa descartada:**
- Permitir fallback `byo → platform` cuando la key del tenant falle.
  Rechazado por el owner para evitar cargar costos de plataforma si el
  cliente no lo esperaba.

**Pendientes / follow-ups:**
- Draft de reportes IA en modo `platform`: requeriría más cuidado con
  el consumo (los reportes son más largos que una minuta). Evaluar
  después de medir el uso real de Groq con el dashboard.
- Rotación automática de `GROQ_API_KEY` (hoy es manual vía
  `/superadmin/ai`).
- Límite de consumo por tenant en modo `platform` (cuotas por-tenant)
  si se detecta abuso.

Registrado el 2026-04-23 junto con la feature.


---

## DEC-018 — Sprint 3 v1.2 acotado; Auth/Roles/Aprobaciones diferidos a v2.0

**Contexto:** el intake de Sprint 2 (2026-04-22) dejó 3 items marcados
`v1.2` — US-059 (recursos sin roles jerárquicos), US-060 (tipos de
usuario Viewer/User/Admin), US-061 (aprobaciones jerárquicas). Al
cerrar v1.1 (2026-04-23), el owner revisa el scope y concluye que
esos 3 items son **un replanteo del modelo Auth + multi-tenancy**,
no un set de enhancements incrementales: tocan permisos, relaciones
de reporte, aprobaciones, y la UX de asignación transversalmente.

Meter eso en v1.2 produciría un sprint mega-grande con regresiones
probables. El owner también pide dos arreglos menores post-v1.1:

- Quitar los defaults editables de Ollama del `/superadmin/ai` (ya no
  se usan tras DEC-017).
- Flujo de recuperación/cambio de contraseña con email (hoy los users
  dependen del admin para resetear).

**Decisión:** se ajusta la cartera:

1. **Sprint 3 v1.2** se acota a **ENH-021** + **US-063** (ambos
   creados en GitHub: #96 y #95). Se enfoca en cerrar loops menores
   post-v1.1 sin abrir scope nuevo.
2. Los 3 items originales de v1.2 (US-059 #88, US-060 #89, US-061
   #90) y el eventual replanteo de cuentas/SSO/2FA se mueven a
   **v2.0 — Major Overhaul**. v2.0 se planifica con un RFC dedicado
   cuando v1.2 esté estable (no antes).

**Consecuencias:**
- SPRINT.md refleja el nuevo backlog.
- Los issues #88, #89, #90 quedan con label `v2.0` (migrar de `v1.2`
  cuando se re-etiqueten en GitHub).
- v1.2 puede cerrarse en un Sprint 3 corto (~2 semanas) y dejar
  margen para estabilizar el deploy productivo de Groq antes del
  sprint grande.

**Alternativa descartada:** meter US-059/060/061 en v1.2 con
implementación parcial. Rechazada porque un overhaul de roles
parcial es peor que no tenerlo (confunde a admins y genera deuda
técnica en migraciones de permisos).

Registrada 2026-04-23, al cerrar Sprint 2 v1.1.


---

## DEC-019 — Catálogo BYO sin Ollama + feature flag del wizard de conexión

> **Update 2026-05-08 (BUG-053):** la "Parte 1" se llevó al límite —
> `OllamaProvider` fue eliminado del runtime. Cualquier tenant que aún
> tenga `settings.ai.byo.provider="ollama"` falla con
> `unsupported_provider` al generar IA. La parte de "back-compat para
> tenants legacy" descrita abajo es histórica.
>
> **Update 2026-05-23:** la "Parte 2 — feature flag `AI_BYO_ENABLED`"
> se removió. BYO está siempre disponible; cualquier tenant admin puede
> conectar provider desde `/admin/ai`. Si una card aparece como
> "Próximamente" hoy, es por entrada `disabled` específica del
> catálogo, no un gate global.

**Contexto (2026-04-24, post-deploy v1.1):** el owner reportó que la
UI `/admin/ai` seguía mostrando las opciones legacy (`sin definir`,
`ollama local`, `claude`, `desactivado`) en el selector de modo IA.
El GET/PATCH del endpoint `/admin/ai/provider` ya usaba el schema
correcto (US-057, DEC-017), pero la UI estaba servida cacheada y
además el catálogo BYO listaba `ollama` — un proveedor que el owner
no quiere exponer al tenant nuevo. La decisión tiene dos partes:

**Parte 1 — Catálogo público BYO sin Ollama:**
- `BYO_PROVIDERS` mantiene `ollama` como valor aceptado por el worker
  (para tenants legacy cuya `settings.ai.byo.provider="ollama"` ya
  está en BD después de la migración 0022).
- Nueva tupla `BYO_PROVIDERS_ALLOWED = ("openai", "claude",
  "perplexity", "gemini")` define qué proveedores puede configurar
  el tenant-admin desde la UI. El endpoint PATCH valida contra esta
  lista (el schema Pydantic además ya no acepta `"ollama"` como
  literal, así que la protección es doble).
- Tenants en prod con Ollama activo (si los hay) siguen funcionando
  pero no pueden editar su config — deben migrar a Groq/OpenAI/
  Claude/Perplexity/Gemini.
- Nuevo módulo `services/ai/byo_catalog.py` expone `BYO_CATALOG` con
  metadata UX (label, descripción, `api_keys_url`, `docs_url`,
  modelos sugeridos). Se sirve en `GET /admin/ai/provider` y la UI lo
  renderiza como cards sin hardcodear URLs.

**Parte 2 — Feature flag `AI_BYO_ENABLED` (default false):**
- El modo BYO queda gate-ado tras el flag `AI_BYO_ENABLED`. Por
  default (`False` en prod) el PATCH rechaza `mode="byo"` con 422
  `BYO_NOT_ENABLED` y el POST de test con la misma señal.
- La UI igual muestra las cards de los 4 proveedores, pero con badge
  "Próximamente" y el wizard abre en modo "preview" (sólo info +
  deep-links, sin guardar).
- Cuando el owner quiera habilitar BYO en prod, setea
  `AI_BYO_ENABLED=1` en Railway y redeploya; ningún otro cambio de
  código requerido.

**Rationale:**
- El wizard de conexión (4 pasos: intro → key → test → save) está
  construido pero no validado en prod con usuarios reales. El flag
  permite entregar el código ahora (reduce el PR gigante de v2.0)
  sin exponer un flujo a medio pulir.
- Quitar Ollama del catálogo público refleja que la oferta para
  tenants nuevos es siempre cloud-managed (Groq plataforma o BYO a
  proveedor cloud). Ollama privado sigue soportado para tenants que
  lo necesiten pero no se anuncia como opción estándar.

**Afecta:**
- SPRINT.md: este bug-fix cierra el bloque post-v1.1 sin abrir Sprint
  3 v1.2 Bloque 2 todavía — el owner decide si arma el Bloque 2.
- Cuando `AI_BYO_ENABLED=1` se encienda, documentar el runbook con
  smoke test del wizard antes de invitar tenants.

**Alternativa descartada:** dejar BYO completamente disponible desde
el PATCH aunque la UI no estuviera lista. Rechazado porque algún
usuario avanzado podría llamar al endpoint directamente, guardar
credenciales mal cifradas o sin test, y meter inconsistencia en la
BD.

Registrada 2026-04-24 en el follow-up de US-057.


---

## DEC-020 — Plataforma sin aprobaciones jerárquicas + permisos simplificados

**Contexto (2026-04-24, durante Sprint 4):** el owner aclara que PMO·aaS
es una **herramienta de apoyo y visualización**, no un sistema de
gestión corporativa con workflow de aprobaciones. El diseño original
de v2.0 (US-059/060/061) planeaba un overhaul con roles jerárquicos
(Viewer/User/Admin + `reports_to_id` + `approve_requests`). Eso agrega
fricción innecesaria al flujo de un PM que solo quiere cargar riesgos,
registrar minutas o distribuir tareas.

La decisión redefine el modelo de permisos:

**Parte 1 — Acceso libre para la mayoría de los recursos:**

Todos los usuarios de la PMO pueden **crear, editar, aprobar y borrar**
libremente los siguientes recursos:

- Proyectos (`projects`)
- Tareas (`tasks`)
- RAID — riesgos, acciones, incidentes, decisiones
- Documentos (`documents`)
- Minutas (`meeting_minutes`)
- Reportes (`reports`) — incluye el permiso `reports` hoy ausente (ver
  BUG-025 #76, rework pendiente)
- Áreas y recursos de proyecto (`project_areas`, `project_area_resources`)
- Lecciones aprendidas (`lessons`)
- Change requests, solicitudes de proyecto

**Parte 2 — Recursos administrativos restringidos:**

Los siguientes recursos **solo** son editables por usuarios con rol
`Admin` (o el futuro equivalente simplificado):

- **Organizaciones** (`organizations`)
- **Programas** (`programs`)
- **Usuarios** (`users`) — incluye alta/baja + permisos

**Parte 3 — Sin aprobaciones jerárquicas:**

- Los workflows de aprobación por jerarquía directa (`reports_to_id`)
  o por rol específico (`Senior PMO aprueba solicitudes`) **no se
  construyen**.
- Las "aprobaciones" en la plataforma (ej. solicitudes de proyecto,
  change requests) pueden ser ejecutadas por cualquier usuario PMO
  con el permiso CRUD correspondiente sobre el recurso — no hay
  jerarquía ni routing condicional.
- El concepto "solicitud" conserva su estado (`draft`, `in_review`,
  `approved`, `rejected`) porque tiene valor semántico (track del
  avance), pero **quien revisa** no está restringido por rol.

**Consecuencias:**
- **US-061 (#90) CANCELADA** — aprobaciones jerárquicas + `reports_to_id`
  quedan fuera del scope. El concepto de "aprobador específico" no
  existe.
- **US-059 (#88) re-scoped** — el modelo "Recursos = usuarios sin rol
  jerárquico" se mantiene pero simplificado: máximo 2-3 tipos de rol
  (Admin / User / Viewer opcional). No se construye granularidad por
  nivel jerárquico.
- **US-060 (#89) re-scoped** — permisos granulares solo para distinguir
  **Admin** (edita organizaciones/programas/usuarios) de **User**
  (todo lo demás libre). Incluye el permiso `reports` hoy ausente
  (rework necesario de BUG-025).
- **US-059 + US-060 se mueven de v2.0 → Sprint 4 v1.3 Bloque 4**
  (después del import XLSX/MPP del Bloque 3). Con el scope reducido,
  ya no son major overhaul y caben en el sprint actual.

**Rationale:**
- Menos pasos de navegación = más adopción. Cada check de permiso
  por rol es una línea de backend + UI + test + edge case.
- El usuario target es PM que conoce a su equipo — no hay necesidad
  de enforcement técnico de jerarquía (la jerarquía vive en el
  proceso social del cliente, no en el software).
- Auditoría se mantiene vía `audit_logs` — quién hizo qué queda
  trazable aunque no haya gate de aprobación.
- Simplifica el overhaul pendiente de Auth: de un "major overhaul
  v2.0" a una US ejecutable en el sprint actual.

**Afecta:**
- `docs/project-management/SPRINT.md` — US-059/060 suben del
  §Backlog v2.0 a Bloque 4 del Sprint 4. US-061 se cierra
  `not_planned`.
- `docs/epics/EP001-auth-users.md` — agregar sección referenciando
  DEC-020.
- `docs/epics/EP002-org-hierarchy.md` — aclarar que la jerarquía
  Organización → Programa → Proyecto sigue siendo estructura de
  datos, NO estructura de permisos.
- Issues #88, #89, #90 actualizados vía comentario.

**Alternativa descartada:** construir US-061 con `reports_to_id` +
permiso `approve_requests` y dejar la jerarquía activa. Rechazada
porque el owner la considera un anti-patrón para su caso de uso — la
plataforma debe ser asistiva, no burocrática.

Registrada 2026-04-24 mid-Sprint 4 tras el primer hotfix BUG-030.

**Update 2026-04-25 (Sprint 6):** la simplificación de roles se
mantiene, pero el mapping `(role × module × action)` propuesto por
esta decisión se reemplaza por **capability-based** (DEC-024). El rol
`viewer` queda eliminado por falta de uso real (los users del tenant
participan; nadie es read-only puro). Productivo migra a 2 roles:
`admin` + `user`, donde `admin` recibe **5 capabilities** específicas
(ver DEC-024). Migración Alembic 0028 normaliza cualquier registro
`viewer` residual a `user`.

---

## DEC-021 — SuperAdmin puede override permisos por tenant (safety net)

**Contexto:** DEC-020 declaró permisos estáticos por `role_type` en
código. Bonito para simplicidad, pero elimina cualquier flexibilidad
cuando un tenant específico necesita ajustes puntuales (dar al rol
`user` un permiso admin-only por excepción, o quitarle al `admin` un
permiso sensible). Además, BUG-031 expuso que sin vía de "rescue" el
sistema puede quedar atrapado (admin lockout irrecuperable).

**Decisión:** el mapping estático de DEC-020 sigue siendo la base. Se
agrega una capa **opcional de overrides por tenant** administrada
exclusivamente por **superadmin**:

- Tabla `tenant_role_permission_overrides (tenant_id, role_type, module, action, granted, reason, updated_by, updated_at)`.
- `CurrentUser.has(module, action)` aplica el mapping estático
  primero y los overrides del tenant actual después. Cache por
  request.
- Overrides requieren `reason` obligatoria → audit log.
- Solo superadmin (`is_superadmin=True`) puede crearlos o quitarlos.
- Superadmin sigue bypassando todo el gate, incluidos los overrides.

**Consecuencias:**
- El mapping estático sigue siendo la fuente de verdad por defecto.
  El 99% de los tenants no tiene overrides.
- Overrides = safety net + flexibilidad quirúrgica.
- Implementación en **US-073** (#126).

**Alternativa descartada:** sistema completo de RBAC editable por
admin de cada tenant. Rechazada: reintroduce la complejidad que
DEC-020 eliminó; reserva la flexibilidad para el superadmin como caso
de emergencia, no para uso normal.

Registrada 2026-04-24 tras BUG-031.

**Update 2026-04-25 (Sprint 6):** post-DEC-024 el vocabulario de
overrides cambia de `(module, action)` a **capability**. La tabla
`tenant_role_permission_overrides` se reinterpreta sin migración:
`module` ahora guarda el string de capability (ej.
`"organizations.delete"`) y `action` se setea fijo en `"grant"`. Las
filas legacy con `module:action` arbitrarios se ignoran silenciosa-
mente al cargar overrides (el cleanup formal queda para US-081 si
es necesario). El gate efectivo aplica overrides en
`CurrentUser.has_capability(name)`.

---

## DEC-022 — Namespaces de rutas: `/pmo` (negocio) vs `/admin` (sistema)

> **Promovida a [ADR-027](../adr/README.md#adr-027) el 2026-08-05.** Es
> irreversible —deshacerla exige migrar datos productivos o rompe un contrato
> público—, y MCS `ARQ-02` exige que toda decisión irreversible viva en un ADR.
> Esta entrada se conserva por la relación bidireccional que pide `CFG-18`.

**Contexto:** el admin panel mezcla recursos de negocio (proyectos,
solicitudes, RAID, minutas, reportes, organigrama informativo) con
gestión del sistema (usuarios, roles, tenant config, AI settings,
audit) todo bajo `/admin/*`. Esto confunde la navegación, duplica
entradas en sidebar (hubo 2 "PMO" post-US-068) y expone rutas CRUD
por defecto cuando muchos usuarios solo necesitan vista informativa.

**Decisión:** separar los namespaces:

- `/pmo/*` — recursos **de negocio**. Proyectos, solicitudes, RAID,
  minutas, reportes, organizations/programs en modo informativo.
  Accesible a cualquier user del tenant (permisos por operación,
  no por ruta).
- `/admin/*` — recursos **del sistema**. Tenant config, users, roles,
  AI config, audit logs. Solo `role_type=admin` o `is_superadmin`.
- `/superadmin/*` — exclusivamente `is_superadmin=True`.

**Consecuencias:**
- Refactor masivo de rutas Next.js (ver US-075 #128).
- Rutas viejas `/admin/projects/*`, `/admin/requests/*`, `/admin/raid/*`,
  etc. quedan como redirects 301 → `/pmo/...` por compat.
- `OrgTreeNav` pasa a ser visible para todos los usuarios del tenant
  (antes solo admin).
- Permisos backend: endpoints GET de `organizations`, `programs`,
  `projects` aceptan lectura de cualquier user del tenant.

**Alternativa descartada:** seguir bajo `/admin/*` y arreglar solo
los duplicados puntuales (hubiera sido el ENH-029 que se desechó).
Rechazada: no salda la deuda conceptual y requiere rework cada vez
que se agrega un recurso nuevo.

**Follow-up abierto (DEC-023):** evaluar `/{tenant_slug}/...` como
prefijo URL — no bloquea DEC-022. Tracking separado (ADR a abrir).

Registrada 2026-04-24 tras BUG-031 + inspección de navegación As-Is.

---

## DEC-024 — Modelo capability-based para permisos del admin (reemplaza matriz CRUD)

> **Promovida a [ADR-028](../adr/README.md#adr-028) el 2026-08-05.** Es
> irreversible —deshacerla exige migrar datos productivos o rompe un contrato
> público—, y MCS `ARQ-02` exige que toda decisión irreversible viva en un ADR.
> Esta entrada se conserva por la relación bidireccional que pide `CFG-18`.

**Contexto (2026-04-25, Sprint 6 kickoff):** DEC-020 simplificó el
modelo a 3 `role_type` estáticos, pero el mapping quedó expresado
como matriz `(módulo × acción CRUD)` que nunca casó con la realidad
de los endpoints. Producción quedó con 3 capas desalineadas:

1. `permissions.py` con módulos sin prefijo (`users`, `organizations`).
2. Endpoints con strings libres desconocidos por el mapping
   (`ai.generate:create`, `documents:upload`).
3. UI `/admin/roles/*` editando el JSON `Role.permissions` que
   `CurrentUser.has()` ignora por completo cuando `role_type` está
   seteado.

Resultado: un admin con "todos los checkboxes marcados" seguía
recibiendo 403 en IA y upload de documentos. El owner redefine el
scope: la herramienta es de **soporte/visualización**, no gestión
transaccional — la granularidad CRUD por módulo no aporta. Todos
los users del tenant hacen casi todo; el admin solo se encarga de
metaconfig.

**Decisión:** reemplazar la matriz `(role_type × módulo × acción)`
por un modelo **capability-based**:

- `Admin` tiene **exactamente 5 capabilities**:
  - `tenant.manage` — configuración del tenant (branding, settings).
  - `ai.configure` — proveedores y modos de IA.
  - `users.manage` — alta/edición/reset/desactivación/asignación
    role_type + asignación a orgs del tenant.
  - `organizations.delete` — **solo** borrar organizaciones.
  - `audit.read` — ver audit log del tenant.
- `User` tiene `set()` de capabilities.
- Todo lo demás (proyectos, tareas, riesgos, issues, change_requests,
  documentos, minutas, lecciones, áreas, dashboard, IA generación,
  project_requests, charters, reports, scheduled reports, importación
  de planes) → accesible a **cualquier user autenticado del tenant**.
  Sin granularidad CRUD por módulo.
- `viewer` queda **eliminado** (en la práctica no aportaba; users con
  `role_type='viewer'` se migran a `'user'` en migración 0028).

**Consecuencias:**
- Endpoints cambian de `require_permission(module, action)` a
  `require_capability(name)` o `require_authenticated()`.
- `CurrentUser.has_capability(name)` reemplaza la API conceptual de
  `has(module, action)` (esta última queda como shim compatible).
- Overrides de tenant (US-073 / DEC-021) pasan a ser por
  `capability`, no por `module:action`. Misma tabla, vocabulario
  reducido.
- UI `/admin/roles/*` + `apps/web/components/role-editor.tsx` se
  eliminan (US-077).
- Nueva página informativa `/admin/permissions` (read-only) en
  su lugar (US-078).
- Tablas `roles` + `user_roles` quedan deprecated en este sprint;
  borrado físico difere a Sprint 7 (US-081) tras validación.
- Tests de matriz `(role × endpoint) → status` en `apps/api/tests/
  test_permission_matrix.py` (US-079) previenen que vuelva a
  aparecer un endpoint huérfano del mapping.

**Alternativa descartada #1:** mantener la matriz CRUD y arreglar
solo los mismatches (`ai.generate` + `documents:upload` + UI zombie).
Rechazada: cada endpoint nuevo repite el riesgo; la matriz es más
granular de lo que el producto usa.

**Alternativa descartada #2:** quitar todo el RBAC y dejar tenant
como boundary único. Rechazada: el owner sí necesita diferenciar
admin (metaconfig) de user (operación), aunque la diferencia sea
pequeña.

**Afecta:**
- `apps/api/app/core/permissions.py` (reescritura).
- `apps/api/app/api/deps.py` (`has_capability`, `require_capability`).
- Todos los endpoints con `require_permission(...)` (~30 archivos).
- Frontend: borrado de `/admin/roles/*` + nueva `/admin/permissions`.
- Migración 0028 (backfill role_type + viewer→user).
- `docs/epics/EP001-auth-users.md`, `EP007-admin.md`, `EP010-superadmin-panel.md`
  reescritos en US-080.

**Relación con DEC-020 y DEC-021:**
- **DEC-020** (3 roles fijos, sin aprobaciones jerárquicas) se
  mantiene conceptualmente. El cambio es cómo se expresa el mapping
  (capabilities en vez de matriz CRUD).
- **DEC-021** (superadmin puede override por tenant) se mantiene.
  Vocabulario de override pasa a `capability` en vez de
  `module:action`. El modelo de la tabla
  `tenant_role_permission_overrides` ya admite este cambio sin
  migración.

Registrada 2026-04-25 tras sesión de diseño del Sprint 6 con owner.
Implementación: Sprint 6 v1.5 (US-076 a US-080). Borrado físico de
tablas legacy en Sprint 7 (US-081).

---

## DEC-025 — Catálogo cerrado de 22 secciones atómicas para todos los niveles de reporte (EP020)
**Fecha:** 2026-05-25
**Decisión:** Una única lista cerrada de 22 secciones (`report_sections.code` S-01..S-36, ver `docs/epics/drafts/EP020-secciones-atomicas.md`) compone TODOS los reportes del PMOaaS sin importar nivel (PMO / Org / Proyecto / Custom). Se cierra el dual-motor heredado de EP014 (templated Python en `operational_reports.py`) y se unifica en un motor declarativo (`app/services/reports/engine.py`) que lee `report_builder_templates.section_codes`.
**Rationale:** Una sola superficie de testing (TC-200..237), una sola pipeline de actualización del catálogo, una sola plantilla base para PDF. Los reportes operativos (US-038/039) siguen funcionando pero los nuevos pasan por el motor declarativo.
**Implementación:** US-120 (catálogo seed), US-122 (4 plantillas seed), US-123 (engine).

## DEC-026 — Dos modos de composición A/B en el motor de render (EP020)
**Fecha:** 2026-05-25
**Decisión:** El motor soporta `composition_mode='A'` ("by_section" — secciones secuenciales, items ordenados por área→fecha) y `composition_mode='B'` ("by_area" — matriz invertida que itera áreas y dentro de cada área renderiza secciones). Es una decisión de render, no de query.
**Rationale:** La estructura del Reporte de Avance (sección × área) y la del Reporte de Seguimiento (área × sección) son las únicas dos vistas que el negocio necesita; codificarlo como flag binario en la plantilla evita que cada PM reinvente layouts ad-hoc.
**Implementación:** US-123, `engine._section_by_section` y `engine._section_by_area`.

## DEC-027 — Sin snapshots históricos en v1.0 (EP020)
**Fecha:** 2026-05-25
**Decisión:** Los reportes Nivel 1/2/3/4 muestran sólo estado actual. NO se persisten snapshots periódicos de KPIs / semáforo / curva S.
**Rationale:** Snapshots requieren tabla aparte + job de captura + lógica de comparación entre cortes, todo fuera del scope de v1.0. Se evalúa en v2.0 cuando haya 3+ tenants pidiendo tendencia.
**Afectados:** S-05 tendencia, S-07 curva S, S-10 entregables formales, sparklines, "deltas vs anterior" — todos descartados de v1.0.
**Backlog:** ver `docs/project-management/SPRINT.md` → "Snapshots históricos (postergado v2.0)".

## DEC-028 — Método de cálculo de % avance configurable por tenant (EP020)
**Fecha:** 2026-05-25
**Decisión:** `tenants.settings.report_builder.progress_calculation_method` (ENH-098) acepta `by_task_count` (default), `by_duration` o `by_effort`. El servicio `progress_calculator.compute_progress_detailed()` dispatcha según el método y devuelve `fallback` cuando los datos requeridos no existen (ej. `by_effort` cae a `by_task_count` porque `tasks.hours_estimated` aún no existe).
**Rationale:** Distintos PMOs miden avance distinto; obligar a un método único genera fricción. El fallback explícito en el resultado deja claro qué se está reportando.
**Implementación:** US-121 + ENH-098 (Sprint 26), reusado por S-06/S-08/S-35 vía `engine`.

## DEC-029 — Gantt snapshot S-19 como SVG Python en v1.0; headless Playwright queda diferido (EP020)
**Fecha:** 2026-05-25
**Decisión:** El endpoint `GET /projects/{id}/gantt/snapshot` devuelve `image/svg+xml` generado 100% en Python (`app/services/reports/gantt_renderer.py`) — agrupación por WBS-N + barras + overlay de % avance. NO se usa Playwright en v1.0.
**Rationale:** Playwright en el worker agrega ~200MB a la imagen + manejo de pool de browsers + auth dance al frontend; render < 10s no garantizable para proyectos grandes. El SVG Python rinde < 1s, es embebible en `<img>` y inlineable por WeasyPrint en el PDF, y el contrato HTTP (`image/svg+xml`) queda estable para cuando se migre a screenshot real.
**Implementación:** US-132. `format=png` devuelve 501 hasta que llegue la evolución headless.
**Trigger para revisar:** dos PMs pidiendo "Gantt idéntico al de la app" o necesidad de exports a herramientas que no rendericen SVG (raro).
