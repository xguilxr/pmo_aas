# DB-CHANGES.md — Cambios de schema por epic

> Claude Code debe leer este archivo antes de implementar cualquier US que toque la BD.
> Convención: una migración Alembic por US. Nunca combinar múltiples cambios estructurales en un solo archivo.

---

## EP002 — Jerarquía Org (CAMBIO MAYOR — BLOQUEANTE)

### Nueva tabla: `business_units`
```sql
CREATE TABLE business_units (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    organization_id uuid NOT NULL REFERENCES organizations(id),
    name text NOT NULL,
    description text,
    is_active bool DEFAULT true,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    deleted_at timestamptz,
    created_by uuid REFERENCES users(id),
    UNIQUE(tenant_id, organization_id, name)
);
CREATE INDEX idx_bu_org ON business_units(organization_id) WHERE deleted_at IS NULL;
```

### Nueva tabla: `departments`
```sql
CREATE TABLE departments (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    business_unit_id uuid NOT NULL REFERENCES business_units(id),
    name text NOT NULL,
    description text,
    is_active bool DEFAULT true,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    deleted_at timestamptz,
    created_by uuid REFERENCES users(id),
    UNIQUE(tenant_id, business_unit_id, name)
);
CREATE INDEX idx_dept_bu ON departments(business_unit_id) WHERE deleted_at IS NULL;
```

### Modificar tabla: `programs`
```sql
-- PASO 1: Agregar columna nullable
ALTER TABLE programs ADD COLUMN department_id uuid REFERENCES departments(id);
-- PASO 2: (post-migración de datos) hacer NOT NULL si aplica
-- NOTA: programs puede colgar de org directamente O de department
-- Decisión: department_id nullable, al menos uno de (organization_id, department_id) debe estar presente
-- organization_id se conserva para compatibilidad y para orgs sin BU/Depto configurado
```

### Modificar tabla: `projects`
```sql
-- Agregar referencia opcional a department (cuando no pasa por programa)
ALTER TABLE projects ADD COLUMN department_id uuid REFERENCES departments(id);
ALTER TABLE projects ADD COLUMN business_unit_id uuid REFERENCES business_units(id);
-- Ambas nullable — se llenan desde la cadena del programa si existe
```

### Modificar tabla: `project_requests`
```sql
-- business_unit y department pasan de text libre a FK real
ALTER TABLE project_requests ADD COLUMN business_unit_id uuid REFERENCES business_units(id);
ALTER TABLE project_requests ADD COLUMN department_id uuid REFERENCES departments(id);
-- Mantener columnas text antiguas como deprecated hasta migración de datos
-- ALTER TABLE project_requests DROP COLUMN business_unit; -- PENDIENTE, fase 2
-- ALTER TABLE project_requests DROP COLUMN department;    -- PENDIENTE, fase 2
```

---

## EP003 — Project Requests + Charter

### Modificar tabla: `project_requests`
```sql
ALTER TABLE project_requests ADD COLUMN requester_name text;      -- default: user.full_name
ALTER TABLE project_requests ADD COLUMN requester_email citext;   -- default: user.email
ALTER TABLE project_requests ADD COLUMN sponsor_email citext;
ALTER TABLE project_requests ADD COLUMN key_people text;          -- texto libre, lista de nombres
ALTER TABLE project_requests ADD COLUMN if_not_done text;         -- "¿Qué pasa si no se hace?"
ALTER TABLE project_requests ADD COLUMN observations text;
ALTER TABLE project_requests ADD COLUMN entregables text;         -- renombrar scope o complementar
```

