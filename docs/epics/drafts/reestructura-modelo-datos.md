---
tipo: gestion
responsable: propietario
estado: borrador
revisado: 2026-08-29
revisar_cada: 30d
---

# Reestructura — Fase 1: Modelo de datos objetivo y migración

> Diseño original del 2026-08-19. Cada oleada, al implementarse, registra su
> cambio en `DB-CHANGES.md` y sus decisiones en `DECISIONS.md`/ADR como manda
> `CLAUDE.md` §0.2. Base: el árbol de `reestructura-conceptos.md` y los
> hallazgos de `reestructura-inventario.md` (archivado — su propósito ya se
> cumplió). Convenciones heredadas: IDs `String(36)` UUID, `TimestampMixin`,
> `tenant_id` indexado, soft-delete con `deleted_at` donde ya existe.

## Estado real, oleada por oleada (verificado contra código, 2026-08-29)

| Oleada | Estado | Nota |
|---|---|---|
| **W1** | ✅ Hecho | `portfolios`, FKs, enum `type`, fases en español — ADR-037/038, migraciones 0108-0111 |
| **W2** | 🟡 Parcial | `user_tenant_memberships` + email global sí (US-214, mig. 0115). `active_organization_id` en el JWT y el endpoint `switch-context` **no se construyeron así**: el contexto de organización activa vive del lado del cliente (`organizacion-activa.tsx`), no como claim de sesión |
| **W3 — RLS** | ⛔ No hecho | Cero `CREATE POLICY` en todas las migraciones. Tiene issues abiertos: #599, #600, #601 (US-240/241/242) |
| **W4** | 🟡 Parcial | Costo-snapshot en participaciones sí (US-215, mig. 0114). `actors.organization_id` **sigue nullable** — el endurecimiento a NOT NULL no se hizo |
| **W5** | 🟡 Parcial | `metric_snapshots` sigue en cadencia semanal, no bi-semanal; sin confirmar el scope `portfolio` explícito. La salud explicable y `HealthWhyPanel` sí están vivos |
| **W6** | 🟡 Parcial | `plan_baselines` (US-212) y `project_dependencies` (US-218) sí. La campaña de RLS de este dominio depende de W3 |
| **W7** | ⛔ Superado, no construido | Ninguna de las cuatro tablas (`ai_agent_roles`, `ai_skills`, `tenant_ai_providers`, `subscription_plans`) existe. Y **la parte de roles de IA no se va a construir así**: el owner decidió lo contrario en EP021 (DEC-033, 2026-08-20) — el agente actúa siempre en nombre de una persona, con las capacidades y el alcance de esa persona; «roles con permisos propios» habría sido un segundo sistema de autorización, y se descartó por eso, no por falta de tiempo. La parte de suscripción se resolvió distinto también: US-221 lee los topes de `tenants.settings.plan` (JSON), no de una tabla `subscription_plans`, y es de solo lectura — sin el enforcement que este documento daba por sentado |
| **W8** | ⛔ No hecho | `business_units`/`departments` siguen en el schema, a propósito: esperan a que el contador de compat confirme que nadie las usa |

El resto de este documento es el diseño original de 2026-08-19, sin editar —
sigue siendo la referencia técnica para W3, el resto de W5 y W8 cuando se
retomen. **La sección 6 sobre roles de IA (W7) es la excepción: no se
construya tal cual está escrita** — ver la fila de arriba.

## 1. Jerarquía organizacional

### 1.1 Nueva tabla `portfolios`

```
portfolios
  id, tenant_id FK, organization_id FK NOT NULL
  name (unique por org), code?, description?, owner_actor_id? FK actors
  is_active, deleted_at, created_by, timestamps
```

Sin métricas propias: salud/presupuesto/conteos agregados se derivan de los
proyectos (igual que hoy hace el dashboard con orgs).

### 1.2 `programs` — re-parenting

- `+ portfolio_id FK NOT NULL` → `portfolios.id` (nace nullable en la
  migración, se backfillea, se endurece a NOT NULL en la misma oleada).
- `- department_id` (ventana de compatibilidad, ver §8).
- `organization_id` se conserva (redundante con portfolio→org pero evita
  joins en todo el filtrado existente; CHECK de consistencia en app).

### 1.3 `projects`

- `+ portfolio_id FK NULL` → puede tener portafolio sin programa.
- `- business_unit_id`, `- department_id` (ventana de compat).
- **Regla de consistencia** (validación en service + CHECK diferido):
  `program_id IS NOT NULL ⇒ portfolio_id = program.portfolio_id`. Al
  asignar programa, el portafolio se autocompleta; no se aceptan pares
  incoherentes.
