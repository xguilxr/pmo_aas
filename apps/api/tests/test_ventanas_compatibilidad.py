"""Las ventanas de compatibilidad se cierran con dato, no con corazonada.

Decisión del owner (2026-08-05). Los renombrados del glosario salen aceptando el
nombre viejo a la entrada para no romper a un cliente que no se ha actualizado.
El problema de una ventana no es abrirla: es que **nadie decide cuándo se
cierra**. Sin criterio se vuelve permanente, y cada renombrado deja una
traducción para siempre.

El criterio elegido es contar. Cada uso de un nombre retirado deja una línea con
el prefijo `compat.nombre_viejo`; a los dos meses se mira el contador. En cero,
se quita la ventana; si no, se sabe quién la usa antes de romperle nada.

Esta suite defiende las dos mitades de que eso funcione:

1. **Que el rastro salga**, en las cuatro puertas abiertas hoy.
2. **Que ninguna ventana quede sin declarar.** Una ventana que nadie anotó es
   exactamente la que nadie recuerda cerrar — el trinquete recorre el código
   buscando `registrar_uso` y exige su fila en `VENTANAS`.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

import pytest

from app.core.compatibilidad import VENTANAS, registrar_uso

RAIZ_API = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Que el rastro salga, y con qué forma
# ---------------------------------------------------------------------------


def test_el_rastro_lleva_el_prefijo_por_el_que_se_cuenta(caplog):
    """`compat.nombre_viejo` es lo que se busca en los registros o en Sentry."""
    with caplog.at_level(logging.INFO, logger="pmoaas.compat"):
        registrar_uso("portfolio_function", donde="prueba")

    assert len(caplog.records) == 1
    mensaje = caplog.records[0].getMessage()
    assert mensaje.startswith("compat.nombre_viejo")
    assert "campo=portfolio_function" in mensaje
    assert "nuevo=discipline" in mensaje
    assert "donde=prueba" in mensaje
    assert "adr=ADR-021" in mensaje


def test_una_clave_sin_declarar_se_registra_igual(caplog):
    """El dato vale aunque falte la ficha; del resto se encarga el trinquete."""
    with caplog.at_level(logging.INFO, logger="pmoaas.compat"):
        registrar_uso("algo_que_nadie_declaro", donde="prueba")

    assert len(caplog.records) == 1
    assert "campo=algo_que_nadie_declaro" in caplog.records[0].getMessage()


def test_registrar_uso_nunca_lanza():
    """Romper la petición que la ventana venía a salvar sería peor que nada."""
    for clave in (None, 7, "", "inexistente"):
        registrar_uso(clave, donde="prueba")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Las cuatro puertas abiertas hoy
# ---------------------------------------------------------------------------


def test_la_fase_vieja_deja_rastro(caplog):
    from app.schemas.project import normalizar_fase

    with caplog.at_level(logging.INFO, logger="pmoaas.compat"):
        normalizar_fase("support")

    assert any("phase=support" in r.getMessage() for r in caplog.records)


def test_la_fase_nueva_no_deja_rastro(caplog):
    """Si el canónico también contara, el contador nunca llegaría a cero."""
    from app.schemas.project import normalizar_fase

    with caplog.at_level(logging.INFO, logger="pmoaas.compat"):
        normalizar_fase("hypercare")
        normalizar_fase("planning")

    assert caplog.records == []


def test_el_cuerpo_con_el_nombre_viejo_deja_rastro(caplog):
    """`AliasChoices` acepta los dos y no dice cuál llegó; por eso se mira crudo."""
    from app.schemas.area import ActorCreate

    with caplog.at_level(logging.INFO, logger="pmoaas.compat"):
        actor = ActorCreate(name="Ana", portfolio_function="datos")

    assert actor.discipline == "datos"
    assert any("donde=cuerpo de creación" in r.getMessage() for r in caplog.records)


def test_el_cuerpo_con_el_nombre_nuevo_no_deja_rastro(caplog):
    from app.schemas.area import ActorCreate

    with caplog.at_level(logging.INFO, logger="pmoaas.compat"):
        ActorCreate(name="Beto", discipline="datos")

    assert caplog.records == []


def test_la_tarea_con_wbs_viejo_deja_rastro_y_se_normaliza(caplog):
    """D-3 / ADR-020: el cliente que aún manda `wbs` sigue funcionando."""
    from app.api.v1.endpoints.tasks import TaskCreate

    with caplog.at_level(logging.INFO, logger="pmoaas.compat"):
        tarea = TaskCreate(name="Analizar", wbs="1.2")

    assert tarea.wbs_code == "1.2", "el nombre viejo tiene que llegar al campo nuevo"
    assert any("donde=cuerpo de tarea" in r.getMessage() for r in caplog.records)


def test_el_patch_de_tarea_tambien_acepta_el_wbs_viejo(caplog):
    """La puerta del PATCH es distinta de la del POST y se olvida más.

    `TaskUpdate` decide qué tocar con `exclude_unset`; si el alias no llegara,
    mandar `wbs` no fallaría — simplemente **no cambiaría nada**, que es la
    forma de romperse que ADR-020 señaló como la peligrosa.
    """
    from app.api.v1.endpoints.tasks import TaskUpdate

    with caplog.at_level(logging.INFO, logger="pmoaas.compat"):
        patch = TaskUpdate(wbs="2.1")

    assert patch.wbs_code == "2.1"
    assert "wbs_code" in patch.model_dump(exclude_unset=True)
    assert any("donde=cuerpo de tarea" in r.getMessage() for r in caplog.records)


def test_la_tarea_con_wbs_code_no_deja_rastro(caplog):
    from app.api.v1.endpoints.tasks import TaskCreate

    with caplog.at_level(logging.INFO, logger="pmoaas.compat"):
        TaskCreate(name="Analizar", wbs_code="1.2")

    assert caplog.records == []


# ---------------------------------------------------------------------------
# Que ninguna ventana quede sin declarar
# ---------------------------------------------------------------------------


def test_toda_ventana_del_codigo_esta_declarada():
    """Una ventana sin ficha es la que nadie recuerda cerrar."""
    usos = set()
    for ruta in (RAIZ_API / "app").rglob("*.py"):
        if ruta.name == "compatibilidad.py":
            continue
        for clave in re.findall(r'registrar_uso\(\s*"([^"]+)"', ruta.read_text(encoding="utf-8")):
            usos.add(clave)

    sin_declarar = usos - set(VENTANAS)
    assert not sin_declarar, (
        f"Estas ventanas se registran pero no están en `VENTANAS`: "
        f"{sorted(sin_declarar)}. Sin ficha no hay ADR, ni fecha, ni criterio "
        f"para cerrarlas."
    )


def test_ninguna_ventana_declarada_esta_muerta():
    """Una ficha sin uso en el código es ruido: o falta cablearla, o sobra."""
    codigo = "".join(
        ruta.read_text(encoding="utf-8")
        for ruta in (RAIZ_API / "app").rglob("*.py")
        if ruta.name != "compatibilidad.py"
    )
    huerfanas = [clave for clave in VENTANAS if f'registrar_uso("{clave}"' not in codigo]

    assert not huerfanas, (
        f"Declaradas y sin usar: {huerfanas}. Si la ventana ya se cerró, quita "
        f"su fila; si no, falta instrumentarla."
    )


@pytest.mark.parametrize("clave", sorted(VENTANAS))
def test_cada_ventana_dice_de_dónde_viene_y_desde_cuándo(clave):
    ventana = VENTANAS[clave]

    assert ventana.nuevo and ventana.nuevo != ventana.viejo
    assert ventana.adr.startswith("ADR-"), "Sin ADR no hay decisión que revisar"
    assert ventana.desde.year >= 2026
