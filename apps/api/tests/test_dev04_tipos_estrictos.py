"""DEV-04 — la verificación de tipos corre, corre estricta, y el gate muerde.

La auditoría dejó el requisito PARCIAL y ALTA: `ruff` cubría el análisis
estático y `tsc --noEmit` la verificación de tipos del frontend, pero en Python
no había ninguna. 191 módulos de backend sin verificar.

`mypy --strict` devolvía 1.188 errores, así que enchufarlo tal cual habría
dejado el CI en rojo en cada PR — la forma conocida de que un control se
desactive en dos días. La salida es la misma que el repositorio ya usó dos
veces: **lo estricto se ejecuta entero** y el pasivo heredado va a una línea
base nominal que solo puede encoger.

Lo que esta suite defiende son los dos extremos por los que ese arreglo se
degrada solo:

- **que `strict` siga siendo `strict`.** La tentación, ante un PR bloqueado, es
  desactivar `no-untyped-def` en la configuración. Eso no rompe nada visible y
  vacía el requisito.
- **que el gate muerda.** Un comparador que dejara pasar un error nuevo
  convertiría la línea base en una lista de excepciones infinita. Se prueba con
  entradas sintéticas, sin llamar a mypy: un gate que solo puede probarse
  corriéndolo entero es un gate que nadie prueba.
"""
from __future__ import annotations

import subprocess
import sys
import tomllib
from collections import Counter
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[3]
API = RAIZ / "apps" / "api"

sys.path.insert(0, str(RAIZ / "scripts"))
from check_tipos import ERROR, comparar  # noqa: E402


@pytest.fixture(scope="module")
def mypy_config() -> dict:
    datos = tomllib.loads((API / "pyproject.toml").read_text(encoding="utf-8"))
    return datos["tool"]["mypy"]


def test_la_verificacion_de_tipos_existe_y_es_estricta(mypy_config: dict) -> None:
    """`strict = true` y no una selección de reglas a mano.

    Elegir qué mitad de estricto se aplica es exactamente la forma de declarar
    el requisito cumplido sin cumplirlo: el marco dice «en modo estricto».
    """
    assert mypy_config.get("strict") is True, (
        "`[tool.mypy] strict` dejó de ser `true`. DEV-04 pide modo estricto; "
        "si hubo que relajarlo, va con razón escrita y no en silencio."
    )
    assert mypy_config.get("files") == ["app"], (
        "El alcance de mypy se movió. Verificar tipos de una parte del backend "
        "y no de la otra deja el requisito en PARCIAL."
    )


def test_no_se_apagan_reglas_de_estricto_por_la_puerta_de_atras(mypy_config: dict) -> None:
    """`strict = true` seguido de `disallow_untyped_defs = false` es un no-op.

    Es la maniobra que un PR bloqueado invita a hacer, y no la ve nadie salvo
    quien lea la configuración entera.
    """
    apagadas = [
        clave
        for clave, valor in mypy_config.items()
        if clave.startswith(("disallow_", "warn_", "strict_", "no_implicit_"))
        and valor is False
    ]
    assert not apagadas, (
        f"Reglas de `strict` desactivadas explícitamente: {apagadas}. El pasivo "
        "heredado va a `.mypy-baseline`, que es nominal y encoge; apagar la "
        "regla lo vuelve ilimitado."
    )
    assert "disable_error_code" not in mypy_config, (
        "`disable_error_code` apaga una familia entera de errores para siempre. "
        "Lo que se tolera va nombrado en la línea base."
    )


def test_las_bibliotecas_sin_tipos_van_enumeradas() -> None:
    """`ignore_missing_imports` global apaga también el aviso de la séptima.

    Meter una dependencia sin tipos tiene que ser una decisión, no un efecto
    secundario de una opción puesta hace meses.
    """
    datos = tomllib.loads((API / "pyproject.toml").read_text(encoding="utf-8"))
    assert datos["tool"]["mypy"].get("ignore_missing_imports") is not True, (
        "`ignore_missing_imports` está puesto globalmente: cualquier "
        "dependencia sin tipos entra sin que nadie lo note."
    )
    (override,) = (
        o for o in datos["tool"]["mypy"]["overrides"] if o.get("ignore_missing_imports")
    )
    assert override["module"], "La lista de bibliotecas sin tipos quedó vacía."


