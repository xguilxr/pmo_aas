"""D-2 / ADR-019 — la fase `support` se llama `hypercare`.

La revisión del glosario confirmó que la fase es legítima —acompañamiento
acotado tras la puesta en marcha, y una forma de cierre— y que el problema era
el nombre: `support` se lee como «mesa de ayuda», que es una función permanente.

Lo que estas pruebas defienden, en orden de importancia:

1. **La ventana de compatibilidad.** Un cliente que todavía mande `support`
   —una pestaña abierta desde antes del despliegue, un filtro guardado, un
   script— sigue funcionando, y su valor se guarda ya como `hypercare`.
   Romperlo sería cobrarle al usuario un cambio de vocabulario que no pidió.
2. **La salida siempre es canónica.** La ventana es para entrar, no para
   quedarse: si el API devolviera `support` alguna vez, el frontend —cuyo tipo
   ya no lo contempla— lo pintaría como fase desconocida.
3. **Que la fase sigue contando como activa.** Es lo que se rompe sin querer al
   renombrar: `ACTIVE_PHASES` decide qué entra en los snapshots y en el
   dashboard, y una lista que se quedara con `support` dejaría los proyectos en
   hypercare fuera de todas las métricas, en silencio.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.schemas.project import PhaseChange, ProjectCreate, normalizar_fase

RAIZ_API = Path(__file__).resolve().parents[1]


def test_el_vocabulario_canonico_son_cuatro_fases():
    from typing import get_args

    from app.schemas.project import ProjectPhase

    assert set(get_args(ProjectPhase)) == {
        "planning",
        "execution",
        "hypercare",
        "closed",
    }


# ---------------------------------------------------------------------------
# La ventana de compatibilidad
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("support", "hypercare"),   # el nombre viejo, traducido
        ("hypercare", "hypercare"),  # el nuevo, intacto
        ("planning", "planning"),    # el resto, sin tocar
        (None, None),                # no explota con lo que no es cadena
        (7, 7),
    ],
)
def test_normalizar_fase(entrada, esperado):
    assert normalizar_fase(entrada) == esperado


def test_un_cliente_viejo_puede_seguir_creando_proyectos():
    from uuid import uuid4

    proyecto = ProjectCreate(
        name="Proyecto de prueba",
        description="d",
        type="bau",
        priority=3,
        organization_id=uuid4(),
        pm_id=uuid4(),
        phase="support",
    )

    assert proyecto.phase == "hypercare", (
        "Un cliente que aún manda `support` debe seguir funcionando, y su valor "
        "guardarse ya como `hypercare` (ADR-019)."
    )


def test_el_cambio_de_fase_tambien_acepta_el_nombre_viejo():
    assert PhaseChange(new_phase="support").new_phase == "hypercare"


def test_lo_que_no_es_una_fase_sigue_fallando():
    """La ventana traduce un nombre conocido; no abre la puerta a cualquiera."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        PhaseChange(new_phase="mesa-de-ayuda")


# ---------------------------------------------------------------------------
# Que no quede nadie hablando el idioma viejo
# ---------------------------------------------------------------------------


#: Los sitios que deciden algo a partir del nombre de la fase. Si uno se queda
#: en `support`, no falla nada: simplemente deja de encontrar proyectos.
DECIDEN_POR_FASE = [
    "app/services/analytics/snapshots.py",
    "app/api/v1/endpoints/dashboard.py",
    "app/api/v1/endpoints/projects.py",
    "app/api/v1/endpoints/admin_panel.py",
    "app/services/lessons_export.py",
]


@pytest.mark.parametrize("ruta", DECIDEN_POR_FASE)
def test_ningun_sitio_sigue_comparando_contra_support(ruta):
    texto = (RAIZ_API / ruta).read_text(encoding="utf-8")
    vivas = [
        n
        for n, linea in enumerate(texto.splitlines(), 1)
        if '"support"' in linea and not linea.lstrip().startswith("#")
    ]

    assert not vivas, (
        f"{ruta} sigue comparando contra «support» en las líneas {vivas}. No "
        f"rompe nada: deja de encontrar proyectos, que es peor."
    )


def test_hypercare_sigue_contando_como_fase_activa():
    """Lo que se rompe sin querer: los proyectos salen de todas las métricas."""
    from app.services.analytics.snapshots import ACTIVE_PHASES

    assert "hypercare" in ACTIVE_PHASES
    assert "closed" not in ACTIVE_PHASES, "«activo» sigue significando «no cerrado»"


def test_la_transicion_de_fases_conserva_la_forma():
    """`execution → hypercare → closed`. Renombrar no reabre el grafo."""
    from app.api.v1.endpoints.projects import VALID_TRANSITIONS

    assert VALID_TRANSITIONS["execution"] == {"hypercare", "closed"}
    assert VALID_TRANSITIONS["hypercare"] == {"closed"}


def test_la_migracion_cubre_las_dos_tablas():
    """`lessons_learned.phase` comparte vocabulario y es la fácil de olvidar."""
    migracion = (
        RAIZ_API / "alembic" / "versions" / "20260805_0098_fase_hypercare.py"
    ).read_text(encoding="utf-8")

    assert '_TABLAS = ("projects", "lessons_learned")' in migracion
    assert "def downgrade" in migracion and "'support'" in migracion.split("def downgrade")[1]
