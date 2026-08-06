"""DOC-01 — cada documento dice quién responde, si sigue vivo y cuándo se revisa.

La auditoría lo midió sin ambigüedad: **0 de 64 documentos** de `docs/` lo
declaraban. El único que lo traía era `MCS-CORE`, y porque llegó de fuera.

No es papeleo, y este repositorio tiene las dos cicatrices que lo prueban:

- `02-GLOSARIO.md` decía «borrador, nada adoptado» **en el cuerpo**, y `LEN-01`
  quedó ALTA por eso hasta que alguien lo leyó entero.
- `design-system/tokens.md` describe una paleta anterior a D-7 y ADR-023, y eso
  constaba **en `SPRINT.md`** — otro archivo. Quien abriera el documento no
  tenía forma de saberlo. Se corrigió en este mismo cambio, y es el caso que
  justifica el requisito completo.

El estado tiene que viajar **con** el documento.

Lo que esta suite defiende, más allá de que los campos estén:

- que el **alcance** no se recorte. Dejar `docs/archive/` fuera «porque está
  archivado» es justo al revés: un documento archivado sin decirlo es el que
  más engaña.
- que `revisado` **no pueda estar en el futuro**, que es la forma barata de
  aparentar frescura.
- que el gate **no falle por vencimiento**. Eso es DOC-07 y sigue abierto: un
  control que enrojece con el paso del tiempo, sin que nadie toque nada, se
  desactiva la primera semana.
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[3]

sys.path.insert(0, str(RAIZ / "scripts"))
from check_docs import (  # noqa: E402
    CAMPOS,
    ESTADOS,
    RAIZ_INCLUIDOS,
    documentos,
    encabezado,
    revisar,
    vencido,
)

HOY = dt.date(2026, 8, 6)
BUENO = "---\nresponsable: propietario\nestado: vigente\nrevisado: 2026-08-01\nrevisar_cada: 90d\n---\n\n# Título\n"


def test_acepta_el_encabezado_completo() -> None:
    assert revisar("docs/x.md", BUENO, HOY) == []


def test_rechaza_el_documento_sin_encabezado() -> None:
    (motivo,) = revisar("docs/x.md", "# Título\n\nCuerpo.\n", HOY)
    assert "no declara encabezado" in motivo


@pytest.mark.parametrize("campo", CAMPOS)
def test_rechaza_cada_campo_que_falte(campo: str) -> None:
    """Uno a uno, porque los cuatro los nombra el requisito por separado.

    Un encabezado con tres de cuatro es un encabezado que parece cumplir.
    """
    mutilado = "\n".join(x for x in BUENO.splitlines() if not x.startswith(f"{campo}:"))
    motivos = revisar("docs/x.md", mutilado + "\n", HOY)
    assert any(campo in m for m in motivos), motivos


def test_rechaza_una_revision_en_el_futuro() -> None:
    """La forma barata de aparentar frescura: poner una fecha que no ha llegado.

    Nadie la escribe con mala fe; sale de copiar el encabezado de otro
    documento recién revisado. Pero el campo se usa para decidir si fiarse.
    """
    futuro = BUENO.replace("revisado: 2026-08-01", "revisado: 2027-01-01")
    assert any("futuro" in m for m in revisar("docs/x.md", futuro, HOY))


def test_rechaza_un_estado_inventado() -> None:
    """Con el vocabulario abierto, «vigente», «activo» y «al día» conviven —
    que es lo que DAT-06 prohíbe, aplicado a los metadatos.
    """
    raro = BUENO.replace("estado: vigente", "estado: al día")
    assert any("no es uno de" in m for m in revisar("docs/x.md", raro, HOY))
    assert "vigente" in ESTADOS and "reemplazado" in ESTADOS


def test_el_vencimiento_se_informa_pero_no_falla() -> None:
    """DOC-07, no DOC-01.

    Si vencer pusiera el CI en rojo, el primer lunes que un documento cumpliera
    90 días bloquearía un PR que no lo tocó, y el gate duraría una semana.
    """
    viejo = BUENO.replace("revisado: 2026-08-01", "revisado: 2026-01-01")
    assert revisar("docs/x.md", viejo, HOY) == [], "vencer no es incumplir DOC-01"
    assert vencido(encabezado(viejo), HOY) is not None, "pero tiene que informarse"


def test_lo_archivado_no_vence() -> None:
    """Un documento archivado no se revisa: se dejó de usar a propósito.

    Contarlo como vencido llenaría el informe de ruido y taparía los que sí
    importan — 36 de los 127 están en `docs/archive/`.
    """
    archivado = BUENO.replace("estado: vigente", "estado: archivado").replace(
        "revisado: 2026-08-01", "revisado: 2024-01-01"
    )
    assert vencido(encabezado(archivado), HOY) is None


def test_el_alcance_incluye_lo_archivado_y_la_raiz() -> None:
    """Recortar el alcance es la forma silenciosa de cerrar el requisito.

    `docs/archive/` fuera «porque está archivado» es al revés: un documento
    archivado que no lo dice es el que más engaña. Y `CLAUDE.md` y `README.md`
    son documentos aunque no vivan en `docs/`.
    """
    rutas = {x.relative_to(RAIZ).as_posix() for x in documentos()}
    assert any(r.startswith("docs/archive/") for r in rutas)
    # Los nombres van escritos y no derivados de `RAIZ_INCLUIDOS`: la primera
    # versión comprobaba `set(RAIZ_INCLUIDOS) <= rutas`, y vaciar la constante
    # la hacía pasar —el conjunto vacío es subconjunto de todo—. La prueba se
    # vaciaba con lo que vigilaba. Lo cazó la mutación, no la lectura.
    assert {"CLAUDE.md", "README.md", "SECURITY.md", "RAILWAY_SETUP.md"} <= rutas, (
        "Documentos de la raíz fuera del alcance. `CLAUDE.md` y `README.md` son "
        "documentos aunque no vivan en `docs/`."
    )
    assert set(RAIZ_INCLUIDOS) <= rutas
    assert len(rutas) > 100, f"Solo {len(rutas)} documentos en el alcance: ¿se movió `docs/`?"


def test_todo_el_arbol_declara() -> None:
    """El estado real, no el del verificador. Es el que cierra el requisito."""
    hoy = dt.date.today()
    fallos = {
        archivo.relative_to(RAIZ).as_posix(): motivos
        for archivo in documentos()
        if (motivos := revisar(
            archivo.relative_to(RAIZ).as_posix(),
            archivo.read_text(encoding="utf-8"),
            hoy,
        ))
    }
    assert not fallos, f"Documentos sin declarar: {fallos}"


def test_el_documento_reemplazado_lo_dice_en_su_cuerpo() -> None:
    """El encabezado es para máquinas; el aviso, para quien lo abre.

    `tokens.md` es el caso: describía una paleta retirada y solo `SPRINT.md` lo
    sabía. Un `estado: reemplazado` que el lector no ve repite el problema en
    otro formato.
    """
    tokens = RAIZ / "docs" / "design-system" / "tokens.md"
    texto = tokens.read_text(encoding="utf-8")
    assert encabezado(texto)["estado"] == "reemplazado"
    cuerpo = texto.split("---\n", 2)[-1]
    assert "Reemplazado" in cuerpo, (
        "El documento se declara reemplazado en el encabezado pero no avisa en "
        "el cuerpo: quien lo abre y lee sigue sin enterarse."
    )