def test_el_gate_rechaza_un_error_nuevo() -> None:
    """El invariante que decide si esto es un control o un adorno."""
    base = Counter({("app/a.py", "no-untyped-def", "falta anotación"): 1})
    observado = Counter(
        {
            ("app/a.py", "no-untyped-def", "falta anotación"): 1,
            ("app/b.py", "arg-type", "tipo incompatible"): 1,
        }
    )
    regresiones, _ = comparar(observado, base)
    assert len(regresiones) == 1 and "app/b.py" in regresiones[0]


def test_el_gate_cuenta_las_repeticiones() -> None:
    """Sin conteo, el segundo `def` sin anotar del mismo archivo entra gratis.

    La huella no lleva número de línea —cambia al insertar cualquier cosa—, así
    que dos errores idénticos en el mismo archivo comparten huella. Solo el
    conteo los distingue.
    """
    huella = ("app/a.py", "no-untyped-def", "falta anotación")
    regresiones, _ = comparar(Counter({huella: 4}), Counter({huella: 3}))
    assert len(regresiones) == 1 and "4 veces, toleradas 3" in regresiones[0]


def test_el_gate_no_se_queja_de_lo_arreglado() -> None:
    """Arreglar no puede poner el CI en rojo, o nadie arregla.

    Se informa para que se regenere la línea base —el trinquete se aprieta—,
    pero no se falla.
    """
    huella = ("app/a.py", "no-untyped-def", "falta anotación")
    regresiones, arreglados = comparar(Counter(), Counter({huella: 2}))
    assert not regresiones
    assert len(arreglados) == 1 and "2 menos" in arreglados[0]


@pytest.mark.parametrize(
    "linea",
    [
        "app/main.py:208: error: Unsupported target for indexed assignment  [index]",
        "app/api/deps.py:12:5: error: Function is missing a return type annotation  [no-untyped-def]",
    ],
)
def test_la_huella_ignora_el_numero_de_linea(linea: str) -> None:
    """Con la línea dentro, la línea base se invalida en cada edición.

    Y una línea base que hay que regenerar cada vez se regenera a ciegas, que
    es como deja de vigilar nada. Se cubren las dos formas de salida de mypy:
    con columna y sin ella.
    """
    m = ERROR.match(linea)
    assert m is not None, f"La expresión dejó de reconocer la salida de mypy: {linea!r}"
    assert not any(c.isdigit() for c in m["ruta"] + m["codigo"])


def test_la_linea_base_no_menciona_archivos_que_ya_no_existen() -> None:
    """Una huella sobre un archivo borrado no la produce nadie: es peso muerto.

    Y peor: infla la cifra del pasivo, que es la que dice cuánto falta.
    """
    base = API / ".mypy-baseline"
    fantasmas = sorted(
        {
            linea.split("\t")[1]
            for linea in base.read_text(encoding="utf-8").splitlines()
            if linea and not linea.startswith("#") and not (API / linea.split("\t")[1]).exists()
        }
    )
    assert not fantasmas, (
        f"La línea base cita archivos inexistentes: {fantasmas}. Regenerá con "
        "`python scripts/check_tipos.py --regenerar`."
    )


def test_el_gate_no_da_verde_cuando_mypy_no_corre() -> None:
    """El defecto que este mismo gate tuvo el día que se escribió.

    Un intérprete sin mypy instalado devuelve **1**, igual que «encontré
    errores», y escribe `No module named mypy` en la salida de error. El
    verificador leía cero errores, los comparaba con una línea base de 1.163 y
    anunciaba «sin regresiones»: verde, sin haber analizado nada. Se vio al
    invocarlo con el intérprete del sistema; en CI habría bastado con que
    cambiara el paso de instalación.

    Un control que da verde cuando no corre es peor que no tenerlo: sustituye
    una ausencia visible por una garantía falsa.
    """
    guion = RAIZ / "scripts" / "check_tipos.py"
    # `sys.executable` dentro de la suite ES el del entorno, que sí tiene mypy.
    # Se busca a propósito un intérprete que no lo tenga.
    ajeno = "/usr/bin/python3"
    if not Path(ajeno).exists():
        pytest.skip("no hay un intérprete sin mypy con el que probarlo")
    sondeo = subprocess.run(
        [ajeno, "-c", "import mypy"], capture_output=True
    )
    if sondeo.returncode == 0:
        pytest.skip(f"{ajeno} también tiene mypy: no sirve de contraejemplo")

    resultado = subprocess.run([ajeno, str(guion)], capture_output=True, text=True)
    assert resultado.returncode == 1, (
        "El gate dio verde con un intérprete sin mypy. Vuelve a ser una "
        "garantía falsa."
    )
    assert "no analizó" in resultado.stderr or "no analizó" in resultado.stdout
