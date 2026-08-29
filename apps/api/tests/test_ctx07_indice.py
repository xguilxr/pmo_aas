"""CTX-07 — el conocimiento se busca por sección, y el índice no envejece.

Medido el 2026-08-28: 40 de los 91 documentos vivos no tenían ninguna ruta de
entrada desde el contexto permanente. Entre ellos
`docs/dominio/07-FICHAS-INDICADORES.md` —las fichas de indicador firmadas por
el owner, con la fórmula de cada métrica— y `docs/dominio/02-GLOSARIO.md`. Los
dos documentos que existen justamente para no re-derivar una definición desde
el código eran inalcanzables, así que cada sesión los re-derivaba.

`scripts/indexar.py` los hace alcanzables. Este trinquete defiende las tres
cosas que hacen que siga siendo cierto mañana:

- que `docs/INDICE.md` **coincida** con el contenido de `docs/` hoy — un índice
  desfasado responde con confianza sobre texto que ya no existe, que es peor
  que no tener índice;
- que el documento **avise** de que se genera, porque el aviso es lo que evita
  el retoque a mano que la siguiente regeneración borra sin decir nada;
- que la búsqueda **encuentre** las secciones que motivaron todo esto, con el
  rango de líneas y no el archivo entero.

Vive en la suite de `apps/api` por lo mismo que `test_doc03_er_generado.py`:
así corre dentro de `api-tests-smoke`, que ya es una verificación requerida,
sin costarle al owner una protección de rama más.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[3]
SCRIPT = RAIZ / "scripts" / "indexar.py"
INDICE = RAIZ / "docs" / "INDICE.md"


def _cargar_indexar():
    """Importa `scripts/indexar.py` sin que `scripts/` sea un paquete."""
    spec = importlib.util.spec_from_file_location("indexar", SCRIPT)
    assert spec and spec.loader, f"no se pudo cargar {SCRIPT}"
    modulo = importlib.util.module_from_spec(spec)
    sys.modules["indexar"] = modulo
    spec.loader.exec_module(modulo)
    return modulo


indexar = _cargar_indexar()


def test_indice_generado_esta_al_dia() -> None:
    """`docs/INDICE.md` es lo que el generador produce hoy, carácter a carácter."""
    esperado = indexar._md_texto(indexar.construir())
    actual = INDICE.read_text(encoding="utf-8")
    assert actual == esperado, (
        "docs/INDICE.md quedó desfasado. Corre `python scripts/indexar.py` "
        "y súbelo en el mismo commit que cambió la documentación."
    )


def test_indice_avisa_que_es_generado() -> None:
    """La mitad del requisito es que el lector sepa que no debe editarlo."""
    texto = INDICE.read_text(encoding="utf-8")
    assert "scripts/indexar.py" in texto
    assert "No se edita a mano" in texto


def test_todo_documento_vivo_aparece_en_el_indice() -> None:
    """Ningún documento vivo se queda fuera del mapa — ese era el fallo original."""
    indice = indexar.construir()
    texto = INDICE.read_text(encoding="utf-8")
    faltantes = [
        d["ruta"]
        for d in indice["documentos"]
        if d["vivo"] and d["ruta"].removeprefix("docs/") not in texto
    ]
    assert not faltantes, f"documentos vivos fuera del índice: {faltantes}"


@pytest.mark.parametrize(
    ("consulta", "ruta_esperada"),
    [
        # Los dos documentos que eran inalcanzables, buscados por el término
        # que alguien usaría de verdad.
        ("avance de la cartera", "docs/dominio/07-FICHAS-INDICADORES.md"),
        ("sobreasignacion capacidad", "docs/dominio/07-FICHAS-INDICADORES.md"),
        ("estado de salud semaforo", "docs/dominio/02-GLOSARIO.md"),
        # Y uno de los que sí tenía ruta, para que la búsqueda no privilegie
        # solo a los huérfanos.
        ("rls aislamiento multi tenant", "docs/architecture/"),
    ],
)
def test_buscar_encuentra_la_seccion(consulta: str, ruta_esperada: str) -> None:
    indice = indexar.construir()
    resultados = indexar.buscar(indice, consulta, limite=5)
    assert resultados, f"«{consulta}» no devolvió nada"
    rutas = [r["ruta"] for r in resultados]
    assert any(r.startswith(ruta_esperada) for r in rutas), (
        f"«{consulta}» no encontró {ruta_esperada}; devolvió {rutas}"
    )


def test_buscar_devuelve_un_rango_util_no_el_archivo_entero() -> None:
    """El valor está en el rango: una sección, no una invitación a leer 442 líneas."""
    indice = indexar.construir()
    resultados = indexar.buscar(indice, "avance de la cartera", limite=3)
    primero = resultados[0]
    assert primero["desde"] >= 1
    assert primero["hasta"] >= primero["desde"]
    # La ficha de `progress_avg` son ~11 líneas. Si el primer resultado pasa de
    # 120, la búsqueda dejó de acotar y volvió a devolver documentos.
    assert primero["lineas"] <= 120, (
        f"el mejor resultado abarca {primero['lineas']} líneas: "
        "la búsqueda está devolviendo documentos, no secciones"
    )


def test_un_archivado_no_le_gana_a_un_vivo() -> None:
    """Los archivados se indexan para responder «por qué», nunca «cómo funciona»."""
    indice = indexar.construir()
    # `docs/archive/initial-epics-es/` tiene epics viejas con títulos muy
    # parecidos a los vivos; es el caso que rompería la búsqueda.
    resultados = indexar.buscar(indice, "dashboard kpis", limite=3)
    assert resultados
    assert resultados[0]["vivo"], (
        f"un documento {resultados[0]['estado']} quedó primero: "
        f"{resultados[0]['ruta']}"
    )


def test_los_encabezados_dentro_de_bloques_de_codigo_no_son_secciones() -> None:
    """Un `# comentario` de Python en un bloque no abre una sección falsa."""
    secciones = indexar._secciones(
        "prueba.md",
        [
            "# Documento",
            "```python",
            "# esto es un comentario, no un encabezado",
            "```",
            "## Sección real",
        ],
    )
    titulos = [s.titulo for s in secciones]
    assert titulos == ["Documento", "Sección real"]
