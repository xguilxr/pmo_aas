"""BUG-053 — drop Ollama legacy: migrate tenants to platform + drop columns.

Cleanup post-Ollama:
1. `tenants.settings.ai.mode` viejos (`ollama`/`gemini`/`claude`) → `platform`.
2. Tenants con `byo.provider=ollama` → reset a `mode=platform` (sin BYO).
3. Borrar `tenants.settings.ai.ollama` (config legacy US-048).
4. Drop columnas `ollama_base_url`, `ollama_model`, `ai_timeout_sec` de
   `platform_ai_settings`.
5. Si `platform_ai_settings.ai_mode` venía con valor legacy, normalizar
   a `platform`.

Implementado en Python (read-modify-write) porque `tenants.settings` es
`JSON` (no `jsonb`) — los operadores `jsonb_set`, `#-`, `?` no aplican.

Revision ID: 20260508_0053
Revises: 20260507_0052
Create Date: 2026-05-08 00:00:00
"""
import json
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260508_0053"
down_revision: str | None = "20260507_0052"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_LEGACY_MODES = {"ollama", "gemini", "claude"}


def upgrade() -> None:
    bind = op.get_bind()

    rows = bind.execute(sa.text("SELECT id, settings FROM tenants")).fetchall()
    for row in rows:
        tenant_id, raw = row[0], row[1]
        settings = _coerce_dict(raw)
        ai = settings.get("ai")
        if not isinstance(ai, dict):
            continue
        changed = False

        mode = str(ai.get("mode") or "").lower()
        if mode in _LEGACY_MODES:
            ai["mode"] = "platform"
            changed = True

        byo = ai.get("byo")
        if isinstance(byo, dict) and str(byo.get("provider") or "").lower() == "ollama":
            ai["mode"] = "platform"
            ai["byo"] = None
            changed = True

        if "ollama" in ai:
            ai.pop("ollama", None)
            changed = True

        if changed:
            settings["ai"] = ai
            bind.execute(
                sa.text("UPDATE tenants SET settings = CAST(:s AS json) WHERE id = :id"),
                {"s": json.dumps(settings), "id": tenant_id},
            )

    # 5: normalizar platform_ai_settings.ai_mode si venía legacy.
    bind.execute(
        sa.text(
            "UPDATE platform_ai_settings "
            "SET ai_mode = 'platform' "
            "WHERE ai_mode IN ('ollama', 'gemini', 'claude')"
        )
    )

    # 4: drop columnas Ollama del singleton.
    op.drop_column("platform_ai_settings", "ollama_base_url")
    op.drop_column("platform_ai_settings", "ollama_model")
    op.drop_column("platform_ai_settings", "ai_timeout_sec")


def downgrade() -> None:
    op.add_column(
        "platform_ai_settings",
        sa.Column("ollama_base_url", sa.String(500), nullable=True),
    )
    op.add_column(
        "platform_ai_settings",
        sa.Column("ollama_model", sa.String(100), nullable=True),
    )
    op.add_column(
        "platform_ai_settings",
        sa.Column("ai_timeout_sec", sa.Integer(), nullable=True),
    )
    # Los tenants migrados a `platform` no se revierten — no preservamos
    # el modo viejo, así que el downgrade es lossy by design.


def _coerce_dict(raw):
    """tenants.settings se materializa como dict (psycopg) o str (sqlite)."""
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str):
        try:
            return json.loads(raw) or {}
        except Exception:
            return {}
    return {}
