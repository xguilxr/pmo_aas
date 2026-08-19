"""ENH-111 — Logos en el .docx del Project Charter.

El charter ahora inserta logo(s) (tenant/PMO + cliente) arriba del título.
El render real (python-docx) se ejerce con `@pytest.mark.heavy` para que el
stub de conftest no intercepte `_render_charter_docx`.
"""
import struct
import zlib
from io import BytesIO

import pytest

from app.services import charter_generator as cg


def _make_png(width: int = 2, height: int = 2) -> bytes:
    """Construye un PNG RGB válido (sin depender de Pillow) que python-docx
    puede parsear para leer dimensiones."""

    def _chunk(typ: bytes, data: bytes) -> bytes:
        body = typ + data
        crc = zlib.crc32(body) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + body + struct.pack(">I", crc)

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # 8-bit RGB
    raw = b"".join(b"\x00" + b"\xff\x00\x00" * width for _ in range(height))
    idat = zlib.compress(raw)
    return sig + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", idat) + _chunk(b"IEND", b"")


# PNG válido reutilizable en los tests.
_PNG_1x1 = _make_png()


class _FakeCharter:
    project_name = "Proyecto Demo"
    description = "desc"
    organization_id = None
    business_unit_id = None
    department_id = None
    sponsor = None
    sponsor_email = None
    business_leader = None
    business_leader_email = None
    tech_leader = None
    tech_leader_email = None
    pm_id = None
    project_type = "innovacion"
    priority = 3
    objective = None
    restrictions = None
    risks_summary = None
    scope = None
    key_people = None
    benefits = None


class _FakeProject:
    folio = "PRJ-0001"
    phase = "preparacion"
    health_status = "green"
    start_date = None
    end_date = None
    budget = None
    progress = 0
    organization_id = None


def _inline_shape_count(data: bytes) -> int:
    from docx import Document as DocxDocument

    return len(DocxDocument(BytesIO(data)).inline_shapes)


@pytest.mark.heavy
def test_render_inserts_two_logos():
    data = cg._render_charter_docx(
        _FakeCharter(), _FakeProject(), [_PNG_1x1, _PNG_1x1]
    )
    assert _inline_shape_count(data) == 2


@pytest.mark.heavy
def test_render_without_logos_has_no_image():
    data = cg._render_charter_docx(_FakeCharter(), _FakeProject(), None)
    assert _inline_shape_count(data) == 0


@pytest.mark.heavy
def test_render_skips_corrupt_logo_without_failing():
    # Un blob no-imagen no debe romper la generación; se omite.
    data = cg._render_charter_docx(
        _FakeCharter(), _FakeProject(), [b"not-an-image", _PNG_1x1]
    )
    assert _inline_shape_count(data) == 1


def test_looks_raster():
    assert cg._looks_raster(_PNG_1x1) is True
    assert cg._looks_raster(b"\xff\xd8\xff\xe0jpeg") is True
    assert cg._looks_raster(b"<svg></svg>") is False


def test_load_local_tenant_logo_png(monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "STORAGE_PATH", str(tmp_path))
    tdir = tmp_path / "tenants" / "tid-1"
    tdir.mkdir(parents=True)
    (tdir / "logo.png").write_bytes(_PNG_1x1)
    assert cg._load_local_tenant_logo("tid-1") == _PNG_1x1


def test_load_local_tenant_logo_skips_svg(monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "STORAGE_PATH", str(tmp_path))
    tdir = tmp_path / "tenants" / "tid-2"
    tdir.mkdir(parents=True)
    (tdir / "logo.svg").write_bytes(b"<svg></svg>")
    # svg no lo soporta python-docx → None.
    assert cg._load_local_tenant_logo("tid-2") is None


async def test_download_image_rejects_relative_url():
    # URL relativa (la del branding interno del tenant) no se descarga.
    assert await cg._download_image("/api/v1/branding/tenants/x/logo") is None
    assert await cg._download_image(None) is None
