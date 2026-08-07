"""IA-02 — una acción del modelo se distingue de una humana en el registro.

«Toda acción ejecutada por un componente de IA DEBE registrarse en el registro
de auditoría, distinguible de una acción humana».

**La primera mitad ya se cumplía.** La IA escribía en `audit_log`. Lo que
faltaba era la segunda, y el motivo es sutil: los tres campos que parecían
servir no servían.

- `module="ai"` significa «el módulo de IA», no «lo hizo la IA»: `report.send`
  es una persona pulsando enviar y también lo lleva.
- El prefijo `ai.` era inconsistente: `ai.minute.generate` lo tiene y
  `report.draft` —que redacta el modelo— no.
- `user_id`, en una acción de IA, guarda **quién la pidió**. Atribuirle el texto
  a esa persona es el error exacto que el requisito evita.

Por eso hay columna propia y no una convención de nombres.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

RAIZ_API = Path(__file__).resolve().parents[1]

#: Módulos donde el que ejecuta es el modelo, no una persona.
#:
#: Es una regla de UBICACIÓN, no una lista de llamadas: cualquier
#: `write_audit` nuevo dentro de estos archivos queda cubierto sin que nadie
#: se acuerde de añadirlo aquí. Una lista de sitios demostraría «los que
#: enumeré», no «todos».
EJECUTA_LA_IA = (
    "app/workers/tasks/ai.py",
)


def _llamadas_write_audit(ruta: Path) -> list[ast.Call]:
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    return [
        n
        for n in ast.walk(arbol)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name)
        and n.func.id == "write_audit"
    ]


def test_el_modelo_puede_declararse_como_actor() -> None:
    """Lo mínimo: que el dato exista y tenga los dos valores, como constantes.

    Constantes y no cadenas sueltas: con el literal escrito a mano en cada
    sitio, un `"IA"` o un `"ai"` se cuela sin que nada chille y parte el filtro
    de quien pregunte después.
    """
    from app.models.audit import AuditLog
    from app.services.audit import ACTOR_HUMANO, ACTOR_IA

    assert ACTOR_IA != ACTOR_HUMANO
    assert "actor_type" in AuditLog.__table__.c


def test_lo_que_ejecuta_la_ia_se_registra_como_ia() -> None:
    """El trinquete. Sin él, una ruta de IA nueva se registraría como humana —
    en silencio y con el `user_id` de quien la pidió.

    Es lo contrario de lo que el requisito busca: no solo se pierde la
    distinción, se atribuye a una persona algo que escribió un modelo.
    """
    sin_marcar = []
    for relativa in EJECUTA_LA_IA:
        ruta = RAIZ_API / relativa
        for llamada in _llamadas_write_audit(ruta):
            claves = {k.arg for k in llamada.keywords}
            if "actor_type" not in claves:
                accion = next(
                    (
                        k.value.value
                        for k in llamada.keywords
                        if k.arg == "action" and isinstance(k.value, ast.Constant)
                    ),
                    "?",
                )
                sin_marcar.append(f"{relativa}:{llamada.lineno} action={accion}")
    assert not sin_marcar, (
        f"Escrituras de auditoría en código que ejecuta el modelo, sin declarar "
        f"`actor_type`: {sin_marcar}. Quedarían como acción humana atribuida a "
        f"quien la pidió."
    )


def test_toda_accion_con_prefijo_ai_se_marca() -> None:
    """La segunda regla, y cubre lo que la de ubicación no ve.

    Una acción llamada `ai.algo` escrita desde un endpoint —fuera de los
    módulos del worker— seguiría siendo del modelo. Se barre el árbol entero
    buscando por nombre.

    Las dos reglas juntas no son redundantes: la de ubicación caza
    `report.draft`, que el modelo escribe **sin** llevar el prefijo; y esta caza
    un `ai.*` que aparezca en un módulo nuevo que nadie añadió a la lista.
    """
    sin_marcar = []
    for ruta in sorted((RAIZ_API / "app").rglob("*.py")):
        for llamada in _llamadas_write_audit(ruta):
            accion = next(
                (
                    k.value.value
                    for k in llamada.keywords
                    if k.arg == "action" and isinstance(k.value, ast.Constant)
                ),
                None,
            )
            if not (isinstance(accion, str) and accion.startswith("ai.")):
                continue
            if {k.arg for k in llamada.keywords} & {"actor_type"}:
                continue
            sin_marcar.append(
                f"{ruta.relative_to(RAIZ_API).as_posix()}:{llamada.lineno} action={accion}"
            )
    assert not sin_marcar, (
        f"Acciones `ai.*` sin `actor_type`: {sin_marcar}. Si de verdad la "
        f"ejecuta una persona —cancelar un trabajo, por ejemplo— pasale "
        f"`actor_type=ACTOR_HUMANO` explícito para que se vea que se decidió."
    )


@pytest.mark.asyncio
async def test_la_fila_guardada_distingue_de_verdad(db_session) -> None:
    """De extremo a extremo, que es lo que ninguna comprobación estática da.

    Sin este caso, el gate podría estar verde con la columna sin llegar nunca a
    la base — que es la forma de fallo de la 0098: la verificación fabricándose
    su propio sujeto.
    """
    from sqlalchemy import select

    from app.models.audit import AuditLog
    from app.services.audit import ACTOR_HUMANO, ACTOR_IA, write_audit

    await write_audit(db_session, action="ai.minute.generate", actor_type=ACTOR_IA)
    await write_audit(db_session, action="minute.create")
    await db_session.commit()

    filas = (await db_session.execute(select(AuditLog))).scalars().all()
    por_accion = {f.action: f.actor_type for f in filas}
    assert por_accion["ai.minute.generate"] == ACTOR_IA
    assert por_accion["minute.create"] == ACTOR_HUMANO, (
        "El valor por defecto dejó de ser `humano`. Con 144 sitios de escritura "
        "que no lo pasan, cambiarlo reetiquetaría el producto entero."
    )


@pytest.mark.asyncio
async def test_se_puede_preguntar_que_hizo_el_modelo(db_session) -> None:
    """La razón de ser del requisito, escrita como la consulta que habilita.

    Si esto no se pudiera responder, la columna sería decorativa.
    """
    from sqlalchemy import func, select

    from app.models.audit import AuditLog
    from app.services.audit import ACTOR_IA, write_audit

    await write_audit(db_session, action="report.draft", actor_type=ACTOR_IA)
    await write_audit(db_session, action="report.send")
    await db_session.commit()

    cuantas = (
        await db_session.execute(
            select(func.count()).select_from(AuditLog).where(AuditLog.actor_type == ACTOR_IA)
        )
    ).scalar_one()
    assert cuantas == 1


def test_la_migracion_no_reescribe_el_registro() -> None:
    """`audit_log` es de solo anexado: la 0097 instala disparadores que rechazan
    `UPDATE` y `DELETE`.

    Una migración que intentara rellenar la columna fila a fila chocaría con
    ellos. Por eso va con `server_default`, que lo resuelve en la definición de
    la columna sin tocar una sola fila.
    """
    fuente = (
        RAIZ_API / "alembic" / "versions" / "20260806_0102_audit_actor_type.py"
    ).read_text(encoding="utf-8")
    assert "server_default" in fuente
    cuerpo = fuente.split('"""', 2)[2]
    for prohibido in ("op.execute", "UPDATE", "update("):
        assert prohibido not in cuerpo, (
            f"La 0102 escribe en las filas (`{prohibido}`). `audit_log` no lo "
            f"permite: los disparadores de la 0097 lo rechazan."
        )
