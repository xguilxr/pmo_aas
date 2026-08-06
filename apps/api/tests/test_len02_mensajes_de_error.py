"""MCS LEN-02 — los mensajes de error siguen diciendo las tres cosas.

> «Todo mensaje de error DEBE indicar qué ocurrió, por qué y qué acción tomar.»

La auditoría R1 lo dejó en PARCIAL: el envoltorio estaba bien y los cuatro
textos por defecto decían solo qué pasó. «Credenciales inválidas» es un qué sin
un porqué y sin una salida.

Lo que esta suite defiende **no** es la redacción de hoy —esa es cosa del
producto— sino que las tres partes sigan estando. Por eso el catálogo guarda
`que`, `porque` y `accion` por separado: una frase corrida cumple el requisito
el día que se escribe y deja de cumplirlo en la primera edición sin que nada
avise, y aquí no hay forma de rellenar dos de tres.

El apartado final comprueba lo otro que la auditoría señaló: que los mensajes de
error no filtren nombres de campo internos. «cambia `pm_id` primero» no
significa nada para quien lo lee.
"""
from __future__ import annotations

import re

import pytest

from app.core.errors import (
    DEFECTOS,
    forbidden,
    not_found,
    unauthorized,
)

#: Los `code` que el catálogo tiene que cubrir. Escrito a mano y no derivado de
#: `DEFECTOS`, para que borrar una entrada del catálogo haga fallar la suite en
#: vez de reducir en silencio lo que se comprueba.
CODES_CON_DEFECTO = {
    "UNAUTHENTICATED",
    "FORBIDDEN",
    "NOT_FOUND",
    "INTERNAL_SERVER_ERROR",
    # Añadido con AM-09: el 429 nació ya con las tres partes.
    "RATE_LIMITED",
}


def test_el_catalogo_cubre_todos_los_defectos():
    assert set(DEFECTOS) == CODES_CON_DEFECTO


@pytest.mark.parametrize("code", sorted(CODES_CON_DEFECTO))
@pytest.mark.parametrize("parte", ["que", "porque", "accion"])
def test_cada_defecto_trae_sus_tres_partes(code, parte):
    valor = getattr(DEFECTOS[code], parte)

    assert valor and valor.strip(), f"{code}.{parte} está vacío (MCS LEN-02)"
    assert valor.strip().endswith((".", "»", "?", "!")), (
        f"{code}.{parte} no termina en punto: las tres partes se unen con un "
        f"espacio y sin puntuación quedan pegadas."
    )


@pytest.mark.parametrize("code", sorted(CODES_CON_DEFECTO))
def test_la_accion_le_dice_al_usuario_que_hacer(code):
    """Un «qué hacer» sin verbo en imperativo no es una acción, es un lamento."""
    accion = DEFECTOS[code].accion.lower()
    imperativos = (
        "vuelve",
        "verifica",
        "pídeselo",
        "usa",
        "avísanos",
        "revisa",
        "intenta",
        "solicita",
        "contacta",
    )
    assert any(v in accion for v in imperativos), (
        f"{code}.accion no propone nada que el usuario pueda hacer: "
        f"«{DEFECTOS[code].accion}»"
    )


def test_los_constructores_usan_el_catalogo():
    """Sin esto, el catálogo podría estar impecable y nadie usarlo."""
    for error, code in ((unauthorized(), "UNAUTHENTICATED"), (forbidden(), "FORBIDDEN")):
        detail = error.detail["detail"]
        for parte in ("que", "porque", "accion"):
            assert getattr(DEFECTOS[code], parte) in detail, (
                f"El texto por defecto de {code} no contiene su parte «{parte}»."
            )


def test_not_found_nombra_la_entidad_y_conserva_las_tres_partes():
    detail = not_found("Minuta").detail["detail"]

    assert "Minuta" in detail
    assert "{entidad}" not in detail, "El hueco de la plantilla quedó sin rellenar"
    for parte in ("porque", "accion"):
        assert getattr(DEFECTOS["NOT_FOUND"], parte) in detail


