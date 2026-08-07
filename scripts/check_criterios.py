#!/usr/bin/env python3
"""MCS REQ-01 — todo requisito cerrado tiene una prueba que lo nombra.

«Todo requisito funcional DEBE tener criterio de aceptación verificable».

La auditoría del 2026-08-03 lo dejó PARCIAL con el hueco escrito: la plantilla
de issue exige criterios de aceptación, «pero varios batches se ejecutaron por
chat **sin crear issues**, así que no hay criterio verificable para ellos».

La regla que cierra el hueco está en
`docs/project-management/CRITERIOS-DE-ACEPTACION.md`: **el criterio de
aceptación de un cambio es la prueba que lo nombra**. No un párrafo que lo
describa — una prueba ejecutable que cite su identificador y falle si el
comportamiento se pierde.

Esto lo comprueba. Los identificadores salen del **registro** (lo que está
declarado CONFORME) y los nombres se buscan en el árbol de pruebas y barridos.
No hay lista escrita a mano por ningún lado: una lista probaría «tienen prueba
los que me acordé de listar».

## Lo que NO comprueba

Que la prueba sea buena. Un caso que nombre `DAT-09` y no compruebe nada
pasaría este barrido. De eso se encarga la verificación por mutación, que es
parte del cierre de cada item y cuyo resultado va en el mensaje del commit. Las
dos juntas dan lo que REQ-01 pide; por separado, ninguna.

Uso:

    python scripts/check_criterios.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
REGISTRO = RAIZ / "scripts" / "registro_conformidad.py"

#: Dónde puede vivir un criterio de aceptación. Son las tres formas que el
#: documento admite: caso de pytest, barrido con trinquete y caso del conjunto
#: de evaluación de IA.
LUGARES = (
    ("apps/api/tests", "*.py"),
    ("apps/api/evaluacion", "*.yaml"),
    ("scripts", "*.py"),
    ("apps/web", "*.test.ts"),
    ("apps/web", "*.test.tsx"),
)


def conformes() -> set[str]:
    """Los requisitos que el registro declara CONFORME, del propio derivador.

    Se leen de `CIERRES` y no de la salida del script para no depender de su
    formato de impresión, que es para personas.
    """
    texto = REGISTRO.read_text(encoding="utf-8")
    return set(re.findall(r'^\s*"([A-Z]{2,3}-\d{2})":\("CONFORME"', texto, re.M))


#: Archivos que citan identificadores **sin verificar nada**: el propio
#: registro los enumera y este control los explica. Incluirlos haría que
#: cualquier requisito se encontrara a sí mismo y el barrido pasara siempre.
#:
#: No es una precaución teórica: la primera versión sí los incluía, y las dos
#: mutaciones —añadir un cierre sin prueba y quitarle el identificador a la
#: prueba que lo cubría— **pasaron en verde**. Es la sexta vez en este
#: expediente que un control se valida contra su propia documentación.
NO_SON_PRUEBA = {
    "scripts/registro_conformidad.py",
    "scripts/check_criterios.py",
}


def corpus_de_pruebas() -> str:
    partes: list[str] = []
    for carpeta, patron in LUGARES:
        base = RAIZ / carpeta
        if not base.exists():
            continue
        for archivo in base.rglob(patron):
            if "node_modules" in archivo.parts or "__pycache__" in archivo.parts:
                continue
            if archivo.relative_to(RAIZ).as_posix() in NO_SON_PRUEBA:
                continue
            partes.append(archivo.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(partes)


#: Cierres que **no se pueden verificar desde este repositorio**, con el motivo
#: escrito. Son hechos de GitHub y de Railway: este árbol no tiene acceso a la
#: configuración de ninguno de los dos, y fingir una prueba que los compruebe
#: sería peor que declararlos.
#:
#: La diferencia entre esto y «se nos pasó» es que aquí está escrito qué habría
#: que mirar y dónde. Un auditor externo puede ir a comprobarlo; el CI no.
FUERA_DEL_REPOSITORIO: dict[str, str] = {
    "CFG-03": (
        "La rama protegida sin escritura directa vive en la configuración de "
        "GitHub. Se comprueba en Settings → Branches → main, con "
        "`enforce_admins` activo."
    ),
    "INT-03": (
        "Que la integración exija las verificaciones en verde es la misma "
        "pantalla de GitHub que CFG-03: protección de rama con checks "
        "requeridos."
    ),
    "SEG-02": (
        "El almacén de secretos es el de variables de Railway. Lo que SÍ se "
        "verifica aquí es el lado negativo —que no haya secretos en el "
        "repositorio—, y eso lo hace gitleaks sobre el historial completo "
        "(CFG-02, con prueba)."
    ),
    "SUM-01": (
        "Que Railway construya desde la rama y nadie despliegue desde su "
        "máquina es configuración del proveedor. Está declarado en ADR-031 con "
        "su consecuencia: no hay artefacto inmutable."
    ),
}


def main() -> int:
    ids = conformes()
    if not ids:
        print(
            "FALLA — REQ-01: no se leyó ningún cierre del registro. O cambió el "
            "formato de `CIERRES`, o este control dejó de mirar donde debía."
        )
        return 1

    corpus = corpus_de_pruebas()
    if len(corpus) < 100_000:
        print(
            f"FALLA — REQ-01: el corpus de pruebas mide {len(corpus)} caracteres. "
            f"El barrido dejó de encontrarlas y estaría pasando por no mirar."
        )
        return 1

    for rid, motivo in FUERA_DEL_REPOSITORIO.items():
        if len(motivo.strip()) < 60:
            print(
                f"FALLA — REQ-01: {rid} se declara no verificable aquí sin decir "
                f"dónde SÍ se comprueba. Eso no es una excepción, es un hueco."
            )
            return 1
    fantasmas = sorted(set(FUERA_DEL_REPOSITORIO) - ids)
    if fantasmas:
        print(
            f"FALLA — REQ-01: {fantasmas} están declarados fuera del repositorio "
            f"y ya no figuran como conformes. Quita la entrada."
        )
        return 1

    sin_criterio = sorted(
        i for i in ids if i not in corpus and i not in FUERA_DEL_REPOSITORIO
    )
    if sin_criterio:
        print("FALLA — REQ-01:\n")
        for rid in sin_criterio:
            print(
                f"  - {rid} está declarado CONFORME y ninguna prueba ni barrido "
                f"lo nombra. Su criterio de aceptación no es verificable."
            )
        print(
            "\nLa regla está en docs/project-management/CRITERIOS-DE-ACEPTACION.md: "
            "el criterio de aceptación de un cambio es la prueba que lo nombra."
        )
        return 1

    con_prueba = len(ids) - len(FUERA_DEL_REPOSITORIO)
    print(
        f"OK — {con_prueba} requisitos conformes tienen prueba que los nombra; "
        f"{len(FUERA_DEL_REPOSITORIO)} se verifican fuera del repositorio, con "
        f"el dónde escrito."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
