"""Smoke del endpoint Ollama local del tenant (EP016 US-047).

Uso:
    python -m app.scripts.ai_local_smoke --tenant {slug} [--prompt "..."]

Resuelve la config `settings.ai.ollama` del tenant y verifica:
  1. `/api/tags` responde 200 y contiene el modelo configurado.
  2. `/api/generate` con un prompt corto responde en ≤ timeout_sec.

Historia:
- US-045 (2026-04-20): versión original con headers CF-Access
  (Cloudflare Tunnel).
- US-047 (2026-04-21): pivote a Tailscale — se eliminan los headers
  CF-Access. El canal es tailnet privado y no requiere auth.

Retorna exit code 0 si todo pasa, 1 si falla.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import time
from typing import Any

import httpx
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.tenant import Tenant

DEFAULT_PROMPT = (
    "Responde en una frase: ¿cuál es la capital de México? Empieza con 'OK:'"
)


async def _load_config(slug: str) -> dict[str, Any]:
    async with SessionLocal() as db:
        row = (
            await db.execute(select(Tenant).where(Tenant.slug == slug))
        ).scalar_one_or_none()
        if row is None:
            print(f"ERR: tenant slug={slug!r} no encontrado", file=sys.stderr)
            sys.exit(1)
        cfg = dict(((row.settings or {}).get("ai") or {}).get("ollama") or {})
        if not cfg.get("base_url"):
            print("ERR: tenant sin `settings.ai.ollama.base_url`", file=sys.stderr)
            sys.exit(1)
        return cfg


async def _run(cfg: dict[str, Any], prompt: str) -> int:
    base = str(cfg["base_url"]).rstrip("/")
    headers: dict[str, str] = {"Accept": "application/json"}
    timeout = float(cfg.get("timeout_sec") or 60)

    print(f"=> base_url     = {base}")
    print(f"=> model        = {cfg.get('model') or '(no configurado)'}")
    print(f"=> timeout_sec  = {int(timeout)}")
    print("=> channel      = tailnet (sin auth headers)")

    async with httpx.AsyncClient(timeout=timeout, headers=headers) as c:
        # 1. tags
        started = time.perf_counter()
        try:
            r = await c.get(f"{base}/api/tags")
        except httpx.HTTPError as exc:
            print(f"FAIL /api/tags: {exc}")
            return 1
        tags_latency = int((time.perf_counter() - started) * 1000)
        if r.status_code != 200:
            print(f"FAIL /api/tags: HTTP {r.status_code}")
            return 1
        models = [m.get("name") for m in r.json().get("models", [])]
        expected = cfg.get("model")
        model_present = bool(expected and expected in models)
        print(f"OK /api/tags ({tags_latency} ms, {len(models)} modelos; "
              f"model_present={model_present})")

        # 2. generate
        if not expected:
            print("SKIP /api/generate (sin modelo configurado)")
            return 0
        started = time.perf_counter()
        try:
            r = await c.post(
                f"{base}/api/generate",
                json={"model": expected, "prompt": prompt, "stream": False},
            )
        except httpx.HTTPError as exc:
            print(f"FAIL /api/generate: {exc}")
            return 1
        gen_latency = int((time.perf_counter() - started) * 1000)
        if r.status_code != 200:
            print(f"FAIL /api/generate: HTTP {r.status_code}: {r.text[:200]}")
            return 1
        response_text = (r.json().get("response") or "").strip()
        print(f"OK /api/generate ({gen_latency} ms)")
        print(f"RESPONSE: {response_text[:200]}")
        if "OK" not in response_text.upper() and "MÉXICO" not in response_text.upper():
            print("WARN: respuesta no contiene 'OK' ni 'México' — revisar prompt / modelo.")
    return 0


async def _amain() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant", required=True, help="Slug del tenant")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    args = parser.parse_args()

    cfg = await _load_config(args.tenant)
    return await _run(cfg, args.prompt)


def main() -> None:
    rc = asyncio.run(_amain())
    sys.exit(rc)


if __name__ == "__main__":
    main()
