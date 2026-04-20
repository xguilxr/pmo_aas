# Seed de datos demo (`seed_demo.py`)

Script para poblar los tenants existentes (`acme`, `globex`) con datos dummy
que simulan una app en uso. Util para demos, QA manual y pruebas de UI.

Ubicacion: `apps/api/app/scripts/seed_demo.py`

## Requisitos previos

1. Migraciones alembic aplicadas (`alembic upgrade head`).
2. Bootstrap seed ya corrido (`SEED_ON_STARTUP=true` al menos una vez, o
   `app.services.seed.run_initial_seed`). Esto garantiza que existan:
   - tenants `acme` y `globex`
   - los 4 roles sistema por tenant (Administrador, PMO Manager, Project Manager, Viewer)
   - el usuario `admin` de cada tenant

Si alguno de los requisitos falta, el script lanza un `RuntimeError` con un
mensaje claro.

## Como ejecutar

```bash
cd apps/api
python -m app.scripts.seed_demo
```

La variable `DATABASE_URL` (o equivalentes en `app/core/config.py`) debe
apuntar a la misma DB donde corrio el bootstrap.

El script es **idempotente**: cada objeto se crea solo si no existe (chequeos
por `slug`/`name`/`username`/`folio`). Se puede correr varias veces sin
duplicar datos.

## Que genera (por cada tenant acme y globex)

### Usuarios (1 por rol)
| Username        | Email                          | Rol              | Password        |
|-----------------|--------------------------------|------------------|-----------------|
| `admin`         | `admin@<slug>.pmoaas.local`    | Administrador    | (bootstrap seed) |
| `pmo.<slug>`    | `pmo@<slug>.pmoaas.local`      | PMO Manager      | `Demo1234!Seed` |
| `pm.<slug>`     | `pm@<slug>.pmoaas.local`       | Project Manager  | `Demo1234!Seed` |
| `viewer.<slug>` | `viewer@<slug>.pmoaas.local`   | Viewer           | `Demo1234!Seed` |

Todos los usuarios nuevos tienen `must_change_password=True`: en el primer
login, el flujo forzara el cambio de contraseña.

### Organizaciones (2)
- `<Slug> Digital` — industria Tecnologia
- `<Slug> Operaciones` — industria Servicios

### Programas (2, uno por organizacion)
- `Transformacion Digital 2026` (en `<Slug> Digital`)
- `Excelencia Operativa` (en `<Slug> Operaciones`)

### Proyectos (8)
- 4 proyectos en `Transformacion Digital 2026`:
  `Portal de clientes v2`, `Motor de recomendaciones IA`, `Migracion a cloud`,
  `App movil empleados`.
- 3 proyectos en `Excelencia Operativa`:
  `Automatizacion de nomina`, `Dashboards de operacion`, `Integracion ERP-CRM`.
- 1 proyecto standalone (sin programa): `Iniciativa independiente`.

Cada proyecto cubre combinaciones distintas de `type` (innovation/transformation/
operation/bau), `phase` (planning/execution/support) y `health_status`
(green/yellow/red), para que los dashboards tengan variedad visual.

Todos los proyectos reciben 3 `project_members`: `pm` (pm.<slug>),
`viewer` (viewer.<slug>) y `stakeholder` (pmo.<slug>).

### Solicitudes (`project_requests`) — una por cada status
- `in_review` — pendiente de revision.
- `approve` — aprobada, con `reviewed_by`, `reviewed_at` y `review_comment`.
- `reject` — rechazada, con comentario de rechazo.
- `needs_info` — pide informacion adicional.

### RAID + extras sobre el primer proyecto
Sobre `Portal de clientes v2 (<slug>)` se crea al menos uno de cada:
- **Risk** — status `mitigating`, con probability/impact/severity y owner.
- **Issue** (type=`issue`) — status `in_progress`.
- **Action** (Issue type=`action`) — status `open`.
- **Decision** (Issue type=`decision`) — status `resolved`.
- **Change Request** — type=`scope`, status `in_review`.
- **Document** — category `plan`, version 1, `is_current=true`.
- **Lesson Learned** — category `improvement`, con tags.
- **Meeting Minute** — kickoff con participantes, topics y agreements.

### Tasks
Sobre el primer proyecto se crean 5 tareas con WBS 1–5 (`Descubrimiento`,
`Diseño`, `Implementacion`, `Pruebas y UAT`, `Go-live`), con duracion,
progreso parcial y 2 milestones.

## Credenciales resumen

Al terminar, el script imprime un banner con los usuarios creados. El password
demo es **`Demo1234!Seed`** y cumple la policy minima (12+ chars, mayuscula,
digito, simbolo).

## Limpieza / re-seed

El script no borra nada. Si necesitas empezar de cero, lo recomendable es
truncar o re-crear la DB y volver a correr `alembic upgrade head` +
`run_initial_seed` + `seed_demo`.

Para borrar solo datos demo (sin tocar tenants/roles/admin), puedes filtrar
por los nombres conocidos (`<Slug> Digital`, `<Slug> Operaciones`, proyectos
con el sufijo `(<slug>)`, usernames `pmo.<slug>`, `pm.<slug>`,
`viewer.<slug>`), pero hazlo con cuidado: los proyectos tienen FK en cascada
hacia RAID y tasks.

## Referencia de schema

El script se apoya en los siguientes modelos (ver `apps/api/app/models/`):
`Tenant`, `User`, `Role`, `UserRole`, `Organization`, `Program`, `Project`,
`ProjectMember`, `ProjectRequest`, `FolioSequence`, `Risk`, `Issue`,
`ChangeRequest`, `Document`, `Lesson`, `MeetingMinute`, `Task`.

Los folios (`PROJ-YYYY-NNN`, `REQ-...`, `RISK-...`, `ISS-...`, `CHG-...`,
`DOC-...`, `LES-...`, `MIN-...`) se generan con `app.services.folio.next_folio`
para respetar la unicidad por `(tenant_id, prefix, year)`.
