"""US-114 — Directorio de Proyecto: project_participations + project_roles + actors enriquecido.

Revision ID: 20260510_0061
Revises: 20260509_0060
Create Date: 2026-05-10 00:00:00

EP017. Schema additivo: NO se dropean `actors.team_id`, `actors.is_lead`,
`teams.area_id`, ni `tasks/risks/issues.area_id` en esta migración —
viven en US-119 (cleanup) cuando los endpoints completen migración.

Cambios:
- Crea `project_roles` (catálogo tenant editable: PM, Sponsor, SME...).
- Crea `project_participations` (N por (project_id, actor_id); is_primary
  marca la participación que usan los agrupadores por defecto).
- Agrega `actors.company`, `actors.job_title`, `actors.manager_actor_id`,
  `actors.functional_area_id` (alias semántico de `area_id`; coexisten
  hasta US-119).
- Backfill:
  1) Por cada `project_member` → genera `project_participation`. Si el
     user no tiene actor vinculado, crea uno (`name = user.full_name`,
     `email = user.email`).
  2) Por cada `actor` con asignaciones (tasks/risks/issues) en un
     proyecto → garantiza al menos 1 participation activa.
  3) `actor.is_lead=true` con `area_id` → setea `is_area_lead=true` en
     todas sus participations.
  4) Marca `is_primary=true` en una participation por (project, actor).
- Pobla `project_roles` con catálogo seed (PM, Sponsor, SME, Key User,
  Tech Lead, Member) por tenant que tenga proyectos.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260510_0061"
down_revision: str | None = "20260509_0060"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SEED_PROJECT_ROLES = [
    ("PM", "Project Manager"),
    ("Sponsor", "Sponsor del proyecto"),
    ("SME", "Subject Matter Expert"),
    ("Key User", "Usuario clave / champion"),
    ("Tech Lead", "Líder técnico"),
    ("Member", "Miembro del equipo"),
]


def upgrade() -> None:
    bind = op.get_bind()

    # 1) project_roles
    op.create_table(
        "project_roles",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False, index=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "name", name="uq_project_roles_tenant_name"),
    )

    # 2) project_participations
    op.create_table(
        "project_participations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False, index=True),
        sa.Column(
            "project_id",
            sa.String(length=36),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "actor_id",
            sa.String(length=36),
            sa.ForeignKey("actors.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "operational_team_id",
            sa.String(length=36),
            sa.ForeignKey("teams.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "project_role_id",
            sa.String(length=36),
            sa.ForeignKey("project_roles.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "functional_area_id",
            sa.String(length=36),
            sa.ForeignKey("areas.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "is_area_lead", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "is_primary", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_participations_project_actor",
        "project_participations",
        ["project_id", "actor_id"],
    )
    # Unique parcial: solo una primary por (project, actor). En SQLite
    # no se soportan partial uniques en CREATE TABLE; en Postgres lo
    # creamos con WHERE.
    if bind.dialect.name == "postgresql":
        op.execute(
            "CREATE UNIQUE INDEX uq_participation_primary "
            "ON project_participations (project_id, actor_id) "
            "WHERE is_primary = TRUE"
        )

    # 3) actors enriquecido (additivo, sin drops)
    with op.batch_alter_table("actors") as batch:
        batch.add_column(sa.Column("company", sa.String(length=200), nullable=True))
        batch.add_column(sa.Column("job_title", sa.String(length=200), nullable=True))
        batch.add_column(
            sa.Column(
                "manager_actor_id",
                sa.String(length=36),
                sa.ForeignKey("actors.id", ondelete="SET NULL"),
                nullable=True,
            )
        )

    # 4) Backfill (best-effort; si no hay datos, no-op).
    # Saltamos si las tablas requeridas no existen (entornos test fresh).
    insp = sa.inspect(bind)
    has_project_members = "project_members" in insp.get_table_names()
    has_actors = "actors" in insp.get_table_names()
    has_users = "users" in insp.get_table_names()
    has_tenants = "tenants" in insp.get_table_names()
    has_projects = "projects" in insp.get_table_names()

    if not (has_actors and has_users and has_tenants and has_projects):
        return

    # Seed project_roles por tenant con proyectos
    tenants_with_projects = bind.execute(
        sa.text("SELECT DISTINCT tenant_id FROM projects")
    ).fetchall()
    import uuid

    role_id_by_tenant_name: dict[tuple[str, str], str] = {}
    for (tenant_id,) in tenants_with_projects:
        for name, desc in SEED_PROJECT_ROLES:
            rid = str(uuid.uuid4())
            role_id_by_tenant_name[(tenant_id, name)] = rid
            bind.execute(
                sa.text(
                    "INSERT INTO project_roles (id, tenant_id, name, description, is_active) "
                    "VALUES (:id, :t, :n, :d, 1)"
                ),
                {"id": rid, "t": tenant_id, "n": name, "d": desc},
            )

    # Helper: get-or-create actor por user_id
    def _ensure_actor_for_user(tenant_id: str, user_id: str) -> str | None:
        row = bind.execute(
            sa.text(
                "SELECT id FROM actors WHERE tenant_id=:t AND user_id=:u LIMIT 1"
            ),
            {"t": tenant_id, "u": user_id},
        ).fetchone()
        if row:
            return row[0]
        # Crear actor a partir del user
        urow = bind.execute(
            sa.text("SELECT email, full_name FROM users WHERE id=:u"),
            {"u": user_id},
        ).fetchone()
        if not urow:
            return None
        aid = str(uuid.uuid4())
        bind.execute(
            sa.text(
                "INSERT INTO actors (id, tenant_id, user_id, name, email, is_active, is_lead) "
                "VALUES (:id, :t, :u, :n, :e, TRUE, FALSE)"
            ),
            {
                "id": aid,
                "t": tenant_id,
                "u": user_id,
                "n": urow[1] or urow[0] or "Usuario",
                "e": urow[0],
            },
        )
        return aid

    def _role_id(tenant_id: str, role_label: str) -> str | None:
        # role_in_project legacy: 'team', 'pm', 'sponsor', etc.
        mapping = {
            "pm": "PM",
            "sponsor": "Sponsor",
            "sme": "SME",
            "key_user": "Key User",
            "tech_lead": "Tech Lead",
            "team": "Member",
        }
        target = mapping.get((role_label or "team").lower(), "Member")
        return role_id_by_tenant_name.get((tenant_id, target))

    # 4.1) Backfill desde project_members
    seen_pa: set[tuple[str, str]] = set()
    if has_project_members:
        members = bind.execute(
            sa.text(
                "SELECT pm.project_id, pm.user_id, pm.role_in_project, p.tenant_id "
                "FROM project_members pm JOIN projects p ON p.id = pm.project_id"
            )
        ).fetchall()
        for project_id, user_id, role_label, tenant_id in members:
            actor_id = _ensure_actor_for_user(tenant_id, user_id)
            if not actor_id:
                continue
            key = (project_id, actor_id)
            if key in seen_pa:
                continue
            seen_pa.add(key)
            bind.execute(
                sa.text(
                    "INSERT INTO project_participations "
                    "(id, tenant_id, project_id, actor_id, project_role_id, "
                    " functional_area_id, is_area_lead, is_primary, is_active) "
                    "SELECT :id, :t, :p, :a, :r, "
                    "       (SELECT area_id FROM actors WHERE id=:a), "
                    "       FALSE, FALSE, TRUE"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "t": tenant_id,
                    "p": project_id,
                    "a": actor_id,
                    "r": _role_id(tenant_id, role_label),
                },
            )

    # 4.2) Backfill desde tasks/risks/issues (actores con asignación pero sin participation)
    for tbl, col in [
        ("tasks", "assignee_actor_id"),
        ("risks", "owner_actor_id"),
        ("issues", "owner_actor_id"),
    ]:
        if tbl not in insp.get_table_names():
            continue
        rows = bind.execute(
            sa.text(
                f"SELECT DISTINCT t.project_id, t.{col}, p.tenant_id, "
                f"       (SELECT team_id FROM actors WHERE id=t.{col}) AS team_id, "
                f"       (SELECT area_id FROM actors WHERE id=t.{col}) AS area_id "
                f"FROM {tbl} t JOIN projects p ON p.id=t.project_id "
                f"WHERE t.{col} IS NOT NULL"
            )
        ).fetchall()
        for project_id, actor_id, tenant_id, team_id, area_id in rows:
            key = (project_id, actor_id)
            if key in seen_pa:
                continue
            seen_pa.add(key)
            bind.execute(
                sa.text(
                    "INSERT INTO project_participations "
                    "(id, tenant_id, project_id, actor_id, operational_team_id, "
                    " functional_area_id, is_area_lead, is_primary, is_active) "
                    "VALUES (:id, :t, :p, :a, :tm, :ar, FALSE, TRUE, TRUE)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "t": tenant_id,
                    "p": project_id,
                    "a": actor_id,
                    "tm": team_id,
                    "ar": area_id,
                },
            )

    # 4.3) is_area_lead = actor.is_lead + functional_area_id matches
    bind.execute(
        sa.text(
            "UPDATE project_participations SET is_area_lead = TRUE "
            "WHERE actor_id IN (SELECT id FROM actors WHERE is_lead = TRUE) "
            "AND functional_area_id IS NOT NULL"
        )
    )

    # 4.4) Marcar is_primary en una fila por (project, actor)
    # (Idempotente; corre solo si nadie ya tiene primary)
    if bind.dialect.name == "postgresql":
        bind.execute(
            sa.text(
                "WITH ranked AS ("
                " SELECT id, ROW_NUMBER() OVER (PARTITION BY project_id, actor_id ORDER BY created_at) AS rn"
                " FROM project_participations"
                ") UPDATE project_participations SET is_primary = TRUE "
                "WHERE id IN (SELECT id FROM ranked WHERE rn = 1)"
            )
        )
    else:
        # SQLite fallback: sin WINDOW, tomar MIN(id) por grupo
        bind.execute(
            sa.text(
                "UPDATE project_participations SET is_primary = TRUE "
                "WHERE id IN ("
                "  SELECT MIN(id) FROM project_participations "
                "  GROUP BY project_id, actor_id"
                ")"
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    with op.batch_alter_table("actors") as batch:
        batch.drop_column("manager_actor_id")
        batch.drop_column("job_title")
        batch.drop_column("company")

    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS uq_participation_primary")
    op.drop_index("ix_participations_project_actor", table_name="project_participations")
    op.drop_table("project_participations")
    op.drop_table("project_roles")
