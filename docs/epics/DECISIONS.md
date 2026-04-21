# DECISIONS.md — Decisiones arquitectónicas

> Claude Code: antes de proponer soluciones alternativas, verifica que no contradiga una decisión aquí registrada. Si necesitas contradecirla, documenta el cambio con fecha y rationale.

---

## DEC-001 — Tracking multi-sesión con GitHub Issues + archivos MD
**Fecha:** 2026-04-20  
**Decisión:** Issues GitHub para tracking público + archivos MD en repo para contexto de Claude Code.  
**Rationale:** Claude Code puede leer MD del repo directamente. GitHub Issues da visibilidad y búsqueda.  
**Alternativa descartada:** Solo Notion (Claude Code no tiene acceso directo).

## DEC-002 — Migración PostgreSQL → MySQL al final del roadmap
**Fecha:** 2026-04-20  
**Decisión:** EP012 es la última épica. Todo el desarrollo v1 usa PostgreSQL.  
**Rationale:** No bloquear desarrollo actual. Migrar cuando el producto esté estable.  
**Riesgo:** Algunas features de PG (RLS, pg_trgm, uuid v7) necesitan equivalentes en MySQL.

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
**Afecta:** EP016 (US-NEW-044/045 quedan SUPERSEDED); ADR-014 reemplazada por ADR-015; subdominio `ollama.pmo-aas.com` se retira de DNS; worker Dockerfile gana sidecar `tailscaled`.
**Alternativa descartada:** CF Tunnel sin Access + Basic Auth via Caddy local — sigue exponiendo el endpoint. ngrok paid — misma exposición, peor precio.
**Plan B:** Self-host Headscale si Tailscale sube precios o limita free tier.
**Referencia:** ADR-015.

## DEC-012 — Base de datos productiva v1.0 en Railway Postgres; HostGator solo para landing `www`
**Fecha:** 2026-04-21
**Decisión:** En v1.0 productiva, `DATABASE_URL` sigue apuntando a **Railway Postgres**. HostGator hostea **exclusivamente el landing/marketing** en `www.pmo-aas.com` (estático). MySQL remoto en HostGator queda **fuera de alcance v1.0**.
**Rationale:** La migración a MySQL HostGator (EP012) tiene blockers operacionales no resueltos: (1) Railway Hobby **no tiene IP estática**, impidiendo whitelist en cPanel Remote MySQL; (2) exposición del puerto MySQL a internet en shared hosting es riesgo alto; (3) queries JSONB/GENERATED/citext en el código requieren rework; (4) HostGator shared no tiene backups automáticos comparables a Railway Pro. Costo Railway prod (~$30-40/mes) vs riesgo operacional HostGator shared justifica mantener Postgres.
**Supersede parcial:** DEC-002 ("Migración PG→MySQL al final del roadmap") se recorta a "MySQL HostGator pasa a v1.1+ solo si los blockers se resuelven con infra dedicada (VPS/RDS); EP012 queda deprioritizado".
**Afecta:** EP012 US-NEW-029/030 pasan de "Bloque 14 productivo" a backlog v1.1 con scope revisado; SPRINT.md reordenado.
**Alternativa descartada:** Mover todo (API + BD) a HostGator — pierde escalabilidad Railway; VPN Railway↔HostGator — complejidad desproporcionada para MVP.
**DNS en Cloudflare (plan de rutas):**
- `app.pmo-aas.com` → CNAME Railway `web` (DNS only / nube gris).
- `api.pmo-aas.com` → CNAME Railway `api` (DNS only / nube gris).
- `www.pmo-aas.com` → A/CNAME HostGator (proxy naranja, Full SSL).
- `pmo-aas.com` (apex) → redirect 301 a `app.pmo-aas.com` (o CNAME flattening).
- `ollama.pmo-aas.com` → **retirado** (ver DEC-011).
