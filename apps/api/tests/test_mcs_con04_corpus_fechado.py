"""El corpus de contexto viaja fechado y avisado (MCS CON-04).

CON-04 pide que las cifras vivas no residan en el corpus y se obtengan en la
consulta con una herramienta determinista. La mitad calculada ya cumple desde la
Tanda A4. Esta es la otra mitad: los tres campos de memoria del proyecto son
texto libre, y nada impide que un PM escriba una cifra ahí.

Lo que se fija aquí es la mitigación: el bloque avisa de que son textos
guardados y cada sección lleva su fecha, para que el modelo pueda relativizar
una cifra vieja en vez de presentarla como actual.
"""
from __future__ import annotations

from datetime import datetime

from app.services.ai.project_context import compose_context_block

MARZO = datetime(2026, 3, 12, 9, 30)
JULIO = datetime(2026, 7, 28, 18, 0)


def test_el_bloque_avisa_de_que_no_son_datos_en_vivo() -> None:
    bloque = compose_context_block(
        project_name="Torre Norte",
        instructions_md="Priorizá el cronograma sobre el costo.",
    )
    assert bloque is not None
    assert "no datos en vivo" in bloque
    assert "gana el dato calculado" in bloque


def test_lo_que_escribe_el_pm_lleva_su_fecha() -> None:
    bloque = compose_context_block(
        instructions_md="El presupuesto son 1.2 M y vamos al 40 %.",
        context_md="El cliente exige informe quincenal.",
        context_updated_at=MARZO,
    )
    assert bloque is not None
    assert "Instrucciones permanentes del PM, escrito el 2026-03-12" in bloque
    assert "reglas de negocio del proyecto, escrito el 2026-03-12" in bloque


def test_el_resumen_automatico_lleva_su_propia_marca() -> None:
    """Lo reescribe el worker por su cuenta: su fecha no es la del PM."""
    bloque = compose_context_block(
        instructions_md="Priorizá el cronograma.",
        auto_summary_md="En la última minuta se acordó adelantar la entrega.",
        context_updated_at=MARZO,
        auto_summary_updated_at=JULIO,
    )
    assert bloque is not None
    assert "minutas previas, actualizado el 2026-07-28" in bloque
    assert "escrito el 2026-03-12" in bloque


def test_sin_fecha_se_dice_que_no_la_hay() -> None:
    """Callar la ausencia de fecha la haría parecer reciente."""
    bloque = compose_context_block(
        auto_summary_md="Resumen sin marca de tiempo.",
    )
    assert bloque is not None
    assert "minutas previas, sin fecha" in bloque


def test_sin_memoria_ni_descripcion_sigue_sin_haber_bloque() -> None:
    """El aviso no debe hacer aparecer un bloque donde antes no había nada."""
    assert compose_context_block(project_name="Torre Norte") is None
    assert compose_context_block() is None
