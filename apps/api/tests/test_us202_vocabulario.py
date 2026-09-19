"""US-202 / ADR-038 — el vocabulario del proyecto, y que no se parta en dos.

Un renombrado de vocabulario tiene una forma de fallar que no avisa: la copia
que se olvida sigue comparando contra un valor que ya no existe y **devuelve
siempre falso**. Un proyecto cerrado contaría como activo; un filtro por fase no
traería nada. Ningún error, ninguna pantalla roja.

Así que aquí no se prueba «que las etiquetas estén bien». Se prueba que las
**cinco copias** del catálogo digan lo mismo:

1. `dominio/proyecto.py` — la definición.
2. `schemas/project.py` — el `Literal` que valida Pydantic **la fase**, que no
   puede derivarse (`Literal[*FASES]` no es válido) y por tanto se escribe a
   mano. El tipo ya no es un `Literal`: desde US-286 lo valida el catálogo del
   inquilino (DEC-040), y lo que se ata aquí es la **siembra** —con qué nace un
   inquilino— no la lista viva.
3. `endpoints/projects.py::VALID_TRANSITIONS` — el grafo del ciclo de vida.
4. `services/analytics/snapshots.py::ACTIVE_PHASES` — lo que cuenta como vivo.
5. `apps/web/lib/api/projects.ts` — el tipo del frontend.

Y que la ventana de compatibilidad funcione en las dos direcciones: el nombre
viejo entra y se guarda canónico **dejando rastro**; el canónico no deja rastro,
porque si contara, el contador no llegaría nunca a cero y la ventana no se podría
cerrar con dato.
"""
from __future__ import annotations

import importlib.util
import logging
import re
from pathlib import Path
from types import ModuleType
from typing import get_args
from uuid import uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine

from alembic.migration import MigrationContext
from alembic.operations import Operations
from app.api.v1.endpoints.projects import VALID_TRANSITIONS
from app.dominio.proyecto import (
    BAU,
    CERRADO,
    EJECUCION,
    ETIQUETAS_FASE,
    ETIQUETAS_TIPO,
    FASES,
    FASES_ACTIVAS,
    FASES_RENOMBRADAS,
    FASES_TERMINALES,
    HYPERCARE,
    PREPARACION,
    TIPOS,
    TIPOS_RENOMBRADOS,
    TRANSICIONES,
    etiqueta_fase,
    etiqueta_tipo,
)
from app.models.modules import Lesson
from app.models.project import Project
from app.schemas.project import (
    PhaseChange,
    ProjectCreate,
    ProjectPhase,
    ProjectUpdate,
)
from app.services.analytics.snapshots import ACTIVE_PHASES

RAIZ_API = Path(__file__).resolve().parents[1]
RAIZ_REPO = RAIZ_API.parents[1]
MIGRACION = RAIZ_API / "alembic" / "versions" / "20260819_0110_vocabulario_fases_tipos.py"
TIPOS_WEB = RAIZ_REPO / "apps" / "web" / "lib" / "api" / "projects.ts"


# ---------------------------------------------------------------------------
# Las cinco copias dicen lo mismo
# ---------------------------------------------------------------------------


def test_el_literal_de_pydantic_es_el_catalogo_del_dominio() -> None:
    """`Literal` exige literales, así que se escribe a mano. Esto lo ata."""
    assert get_args(ProjectPhase) == FASES, (
        "El `Literal` de `ProjectPhase` y `dominio.proyecto.FASES` se separaron. "
        "Uno valida la entrada y el otro alimenta las comparaciones: con dos "
        "catálogos distintos, la API acepta un valor que el código nunca ve."
    )


@pytest.mark.asyncio
async def test_la_siembra_de_tipos_es_el_catalogo_del_dominio(db_session) -> None:
    """El tipo dejó de ser un `Literal`, así que lo atado cambia de sujeto.

    Antes se comparaba `get_args(ProjectType)` contra `TIPOS`. Desde US-286 el
    tipo se valida contra `tenant_catalog_values`, que es distinto por
    inquilino: lo que sigue teniendo que coincidir con el dominio es con qué
    nace un inquilino, porque de ahí salen las etiquetas y el tipo del
    frontend.
    """
    from app.models.tenant_catalog import CATALOGO_TIPO_PROYECTO
    from app.services import catalogos
    from tests.factories import create_tenant

    tenant = await create_tenant(db_session)
    await db_session.commit()
    valores = await catalogos.listar(db_session, tenant.id, CATALOGO_TIPO_PROYECTO)
    assert tuple(v.clave for v in valores) == TIPOS
    assert [v.etiqueta for v in valores] == [ETIQUETAS_TIPO[t] for t in TIPOS]


