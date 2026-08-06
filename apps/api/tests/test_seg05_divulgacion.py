"""SEG-05 — la política de divulgación responsable existe y sigue siendo útil.

El requisito («DEBE publicarse una política de divulgación responsable») se
cierra con un archivo, y ese es justo el riesgo: un archivo se escribe una vez,
se vacía a la mitad en el siguiente retoque y nadie se entera, porque nada lo
mira. Un control que no se ejecuta es PARCIAL, nunca CONFORME (MCS-CORE §6.1).

Lo que esta suite defiende NO es el texto —fijar literales de la fuente produce
pruebas que no pueden fallar, y este expediente ya se comió dos— sino las
**cuatro piezas sin las cuales la política deja de serlo**:

- un canal **privado** al que reportar,
- **plazos** con número,
- el **alcance**, que es lo que evita el reporte inútil,
- el **puerto seguro**, que es lo que hace que alguien se anime a reportar.

Y una quinta que se rompe sola con el tiempo: los **enlaces internos**. Una
política que apunta a un documento movido manda al investigador a un 404 en el
momento en que más prisa tiene.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[3]
POLITICA = RAIZ / "SECURITY.md"


@pytest.fixture(scope="module")
def texto() -> str:
    assert POLITICA.is_file(), (
        "SEG-05 exige una política de divulgación publicada. `SECURITY.md` "
        "va en la raíz: es donde GitHub la busca para mostrarla en la pestaña "
        "Security y en el aviso de 'Report a vulnerability'."
    )
    return POLITICA.read_text(encoding="utf-8")


def test_declara_un_canal_privado_de_reporte(texto: str) -> None:
    """Sin canal privado, reportar equivale a publicar.

    El repositorio es público. Si la única vía es un issue, el investigador
    que sigue la política está divulgando el fallo, no reportándolo.
    """
    assert "security/advisories/new" in texto, (
        "La política debe enlazar el formulario privado de GitHub Security "
        "Advisories, no solo mencionarlo."
    )
    assert re.search(r"NO abras un issue p[úu]blico", texto), (
        "La prohibición de reportar en público tiene que estar escrita: es la "
        "parte que el investigador apurado se salta."
    )


def test_los_plazos_llevan_numero(texto: str) -> None:
    """«Responderemos a la brevedad» no es un plazo.

    Se exige que los cuatro hitos —acuse, triaje, corrección y publicación—
    tengan una cifra, que es lo único contra lo que se puede incumplir.
    """
    seccion = _seccion(texto, "## 4. Plazos")
    dias = re.findall(r"\|\s*(\d+)\s*d[íi]as?\s*\|", seccion)
    assert len(dias) >= 4, (
        "La tabla de plazos perdió hitos: se esperan al menos cuatro con "
        f"cifra (acuse, triaje, corrección crítica, corrección media). Hay {len(dias)}."
    )
    assert "Acuse de recibo" in seccion and "Triaje" in seccion
    assert re.search(r"Publicaci[óo]n coordinada", seccion), (
        "Sin fecha de publicación coordinada el investigador no sabe cuándo "
        "puede hablar, que es la mitad del trato."
    )


def test_delimita_el_alcance_en_las_dos_direcciones(texto: str) -> None:
    """Un alcance que solo dice qué entra deja fuera la parte útil.

    Lo que ahorra trabajo a ambos lados es la lista de lo que NO se acepta:
    salida de escáner sin explotación, denegación por volumen, terceros.
    """
    seccion = _seccion(texto, "## 3. Qué está dentro del alcance")
    assert "Fuera de alcance" in seccion, (
        "Falta la lista de lo que no se acepta. Sin ella, el canal privado se "
        "llena de salida de escáner y el triaje de 5 días deja de cumplirse."
    )
    dentro, fuera = seccion.split("Fuera de alcance", 1)
    assert dentro.count("\n- ") >= 3 and fuera.count("\n- ") >= 3


def test_ofrece_puerto_seguro_con_sus_condiciones(texto: str) -> None:
    """El puerto seguro sin condiciones es una invitación a tocar producción.

    Y las condiciones sin puerto seguro son una amenaza velada. Van juntas.
    """
    seccion = _seccion(texto, "## 5. Puerto seguro")
    assert re.search(r"no\s+empren\w+\s+acciones legales", seccion, re.I), (
        "Falta el compromiso explícito de no emprender acciones legales: es "
        "lo que distingue una política de divulgación de un aviso legal."
    )
    assert re.search(r"^\s*\d+\.\s", seccion, re.M), (
        "El puerto seguro tiene que enumerar sus condiciones. Sin ellas "
        "autoriza implícitamente probar contra producción con datos reales."
    )


def test_dice_si_hay_recompensa(texto: str) -> None:
    """Callarlo hace que alguien invierta días esperando un pago que no llega."""
    assert re.search(r"No hay recompensa", _seccion(texto, "## 6. Reconocimiento"))


def test_los_enlaces_internos_apuntan_a_algo_que_existe(texto: str) -> None:
    """El enlace roto se produce solo, al mover un documento.

    Este es el único invariante de la suite que se rompe sin que nadie toque
    `SECURITY.md`, y por eso es el que más falta hacía.
    """
    rotos = [
        destino
        for destino in re.findall(r"\]\((?!https?:|#)([^)\s]+)\)", texto)
        if not (RAIZ / destino).exists()
    ]
    assert not rotos, f"Enlaces a rutas inexistentes en SECURITY.md: {rotos}"


def test_declara_responsable_estado_y_revision(texto: str) -> None:
    """DOC-01 aplica también a este documento, y una política caduca engaña.

    Una política de seguridad sin fecha de revisión es peor que no tenerla:
    promete plazos que quizá ya nadie sostiene.
    """
    encabezado = _seccion(texto, "---")[: texto.index("# Política")]
    for campo in ("responsable:", "estado:", "revisado:", "revisar_cada:"):
        assert campo in encabezado, f"El encabezado no declara `{campo}` (DOC-01)."


def _seccion(texto: str, titulo: str) -> str:
    """Devuelve desde `titulo` hasta el siguiente encabezado del mismo nivel."""
    inicio = texto.index(titulo)
    nivel = re.match(r"#+", titulo)
    if nivel is None:  # el front-matter, delimitado por `---`
        return texto[inicio:]
    siguiente = re.search(rf"^{'#' * len(nivel.group())} ", texto[inicio + len(titulo) :], re.M)
    fin = inicio + len(titulo) + siguiente.start() if siguiente else len(texto)
    return texto[inicio:fin]