- `type`: de `String(50)` libre → enum `transformacion | operacion |
  innovacion | bau` (+ ventana de compat para valores libres existentes).
- `phase`: mapeo de vocabulario (decisión sobre ADR-019/022):
  `planning → preparacion`, `execution → ejecucion`, `closed → cerrado`,
  `cancelled → cancelado`. **Propuesta**: `hypercare` se conserva como fase
  propia entre ejecución y cierre (es real en la operación y ya tiene
  semántica en reportes). Fase de "solicitud" NO es fase del proyecto: vive
  en `project_requests.status` — el proyecto nace en `preparacion`.
- `+ included_in_initial_portfolio bool` (onboarding masivo, cliente 23).
- `sponsor` hoy es `String(200)`: se mantiene texto en esta fase; vincularlo
  a `actors` es candidato de oleada posterior (junto a consolidación §7).

### 1.4 Migración de datos BU/Depto — decidido (owner 2026-08-19)

**BU/Departamentos no tienen uso en producción** (owner: «no he utilizado
BU/Departamentos»), así que no hay datos que mapear: Portafolio/Programa los
**reemplazan directamente**. La migración se simplifica:

- W1 crea `portfolios` sin backfill desde BU; los programas existentes se
  asignan a un **«Portafolio General»** autocreado por organización (para
  poder endurecer `portfolio_id NOT NULL`).
- `projects.business_unit_id/department_id` y las columnas de solicitudes/
  charter se retiran directo (verificar en la migración que estén vacías;
  si aparece algún dato residual, se vuelca a un JSON de auditoría antes de
  soltar la FK).
- Las tablas `business_units`/`departments` quedan sin lectores tras W1 y se
  dropean en W8 (drop = irreversible → ADR; sin ventana de compat larga al
  no haber datos).

## 2. Identidad multi-tenant

### 2.1 Nueva tabla `user_tenant_memberships`

```
user_tenant_memberships
  id, user_id FK users, tenant_id FK tenants
  role_type ('admin' | 'pm_sr' | 'user')   ← se muda desde users.role_type
  is_default bool, is_active bool, timestamps
  UNIQUE (user_id, tenant_id)
```

### 2.2 `users` — globalización

- `email`/`username` pasan de unique-por-tenant a **unique global**
  (pre-chequeo de colisiones antes de migrar; colisión = mismo humano en
  dos tenants → se fusiona en un user con dos membresías, o se renombra).
- `tenant_id` y `role_type` quedan como ventana de compat (lectura de
  fallback) y se retiran al cerrar; la verdad pasa a la membresía.
- `organization_user_exclusions` (modelo opt-out) se retira; la visibilidad
  queda en `user_scope_assignments` (opt-in explícito, ya existe) validada
  contra la membresía del tenant activo.

### 2.3 Sesión y JWT

- Claims: `tenant_ids` (ya existe) + `active_tenant_id` (ya existe) +
  **`active_organization_id`** (nuevo, nullable = todas las asignadas).
- `POST /auth/switch-tenant` se generaliza a `switch-context`
  (tenant y/u organización); re-emite el JWT sin re-login.
- `CurrentUser.effective_tenant_id` deja de mirar `users.tenant_id` y
  resuelve por membresía (compat: fallback a la columna vieja mientras viva).

## 3. RLS en Postgres (materializa ADR-003)

Defensa en profundidad — el filtrado ORM se conserva; RLS ataja el bug que
lo omita:

1. La dependencia de sesión de DB ejecuta
   `SET LOCAL app.tenant_id = :tid` con el `effective_tenant_id` del request
   (y un rol de conexión sin `BYPASSRLS`).
2. Por tabla tenant-scoped: `ENABLE ROW LEVEL SECURITY` + policy
   `USING (tenant_id = current_setting('app.tenant_id', true))`.
3. Rollout **incremental por dominio** (una migración por oleada de tablas,
   empezando por jerarquía y proyectos), con test de trinquete que enumera
   las tablas con policy y falla si una tabla nueva con `tenant_id` nace sin
   ella.
4. Prerrequisito: FKs de `tenant_id` faltantes (tasks, ai_jobs, reports,
   módulos `_ModuleBase`) se añaden en la misma pasada.
