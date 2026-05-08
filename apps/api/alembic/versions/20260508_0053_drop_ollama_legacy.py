"""BUG-053 — drop Ollama legacy: migrate tenants to platform + drop columns.

Cleanup post-Ollama:
1. `tenants.settings.ai.mode` viejos (`ollama`/`gemini`/`claude`) → `platform`.
2. Tenants con `byo.provider=ollama` → reset a `mode=platform` (sin BYO).
3. Borrar `tenants.settings.ai.ollama` (config legacy US-048).
4. Drop columnas `ollama_base_url`, `ollama_model`, `ai_timeout_sec` de
   `platform_ai_settings`.
5. Si `platform_ai_settings.ai_mode` venía con valor legacy, normalizar
   a `platform`.

Revision ID: 20260508_0053
Revises: 20260507_0052
Create Date: 2026-05-08 00:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260508_0053"
down_revision: str | None = "20260507_0052"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_LEGACY_MODES = ("ollama", "gemini", "claude")


def upgrade() -> None:
    bind = op.get_bind()

    # 1+2+3: migrar tenants. Usamos jsonb_set + condicionales en SQL puro
    # para no levantar el ORM (más seguro en runtime de migración).
    bind.execute(
        sa.text(
            """
            UPDATE tenants
            SET settings = jsonb_set(
                COALESCE(settings, '{}'::jsonb),
                '{ai,mode}',
                '"platform"'::jsonb,
                true
            )
            WHERE COALESCE(settings->'ai'->>'mode', '') IN :legacy
            """
        ).bindparams(sa.bindparam("legacy", _LEGACY_MODES, expanding=True))
    )

    # Tenants con BYO provider=ollama → reset a platform (sin BYO).
    bind.execute(
        sa.text(
            """
            UPDATE tenants
            SET settings = jsonb_set(
                settings #- '{ai,byo}',
                '{ai,mode}',
                '"platform"'::jsonb,
                true
            )
            WHERE settings->'ai'->'byo'->>'provider' = 'ollama'
            """
        )
    )

    # Borrar config legacy `tenants.settings.ai.ollama` (US-048).
    bind.execute(
        sa.text(
            """
            UPDATE tenants
            SET settings = settings #- '{ai,ollama}'
            WHERE settings->'ai' ? 'ollama'
            """
        )
    )

    # 5: normalizar platform_ai_settings.ai_mode si venía legacy.
    bind.execute(
        sa.text(
            """
            UPDATE platform_ai_settings
            SET ai_mode = 'platform'
            WHERE ai_mode IN ('ollama', 'gemini', 'claude')
            """
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
