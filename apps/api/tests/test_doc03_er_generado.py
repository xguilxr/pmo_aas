"""DOC-03 — el diagrama ER se genera del modelo y no se queda atrás.

> «Lo que pueda generarse a partir del código DEBE generarse. El contenido
> generado NO DEBE editarse manualmente.»

`database.md` llevaba un `erDiagram` dibujado a mano y una sección titulada «la
tabla de tablas (**las 49 reales**)». Eran **56**. Siete de más, y nadie lo
notó — que es precisamente lo que le pasa a un diagrama a mano: no falla,
envejece, y sigue pareciendo correcto.

La suite vive en `apps/api` y no en un job propio del CI a propósito: aquí
están las dependencias del modelo, y así el gate corre dentro de
`api-tests-smoke`, que ya es una verificación requerida. Una más costaría una
acción del owner sin añadir cobertura.

Lo que se defiende:

- que el generado **coincida** con `Base.metadata` hoy;
- que el documento **avise** de que no se edita, porque el aviso es la mitad
  del requisito («el contenido generado NO DEBE editarse manualmente»);
- que `database.md` **no vuelva** a dibujar el diagrama ni a escribir el conteo,
  que son las dos formas en que este trabajo se deshace solo.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]

sys.path.insert(0, str(RAIZ / "scripts"))
from generar_er import DESTINO, diagrama, render  # noqa: E402

DATABASE_MD = RAIZ / "docs" / "architecture" / "database.md"


def _metadata():
    import app.models  # noqa: F401  — registra los modelos en el metadata
    from app.db.base import Base

    return Base.metadata


def test_el_generado_coincide_con_el_modelo() -> None:
    """El invariante entero del requisito, en una comparación.

    Se ignora `revisado:` al comparar: esa línea la mueve el generador y no
    tiene nada que ver con si el diagrama está al día. Confundir «regenerado
    hoy» con «coincide» produce un gate que se pone rojo sin motivo, y uno que
    se pone rojo sin motivo se desactiva.
    """
    actual = DESTINO.read_text(encoding="utf-8")
    fecha = re.search(r"^revisado:\s*(\S+)", actual, re.M).group(1)
    esperado = render(_metadata(), fecha)

    assert actual == esperado, (
        "El modelo cambió y `docs/architecture/er-generado.md` no. Corré "
        "`python scripts/generar_er.py` y commiteá el resultado — no lo "
        "edites a mano."
    )


def test_el_documento_avisa_de_que_no_se_edita() -> None:
    """La segunda mitad del requisito, y la que se olvida.

    Un archivo generado que no lo dice invita a arreglarlo a mano, y el arreglo
    sobrevive hasta la siguiente regeneración, que lo borra sin avisar.
    """
    texto = DESTINO.read_text(encoding="utf-8")
    assert "NO EDITAR A MANO" in texto
    assert "scripts/generar_er.py" in texto


def test_el_diagrama_cubre_todas_las_tablas() -> None:
    """Una tabla sin clave foránea no aparece en ningún enlace.

    Si el generador solo emitiera enlaces, esas tablas desaparecerían del
    diagrama y el documento diría menos que el modelo — que es el defecto que
    venía a arreglar. Hoy son tres: `audit_log`, `platform_ai_settings` y
    `report_sections`.
    """
    metadata = _metadata()
    cuerpo, n_tablas, _ = diagrama(metadata)
    assert n_tablas == len(metadata.tables)
    faltan = [t for t in metadata.tables if t.upper() not in cuerpo]
    assert not faltan, f"Tablas que no aparecen en el diagrama: {faltan}"


def test_la_cardinalidad_sale_del_esquema_y_no_de_una_opinion() -> None:
    """`|o` opcional / `||` obligatoria viene de `nullable`; `o|` de la unicidad.

    Es lo que hace que el diagrama valga más que el dibujado: no interpreta.
    """
    cuerpo, _, _ = diagrama(_metadata())
    # `actors.tenant_id` es obligatoria; `actors.area_id` admite nulo.
    assert "TENANTS ||--o{ ACTORS : tenant_id" in cuerpo
    assert "AREAS |o--o{ ACTORS : area_id" in cuerpo


def test_database_md_no_vuelve_a_dibujar_el_diagrama() -> None:
    """La forma en que este trabajo se deshace solo.

    Nadie borra el generador: alguien pega un `erDiagram` «solo para ilustrar»
    en el documento de al lado, y a partir de ahí hay dos, uno de los cuales
    envejece.
    """
    texto = DATABASE_MD.read_text(encoding="utf-8")
    assert "erDiagram" not in texto, (
        "`database.md` volvió a llevar un diagrama propio. El diagrama se "
        "genera; este documento explica y enlaza."
    )


def test_database_md_no_vuelve_a_escribir_el_conteo() -> None:
    """«las 49 reales» con 56 tablas en el modelo. Ese era el síntoma.

    Se miran los **encabezados** y no el cuerpo: el cuerpo cuenta la historia
    —«decía las 49 reales cuando eran 56»— y una búsqueda literal tomaría esa
    explicación por la infracción que documenta. Es la tercera vez en esta
    sesión que hace falta distinguir «hablar de» de «hacer».
    """
    encabezados = [
        x for x in DATABASE_MD.read_text(encoding="utf-8").splitlines() if x.startswith("#")
    ]
    # Un conteo en un encabezado va entre paréntesis —«(las 49 reales)»—, que
    # es lo que lo distingue de «PostgreSQL 16», donde el número es parte del
    # nombre y no una medición que pueda quedar obsoleta.
    culpables = [x for x in encabezados if re.search(r"\([^)]*\b\d+\b[^)]*\)", x)]
    assert not culpables, (
        f"Un encabezado de `database.md` lleva un conteo escrito a mano: "
        f"{culpables}. Se deriva en `er-generado.md`, que es lo que impide que "
        f"vuelva a mentir."
    )
