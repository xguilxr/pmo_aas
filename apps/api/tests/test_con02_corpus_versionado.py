"""CON-02 — el conocimiento del dominio no vive solo en el prompt.

«El conocimiento del dominio DEBE residir en artefactos versionados. NO DEBE
implementarse **únicamente** mediante instrucciones de rol dirigidas a un
modelo».

El contraste que pedía `06-COMPETENCIA.md` §5 se hizo el 2026-08-06 sobre las
cuatro instrucciones de sistema. La mayor parte de su texto es **contrato de
salida** —qué claves devolver, en qué orden, sin bloques de código— y eso no es
conocimiento de dominio. Quedaron dos cosas que sí lo eran:

1. **La taxonomía RAID.** Versionada estaba, en `validator.py` y en
   `minutes_formatter.py`. Lo que no cuadraba era el glosario: definía riesgo,
   incidencia, acción y lección, y **no mencionaba la decisión**, que es una de
   las cuatro que el producto implementa. Dos artefactos versionados diciendo
   cosas distintas es la misma enfermedad con otra cara.

2. **El mapa de señales** («se acordó» → Decisión). Criterio de dominio puro,
   y existía únicamente dentro de la cadena del prompt. El caso exacto que el
   requisito nombra.

Lo que se comprueba aquí es que sigan unidos los cuatro sitios donde el hecho
vive: el glosario, `corpus.py`, el validador y la instrucción generada. Cuatro
copias divergen — ya divergieron, y así se encontró.
"""
from __future__ import annotations

import re
from pathlib import Path

from app.services.ai.corpus import FUERA_DEL_RAID, RAID, bloque_raid
from app.services.ai.prompts import MINUTE_SYSTEM
from app.services.ai.validator import ALLOWED_RAID_TYPES
from app.services.minutes_formatter import RAID_TYPE_LABELS, RAID_TYPE_ORDER

RAIZ = Path(__file__).resolve().parents[3]
GLOSARIO = RAIZ / "docs" / "dominio" / "02-GLOSARIO.md"
PROMPTS = Path(__file__).resolve().parents[1] / "app" / "services" / "ai" / "prompts.py"


def _sin_ejemplos(fuente: str) -> str:
    """El archivo sin sus bloques de ejemplo (`FEW-SHOT`).

    Un ejemplo cita el dominio; no lo define. La frontera se toma en el
    marcador y hasta el separador que lo cierra, los dos ya presentes en el
    archivo, para no inventar una convención nueva solo para esta prueba.
    """
    lineas = fuente.splitlines()
    fuera: list[str] = []
    dentro_del_ejemplo = False
    for linea in lineas:
        if linea.startswith("FEW-SHOT"):
            dentro_del_ejemplo = True
            continue
        if dentro_del_ejemplo:
            if linea.startswith("===="):
                dentro_del_ejemplo = False
            continue
        fuera.append(linea)
    assert not dentro_del_ejemplo, (
        "Un bloque FEW-SHOT quedó sin cerrar con su separador `====`, así que "
        "esta prueba estaría descontando el resto del archivo entero."
    )
    return "\n".join(fuera)


def test_las_cuatro_categorias_coinciden_en_los_tres_sitios() -> None:
    """Corpus, validador y presentador. El que divergía era el glosario."""
    del_corpus = {c.letra for c in RAID}
    assert del_corpus == set(ALLOWED_RAID_TYPES), (
        f"El corpus dice {sorted(del_corpus)} y el validador acepta "
        f"{sorted(ALLOWED_RAID_TYPES)}. Una categoría que el modelo recibe y "
        f"el validador tira se descarta en silencio, y la minuta sale corta "
        f"sin que nadie sepa por qué."
    )
    assert tuple(c.letra for c in RAID) == RAID_TYPE_ORDER, (
        "El orden del corpus no es el que ve quien lee la minuta."
    )
    assert set(RAID_TYPE_LABELS) == del_corpus


def test_el_glosario_define_las_cuatro() -> None:
    """DAT/CON-02: el artefacto de dominio cubre lo que el producto implementa.

    Antes del 2026-08-06 el §3 no mencionaba la decisión. El modelo la recibía
    en su instrucción, el validador la aceptaba y el glosario no sabía que
    existía.
    """
    texto = GLOSARIO.read_text(encoding="utf-8")
    seccion = texto[texto.index("\n## 3. RAID") : texto.index("\n## 4. ")]
    for categoria in RAID:
        assert re.search(rf"^### 3\.\d+ {categoria.nombre}$", seccion, re.M), (
            f"El glosario §3 no define «{categoria.nombre}», que es una de las "
            f"cuatro categorías del RAID que el producto implementa."
        )