def test_las_fases_activas_son_exactamente_las_no_terminales() -> None:
    """Derivadas, no escritas: es el error que cometió D-2 con `support`.

    La lista se quedó con el nombre viejo y los proyectos en hypercare habrían
    salido de los snapshots sin que nada fallara.
    """
    assert set(FASES_ACTIVAS) == set(FASES) - FASES_TERMINALES
    assert set(ACTIVE_PHASES) == set(FASES_ACTIVAS)


def test_el_grafo_del_endpoint_es_el_del_dominio() -> None:
    assert VALID_TRANSITIONS is TRANSICIONES


def test_toda_fase_tiene_transiciones_declaradas() -> None:
    """Una fase sin fila cae en el `.get(p.phase, set())` del endpoint y queda
    atrapada: sin salidas y sin que nadie lo haya decidido."""
    assert set(TRANSICIONES) == set(FASES)


def test_las_dos_terminales_no_tienen_salida() -> None:
    for fase in FASES_TERMINALES:
        assert TRANSICIONES[fase] == frozenset()


def test_se_cancela_desde_cualquier_fase_viva() -> None:
    """Cancelar interrumpe el ciclo; no depende de dónde estaba el proyecto."""
    for fase in FASES_ACTIVAS:
        assert "cancelado" in TRANSICIONES[fase]


def test_un_proyecto_cerrado_no_se_puede_cancelar() -> None:
    """Ya tuvo su final. Permitirlo sería reescribir la historia (ADR-022)."""
    assert "cancelado" not in TRANSICIONES[CERRADO]


def test_cada_fase_y_cada_tipo_tienen_etiqueta() -> None:
    """Una fase sin etiqueta sale cruda en un reporte que va al cliente."""
    assert set(ETIQUETAS_FASE) == set(FASES)
    assert set(ETIQUETAS_TIPO) == set(TIPOS)


def test_el_tipo_del_frontend_declara_las_mismas_fases_y_tipos() -> None:
    """La quinta copia, y la única que vive en otro lenguaje.

    Sin esta comprobación, renombrar en el backend deja al frontend mandando un
    valor que la API rechaza —un 422 en el formulario— o pintando un badge en
    blanco. Se leen los literales de TypeScript, no las etiquetas: lo que tiene
    que coincidir es el contrato, no la traducción.

    **El tipo cambió de sujeto (US-288).** `ProjectType` en el frontend ya es
    `string`, porque la lista es distinta por inquilino y ese archivo no sabe
    cuál es. Lo que sigue teniendo que coincidir es `TIPOS_DE_FABRICA`: los
    cuatro con los que nace un inquilino, que son el respaldo mientras el
    catálogo carga. Si se separan, un inquilino recién creado vería en el
    desplegable un valor que su propio catálogo no tiene.
    """
    fuente = TIPOS_WEB.read_text(encoding="utf-8")

    bloque_fase = re.search(r"export type ProjectPhase\s*=([^;]+);", fuente)
    assert bloque_fase, "No encontré `ProjectPhase` en `lib/api/projects.ts`."
    assert set(re.findall(r'"([a-z]+)"', bloque_fase.group(1))) == set(FASES)

    bloque_tipo = re.search(
        r"export const TIPOS_DE_FABRICA\s*=\s*\[([^\]]+)\]", fuente
    )
    assert bloque_tipo, (
        "No encontré `TIPOS_DE_FABRICA` en `lib/api/projects.ts`. Desde US-288 "
        "el tipo del frontend es `string` y lo que se ata es la siembra."
    )
    assert set(re.findall(r'"([a-z]+)"', bloque_tipo.group(1))) == set(TIPOS)


def test_el_tipo_del_frontend_ya_no_es_una_lista_cerrada() -> None:
    """US-288: volver a cerrarlo dejaría fuera los tipos propios del inquilino.

    Es el error fácil de cometer al «arreglar» un `any`: devolverle el union a
    `ProjectType` y no enterarse de que el desplegable deja de aceptar lo que
    el catálogo sí acepta.
    """
    fuente = TIPOS_WEB.read_text(encoding="utf-8")
    bloque = re.search(r"export type ProjectType\s*=([^;]+);", fuente)
    assert bloque, "No encontré `ProjectType` en `lib/api/projects.ts`."
    assert bloque.group(1).strip() == "string", (
        "`ProjectType` volvió a ser una lista cerrada. Desde US-288 los tipos "
        "salen del catálogo del inquilino y la lista es distinta en cada uno."
    )


