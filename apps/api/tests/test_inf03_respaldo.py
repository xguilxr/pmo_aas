"""INF-03 — hay copias de seguridad automáticas, y se restauran.

«DEBEN existir copias de seguridad automáticas». No había ninguna, y es el
requisito abierto con el peor desenlace: el resto degradan el producto, este
pierde el trabajo de los clientes.

**El caso que da valor a esta suite es el de restauración**, y corre contra
Postgres de verdad. Una copia que nunca se ha restaurado no es una copia: es un
fichero del que nadie sabe si sirve, y averiguarlo el día del incidente es
tarde.
"""
from __future__ import annotations

import os
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine

from app.services.respaldo import (
    PREFIJO,
    RETENCION_DIAS,
    RespaldoError,
    _url_sincrona,
    clave_del_dia,
    volcar,
)

RAIZ_API = Path(__file__).resolve().parents[1]


def test_la_clave_ordena_por_antiguedad() -> None:
    """`AAAA-MM-DD` y no `DD-MM-AAAA`: listar el prefijo sale ordenado.

    Con la fecha en otro orden, la limpieza por retención tendría que leer los
    metadatos de cada objeto — una llamada por copia, todos los días.
    """
    clave = clave_del_dia(datetime(2026, 8, 6, tzinfo=UTC))
    assert clave == f"{PREFIJO}/2026-08-06.dump"
    anterior = clave_del_dia(datetime(2026, 7, 30, tzinfo=UTC))
    assert anterior < clave


def test_la_retencion_esta_declarada() -> None:
    """El número escrito, no derivado: subirlo es una decisión de coste."""
    assert RETENCION_DIAS == 30


def test_el_worker_lo_tiene_programado() -> None:
    """Una copia sin programar es una copia que nadie hace.

    Se comprueba sobre la configuración real de Celery y no sobre el fichero:
    una entrada en `beat_schedule` que apunte a una tarea no registrada no
    corre nunca, y leyendo el texto no se ve.
    """
    from app.workers.celery_app import celery_app

    programado = celery_app.conf.beat_schedule
    assert "respaldo-diario" in programado, "La copia diaria salió del planificador."
    assert programado["respaldo-diario"]["task"] == "respaldo.diario"


def test_la_tarea_esta_registrada() -> None:
    """El complemento del anterior: que el nombre programado exista de verdad."""
    import app.workers.tasks.respaldo  # noqa: F401  (registra la tarea)
    from app.workers.celery_app import celery_app

    assert "respaldo.diario" in celery_app.tasks


def test_la_imagen_trae_pg_dump() -> None:
    """Sin el binario, la tarea falla el primer día.

    Y falla de la peor manera: el programado existe, el trabajo se lanza, y lo
    único que queda es un error en los registros que nadie mira hasta que hace
    falta restaurar.
    """
    dockerfile = (RAIZ_API / "Dockerfile").read_text(encoding="utf-8")
    sin_comentarios = "\n".join(
        l for l in dockerfile.splitlines() if not l.lstrip().startswith("#")
    )
    assert "postgresql-client" in sin_comentarios, (
        "`postgresql-client` salió de la imagen: `pg_dump` no existirá en el "
        "contenedor y la copia diaria fallará entera."
    )


def test_un_volcado_vacio_no_pasa_por_copia(monkeypatch: pytest.MonkeyPatch) -> None:
    """El fallo silencioso de esta función, cerrado.

    `pg_dump` puede devolver código 0 y salida vacía. Subir eso deja en el
    almacenamiento un fichero de cero bytes que parece una copia hasta el día
    que alguien intenta restaurarlo.
    """
    import subprocess

    class _Vacio:
        returncode = 0
        stdout = b""
        stderr = b""

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Vacio())
    with pytest.raises(RespaldoError, match="vacío"):
        volcar()


def test_sin_pg_dump_lo_dice_con_la_solucion(monkeypatch: pytest.MonkeyPatch) -> None:
    """El mensaje incluye qué hacer, como pide LEN-02."""
    import subprocess

    def _no_esta(*a: object, **k: object) -> None:
        raise FileNotFoundError

    monkeypatch.setattr(subprocess, "run", _no_esta)
    with pytest.raises(RespaldoError, match="postgresql-client"):
        volcar()