def test_el_401_no_revela_si_la_cuenta_existe():
    """Distinguir «no existe» de «contraseña incorrecta» enumera cuentas.

    Vive aquí y no en la suite de autenticación porque el texto es lo que
    filtra: el código de estado es el mismo en los dos casos.
    """
    detail = unauthorized().detail["detail"].lower()

    for filtracion in ("no existe", "usuario no encontrado", "no está registrado"):
        assert filtracion not in detail, (
            f"El texto por defecto de 401 dice «{filtracion}», que confirma qué "
            f"cuentas existen."
        )


@pytest.mark.parametrize("code", sorted(CODES_CON_DEFECTO))
def test_ningun_defecto_filtra_nombres_de_campo_internos(code):
    """`pm_id`, `tenant_id` y compañía no significan nada para quien lee.

    Es el segundo defecto que la auditoría nombró, con «No puedes remover al PM
    vigente; cambia `pm_id` primero» de ejemplo. Aquí se ataja al menos en el
    catálogo, que es lo que se aplica cuando el sitio no dice nada.
    """
    texto = DEFECTOS[code].texto(entidad="Minuta")
    internos = re.findall(r"\b[a-z][a-z0-9]*_(?:id|ids|at|by)\b", texto)

    assert not internos, (
        f"El texto por defecto de {code} nombra campos internos: {internos}"
    )


# ---------------------------------------------------------------------------
# 2026-08-06 — el mecanismo que hace que los 177 restantes se arreglen solos
# ---------------------------------------------------------------------------

def test_las_tres_partes_no_se_pueden_rellenar_a_medias() -> None:
    """`mensaje()` son tres argumentos con nombre y ninguno tiene defecto.

    Ahí está toda la garantía. Un `f"No puedes borrar un super admin"` cumple
    el requisito a medias y nada avisa; esto ni siquiera se puede llamar sin
    el porqué.
    """
    from app.core.errors import mensaje

    with pytest.raises(TypeError):
        mensaje(que="Pasó algo.")  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        mensaje(que="Pasó algo.", porque="Por esto.")  # type: ignore[call-arg]

    texto = mensaje(que="Pasó algo.", porque="Por esto.", accion="Hacé aquello.")
    assert texto == "Pasó algo. Por esto. Hacé aquello."


def test_las_tres_partes_son_solo_por_nombre() -> None:
    """Posicional invitaría a `mensaje(a, b)` y a discutir cuál falta.

    Con `*` delante, el error de llamada nombra el argumento que falta, que es
    lo que hace que la corrección sea obvia sin abrir esta prueba.
    """
    from app.core.errors import mensaje

    with pytest.raises(TypeError):
        mensaje("qué", "por qué", "acción")  # type: ignore[misc]


def test_el_trinquete_ve_los_mensajes_con_texto_suelto() -> None:
    """El verificador, contra entradas sintéticas.

    Se prueba la FORMA y no la prosa: se intentó primero con una heurística
    —buscar un verbo en imperativo— y acierta a medias en los dos sentidos. Un
    gate que discute la redacción con quien escribe se desactiva.
    """
    import ast
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
    from check_mensajes import _texto_literal

    def _llamada(codigo: str):
        return next(
            n for n in ast.walk(ast.parse(codigo)) if isinstance(n, ast.Call)
        )

    assert _texto_literal(_llamada('conflict("ya existe")')) == "ya existe"
    assert _texto_literal(_llamada('business_rule(f"falta {x}")')) == "falta {}"
    # Lo construido no se juzga: es justo lo que se quiere fomentar.
    assert _texto_literal(_llamada("conflict(mensaje(que=a, porque=b, accion=c))")) is None
    assert _texto_literal(_llamada("conflict(texto_por_defecto('X'))")) is None


def test_la_linea_base_solo_puede_encoger() -> None:
    """El pasivo declarado tiene que corresponderse con el árbol de hoy.

    Si crece, alguien añadió un mensaje con texto suelto y regeneró la línea
    base en vez de escribir las tres partes — que es la forma de aflojar un
    trinquete sin que se note.
    """
    import sys
    from pathlib import Path

    raiz = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(raiz / "scripts"))
    from check_mensajes import LINEA_BASE, _clave, sitios

    declarados = {
        x
        for x in LINEA_BASE.read_text(encoding="utf-8").splitlines()
        if x.strip() and not x.startswith("#")
    }
    observados = {_clave(s) for s in sitios()}
    assert observados <= declarados, (
        f"Mensajes con texto suelto fuera de la línea base: "
        f"{sorted(observados - declarados)}"
    )