5. Superadmin/jobs de plataforma: rol de conexión aparte o
   `app.tenant_id = '*'` contemplado en la policy — decidir en la
   implementación; nunca `BYPASSRLS` en el rol del API.

## 4. Recursos y capacity

- `actors.organization_id`: de nullable → **NOT NULL** (el catálogo es por
  organización). Actors globales existentes (`NULL`) se asignan a la org
  correspondiente (si el tenant tiene una) o exigen decisión por dato en
  tenants multi-org — reporte previo a la migración.
- `project_participations`:
  - `+ cost_rate_snapshot Numeric(12,2)?` + `+ cost_currency String(3)?` —
    congelados desde `actors.fte_cost_rate` **al crear/activar** la
    asignación; nunca recalculados. Backfill de filas existentes: rate
    actual del actor (única fuente disponible; se documenta la salvedad).
  - `allocation_pct`, periodo y status ya existen — sin cambio.
- `area_assignments` (cascada org/program/project): `+ portfolio_id?` como
  nivel de cascada nuevo entre org y program.
- Dependencias entre proyectos: nueva `project_dependencies`
  `(tenant_id, predecessor_project_id, successor_project_id, type,
  milestone_id?, note)` — alimenta roadmap consolidado.
- Baseline del plan: nueva `plan_baselines`
  `(tenant_id, project_id, name, captured_at, captured_by)` +
  `plan_baseline_tasks` (snapshot inmutable por tarea: fechas, duración,
  wbs). `tasks.is_key_milestone bool` nuevo.

## 5. Snapshots, salud y completitud

- **Snapshot bi-semanal**: se extiende `metric_snapshots` (ya soporta scope
  tenant/org/program/project) con: `+ scope portfolio`, `+ cadence
  ('weekly'|'biweekly'|'ondemand')` y un scheduler que lo capture
  bi-semanalmente por tenant (config en settings). Nueva tabla
  `project_report_snapshots` para la parte narrativa del corte bi-semanal:
  `(project_id, period_start/end, health_calculated, health_declared,
  divergence_reason?, pm_commentary, changes_since_last JSON, new_risks
  JSON, decisions_required JSON, next_milestones JSON, submitted_by/at)`.
- **Salud explicable**: pesos por dimensión configurables por tenant en
  `tenants.settings.health_weights` (validado por schema tipado, mismo
  patrón que `report_builder`); el motor (`services/project_health.py`)
  expone el desglose del cálculo (ya hay `HealthWhyPanel` en UI).
  `health_source/health_reason` ya cubren declarada-vs-calculada; el
  historial declarado ya vive en `project_health_evaluations` — falta
  persistir la **calculada** en cada snapshot (columna en
  `project_report_snapshots`, arriba).
- **Completitud**: derivada, no almacenada — servicio que evalúa el
  checklist (sponsor, PM, plan, recursos, presupuesto, próxima fecha de
  reporte, salud actualizada, RAID con owner/fecha) y se persiste solo
  dentro del snapshot bi-semanal para tendencia. Sin tabla propia.

## 6. IA y suscripción

> **La parte de roles de IA de esta sección NO se construyó así, por
> decisión explícita del owner (DEC-033, EP021, 2026-08-20): el agente actúa
> siempre en nombre de una persona, con sus capacidades y su alcance — nunca
> con permisos propios. `allowed_capabilities JSON` de abajo habría sido
> exactamente el segundo sistema de autorización que esa decisión descarta.
> Se conserva el texto original por trazabilidad, no como diseño vigente.**

- Catálogo IA (scope plataforma/tenant/org por columna `scope` + FK
  nullable):
  - `ai_agent_roles` — personalidades del agente: `name, description,
    system_prompt, allowed_capabilities JSON` (permisos propios del agente,
    paralelos al RBAC humano, evaluados por el mismo gate fail-closed).
  - `ai_skills` (`name, kind ('skill'|'tool'|'prompt'|'workflow'),
    definition JSON, version, is_active`) — una tabla, no cuatro: el `kind`
    discrimina y la definición es JSON validado por tipo.
- BYOK: sale de `tenants.settings.ai.byo` a tabla `tenant_ai_providers`
  `(tenant_id, provider, model, api_key_encrypted, is_default, limits
  JSON)` — permite N proveedores y override por org/proyecto después.
- Suscripción: `subscription_plans`
  `(code ('free'|'pro'|'enterprise'), name, max_organizations,
  max_projects, max_users, ai_limits JSON, price?)` + seed de los 3 planes
  (free = 1 org / 3 proyectos **sumados por tenant**) +
  `tenants.plan_code FK` (default `free`). Enforcement: validación en los
  endpoints de creación (org/proyecto/usuario) — sin paywall ni billing.