# ---------------------------------------------------------------------------
# El que importa: volcar y RESTAURAR de verdad
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL_POSTGRES"),
    reason="Sin Postgres; el job `api-migrations-postgres` sí lo define.",
)
def test_el_volcado_se_restaura_y_los_datos_vuelven(monkeypatch: pytest.MonkeyPatch) -> None:
    """Volcar una tabla con datos, borrarla, restaurar, y comprobar que están.

    **Es la única prueba que convierte un fichero en una copia de seguridad.**
    Todo lo demás —que exista el programado, que haya binario, que suba— es
    condición necesaria; esto es la suficiente.
    """
    if not shutil.which("pg_dump") or not shutil.which("pg_restore"):
        pytest.skip("Faltan `pg_dump`/`pg_restore` en este entorno.")

    url = os.environ["DATABASE_URL_POSTGRES"]
    monkeypatch.setattr("app.services.respaldo.settings.DATABASE_URL", url)

    md = sa.MetaData()
    tabla = sa.Table(
        "prueba_respaldo",
        md,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("dato", sa.String(50), nullable=False),
    )
    motor = create_engine(url)
    try:
        with motor.begin() as c:
            tabla.drop(c, checkfirst=True)
            tabla.create(c)
            c.execute(tabla.insert(), [{"id": 1, "dato": "sobrevive"}])

        volcado = volcar()
        assert len(volcado) > 100, "El volcado es sospechosamente pequeño."

        # Se pierde la tabla, como en el incidente que esto previene.
        with motor.begin() as c:
            tabla.drop(c)

        destino = RAIZ_API / "prueba_respaldo.dump"
        destino.write_bytes(volcado)
        try:
            import subprocess

            r = subprocess.run(
                # `_url_sincrona()` y no `url` a secas: `DATABASE_URL` trae el
                # dialecto de SQLAlchemy (`+psycopg`) y `libpq` no lo entiende
                # — lo ignora y cae al socket local, que en el contenedor
                # intenta el rol `root` y falla. Lo destapó este mismo caso.
                ["pg_restore", "--dbname", _url_sincrona(), "--no-owner", str(destino)],
                capture_output=True,
                check=False,
            )
            assert r.returncode == 0, r.stderr.decode("utf-8", errors="replace")[:400]
        finally:
            destino.unlink(missing_ok=True)

        with motor.connect() as c:
            fila = c.execute(sa.text("SELECT dato FROM prueba_respaldo")).fetchone()
        assert fila is not None and fila[0] == "sobrevive", (
            "La restauración no devolvió los datos. El volcado no sirve como "
            "copia de seguridad."
        )
    finally:
        with motor.begin() as c:
            tabla.drop(c, checkfirst=True)
        motor.dispose()


def test_la_limpieza_respeta_lo_que_no_reconoce() -> None:
    """Borrar por descarte es cómo una limpieza se lleva lo que no le tocaba.

    Se comprueba sobre el código porque el caso real requiere el
    almacenamiento: lo que importa es que exista el `continue`, no simularlo.
    """
    fuente = (RAIZ_API / "app" / "services" / "respaldo.py").read_text(encoding="utf-8")
    cuerpo = fuente[fuente.index("def limpiar_antiguos"):]
    assert "except ValueError:" in cuerpo and "continue" in cuerpo, (
        "La limpieza dejó de saltarse lo que no sigue el patrón de fecha: "
        "borraría por descarte."
    )


def test_la_retencion_corta_por_fecha() -> None:
    """La aritmética del corte, aislada del almacenamiento."""
    hoy = datetime(2026, 8, 6, tzinfo=UTC)
    corte = hoy - timedelta(days=RETENCION_DIAS)
    assert datetime(2026, 7, 6, tzinfo=UTC) < corte, "Una de 31 días debe borrarse."
    assert datetime(2026, 7, 20, tzinfo=UTC) > corte, "Una de 17 días debe quedarse."


def test_la_url_pierde_el_dialecto_de_sqlalchemy() -> None:
    """`pg_dump` y `pg_restore` hablan `libpq`, no SQLAlchemy.

    Con `+psycopg` o `+asyncpg` en la cadena, `libpq` **no da error**: ignora
    lo que no entiende y cae al socket local. En el contenedor eso intenta el
    rol `root` y falla con un mensaje que no menciona la causa.

    Lo destapó el caso de restauración de arriba, que llamaba a `pg_restore`
    con la URL cruda.
    """
    import app.services.respaldo as modulo

    for dialecto in ("+asyncpg", "+psycopg", "+psycopg2"):
        original = modulo.settings.DATABASE_URL
        try:
            modulo.settings.DATABASE_URL = f"postgresql{dialecto}://u:p@h:5432/d"
            assert _url_sincrona() == "postgresql://u:p@h:5432/d"
        finally:
            modulo.settings.DATABASE_URL = original