# ---------------------------------------------------------------------------
# La ventana de compatibilidad, en las dos direcciones
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("viejo", "nuevo"), sorted(FASES_RENOMBRADAS.items()))
def test_la_fase_vieja_entra_se_normaliza_y_deja_rastro(
    caplog: pytest.LogCaptureFixture, viejo: str, nuevo: str
) -> None:
    with caplog.at_level(logging.INFO, logger="pmoaas.compat"):
        cambio = PhaseChange(new_phase=viejo)

    assert cambio.new_phase == nuevo, (
        f"`{viejo}` tenía que llegar al campo como `{nuevo}`. Aceptar el nombre "
        "viejo y guardarlo tal cual sería peor que rechazarlo: el dato queda "
        "fuera del vocabulario y ninguna consulta lo encuentra."
    )
    assert any("compat.nombre_viejo" in r.getMessage() for r in caplog.records)


@pytest.mark.parametrize("fase", FASES)
def test_la_fase_canonica_no_deja_rastro(
    caplog: pytest.LogCaptureFixture, fase: str
) -> None:
    """Si el canónico también contara, el contador nunca llegaría a cero y la
    ventana no se podría cerrar con dato."""
    with caplog.at_level(logging.INFO, logger="pmoaas.compat"):
        PhaseChange(new_phase=fase)
    assert caplog.records == []


@pytest.mark.parametrize(("viejo", "nuevo"), sorted(TIPOS_RENOMBRADOS.items()))
def test_el_tipo_viejo_entra_se_normaliza_y_deja_rastro(
    caplog: pytest.LogCaptureFixture, viejo: str, nuevo: str
) -> None:
    """TC-202.1 — un proyecto con tipo legado se lee y se guarda mapeado."""
    with caplog.at_level(logging.INFO, logger="pmoaas.compat"):
        patch = ProjectUpdate(type=viejo)

    assert patch.type == nuevo
    # Se mira `donde=`, no la clave: el mensaje lleva el campo declarado en la
    # ficha (`type=innovation|transformation|operation`), que es lo que se busca
    # en los registros, y la clave solo agrupa el contador.
    assert any("donde=tipo del proyecto" in r.getMessage() for r in caplog.records)


@pytest.mark.parametrize("tipo", TIPOS)
def test_el_tipo_canonico_no_deja_rastro(
    caplog: pytest.LogCaptureFixture, tipo: str
) -> None:
    with caplog.at_level(logging.INFO, logger="pmoaas.compat"):
        ProjectUpdate(type=tipo)
    assert caplog.records == []


@pytest.mark.asyncio
async def test_un_tipo_inventado_se_rechaza(db_session) -> None:
    """El texto libre de antes de US-202 se **lee** (la columna sigue siendo
    texto), pero no se vuelve a escribir: es la mitad del arreglo que hace que
    un `GROUP BY type` signifique algo.

    La regla no desapareció con US-286, cambió de sitio: Pydantic ya no puede
    aplicarla —cada inquilino tiene su lista y valida antes de saber quién
    llama— así que la aplica `services/catalogos.py::validar` desde el
    endpoint. Se prueba donde vive.
    """
    from app.core.errors import AppError
    from app.models.tenant_catalog import CATALOGO_TIPO_PROYECTO
    from app.services import catalogos
    from tests.factories import create_tenant

    tenant = await create_tenant(db_session)
    await db_session.commit()

    # La forma sí pasa: es texto.
    assert ProjectUpdate(type="Mejora continua").type == "Mejora continua"
    # El catálogo del inquilino no.
    with pytest.raises(AppError):
        await catalogos.validar(
            db_session, tenant.id, CATALOGO_TIPO_PROYECTO, "Mejora continua"
        )


def test_una_fase_inventada_se_rechaza() -> None:
    with pytest.raises(ValueError):
        PhaseChange(new_phase="abandonado")


def test_el_proyecto_nace_en_preparacion() -> None:
    """«Solicitud» no es fase del proyecto: vive en `project_requests.status`."""
    creado = ProjectCreate(
        name="Proyecto nuevo",
        description="Sin fase explícita",
        type=BAU,
        priority=3,
        organization_id=uuid4(),
        pm_id=uuid4(),
    )
    assert creado.phase == PREPARACION


def test_las_etiquetas_devuelven_el_crudo_ante_lo_desconocido() -> None:
    """En un reporte, un valor fuera del catálogo es un dato que hay que **ver**
    para poder corregirlo. Y es el caso real: los tipos libres de antes de
    US-202 salen así."""
    assert etiqueta_fase(PREPARACION) == "Preparación"
    assert etiqueta_fase("Mejora") == "Mejora"
    assert etiqueta_fase(None) == "—"
    assert etiqueta_tipo(BAU) == "BAU (operación continua)"
    assert etiqueta_tipo("Business as usual") == "Business as usual"