### Nueva tabla: `project_charters`
```sql
CREATE TABLE project_charters (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    project_id uuid NOT NULL REFERENCES projects(id) UNIQUE,
    request_id uuid REFERENCES project_requests(id),

    -- Sección 1: Información General (se llena desde proyecto/solicitud)
    project_name text NOT NULL,
    description text,
    organization_id uuid REFERENCES organizations(id),
    business_unit_id uuid REFERENCES business_units(id),
    department_id uuid REFERENCES departments(id),

    -- Sección 2: Stakeholders
    sponsor text,
    sponsor_email citext,
    business_leader text,
    business_leader_email citext,
    tech_leader text,
    tech_leader_email citext,
    pm_id uuid REFERENCES users(id),

    -- Sección 3: Clasificación
    project_type text,
    priority smallint,
    objective text,
    restrictions text,
    risks_summary text,
    scope text,
    key_people text,
    benefits text,

    -- Sección 4: Datos de Gestión (se actualiza dinámicamente desde el proyecto)
    start_date date,
    estimated_end_date date,
    phase text,
    health_status text,
    progress smallint,
    planned_progress smallint,
    assigned_budget numeric(14,2),
    used_budget numeric(14,2),
    assigned_hours numeric(10,2),
    consumed_hours numeric(10,2),

    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    created_by uuid REFERENCES users(id)
);
```

---

## EP005 — Projects

### Nueva tabla: `project_areas`
```sql
-- Actores y áreas del proyecto (sin acceso a plataforma, solo referenciables)
CREATE TABLE project_areas (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    project_id uuid NOT NULL REFERENCES projects(id),
    name text NOT NULL,
    type text DEFAULT 'area',   -- 'area' | 'actor' | 'team'
    description text,
    contact_name text,
    contact_email citext,
    is_active bool DEFAULT true,
    created_at timestamptz DEFAULT now(),
    created_by uuid REFERENCES users(id)
);
CREATE INDEX idx_project_areas_project ON project_areas(project_id);
```

---

## EP006 — RAID consolidado

### Modificar tabla: `issues`
```sql
-- Actualmente type = 'action'|'issue'|'decision'
-- Agregar 'incident' para completar RAID
-- El tipo 'action' = Acciones, 'issue' = Incidentes, 'decision' = Decisiones
-- RAID = Risks (tabla risks) + Actions + Incidents + Decisions (tabla issues con type)
-- No requiere cambio de schema, solo validar que type acepta los 4 valores
-- Documentar: RAID se construye combinando risks + issues con sus types
```

---

## EP011 — Notificaciones

### Nueva tabla: `notifications`
```sql
CREATE TABLE notifications (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    user_id uuid NOT NULL REFERENCES users(id),
    type text NOT NULL,         -- 'request_approved'|'request_rejected'|'pm_assigned'|
                                --  'aid_overdue'|'comment_added'|'phase_changed'|etc.
    title text NOT NULL,
    body text,
    entity_type text,           -- 'project'|'risk'|'request'|etc.
    entity_id uuid,
    link text,                  -- URL relativa a la que navegar al click
    is_read bool DEFAULT false,
    read_at timestamptz,
    created_at timestamptz DEFAULT now()
);
CREATE INDEX idx_notif_user_unread ON notifications(user_id, is_read, created_at DESC)
    WHERE is_read = false;
CREATE INDEX idx_notif_tenant ON notifications(tenant_id, created_at DESC);
```

---

## EP010 / EP007 — Sin cambios de BD nuevos
Los cambios de EP007 (gestión de tenant/org) usan tablas existentes.
EP010 ya tiene sus tablas en el archivo original.

---

## EP012 — Migración MySQL (planificar al final)
Ver EP012-db-migration.md para el plan completo.
Impactos principales:
- RLS de PostgreSQL no existe en MySQL → implementar filtros en ORM
- `gen_random_uuid()` → `UUID()` en MySQL
- `citext` → `VARCHAR COLLATE utf8mb4_unicode_ci`
- `pg_trgm` (fuzzy search) → `FULLTEXT INDEX` en MySQL
- `GENERATED ALWAYS AS ... STORED` → trigger o columna calculada en app
- Alembic funciona con MySQL, solo cambiar dialect