def test_las_senales_no_estan_escritas_en_el_prompt() -> None:
    """El corazón de CON-02: el criterio de dominio no se teclea en la cadena.

    Si alguien vuelve a escribirlas ahí, la instrucción puede decir algo que el
    dominio no diga, y cambiar una señal deja de tener historia en `git log`
    sobre un artefacto de dominio para tenerla sobre una cadena de 180 líneas.
    """
    fuente = PROMPTS.read_text(encoding="utf-8")
    # Se mira el ARCHIVO, no la constante ya ensamblada: la constante contiene
    # las señales por construcción, y comprobarla ahí sería validar el control
    # contra su propia salida.
    #
    # Se descuenta el ejemplo del FEW-SHOT, y no por comodidad: ahí las señales
    # aparecen **dentro de un transcript de muestra** —«Eli: preocupación, los
    # workarounds…»—, que es material ilustrativo, no la regla. Prohibirlas ahí
    # obligaría a inventar un transcript que no se parece a uno real, y un
    # ejemplo que no se parece al caso no enseña nada. La primera versión de
    # esta prueba no lo descontaba y falló por eso.
    fuente = _sin_ejemplos(fuente)

    # 1. Ninguna línea escribe un MAPA señal → categoría. Lo prohibido no es
    #    que aparezca la palabra «riesgo» —el prompt habla del RAID en prosa y
    #    tiene que poder nombrarlo—, sino que alguien vuelva a teclear la
    #    correspondencia. La primera versión de esta prueba buscaba las señales
    #    sueltas y saltaba con «riesgo» e «issue», que son palabras normales.
    letras = "|".join(c.letra for c in RAID)
    nombres = "|".join(c.nombre for c in RAID)
    mapa = re.compile(rf"→\s*\(?({letras}|{nombres})\b", re.I)
    escritas = [l.strip() for l in fuente.splitlines() if mapa.search(l)]
    assert not escritas, (
        "Estas líneas de `prompts.py` escriben a mano la correspondencia "
        "señal → categoría, que es criterio de dominio:\n  "
        + "\n  ".join(escritas)
        + "\n\nSu sitio es `corpus.py`, de donde la instrucción se genera."
    )

    # 2. Las señales de varias palabras —las que sí son criterio y no
    #    vocabulario— no aparecen en absoluto.
    for categoria in RAID:
        for senal in categoria.senales:
            if " " not in senal:
                continue
            assert senal not in fuente, (
                f'La señal "{senal}" está escrita en `prompts.py`. Su sitio es '
                f"`corpus.py`, que es el artefacto versionado del que la "
                f"instrucción se genera."
            )

    assert "bloque_raid()" in fuente, (
        "`prompts.py` dejó de generar el bloque RAID desde el corpus."
    )


def test_la_instruccion_generada_lleva_las_cuatro_y_sus_senales() -> None:
    """La otra mitad: generarlo no sirve si no llega a la instrucción.

    Es la forma de fallo de la 0098 —la verificación fabricándose su sujeto—:
    una función que produce el texto correcto y un prompt que no la llama.
    """
    bloque = bloque_raid()
    assert bloque in MINUTE_SYSTEM, (
        "`MINUTE_SYSTEM` no contiene el bloque generado. El sustituto no se "
        "aplicó, y el modelo está recibiendo el marcador de posición."
    )
    assert "{{BLOQUE_RAID}}" not in MINUTE_SYSTEM
    for categoria in RAID:
        assert categoria.definicion in bloque
        for senal in categoria.senales:
            assert senal in bloque


def test_lo_excluido_del_raid_dice_por_que() -> None:
    """«NO emitas lecciones» sin motivo es una orden; con motivo es dominio.

    El descarte silencioso de una categoría hace que la minuta salga corta.
    Quien la lea merece saber que fue a propósito y a dónde fue esa
    información.
    """
    assert FUERA_DEL_RAID, "No se declara nada fuera del RAID."
    bloque = bloque_raid()
    for nombre, porque in FUERA_DEL_RAID:
        assert porque.strip(), f"«{nombre}» se excluye sin motivo escrito."
        assert "`" in porque, (
            f"«{nombre}» se excluye sin decir a qué registro va en su lugar. "
            f"Sin eso, «descártalas» es pérdida de información."
        )
        assert nombre in bloque


def test_cada_categoria_trae_definicion_y_senales() -> None:
    """Una categoría sin señales no se puede clasificar; sin definición, no se
    puede discutir si la clasificación fue correcta."""
    for categoria in RAID:
        assert len(categoria.definicion) > 60, (
            f"«{categoria.nombre}» no está definida, solo nombrada."
        )
        assert len(categoria.senales) >= 3, (
            f"«{categoria.nombre}» tiene {len(categoria.senales)} señales. Con "
            f"menos de tres, el modelo clasifica por parecido y no por regla."
        )