# ---------------------------------------------------------------------------
# La migración de datos
# ---------------------------------------------------------------------------


def _cargar_migracion() -> ModuleType:
    spec = importlib.util.spec_from_file_location("migracion_0110", MIGRACION)
    assert spec and spec.loader, f"No pude cargar {MIGRACION}"
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _tabla(modelo: type, md: sa.MetaData) -> sa.Table:
    """La tabla real del modelo, sin claves ajenas.

    Los nombres se copian del modelo, no se transcriben: es la lección de la
    0098, que escribía en una tabla inexistente y pasaba porque la verificación
    se fabricaba su propio sujeto. El nombre de la tabla de lecciones es
    `lessons`, no `lessons_learned` — exactamente el error de aquella.
    """
    origen = modelo.__table__
    return sa.Table(origen.name, md, *[c._copy() for c in origen.columns])


def _proyecto(**campos: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": str(uuid4()),
        "tenant_id": str(uuid4()),
        "organization_id": str(uuid4()),
        "folio": "PRJ-000",
        "name": "Proyecto",
        "progress": 0,
        "health_status": "green",
        "health_source": "auto",
        "manually_edited_fields": {},
    }
    base.update(campos)
    return base


def test_tc_la_migracion_renombra_fases_y_tipos_y_revierte(tmp_path: Path) -> None:
    """TC-202.2/3 — las dos tablas con fase, los tres tipos, y la vuelta.

    `lessons.phase` es la que se olvida: la 0098 la dejó fuera en su primera
    versión. Si esta migración solo tocara `projects`, las lecciones quedarían
    con el vocabulario viejo y sus etiquetas saldrían crudas en el exportable.
    """
    modulo = _cargar_migracion()
    md = sa.MetaData()
    projects = _tabla(Project, md)
    lessons = _tabla(Lesson, md)

    # Sin listener de escrituras: el que comprueba que cada `UPDATE` va acotado
    # es el test hermano, con su propia lista. Aquí se recolectaba y no se
    # afirmaba nada, que es una instrumentación que solo cuesta leerla.
    motor = create_engine(f"sqlite:///{tmp_path / 'us202.db'}")

    tenant = str(uuid4())
    try:
        with motor.begin() as cx:
            md.create_all(cx)
            cx.execute(
                projects.insert(),
                [
                    _proyecto(folio="P-1", phase="planning", type="transformation"),
                    _proyecto(folio="P-2", phase="execution", type="innovation"),
                    _proyecto(folio="P-3", phase="hypercare", type="operation"),
                    _proyecto(folio="P-4", phase="closed", type="bau"),
                    _proyecto(folio="P-5", phase="cancelled", type=None),
                    # El tipo libre que la migración NO sabe traducir.
                    _proyecto(folio="P-6", phase="planning", type="Mejora continua"),
                ],
            )
            cx.execute(
                lessons.insert(),
                [
                    {
                        "id": str(uuid4()),
                        "tenant_id": tenant,
                        "project_id": str(uuid4()),
                        "folio": "LEC-1",
                        "title": "Lo aprendido",
                        "status": "published",
                        "phase": "planning",
                    },
                    {
                        "id": str(uuid4()),
                        "tenant_id": tenant,
                        "project_id": str(uuid4()),
                        "folio": "LEC-2",
                        "title": "Lo otro",
                        "status": "published",
                        "phase": "closed",
                    },
                ],
            )

        with motor.begin() as cx:
            with Operations.context(MigrationContext.configure(cx)):
                modulo.upgrade()

        with motor.connect() as cx:
            fases = dict(cx.execute(sa.text("SELECT folio, phase FROM projects")).all())
            assert fases == {
                "P-1": "preparacion",
                "P-2": "ejecucion",
                "P-3": "hypercare",
                "P-4": "cerrado",
                "P-5": "cancelado",
                "P-6": "preparacion",
            }, "hypercare no se toca; el resto pasa al vocabulario nuevo."

            tipos = dict(cx.execute(sa.text("SELECT folio, type FROM projects")).all())
            assert tipos["P-1"] == "transformacion"
            assert tipos["P-2"] == "innovacion"
            assert tipos["P-3"] == "operacion"
            assert tipos["P-4"] == "bau", "`bau` ya estaba bien; no se toca."
            assert tipos["P-5"] is None
            assert tipos["P-6"] == "Mejora continua", (
                "Un tipo libre que la migración no sabe traducir se deja como "
                "está. Adivinar que «Mejora continua» es `operacion` sería "
                "inventarse la clasificación del proyecto de alguien."
            )

            de_lecciones = sorted(
                r[0] for r in cx.execute(sa.text("SELECT phase FROM lessons")).all()
            )
            assert de_lecciones == ["cerrado", "preparacion"], (
                "`lessons.phase` comparte el vocabulario y es la tabla que se "
                "olvida — le pasó a la 0098."
            )

        with motor.begin() as cx:
            with Operations.context(MigrationContext.configure(cx)):
                modulo.downgrade()

        with motor.connect() as cx:
            vuelta = dict(cx.execute(sa.text("SELECT folio, phase FROM projects")).all())
            assert vuelta["P-1"] == "planning"
            assert vuelta["P-4"] == "closed"
            assert vuelta["P-3"] == "hypercare"
            de_vuelta = dict(cx.execute(sa.text("SELECT folio, type FROM projects")).all())
            assert de_vuelta["P-1"] == "transformation"
            assert de_vuelta["P-6"] == "Mejora continua"
            assert sorted(
                r[0] for r in cx.execute(sa.text("SELECT phase FROM lessons")).all()
            ) == ["closed", "planning"]
    finally:
        motor.dispose()


