"""REQ-02 — la generación de informes se mide, para poder declarar el escenario.

MCS REQ-02 pide **cuatro escenarios de calidad con medida numérica**. Hoy hay
cero, y el motivo no es descuido: no se puede declarar «un informe se genera en
menos de N segundos» sin saber cuánto tarda. Poner un número a ojo es el error
que este expediente lleva cinco recuentos evitando.

Primero se mide; el escenario se declara después, con el percentil 95 real.

Esta suite prueba el instrumento, no el número: que mida, que no altere el
resultado, que no se trague un fallo, y —el caso que de verdad importa— que una
corrutina se mida de verdad en vez de devolver cero milisegundos siempre.
"""
from __future__ import annotations

import asyncio
import inspect
import logging

import pytest

from app.core.observabilidad import medido, medir


def test_mide_y_devuelve_el_valor_intacto(caplog: pytest.LogCaptureFixture) -> None:
    """Lo primero que tiene que cumplir una instrumentación: no estorbar."""

    @medido("prueba.sincrona")
    def calcular(a: int, b: int) -> int:
        return a + b

    with caplog.at_level(logging.INFO, logger="pmoaas.medicion"):
        assert calcular(2, 3) == 5

    (registro,) = (r for r in caplog.records if r.msg == "generacion")
    assert registro.operacion == "prueba.sincrona"
    assert registro.exito is True
    assert isinstance(registro.duracion_ms, int)


@pytest.mark.asyncio
async def test_una_corrutina_se_mide_de_verdad(caplog: pytest.LogCaptureFixture) -> None:
    """El caso que justifica que el decorador mire la firma.

    Si `medido` envolviera una corrutina con el envoltorio síncrono, devolvería
    el objeto corrutina **sin esperarlo**: la medición marcaría microsegundos
    siempre, pasara lo que pasara dentro. Y eso no se lee como un error, se lee
    como un informe instantáneo — que es la peor forma de fallar para algo cuyo
    único propósito es dar una cifra creíble.

    Por eso el caso duerme: sin espera real, el tiempo medido no puede superar
    el umbral.
    """

    @medido("prueba.asincrona")
    async def tarda() -> str:
        await asyncio.sleep(0.05)
        return "listo"

    with caplog.at_level(logging.INFO, logger="pmoaas.medicion"):
        assert await tarda() == "listo"

    (registro,) = (r for r in caplog.records if r.msg == "generacion")
    assert registro.duracion_ms >= 40, (
        f"midió {registro.duracion_ms} ms sobre una corrutina que duerme 50. "
        f"El decorador no esperó: está midiendo la creación de la corrutina, "
        f"no su ejecución."
    )


def test_el_decorador_conserva_la_naturaleza_de_la_funcion() -> None:
    """El complemento del anterior, comprobado sobre los puntos reales.

    Si un `async def` decorado dejara de ser corrutina, cualquier `await` sobre
    él fallaría — o peor, algún llamador lo trataría como valor.
    """
    from app.services.charter_generator import generate_charter_docx
    from app.services.html_report_renderer import render_report_html
    from app.services.reports.engine import render_template

    assert inspect.iscoroutinefunction(generate_charter_docx)
    assert inspect.iscoroutinefunction(render_template)
    assert not inspect.iscoroutinefunction(render_report_html)


def test_no_se_traga_la_excepcion_y_la_marca(caplog: pytest.LogCaptureFixture) -> None:
    """Una instrumentación que se coma un fallo es peor que no tenerla.

    Y además hay que medir el camino de error: los informes que revientan
    suelen ser los lentos, así que excluirlos sesga la medición justo hacia
    donde no interesa.
    """

    @medido("prueba.falla")
    def revienta() -> None:
        raise ValueError("sube")

    with caplog.at_level(logging.INFO, logger="pmoaas.medicion"):
        with pytest.raises(ValueError, match="sube"):
            revienta()

    (registro,) = (r for r in caplog.records if r.msg == "generacion")
    assert registro.exito is False


def test_las_etiquetas_del_bloque_llegan_al_registro(caplog: pytest.LogCaptureFixture) -> None:
    """Lo que solo se sabe dentro del bloque —tamaño, filas— es lo que después
    permite preguntar «¿tarda por el volumen o por otra cosa?».
    """
    with caplog.at_level(logging.INFO, logger="pmoaas.medicion"):
        with medir("prueba.etiquetas", tipo="semanal") as m:
            m["bytes"] = 2048

    (registro,) = (r for r in caplog.records if r.msg == "generacion")
    assert registro.tipo == "semanal"
    assert registro.bytes == 2048


def test_funciona_sin_sentry() -> None:
    """En las pruebas y en local no hay DSN, y aun así la duración tiene que salir.

    Una medición que solo existe en producción no se puede probar, y una que no
    se puede probar deja de funcionar sin que nadie lo note.
    """
    from app.core.config import settings

    assert not settings.SENTRY_DSN, "Este caso mide el camino SIN Sentry."
    with medir("prueba.sin_sentry"):
        pass


def test_los_cuatro_puntos_de_generacion_estan_medidos() -> None:
    """El barrido: sin él, bastaría quitar un decorador para perder un cuarto de
    la medición sin que nada se ponga rojo.

    Son los cuatro sitios donde el producto construye un entregable: informe de
    proyecto, minuta, acta en `.docx` y plantilla del constructor de informes.
    """
    from pathlib import Path

    raiz = Path(__file__).resolve().parents[1] / "app" / "services"
    esperado = {
        "html_report_renderer.py": ["informe.html", "informe.minuta_html"],
        "charter_generator.py": ["informe.acta_docx"],
        "reports/engine.py": ["informe.plantilla"],
    }
    for relativa, operaciones in esperado.items():
        fuente = (raiz / relativa).read_text(encoding="utf-8")
        for operacion in operaciones:
            assert f'@medido("{operacion}' in fuente, (
                f"`{relativa}` perdió la medición de «{operacion}». REQ-02 se "
                f"declara con el percentil 95 real, y un cuarto de la muestra "
                f"que deja de emitirse no se nota en el percentil: lo sesga."
            )
