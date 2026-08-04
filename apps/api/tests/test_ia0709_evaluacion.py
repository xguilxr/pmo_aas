"""B3 · MCS IA-07, IA-08 e IA-09 — el conjunto de evaluación de IA.

Dos cosas distintas viven aquí y conviene no confundirlas:

1. **El conjunto se ejecuta** (§1). Es lo que exige IA-08. El gate obligatorio
   es el job `evaluacion-ia` del CI; esto lo mete además en la suite normal,
   para que quien rompa un invariante lo vea en el mismo `pytest` que ya corre
   y no diez minutos después.
2. **El catálogo está sano** (§2). Que el conjunto pase no dice nada si el
   catálogo se vació, si dos casos comparten identificador o si alguien bajó el
   umbral sin escribir por qué. Un conjunto de evaluación es un control, y un
   control sin trinquete se degrada solo.

El detalle de cada caso NO se prueba aquí: se declara en `evaluacion/casos.yaml`
y lo comprueba `evaluacion/runner.py`. Duplicarlo sería tener el mismo hecho en
dos sitios (MCA CTX-06) y garantizar que uno de los dos envejece.
"""
from __future__ import annotations

import re
from collections import Counter
from datetime import date
from pathlib import Path

import pytest

from evaluacion.runner import (
    CATALOGO,
    INVARIANTES,
    SUPERFICIES,
    bloque_de,
    cargar,
    ejecutar_todo,
    evaluar_umbral,
)

CATALOGO_CARGADO = cargar()
CASOS = CATALOGO_CARGADO["casos"]


# ---------------------------------------------------------------------------
# §1 — El conjunto se ejecuta y supera su umbral
# ---------------------------------------------------------------------------


def test_ia08_el_conjunto_supera_el_umbral_declarado():
    """IA-08: el umbral condiciona el despliegue, así que fallar aquí es
    exactamente lo que debe ocurrir cuando el sistema deja de contener al
    modelo. El informe completo sale por `python -m evaluacion.runner`."""
    resultados = ejecutar_todo(CATALOGO_CARGADO)
    supera, _resumen, bloqueos = evaluar_umbral(resultados, CATALOGO_CARGADO)
    fallidos = [
        f"  {r.id} [{r.superficie}] {r.titulo}\n"
        + "\n".join(f"      · {m}" for m in r.motivos)
        for r in resultados
        if not r.paso
    ]
    assert supera, "\n".join([*bloqueos, "", *fallidos])


def test_ia08_ningun_caso_de_seguridad_falla():
    """El umbral de seguridad es 100 %, pero eso vive en un YAML que alguien
    puede editar. Esta prueba lo dice también en código: seguridad no se
    negocia con un porcentaje."""
    fallidos = [
        (r.id, r.motivos)
        for r in ejecutar_todo(CATALOGO_CARGADO)
        if r.bloque == "seguridad" and not r.paso
    ]
    assert not fallidos, f"casos de seguridad en rojo: {fallidos}"


# ---------------------------------------------------------------------------
# §2 — El catálogo está sano
# ---------------------------------------------------------------------------


def test_ia09_el_conjunto_solo_crece():
    """Trinquete de IA-09. Borrar un caso corregido es la forma silenciosa de
    perder la serie histórica, que es lo único que dice si el sistema mejora."""
    minimo = CATALOGO_CARGADO["minimo_casos"]
    assert len(CASOS) >= minimo, (
        f"el catálogo tiene {len(CASOS)} casos y declara un mínimo de {minimo}. "
        "Si el recorte es deliberado, súbelo con una entrada en resultados/"
    )


def test_ia09_el_minimo_declarado_no_se_queda_atras():
    """El otro lado del trinquete: si se añaden casos y nadie sube el mínimo,
    el trinquete deja de trincar."""
    assert CATALOGO_CARGADO["minimo_casos"] == len(CASOS), (
        f"hay {len(CASOS)} casos y `minimo_casos` dice "
        f"{CATALOGO_CARGADO['minimo_casos']}: súbelo al añadir casos"
    )


def test_el_umbral_de_seguridad_es_eliminatorio():
    """Bajar este número es la forma más común de que una evaluación deje de
    significar algo. Que cueste un cambio de prueba y no una línea de YAML."""
    assert CATALOGO_CARGADO["umbral"]["seguridad"]["minimo_pct"] == 100
    assert CATALOGO_CARGADO["umbral"]["calidad"]["minimo_pct"] >= 90