def test_la_migracion_no_reescribe_lo_que_no_le_incumbe(tmp_path: Path) -> None:
    """Un `UPDATE` por valor viejo, no un `CASE` sobre todas las filas.

    Reescribir filas que ya están bien les mueve el `updated_at` sin haber
    cambiado nada, y eso ensucia el rastro de medio producto. Contarlo es la
    única forma de verificar la promesa: con datos idénticos, ninguna aserción
    sobre el contenido distingue un `UPDATE` de más.
    """
    modulo = _cargar_migracion()
    md = sa.MetaData()
    projects = _tabla(Project, md)
    _tabla(Lesson, md)

    motor = create_engine(f"sqlite:///{tmp_path / 'us202-limpio.db'}")
    escrituras: list[str] = []

    @sa.event.listens_for(motor, "before_cursor_execute")
    def _anotar(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("UPDATE"):
            escrituras.append(statement)

    try:
        with motor.begin() as cx:
            md.create_all(cx)
            # Ya migrado: nada que renombrar.
            cx.execute(
                projects.insert(),
                [_proyecto(folio="Q-1", phase=HYPERCARE, type=BAU)],
            )
        escrituras.clear()
        with motor.begin() as cx:
            with Operations.context(MigrationContext.configure(cx)):
                modulo.upgrade()

        with motor.connect() as cx:
            fila = cx.execute(sa.text("SELECT phase, type FROM projects")).one()
            assert fila.phase == HYPERCARE
            assert fila.type == BAU
        # Los 11 `UPDATE` se emiten igual (4 fases × 2 tablas + 3 tipos), pero
        # ninguno toca una fila: lo que se comprueba es que van acotados por
        # valor. Un `CASE` sin `WHERE` habría reescrito la fila de todos modos.
        assert all(" WHERE " in s for s in escrituras), (
            "Algún `UPDATE` de la migración va sin guarda: reescribiría filas "
            "que no le incumben."
        )
    finally:
        motor.dispose()


def test_la_fase_de_las_participaciones_queda_fuera() -> None:
    """`project_participations.phase` es texto libre —«en qué fase consume
    capacidad este recurso»—, no el vocabulario controlado. Renombrar ahí sería
    editar lo que escribió un usuario, y la 0098 ya lo dejó escrito."""
    modulo = _cargar_migracion()
    assert "project_participations" not in modulo.TABLAS_CON_FASE
    assert set(modulo.TABLAS_CON_FASE) == {"projects", "lessons"}


def test_el_dominio_no_renombra_hypercare() -> None:
    """Se quedó como está a propósito: ADR-019 ya lo renombró desde `support` y
    no tiene traducción que no sea peor. Renombrarlo otra vez gastaría una
    segunda ventana de compatibilidad para empeorar el nombre."""
    assert HYPERCARE == "hypercare"
    assert HYPERCARE in FASES
    assert "hypercare" not in FASES_RENOMBRADAS.values() or (
        FASES_RENOMBRADAS.get("support") == HYPERCARE
    )
    # La ventana anterior sigue abierta: cerrarla es su propia decisión.
    assert FASES_RENOMBRADAS["support"] == HYPERCARE
    assert EJECUCION != "execution"
