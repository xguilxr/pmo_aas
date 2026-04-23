# DECISIONS.md — Decisiones arquitectónicas

> Claude Code: antes de proponer soluciones alternativas, verifica que no contradiga una decisión aquí registrada. Si necesitas contradecirla, documenta el cambio con fecha y rationale.

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
**Fecha:** 2026-04-20  
**Decisión:** RAID = tabla `risks` (R) + tabla `issues` con types: action(A), incident(I), decision(D).  
**No se crea** una tabla `raid` nueva. Solo se agrega UI que agrupe las 4 fuentes bajo el tab RAID.  
**Rationale:** Schema existente ya soporta los 4 tipos, evita duplicación de datos.

## DEC-008 — Project Charter es una tabla separada (no documento PDF guardado)
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
