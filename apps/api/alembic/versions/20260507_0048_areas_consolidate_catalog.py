"""areas catálogo compartido + drop project_areas — US-103.

Revision ID: 20260507_0048
Revises: 20260507_0047
Create Date: 2026-05-07 12:00:00

Owner decisión 2026-05-07 (Opción A): el catálogo tenant `areas` /
`teams` / `actors` (US-097) es la fuente única de verdad. La tabla
`project_areas` (US-018/091) se deprecia. Se introduce
`area_assignments` para controlar qué áreas se ven desde qué
Org/Programa/Proyecto en cascada.

Cambios:
1. Crea `area_assignments(area_id, organization_id, program_id,
   project_id, is_global)` — un assignment con todos los scopes en
   NULL + is_global=true significa "área disponible globalmente"
   (ej.: PMO seed).
2. Backfill: cada `project_areas.type='area'` se promueve al catálogo
   tenant (insert en `areas` con dedup por (tenant_id, name)) y se
   crea `area_assignments` apuntando al proyecto. Equipos/recursos
   se promueven a `teams`/`actors` respectivos.
3. Repunta `tasks.area_id`, `risks.area_id`, `issues.area_id` de
   `project_areas` → `areas` (revierte 0046 + extiende). Las áreas
   ya migradas mantienen el mapeo via tabla temporal.
4. Drop `project_areas` + `project_area_resources` (junto a sus FKs).
5. Seed por tenant: área "PMO" con assignment global.
"""
from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision: str = "20260507_0048"
down_revision: str | None = "20260507_0047"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()

    # ------------------------------------------------------------------
    # 1. area_assignments
    # ------------------------------------------------------------------
    op.create_table(
        "area_assignments",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(length=36),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "area_id",
            sa.String(length=36),
            sa.ForeignKey("areas.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            sa.String(length=36),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "program_id",
            sa.String(length=36),
            sa.ForeignKey("programs.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "project_id",
            sa.String(length=36),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "is_global",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_by",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_area_assignments_area",
        "area_assignments",
        ["area_id"],
    )
    op.create_index(
        "ix_area_assignments_project",
        "area_assignments",
        ["tenant_id", "project_id"],
    )
    op.create_index(
        "ix_area_assignments_program",
        "area_assignments",
        ["tenant_id", "program_id"],
    )
    op.create_index(
        "ix_area_assignments_org",
        "area_assignments",
        ["tenant_id", "organization_id"],
    )

    # ------------------------------------------------------------------
    # 2. Backfill project_areas → areas/teams/actors + assignments.
    #
    # `project_areas` tiene type in {area, team, actor}. Estrategia:
    # - rows type=area → upsert en `areas` (por (tenant_id, name)) y
    #   crear `area_assignments` para project_id correspondiente.
    # - rows type=team con area_id → upsert en `teams` mapeando al
    #   area promovida.
    # - `project_area_resources` → upsert en `actors`, vinculados al
    #   team o area mapeada.
    # - Tasks/risks/issues: actualizan area_id apuntando al area
    #   tenant correspondiente (vía mapping project_area.id→area.id).
    # ------------------------------------------------------------------
    pa_rows = bind.execute(
        sa.text(
            "SELECT id, tenant_id, project_id, name, type, description, "
            "contact_name, contact_email, area_id, team_id, phone, "
            "is_active, created_by FROM project_areas"
        )
    ).fetchall()

    # Map project_area.id → tenant area.id (only for rows that become areas)
    pa_to_area: dict[str, str] = {}
    # Map project_area.id (team rows) → tenant team.id
    pa_to_team: dict[str, str] = {}

    # Upsert helper: dedup by (tenant_id, name) for areas.
    def _ensure_area(tenant_id: str, name: str, description: str | None,
                     created_by: str | None) -> str:
        existing = bind.execute(
            sa.text(
                "SELECT id FROM areas WHERE tenant_id=:t AND name=:n LIMIT 1"
            ),
            {"t": tenant_id, "n": name},
        ).fetchone()
        if existing:
            return existing[0]
        new_id = str(uuid4())
        bind.execute(
            sa.text(
                "INSERT INTO areas (id, tenant_id, name, description, "
                "is_active, created_by, created_at, updated_at) "
                "VALUES (:id, :t, :n, :d, true, :cb, now(), now())"
            ),
            {"id": new_id, "t": tenant_id, "n": name, "d": description, "cb": created_by},
        )
        return new_id

    def _ensure_team(tenant_id: str, area_id: str, name: str,
                     created_by: str | None) -> str:
        existing = bind.execute(
            sa.text(
                "SELECT id FROM teams WHERE tenant_id=:t AND area_id=:a "
                "AND name=:n LIMIT 1"
            ),
            {"t": tenant_id, "a": area_id, "n": name},
        ).fetchone()
        if existing:
            return existing[0]
        new_id = str(uuid4())
        bind.execute(
            sa.text(
                "INSERT INTO teams (id, tenant_id, area_id, name, "
                "is_active, created_by, created_at, updated_at) "
                "VALUES (:id, :t, :a, :n, true, :cb, now(), now())"
            ),
            {"id": new_id, "t": tenant_id, "a": area_id, "n": name, "cb": created_by},
        )
        return new_id

    def _ensure_assignment(tenant_id: str, area_id: str, project_id: str,
                           created_by: str | None) -> None:
        existing = bind.execute(
            sa.text(
                "SELECT id FROM area_assignments WHERE tenant_id=:t AND "
                "area_id=:a AND project_id=:p LIMIT 1"
            ),
            {"t": tenant_id, "a": area_id, "p": project_id},
        ).fetchone()
        if existing:
            return
        bind.execute(
            sa.text(
                "INSERT INTO area_assignments (id, tenant_id, area_id, "
                "project_id, is_global, created_by, created_at) "
                "VALUES (:id, :t, :a, :p, false, :cb, now())"
            ),
            {
                "id": str(uuid4()),
                "t": tenant_id,
                "a": area_id,
                "p": project_id,
                "cb": created_by,
            },
        )

    # Pass 1: areas
    for r in pa_rows:
        if r.type != "area":
            continue
        area_id = _ensure_area(r.tenant_id, r.name, r.description, r.created_by)
        pa_to_area[r.id] = area_id
        _ensure_assignment(r.tenant_id, area_id, r.project_id, r.created_by)

    # Pass 2: teams (need parent area)
    for r in pa_rows:
        if r.type != "team":
            continue
        if not r.area_id or r.area_id not in pa_to_area:
            # Equipo huérfano: crear área wrapper "Sin área" o skip.
            continue
        parent_area_id = pa_to_area[r.area_id]
        team_id = _ensure_team(r.tenant_id, parent_area_id, r.name, r.created_by)
        pa_to_team[r.id] = team_id

    # Pass 3: actors (from project_areas type=actor) + project_area_resources
    par_rows = bind.execute(
        sa.text(
            "SELECT id, tenant_id, area_id, user_id, name, email, role, "
            "is_active, created_by FROM project_area_resources"
        )
    ).fetchall()

    def _ensure_actor(
        tenant_id: str,
        team_id: str | None,
        user_id: str | None,
        name: str,
        email: str | None,
        phone: str | None,
        created_by: str | None,
    ) -> None:
        # Dedup by (tenant_id, email) when email present.
        if email:
            existing = bind.execute(
                sa.text(
                    "SELECT id FROM actors WHERE tenant_id=:t AND email=:e LIMIT 1"
                ),
                {"t": tenant_id, "e": email},
            ).fetchone()
            if existing:
                # Si ya existe, actualizar team_id si no lo tenía.
                if team_id:
                    bind.execute(
                        sa.text(
                            "UPDATE actors SET team_id=:tm WHERE id=:i AND team_id IS NULL"
                        ),
                        {"tm": team_id, "i": existing[0]},
                    )
                return
        bind.execute(
            sa.text(
                "INSERT INTO actors (id, tenant_id, team_id, user_id, name, "
                "email, phone, is_active, created_by, created_at, updated_at) "
                "VALUES (:id, :t, :tm, :u, :n, :e, :p, true, :cb, now(), now())"
            ),
            {
                "id": str(uuid4()),
                "t": tenant_id,
                "tm": team_id,
                "u": user_id,
                "n": name,
                "e": email,
                "p": phone,
                "cb": created_by,
            },
        )

    # actor rows in project_areas (US-091 había rows con type='actor')
    for r in pa_rows:
        if r.type != "actor":
            continue
        team_id = pa_to_team.get(r.team_id) if r.team_id else None
        _ensure_actor(
            r.tenant_id,
            team_id,
            None,
            r.name,
            r.contact_email,
            r.phone,
            r.created_by,
        )

    # project_area_resources (legacy ENH-020)
    for r in par_rows:
        team_id = None
        # area_id en project_area_resources apunta a project_areas.id
        # que puede ser type=area o type=team. Resolver:
        if r.area_id in pa_to_team:
            team_id = pa_to_team[r.area_id]
        # else: recurso colgado de un area (sin equipo) → team_id stays None
        _ensure_actor(
            r.tenant_id,
            team_id,
            r.user_id,
            r.name or (r.email or "(sin nombre)"),
            r.email,
            None,
            r.created_by,
        )

    # ------------------------------------------------------------------
    # 3. Repunta tasks.area_id / risks.area_id / issues.area_id de
    # project_areas → areas (vía pa_to_area).
    # ------------------------------------------------------------------
    # Drop FKs viejas
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_index("ix_tasks_area_id")
        batch_op.drop_constraint("fk_tasks_project_area", type_="foreignkey")

    with op.batch_alter_table("risks") as batch_op:
        # FK al project_areas — nombre puede variar; usamos drop por columna
        # mediante autogen en SQLite/Postgres robusto.
        try:
            batch_op.drop_constraint("risks_area_id_fkey", type_="foreignkey")
        except Exception:
            pass

    with op.batch_alter_table("issues") as batch_op:
        try:
            batch_op.drop_constraint("issues_area_id_fkey", type_="foreignkey")
        except Exception:
            pass

    # Update referencias usando pa_to_area
    for pa_id, area_id in pa_to_area.items():
        bind.execute(
            sa.text("UPDATE tasks SET area_id=:a WHERE area_id=:p"),
            {"a": area_id, "p": pa_id},
        )
        bind.execute(
            sa.text("UPDATE risks SET area_id=:a WHERE area_id=:p"),
            {"a": area_id, "p": pa_id},
        )
        bind.execute(
            sa.text("UPDATE issues SET area_id=:a WHERE area_id=:p"),
            {"a": area_id, "p": pa_id},
        )

    # NULL out cualquier residuo (rows que apuntaban a project_areas que no
    # eran type=area, ej. tasks asignadas a un team o actor por error).
    bind.execute(
        sa.text(
            "UPDATE tasks SET area_id=NULL WHERE area_id IS NOT NULL AND "
            "area_id NOT IN (SELECT id FROM areas)"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE risks SET area_id=NULL WHERE area_id IS NOT NULL AND "
            "area_id NOT IN (SELECT id FROM areas)"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE issues SET area_id=NULL WHERE area_id IS NOT NULL AND "
            "area_id NOT IN (SELECT id FROM areas)"
        )
    )

    # Recrear FKs apuntando a areas
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.create_foreign_key(
            "fk_tasks_area",
            "areas",
            ["area_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_tasks_area_id", ["area_id"])

    with op.batch_alter_table("risks") as batch_op:
        batch_op.create_foreign_key(
            "fk_risks_area",
            "areas",
            ["area_id"],
            ["id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table("issues") as batch_op:
        batch_op.create_foreign_key(
            "fk_issues_area",
            "areas",
            ["area_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # ------------------------------------------------------------------
    # 4. project_areas + project_area_resources se DEPRECAN pero se
    # mantienen vivas para que la UI legacy no rompa. El drop lo hace
    # ENH-078 (migración 0049) después de reescribir la página
    # `pmo/projects/[id]/areas`.
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 5. Seed PMO area por tenant + assignment global.
    # ------------------------------------------------------------------
    tenants = bind.execute(sa.text("SELECT id FROM tenants")).fetchall()
    for (tenant_id,) in tenants:
        existing = bind.execute(
            sa.text("SELECT id FROM areas WHERE tenant_id=:t AND name='PMO' LIMIT 1"),
            {"t": tenant_id},
        ).fetchone()
        if existing:
            pmo_id = existing[0]
        else:
            pmo_id = str(uuid4())
            bind.execute(
                sa.text(
                    "INSERT INTO areas (id, tenant_id, name, description, "
                    "is_active, created_at, updated_at) "
                    "VALUES (:id, :t, 'PMO', "
                    "'Project Management Office (área default global)', "
                    "true, now(), now())"
                ),
                {"id": pmo_id, "t": tenant_id},
            )
        # Global assignment (project/program/org NULL + is_global true)
        already = bind.execute(
            sa.text(
                "SELECT id FROM area_assignments WHERE tenant_id=:t AND "
                "area_id=:a AND is_global=true LIMIT 1"
            ),
            {"t": tenant_id, "a": pmo_id},
        ).fetchone()
        if not already:
            bind.execute(
                sa.text(
                    "INSERT INTO area_assignments (id, tenant_id, area_id, "
                    "is_global, created_at) VALUES (:id, :t, :a, true, now())"
                ),
                {"id": str(uuid4()), "t": tenant_id, "a": pmo_id},
            )


def downgrade() -> None:
    # Re-repunta tasks/risks/issues a project_areas (revierte parcial).
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_index("ix_tasks_area_id")
        batch_op.drop_constraint("fk_tasks_area", type_="foreignkey")
    op.execute("UPDATE tasks SET area_id=NULL")
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.create_foreign_key(
            "fk_tasks_project_area",
            "project_areas",
            ["area_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_tasks_area_id", ["area_id"])

    with op.batch_alter_table("risks") as batch_op:
        try:
            batch_op.drop_constraint("fk_risks_area", type_="foreignkey")
        except Exception:
            pass
    op.execute("UPDATE risks SET area_id=NULL")
    with op.batch_alter_table("risks") as batch_op:
        batch_op.create_foreign_key(
            "risks_area_id_fkey",
            "project_areas",
            ["area_id"],
            ["id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table("issues") as batch_op:
        try:
            batch_op.drop_constraint("fk_issues_area", type_="foreignkey")
        except Exception:
            pass
    op.execute("UPDATE issues SET area_id=NULL")
    with op.batch_alter_table("issues") as batch_op:
        batch_op.create_foreign_key(
            "issues_area_id_fkey",
            "project_areas",
            ["area_id"],
            ["id"],
            ondelete="SET NULL",
        )

    op.drop_index("ix_area_assignments_org", table_name="area_assignments")
    op.drop_index("ix_area_assignments_program", table_name="area_assignments")
    op.drop_index("ix_area_assignments_project", table_name="area_assignments")
    op.drop_index("ix_area_assignments_area", table_name="area_assignments")
    op.drop_table("area_assignments")
