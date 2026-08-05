"""DAT-06 — un concepto, un término. El semáforo se dice `yellow`, y nada más.

> «NO DEBEN emplearse sinónimos ni adjetivos acumulados para designar un mismo
> concepto.»

El glosario ya había tomado la decisión y la había escrito (D-1, 2026-08-04):
el valor es **`yellow`**, `amber` queda **vetado**, y la UI dice «Amarillo».
RAG —*Red, Amber, Green*— es el término de P3O y PRINCE2, y este producto se
aparta de él a conciencia: `yellow` es el contrato de la API, la migración 0091
convirtió los datos, y los snapshots históricos ya guardan `health_yellow`.

Y aun así quedaban cuatro restos, tres de ellos donde menos se miran:

- `reports/engine.py` **traducía `yellow` → `amber`** para hablarle a la
  plantilla. Ese es el mecanismo por el que un vocabulario retirado sobrevive
  para siempre: no se usa en el dominio, se reintroduce en el borde.
- `s-03.html` ponía `amber` de valor por defecto y, peor, **la etiqueta que ve
  el cliente decía «Ámbar»**. El sinónimo no estaba en el código: estaba en el
  PDF que se le manda al cliente.
- `base.html` llevaba una clase `.dot.amber`.
- `charter_generator.py` llevaba una clave `amber` alias de `yellow`.

Un alias que nadie usa no es tolerancia: es el sitio por donde el término
vuelve la próxima vez que alguien copie el diccionario. Por eso esta suite
mira el **árbol**, no una lista de sitios conocidos.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ_API = Path(__file__).resolve().parents[1]

#: `amber` como VALOR del semáforo. `amber_max` no entra: es una llave guardada
#: en `tenant.settings` de inquilinos reales, así que renombrarla es un cambio
#: de contrato sobre datos existentes y necesita ventana de compatibilidad —
#: como `wbs`. Está declarado en el plan de remediación como trabajo de Ola 3,
#: no como un olvido de esta.
VETADO = re.compile(r"\bamber\b(?!_max)", re.I)

#: Lo que ve el cliente. «Ámbar» es la traducción del término del que el
#: producto se aparta; la palabra en la interfaz es «Amarillo».
VETADO_VISIBLE = re.compile(r"Ámbar", re.I)

RUTAS = [
    RAIZ_API / "app",
]
EXTENSIONES = ("*.py", "*.html")


def _fuentes() -> list[Path]:
    return sorted(
        archivo
        for raiz in RUTAS
        for patron in EXTENSIONES
        for archivo in raiz.rglob(patron)
    )


def _sin_comentarios(texto: str, sufijo: str) -> str:
    """Quita comentarios y docstrings; explicar el veto no es incumplirlo.

    Sin esto, la única forma de documentar por qué `amber` se fue sería no
    documentarlo — que es exactamente el incentivo contrario al que interesa.
    """
    if sufijo == ".html":
        return re.sub(r"\{#.*?#\}|<!--.*?-->", "", texto, flags=re.S)
    sin_docstrings = re.sub(r'"""(?:.|\n)*?"""|\'\'\'(?:.|\n)*?\'\'\'', "", texto)
    return re.sub(r"#[^\n]*", "", sin_docstrings)


def test_el_termino_vetado_no_esta_en_el_codigo() -> None:
    """El caso general, y por eso mira el árbol y no una lista de sitios.

    Una prueba que enumerara `engine.py`, `s-03.html`, `base.html` y
    `charter_generator.py` quedaría verde el día que el término reaparezca en
    un quinto archivo — que es como volvió tres veces ya.
    """
    culpables = []
    for archivo in _fuentes():
        cuerpo = _sin_comentarios(archivo.read_text(encoding="utf-8"), archivo.suffix)
        for n, linea in enumerate(cuerpo.splitlines(), 1):
            if VETADO.search(linea):
                culpables.append(f"{archivo.relative_to(RAIZ_API)}:{n}: {linea.strip()[:80]}")
    assert not culpables, (
        "`amber` está vetado como valor del semáforo (glosario §6, D-1). El "
        "valor es `yellow`.\n" + "\n".join(culpables)
    )


def test_la_etiqueta_que_ve_el_cliente_dice_amarillo() -> None:
    """El resto más caro de los cuatro, y el que ninguna búsqueda de código
    encuentra: estaba en el PDF, no en una variable.
    """
    culpables = [
        str(archivo.relative_to(RAIZ_API))
        for archivo in _fuentes()
        if VETADO_VISIBLE.search(_sin_comentarios(archivo.read_text(encoding="utf-8"), archivo.suffix))
    ]
    assert not culpables, (
        "La interfaz dice «Amarillo», no «Ámbar» — «Ámbar» traduce el término "
        f"RAG del que el producto se aparta (D-1). En: {culpables}"
    )


def test_el_motor_de_informes_no_traduce_el_vocabulario() -> None:
    """Traducir en el borde es lo que mantiene vivo un término retirado.

    El dominio hablaba `yellow` y la plantilla `amber`, con una tabla en medio.
    Mientras esa tabla exista, retirar el término del dominio no lo retira del
    producto — solo lo mueve a la mitad que nadie audita.
    """
    from app.services.reports import engine

    fuente = Path(engine.__file__).read_text(encoding="utf-8")
    assert not re.search(r'"yellow"\s*:\s*"[^y]', fuente), (
        "Alguien volvió a mapear `yellow` a otro término en el motor de informes."
    )


@pytest.mark.parametrize(
    ("salud", "esperado"),
    [("green", "green"), ("yellow", "yellow"), ("red", "red"), ("lo que sea", "yellow")],
)
def test_el_semaforo_del_informe_sale_en_el_vocabulario_canonico(salud: str, esperado: str) -> None:
    """Comprueba el comportamiento, no el texto del archivo.

    Una prueba que fijara el literal de la fuente no puede fallar — este
    expediente ya se comió tres. Esta llama a la función y mira lo que sale,
    incluido el caso por defecto, que era el que ponía `amber` cuando la salud
    llegaba con un valor inesperado.
    """
    from app.services.reports.engine import _build_s03_rag

    class _Proyecto:
        health_status = salud
        health_reason = None
        health_source = "auto"

    class _Ctx:
        project = _Proyecto()

    assert _build_s03_rag(_Ctx(), None, None)["status_rag"] == esperado
