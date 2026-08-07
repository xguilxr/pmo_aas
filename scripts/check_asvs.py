#!/usr/bin/env python3
"""MCS SEG-01 — el mapeo contra ASVS L1 está completo y no se maquilla.

«El producto DEBE cumplir los controles de OWASP ASVS nivel 1 aplicables».

La auditoría del 2026-08-03 lo puso NO VERIFICABLE («sin evaluación ASVS»); la
R1 lo bajó a PARCIAL con **un muestreo declarado** y tres huecos con nombre. Los
tres se cerraron después —límite por IP en el inicio de sesión, `audit_log` de
solo anexado, y `python-jose` sustituido por PyJWT—, pero el propio informe
avisaba: «con los tres cerrados seguiría haciendo falta el mapeo completo».

El mapeo completo existe desde el 2026-08-07 y este control lo sostiene.

## Qué vigila

1. **Que esté completo.** Los 127 controles L1 del catálogo, uno por uno. El
   catálogo es el de verdad —`marco/asvs-4.0.3-L1.csv`, extraído de la fuente
   de OWASP— y no una lista escrita a mano: sin eso, «completo» significaría
   «completo entre los que recordé».
2. **Que ningún estado se maquille.** Un `NO APLICA` sin motivo escrito es un
   hueco con otro nombre, y es la forma más cómoda de cerrar un capítulo
   entero. Aquí no pasa el barrido.
3. **Que los huecos no encojan solos.** El número medido va escrito en el
   propio archivo; bajarlo exige cerrar controles de verdad, no reclasificarlos.

## Lo que NO vigila

Que la evidencia sea cierta. «CUMPLE — SQLAlchemy con parámetros ligados» lo
escribe una persona, y este barrido lo lee sin comprobarlo. Lo que lo comprueba
son las suites de cada control —SEG-04 tiene sus 18 casos, IA-11 los suyos— y
el hecho de que la evidencia cite archivo y función, para que un auditor pueda
ir a mirar.

Uso:

    python scripts/check_asvs.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[1]
CATALOGO = RAIZ / "docs" / "conformidad" / "marco" / "asvs-4.0.3-L1.csv"
MAPEO = RAIZ / "docs" / "conformidad" / "asvs-l1.yaml"

#: `ACEPTADO` no es un cuarto sabor de «cumple». Es «no se cumple y hay una
#: decisión escrita detrás», y se separa de HUECO porque no está pendiente de
#: nadie, y de CUMPLE porque el control no se satisface. Mismo patrón que los
#: residuales aceptados del modelo de amenazas.
ESTADOS = {"CUMPLE", "NO APLICA", "HUECO", "ACEPTADO"}

#: Lo medido el 2026-08-07, **después** de cerrar doce de los quince que sacó el
#: mapeo. El barrido falla si los huecos **crecen**; que encojan es el objetivo.
#:
#: Se fija aquí y no en el YAML para que bajarlo sea un cambio deliberado y no un
#: efecto de reclasificar tres controles. Y se baja **al cerrar**, no antes: un
#: tope por encima de la medición real deja sitio para que un hueco vuelva a
#: aparecer sin que nada falle, que es la forma silenciosa de perder lo ganado.
#:
#: Los tres que quedan —`4.3.1` segundo factor de administración, `8.3.2`
#: derechos de exportación y supresión, `8.3.3` consentimiento— son producto por
#: construir, no configuración por ajustar. Están en `asvs-l1.md`.
HUECOS_MAXIMOS = 3


def main() -> int:
    catalogo = {
        f["control"]: f["descripcion"]
        for f in csv.DictReader(CATALOGO.open(encoding="utf-8"))
    }
    mapeo = yaml.safe_load(MAPEO.read_text(encoding="utf-8"))["controles"]
    problemas: list[str] = []

    if len(catalogo) < 120:
        problemas.append(
            f"El catálogo tiene {len(catalogo)} controles. ASVS 4.0.3 L1 son 127; "
            f"o se truncó el archivo o el barrido dejó de leerlo entero."
        )

    faltan = sorted(set(catalogo) - set(mapeo))
    if faltan:
        problemas.append(
            f"Sin mapear ({len(faltan)}): {faltan[:8]}{'…' if len(faltan) > 8 else ''}. "
            f"Un mapeo incompleto presentado como completo es lo que produjo los "
            f"dos recuentos equivocados de este expediente."
        )
    sobran = sorted(set(mapeo) - set(catalogo))
    if sobran:
        problemas.append(f"Mapeados y no en el catálogo: {sobran}")

    huecos = 0
    for control, dato in sorted(mapeo.items()):
        estado = (dato or {}).get("estado")
        evidencia = str((dato or {}).get("evidencia") or "").strip()
        if estado not in ESTADOS:
            problemas.append(f"{control}: estado {estado!r} no es uno de {sorted(ESTADOS)}")
            continue
        if not evidencia:
            problemas.append(f"{control}: {estado} sin evidencia escrita")
        elif estado == "NO APLICA" and len(evidencia) < 30:
            problemas.append(
                f"{control}: «NO APLICA» con un motivo de {len(evidencia)} caracteres. "
                f"Un no-aplica sin explicar es un hueco con otro nombre, y es la "
                f"forma más cómoda de cerrar un capítulo entero."
            )
        if estado == "HUECO":
            huecos += 1
        if estado == "ACEPTADO" and "ADR-" not in evidencia:
            problemas.append(
                f"{control}: «ACEPTADO» sin citar la decisión que lo acepta. "
                f"Un residual sin ADR detrás es un hueco al que alguien le "
                f"cambió la etiqueta."
            )

    if huecos > HUECOS_MAXIMOS:
        problemas.append(
            f"Los huecos pasaron de {HUECOS_MAXIMOS} a {huecos}. El trinquete "
            f"admite que bajen, no que suban."
        )

    if problemas:
        print("FALLA — SEG-01:\n")
        for p in problemas:
            print(f"  - {p}")
        return 1

    cuenta = {e: sum(1 for d in mapeo.values() if d["estado"] == e) for e in sorted(ESTADOS)}
    print(
        f"OK — {len(mapeo)}/{len(catalogo)} controles ASVS L1 mapeados: "
        f"{cuenta['CUMPLE']} CUMPLE · {cuenta['NO APLICA']} NO APLICA · "
        f"{cuenta['ACEPTADO']} ACEPTADO · {huecos} HUECO (tope {HUECOS_MAXIMOS})."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