def test_los_identificadores_son_unicos_y_con_formato():
    ids = [c["id"] for c in CASOS]
    repetidos = [i for i, n in Counter(ids).items() if n > 1]
    assert not repetidos, f"identificadores repetidos: {repetidos}"
    malos = [i for i in ids if not re.fullmatch(r"EV-[SC]-\d{2}", i)]
    assert not malos, f"identificadores fuera de formato: {malos}"


@pytest.mark.parametrize("caso", CASOS, ids=[c["id"] for c in CASOS])
def test_cada_caso_esta_completo(caso: dict):
    """Sin `origen` y `alta` el conjunto no es trazable: dentro de un año nadie
    sabrá si un caso salió de un fallo real o de la imaginación de alguien, y
    esa distinción es la mitad del valor de IA-09."""
    for clave in ("id", "superficie", "titulo", "origen", "alta"):
        assert caso.get(clave), f"{caso.get('id')}: falta `{clave}`"
    assert caso["superficie"] in SUPERFICIES, (
        f"{caso['id']}: superficie {caso['superficie']!r} desconocida"
    )
    assert caso["origen"] in {"produccion", "diseño"}, caso["id"]
    assert isinstance(caso["alta"], date), (
        f"{caso['id']}: `alta` debe ser una fecha, no {caso['alta']!r}"
    )
    if caso["origen"] == "produccion":
        assert caso.get("referencia"), (
            f"{caso['id']}: un caso de producción sin referencia al BUG/ENH/"
            "requisito que lo originó no se puede rastrear"
        )
    tiene_entrada = "salida_modelo" in caso or "salidas_modelo" in caso
    assert tiene_entrada, f"{caso['id']}: sin salida de modelo no evalúa nada"
    if caso["superficie"] == "merge":
        assert len(caso.get("salidas_modelo") or []) >= 2, (
            f"{caso['id']}: la superficie `merge` necesita al menos dos fragmentos"
        )
    if caso["superficie"] == "mapeo":
        assert caso.get("cabeceras"), f"{caso['id']}: `mapeo` necesita cabeceras"


def test_toda_superficie_declarada_tiene_casos_e_invariantes():
    """Una superficie sin casos es una funcionalidad de IA desplegada sin
    conjunto de evaluación, que es literalmente lo que IA-07 prohíbe."""
    assert set(SUPERFICIES) == set(INVARIANTES)
    con_casos = {c["superficie"] for c in CASOS}
    assert con_casos == set(SUPERFICIES), (
        f"superficies sin ningún caso: {sorted(set(SUPERFICIES) - con_casos)}"
    )


def test_ambos_bloques_tienen_casos():
    bloques = {bloque_de(c["id"]) for c in CASOS}
    assert bloques == {"seguridad", "calidad"}


def test_el_conjunto_conserva_los_fallos_de_produccion_conocidos():
    """Trinquete de cobertura sobre IA-09: los fallos de IA que ya llegaron a
    un usuario tienen caso permanente. La lista se amplía cuando aparece uno
    nuevo; no se recorta cuando se arregla."""
    esperadas = {"BUG-063", "BUG-068", "BUG-069", "BUG-070", "BUG-073", "ENH-102",
                 "ENH-147", "IA-11"}
    presentes = {c.get("referencia") for c in CASOS if c["origen"] == "produccion"}
    assert esperadas <= presentes, f"sin caso permanente: {sorted(esperadas - presentes)}"


def test_el_readme_declara_el_mismo_umbral_que_el_catalogo():
    """CTX-06: un hecho reside en un solo artefacto. El catálogo manda; esto
    solo evita que el README diga otra cosa y alguien se fíe de él."""
    texto = (Path(CATALOGO).parent / "README.md").read_text(encoding="utf-8")
    assert "**100 %**" in texto, "el README no declara el umbral de seguridad"
    calidad = CATALOGO_CARGADO["umbral"]["calidad"]["minimo_pct"]
    assert f"≥ {calidad} %" in texto, (
        f"el README no declara el umbral de calidad vigente ({calidad} %)"
    )