## 7. Consolidaciones de paso (deuda)

| Duplicado | Sobrevive | Se retira | Cómo |
|---|---|---|---|
| `documents` vs `project_artifacts` | project_artifacts | documents | Migrar filas vigentes como artefactos tipo `legacy`; endpoint `/documents` a compat |
| `project_members` vs `project_participations` | participations | project_members | Backfill: member sin participación → participación con rol equivalente |
| `stakeholders` vs `actors` | actors | stakeholders | Stakeholder → actor `resource_type='stakeholder'` sin capacidad; tabla a compat |
| `roles`/`user_roles` (deprecated DEC-024) | — | ambas | Drop directo (ya sin lectores; cerrar US-081) |

## 8. Estrategia de migración — oleadas

Cada oleada = un bloque de despliegue compatible hacia atrás (el código
n−1 sigue funcionando), con su ventana de compat medida por
`core/compatibilidad.py` donde aplique. Migraciones consecutivas, 1 lane
(CLAUDE.md §8). El **drop** de lo viejo siempre va en W8, nunca en la
oleada que lo sustituye.

| Oleada | Contenido | Compat que abre |
|---|---|---|
| **W1** | `portfolios` + FKs en programs/projects + backfill BU→portafolio (opción A) + regla de consistencia + enum `type` + rename de fases | `bu_depto_readonly`, `project_type_libre`, `phase=planning` (ya abierta) |
| **W2** | `user_tenant_memberships` + email global + claim `active_organization_id` + `switch-context` | `users.tenant_id`, `org_exclusions` |
| **W3** | FKs de tenant_id faltantes + RLS dominio jerarquía/proyectos + trinquete CI | — |
| **W4** | `actors.organization_id NOT NULL` + costo-snapshot en participations + cascada portafolio en area_assignments | `actors_global` |
| **W5** | Snapshot bi-semanal (`metric_snapshots` ext + `project_report_snapshots`) + pesos de salud + completitud + scheduler | — |
| **W6** | `plan_baselines` + `project_dependencies` + `is_key_milestone` + RLS dominio módulos | — |
| **W7** | Catálogo IA (`ai_agent_roles`, `ai_skills`, `tenant_ai_providers`) + `subscription_plans` + enforcement + RLS resto | `byok_settings_json` |
| **W8** | Cierre de ventanas: drop BU/depto, users.tenant_id, documents, project_members, stakeholders, roles viejos | cierra todas |

W1–W2 desbloquean todo el frontend nuevo (Fase 2 puede correr en paralelo
desde W2). W3 (RLS) es independiente del producto visible y puede
intercalarse. El orden W4→W7 es ajustable por prioridad de bloques B2–B10
del plan.

## 9. Decisiones que requieren registro al implementar

| Decisión | Instrumento | Por qué |
|---|---|---|
| Jerarquía org→portafolio⊃programa; retiro de BU/depto | **ADR nuevo** (supersede ADR-024 parcial, ADR-016, ENH-190) | Irreversible: migra datos productivos |
| Mapeo de datos BU/depto (opción A vs B de §1.4) | mismo ADR | Define qué ven los tenants al día siguiente |
| Activación de RLS + modelo de sesión (`app.tenant_id`) | **ADR nuevo** (materializa ADR-003) | Contrato de seguridad de la plataforma |
| Usuario global + membresía M:N | **ADR nuevo** | Rompe unique-por-tenant (contrato de datos) |
| Vocabulario de fases (mapear, conservar `hypercare`) | DECISIONS.md (supersede ADR-019/022 en vocabulario) | Reversible con renames |
| Levantar veto "portafolio" del glosario (ADR-021) | DECISIONS.md | Actualización de vocabulario |
| Roles de agente IA con capabilities propias | DECISIONS.md | Extiende DEC-024, no lo reemplaza |
| Planes de suscripción (schema sin billing) | DECISIONS.md | Reversible |

## 10. Qué valida cada oleada (gate de cierre)

- Migración con `upgrade` y `downgrade` reales; smoke sobre copia de datos
  productivos para W1/W2/W4 (backfills).
- Trinquetes: matriz de permisos, guard de irreversibles, y el nuevo
  trinquete RLS (§3.3) desde W3.
- Contadores de compat en cero antes de que W8 dropee nada.
