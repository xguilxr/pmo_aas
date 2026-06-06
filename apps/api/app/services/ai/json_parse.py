"""ENH-147 — parser tolerante para salidas JSON de modelos IA.

Los modelos a veces envuelven el JSON en fences ```json … ```, o dejan
comas colgantes antes de `}`/`]`. Este parser limpia eso y, como último
recurso, recorta el substring entre la primera `{` y la última `}`.

NO removemos comentarios `//` deliberadamente: corromperían URLs dentro
de strings (`"https://..."`). En su lugar, `prompts.py` ya no induce
comentarios y `json_mode` fuerza salida válida en los proveedores que lo
soportan; este parser es la red de seguridad.
"""
from __future__ import annotations

import json
import re

_FENCE_RE = re.compile(r"^\s*```(?:json|JSON)?\s*|\s*```\s*$")
_TRAILING_COMMA_RE = re.compile(r",(\s*[}\]])")


def _strip_fences(s: str) -> str:
    t = s.strip()
    if "```" in t:
        # quita fences de apertura/cierre dejando el cuerpo.
        t = t.strip("`").strip()
        t = _FENCE_RE.sub("", t).strip()
        if t.lower().startswith("json"):
            t = t[4:].strip()
    return t


def parse_json_lenient(text: str | None) -> dict | None:
    """Devuelve un dict si logra parsear; None si no.

    Orden de intentos: loads directo → strip de fences → recorte entre
    llaves → recorte + eliminación de comas colgantes.
    """
    if not text:
        return None
    raw = text.strip()
    candidates: list[str] = [raw]

    stripped = _strip_fences(raw)
    if stripped and stripped != raw:
        candidates.append(stripped)

    start, end = stripped.find("{"), stripped.rfind("}")
    if start >= 0 and end > start:
        sub = stripped[start : end + 1]
        candidates.append(sub)
        candidates.append(_TRAILING_COMMA_RE.sub(r"\1", sub))

    for cand in candidates:
        try:
            obj = json.loads(cand)
        except Exception:
            continue
        if isinstance(obj, dict):
            return obj
    return None
