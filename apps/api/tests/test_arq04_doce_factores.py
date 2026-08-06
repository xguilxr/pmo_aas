"""ARQ-04 — los tres factores que el requisito nombra, verificados uno a uno.

MCS ARQ-04 dice literalmente: «el producto DEBE cumplir los doce factores:
**configuración en el entorno, procesos sin estado, registros a la salida
estándar**». Nombra tres de los doce, y son esos tres los que se comprueban:
inventarse los otros nueve sería medir contra algo que el marco no pidió.

De los tres, dos ya estaban y uno tenía un hueco que no se veía leyendo código.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest
from pydantic import ValidationError

RAIZ_API = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Factor 3 — configuración en el entorno
# ---------------------------------------------------------------------------

def test_la_configuracion_viene_del_entorno() -> None:
    """Un único punto: `Settings`. Si algo leyera `os.environ` por su cuenta,
    habría configuración que no aparece en la clase y nadie sabría que existe.
    """
    from app.core.config import Settings, settings

    assert issubclass(Settings, __import__("pydantic_settings").BaseSettings)
    assert settings.model_config.get("env_file") == ".env"


def test_nadie_lee_el_entorno_por_su_cuenta() -> None:
    """`os.environ` suelto en el código de aplicación es configuración fuera
    del contrato: no está declarada, no tiene tipo y no tiene valor por defecto.

    Las excepciones se declaran con su motivo, no se toleran en silencio.
    """
    fronteras = {
        "app/core/config.py": "es el punto donde la configuración entra",
    }
    culpables = []
    for p in sorted((RAIZ_API / "app").rglob("*.py")):
        relativa = p.relative_to(RAIZ_API).as_posix()
        if relativa in fronteras:
            continue
        texto = p.read_text(encoding="utf-8")
        # Se descartan comentarios y cadenas: un docstring que MENCIONE
        # `os.environ` no es una lectura del entorno. Es el fallo que ya
        # apareció tres veces en esta sesión —el control marcando su propia
        # documentación—, así que aquí se analiza el árbol, no el texto.
        try:
            arbol = ast.parse(texto)
        except SyntaxError:
            continue
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Attribute) and nodo.attr in {"environ", "getenv"}:
                culpables.append(f"{relativa}:{nodo.lineno}")
    assert not culpables, (
        f"Configuración leída fuera de `Settings`: {culpables}. Añadila a la "
        f"clase, o declarala en `fronteras` con su motivo."
    )


# ---------------------------------------------------------------------------
# Factor 6 — procesos sin estado
# ---------------------------------------------------------------------------

def test_produccion_no_arranca_con_almacenamiento_local() -> None:
    """El hueco real de ARQ-04, y no se veía leyendo el código.

    `STORAGE_BACKEND` vale `local` por defecto. En producción eso manda los
    archivos al disco del contenedor: se pierden en cada despliegue y una
    segunda réplica no ve los de la primera. Y falla en silencio — la subida
    devuelve 200 y el documento desaparece más tarde, cuando ya nadie asocia
    las dos cosas.

    Nada lo impedía. Ahora no arranca.
    """
    from app.core.config import Settings

    with pytest.raises(ValidationError, match="STORAGE_BACKEND"):
        Settings(PYTHON_ENV="production", STORAGE_BACKEND="local")


def test_produccion_arranca_con_almacenamiento_de_objetos() -> None:
    """El caso simétrico: sin él, la validación podría rechazar todo y el
    arreglo sería quitarla.
    """
    from app.core.config import Settings

    assert Settings(PYTHON_ENV="production", STORAGE_BACKEND="s3").STORAGE_BACKEND == "s3"


def test_desarrollo_sigue_pudiendo_usar_disco_local() -> None:
    """Exigir S3 en local obligaría a levantar MinIO para escribir código, y un
    control que estorba al trabajo diario se desactiva.
    """
    from app.core.config import Settings

    assert Settings(PYTHON_ENV="development", STORAGE_BACKEND="local").STORAGE_BACKEND == "local"


def test_no_hay_estado_de_proceso_en_memoria() -> None:
    """El barrido: una estructura mutable a nivel de módulo que acumule datos
    entre peticiones es estado de proceso, y con dos réplicas cada una tiene el
    suyo.

    Se aceptan las constantes en MAYÚSCULAS —tablas de consulta, no estado— y
    `__all__`, que es protocolo del lenguaje.
    """
    sospechosos = []
    for p in sorted((RAIZ_API / "app").rglob("*.py")):
        try:
            arbol = ast.parse(p.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for nodo in arbol.body:
            if isinstance(nodo, ast.Assign) and isinstance(
                nodo.value, (ast.Dict, ast.List, ast.Set)
            ):
                for destino in nodo.targets:
                    if isinstance(destino, ast.Name) and not destino.id.isupper():
                        if destino.id == "__all__":
                            continue
                        sospechosos.append(
                            f"{p.relative_to(RAIZ_API).as_posix()}:{nodo.lineno}: {destino.id}"
                        )
    assert not sospechosos, (
        f"Estado mutable a nivel de módulo: {sospechosos}. Con más de una "
        f"réplica cada proceso tendría el suyo, y el resultado dependería de "
        f"cuál atendió la petición. Va a Redis o a la base."
    )


def test_el_estado_compartido_vive_fuera_del_proceso() -> None:
    """Lo que sí es estado —el preview del asistente de importación— está en
    Redis y no en un diccionario del módulo. Es el caso que demuestra que el
    barrido de arriba no pasa por casualidad.
    """
    fuente = (RAIZ_API / "app" / "services" / "import_job_store.py").read_text(encoding="utf-8")
    assert "redis" in fuente.lower()


# ---------------------------------------------------------------------------
# Factor 11 — registros a la salida estándar
# ---------------------------------------------------------------------------

def test_los_registros_salen_por_la_salida_estandar() -> None:
    """Cerrado por OPS-01 y comprobado aquí porque ARQ-04 lo nombra aparte.

    `stdout` explícitamente, no `stderr`: `logging` manda a `stderr` por
    defecto, y ahí un INFO se lee como un fallo en cualquier agregador que
    separe los dos flujos.
    """
    fuente = (RAIZ_API / "app" / "core" / "observabilidad.py").read_text(encoding="utf-8")
    assert "StreamHandler(sys.stdout)" in fuente


def test_los_dos_procesos_configuran_su_registro() -> None:
    """El worker es el que se olvida: sobrescribe el CMD y nunca importa
    `main.py`, así que lo que se cablee allí en el worker no existe.
    """
    for entrada in ("app/main.py", "app/workers/celery_app.py"):
        fuente = (RAIZ_API / entrada).read_text(encoding="utf-8")
        assert "configurar_registro(" in fuente, f"`{entrada}` no configura su registro."
