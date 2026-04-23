"""platform_ai_settings.groq_* + ai_jobs.provider + tenant_ai.mode default disabled (US-057)

Revision ID: 20260423_0021
Revises: 20260423_0020
Create Date: 2026-04-23 18:00:00

Schema:
- `platform_ai_settings.groq_api_key_encrypted` (Fernet-cifrada) +
  `platform_ai_settings.groq_model` para la IA base compartida.
- `ai_jobs.provider` (índice) para el dashboard superadmin de uso Groq
  y el panel de status por tenant.

Data migration:
- Todos los tenants existentes se setean en modo `disabled` (opt-in del
  owner). El owner-admin cambia el modo desde `/admin/ai` cuando quiera
  activar la IA. Por retro-compat, si ya existe
  `tenants.settings.ai.ollama`, se preserva intacto: el commit 0022
  (data migration) lo traslada al nuevo shape BYO.
"""
import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260423_0021"
down_revision: Union[str, None] = "20260423_0020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Schema ---
    op.add_column(
        "platform_ai_settings",
        sa.Column("groq_api_key_encrypted", sa.String(length=1000), nullable=True),
    )
    op.add_column(
        "platform_ai_settings",
        sa.Column("groq_model", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "ai_jobs",
        sa.Column("provider", sa.String(length=32), nullable=True),
    )
    op.create_index("ix_ai_jobs_provider", "ai_jobs", ["provider"])

    # --- Data: set all existing tenants to mode='disabled' (opt-in) ---
    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, settings FROM tenants WHERE deleted_at IS NULL")
    ).fetchall()
    for tenant_id, settings in rows:
        cfg = _load_settings(settings)
        ai = cfg.get("ai") if isinstance(cfg.get("ai"), dict) else {}
        # Si ya hay `mode`, respetamos (rollback/re-run friendly).
        if "mode" not in ai:
            ai["mode"] = "disabled"
        # `byo` comienza vacío — el commit 0022 lo llena desde ollama legacy.
        if "byo" not in ai:
            ai["byo"] = None
        cfg["ai"] = ai
        bind.execute(
            sa.text("UPDATE tenants SET settings = :s WHERE id = :id"),
            {"s": json.dumps(cfg), "id": tenant_id},
        )


def downgrade() -> None:
    # No revertimos la mutación de settings — es idempotente y segura.
    op.drop_index("ix_ai_jobs_provider", table_name="ai_jobs")
    op.drop_column("ai_jobs", "provider")
    op.drop_column("platform_ai_settings", "groq_model")
    op.drop_column("platform_ai_settings", "groq_api_key_encrypted")


def _load_settings(raw) -> dict:
    """Acepta dict (Postgres JSONB) o str (SQLite JSON)."""
    if raw is None or raw == "":
        return {}
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8")
    try:
        loaded = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    return loaded if isinstance(loaded, dict) else {}
