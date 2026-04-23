"""Migrar tenants.settings.ai.ollama legacy a shape BYO (US-057)

Revision ID: 20260423_0022
Revises: 20260423_0021
Create Date: 2026-04-23 19:00:00

Data migration idempotente. Para cada tenant con
`settings.ai.ollama.base_url` configurada (US-048 legacy) y sin
`settings.ai.byo` ni modo explícito distinto de `disabled`:

- `settings.ai.mode` se setea a `"byo"`.
- `settings.ai.byo` pasa a `{provider: "ollama", base_url, model,
  api_key_encrypted: ""}` — Ollama tailnet no requiere key.
- `settings.ai.ollama` se conserva intacto para retro-compat/audit.

Si el tenant ya migró (tiene `byo.provider = "ollama"`) o está en
modo `platform`/`byo` distinto, no se toca.
"""
import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260423_0022"
down_revision: Union[str, None] = "20260423_0021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _load(raw) -> dict:
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


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, settings FROM tenants WHERE deleted_at IS NULL")
    ).fetchall()
    for tenant_id, settings_raw in rows:
        cfg = _load(settings_raw)
        ai = cfg.get("ai") if isinstance(cfg.get("ai"), dict) else {}
        ollama = ai.get("ollama") if isinstance(ai.get("ollama"), dict) else None
        if not ollama:
            continue
        if not ollama.get("base_url"):
            continue

        # No pisamos una config BYO ya existente ni el modo platform.
        current_mode = ai.get("mode")
        byo_existing = ai.get("byo") if isinstance(ai.get("byo"), dict) else None
        if byo_existing:
            continue
        if current_mode in ("platform", "byo"):
            continue

        ai["mode"] = "byo"
        ai["byo"] = {
            "provider": "ollama",
            "api_key_encrypted": "",
            "model": ollama.get("model"),
            "base_url": ollama.get("base_url"),
            "last_test_at": None,
            "last_test_status": None,
            "last_test_error": None,
        }
        cfg["ai"] = ai
        bind.execute(
            sa.text("UPDATE tenants SET settings = :s WHERE id = :id"),
            {"s": json.dumps(cfg), "id": tenant_id},
        )


def downgrade() -> None:
    # No se revierte: borrar byo sólo con confianza si viene de ollama
    # y el ollama original sigue intacto — irrelevante en prod.
    pass
