"""Helper para generar slugs estables a partir de nombres de proyecto.

Se usa al armar `Content-Disposition` de descargas de artefactos
(Charter, Plan, RAID, etc.) para que el archivo descargado tenga un
nombre legible derivado del proyecto y no su UUID.

Reglas (ENH-092 / ENH-093):
- lowercase
- acentos / diacríticos quitados
- todo lo no [a-z0-9] se vuelve "-"
- runs de "-" colapsados, sin "-" al inicio/fin
- fallback: "proyecto" si el slug queda vacío
"""
from __future__ import annotations

import re
import unicodedata


def slugify_project_name(name: str | None, *, fallback: str = "proyecto") -> str:
    if not name:
        return fallback
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_only = nfkd.encode("ascii", "ignore").decode("ascii")
    ascii_only = ascii_only.lower()
    ascii_only = re.sub(r"[^a-z0-9]+", "-", ascii_only)
    ascii_only = re.sub(r"-+", "-", ascii_only).strip("-")
    return ascii_only or fallback


def artifact_filename(project_name: str | None, kind: str, ext: str) -> str:
    """`{project-slug}-{kind}.{ext}` — patrón canónico aprobado por owner."""
    slug = slugify_project_name(project_name)
    safe_kind = re.sub(r"[^a-z0-9]+", "-", kind.lower()).strip("-") or "artifact"
    return f"{slug}-{safe_kind}.{ext}"


def raid_display_filename(project_name: str | None) -> str:
    """ENH-152: filename legible `RAID-[Nombre Proyecto].xlsx`.

    A diferencia de `artifact_filename` (que slugifica), preserva
    mayúsculas, espacios y acentos del nombre del proyecto; sólo elimina
    los caracteres ilegales en un filename. Fallback `RAID-proyecto.xlsx`.
    El `Content-Disposition` ya expone `filename*` UTF-8 para los acentos.
    """
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", project_name or "")
    name = re.sub(r"\s+", " ", name).strip()
    return f"RAID-{name or 'proyecto'}.xlsx"
