"""AM-08 · MCS SEG-07 — el registro de auditoría no se modifica ni se borra.

`docs/architecture/modelo-amenazas.md` AM-08: `audit_log` era una tabla
ordinaria. Importa más de lo que parece porque **AM-06 se apoya en ella como
único control**, y un control que descansa sobre otro que no existe no es un
control.

El control se instala en dos capas, y esta suite cubre cada una donde se puede
comprobar:

- **Disparadores de PostgreSQL** (migración `0097`). Actúan pase lo que pase,
  incluido el SQL crudo. La suite corre sobre SQLite, así que aquí solo se
  comprueba que la migración los declare y sea reversible — ejecutarlos es cosa
  del job `api-migrations-postgres`.
- **Guardián del ORM** (`app/models/audit.py`). Ese sí se ejercita de verdad.

Y una tercera cosa, que es la que de verdad se rompería sin querer: que ningún
sitio de la aplicación intente modificar el registro. Hoy solo lo inserta y lo
consulta.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from sqlalchemy import delete, select

from app.models.audit import AuditLog, RegistroInmutableError

MIGRACION = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "20260805_0097_audit_log_solo_anexa.py"
)


async def _anexar(db_session) -> AuditLog:
    fila = AuditLog(action="login", module="auth", details={"x": 1})
    db_session.add(fila)
    await db_session.commit()
    return fila


# ---------------------------------------------------------------------------
# Guardián del ORM — se ejercita de verdad
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_anexar_sigue_funcionando(db_session):
    """El control no sirve de nada si rompe lo único que la tabla debe hacer."""
    fila = await _anexar(db_session)

    assert fila.id is not None
    guardadas = (await db_session.execute(select(AuditLog))).scalars().all()
    assert len(guardadas) == 1


@pytest.mark.asyncio
async def test_modificar_una_fila_falla(db_session):
    fila = await _anexar(db_session)
    fila.action = "login_falseado"

    with pytest.raises(RegistroInmutableError, match="UPDATE"):
        await db_session.commit()


@pytest.mark.asyncio
async def test_borrar_una_fila_falla(db_session):
    fila = await _anexar(db_session)
    await db_session.delete(fila)

    with pytest.raises(RegistroInmutableError, match="DELETE"):
        await db_session.commit()


@pytest.mark.asyncio
async def test_el_borrado_masivo_pasa_el_guardian_del_orm(db_session):
    """Se comprueba el hueco a propósito, para que quede escrito y no sorprenda.

    `session.execute(delete(...))` no pasa por los eventos del mapeador. En
    PostgreSQL lo detiene el disparador; en SQLite no lo detiene nada. Si algún
    día el guardián del ORM cubre también las sentencias masivas, esta prueba
    falla y hay que celebrarlo, no arreglarla en silencio.
    """
    await _anexar(db_session)

    await db_session.execute(delete(AuditLog))
    await db_session.commit()

    quedan = (await db_session.execute(select(AuditLog))).scalars().all()
    assert quedan == [], (
        "El borrado masivo ya no pasa. Actualiza esta prueba y AM-08: el hueco "
        "que documentaba se cerró."
    )


# ---------------------------------------------------------------------------
# Disparadores de PostgreSQL — se comprueba lo que la migración declara
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fragmento",
    [
        "BEFORE UPDATE OR DELETE ON audit_log",
        "BEFORE TRUNCATE ON audit_log",
        "REVOKE UPDATE, DELETE, TRUNCATE ON TABLE audit_log FROM PUBLIC",
    ],
)
def test_la_migracion_instala_las_tres_defensas(fragmento):
    assert fragmento in MIGRACION.read_text(encoding="utf-8")


def test_la_migracion_es_reversible():
    """El CI corre `downgrade base`: lo que no se deshace, rompe el job."""
    texto = MIGRACION.read_text(encoding="utf-8")
    cuerpo_downgrade = texto[texto.index("def downgrade()") :]

    for objeto in ("audit_log_sin_truncado", "audit_log_sin_modificacion",
                   "audit_log_rechaza_modificacion"):
        assert objeto in cuerpo_downgrade, f"`downgrade` no deshace {objeto}"


def test_la_migracion_no_corre_en_sqlite():
    """Sin la guarda de dialecto, la suite entera se caería al migrar."""
    texto = MIGRACION.read_text(encoding="utf-8")

    assert texto.count('dialect.name != "postgresql"') == 2, (
        "`upgrade` y `downgrade` tienen que salir temprano fuera de PostgreSQL"
    )


# ---------------------------------------------------------------------------
# Que la aplicación no lo intente
# ---------------------------------------------------------------------------


def test_ningun_endpoint_ni_servicio_modifica_el_registro():
    """Lo que se rompería sin querer: un borrado en cascada, una purga.

    Se busca `AuditLog` dentro de un `delete(` o un `update(` de SQLAlchemy en
    todo `app/`. Hoy solo se inserta y se consulta.

    Las líneas de comentario se descartan: `models/audit.py` menciona
    `delete(AuditLog)` justo para documentar el hueco de las sentencias
    masivas, y una prueba que se pone roja por su propia documentación acaba
    borrando la documentación.
    """
    raiz = Path(__file__).resolve().parents[1] / "app"
    patron = re.compile(r"\b(delete|update)\(\s*AuditLog\b")

    culpables = [
        f"{ruta.relative_to(raiz)}:{n}"
        for ruta in raiz.rglob("*.py")
        for n, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1)
        if patron.search(linea) and not linea.lstrip().startswith("#")
    ]

    assert not culpables, (
        f"Estos sitios modifican `audit_log`, que es de solo anexado "
        f"(AM-08): {culpables}"
    )
