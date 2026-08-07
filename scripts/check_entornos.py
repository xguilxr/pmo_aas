#!/usr/bin/env python3
"""MCS INF-02 — la paridad de versiones declarada se cumple de verdad.

«DEBEN existir entornos separados para desarrollo y producción, con paridad en
las versiones de los servicios de datos».

Los entornos existen. Lo que no existía era la paridad **declarada**: sin un
sitio que dijera qué versión toca, «paridad» no se puede afirmar ni desmentir,
solo suponer.

**Y la suposición estaba mal.** El 2026-08-06, al correr a mano lo que el CI no
podía, la base local resultó ser Postgres **16** contra el **15** del workflow.
Nadie lo eligió: era el que traía el sistema. Con la migración 0101 en juego
—reescrita por miedo a una diferencia entre motores— era justo la divergencia
que no debía existir.

Este control lee `servicios-datos.yml` y comprueba que el workflow lo respeta.
Es la mitad verificable del requisito: lo que corre en Railway no se puede
comprobar desde aquí, y por eso el runbook lo declara con fecha en vez de
fingir que se mide.

Uso:

    python scripts/check_entornos.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[1]
DECLARACION = RAIZ / "servicios-datos.yml"
FLUJO = RAIZ / ".github" / "workflows" / "ci.yml"


def declarado() -> dict:
    return yaml.safe_load(DECLARACION.read_text(encoding="utf-8"))


def imagenes_del_flujo() -> list[str]:
    """Las imágenes de servicio que el CI levanta.

    Se descartan los comentarios antes de mirar: el workflow explica en prosa
    por qué usa cada versión, y buscar en el texto crudo haría que el control
    se validara contra su propia documentación. Ha pasado cinco veces en este
    repositorio; aquí se evita por construcción.
    """
    texto = "\n".join(
        linea
        for linea in FLUJO.read_text(encoding="utf-8").splitlines()
        if not linea.lstrip().startswith("#")
    )
    return re.findall(r"^\s*image:\s*(\S+)\s*$", texto, re.M)


def main() -> int:
    decl = declarado()
    imagenes = imagenes_del_flujo()
    problemas: list[str] = []

    esperada = decl["postgres"]["imagen_ci"]
    postgres = [i for i in imagenes if i.startswith("postgres:")]
    if not postgres:
        problemas.append(
            "El CI no levanta ningún servicio Postgres. El trabajo de "
            "migraciones dejó de ejercerse contra el motor real."
        )
    elif esperada not in postgres:
        problemas.append(
            f"El CI levanta {postgres} y `servicios-datos.yml` declara "
            f"«{esperada}». Una divergencia de versión entre lo que se prueba y "
            f"lo que corre en producción es la forma de BUG-039: el motor "
            f"acepta en un sitio lo que rechaza en el otro."
        )

    # Que la declaración no se contradiga a sí misma: la imagen del CI tiene
    # que ser de la serie mayor declarada. Sin esto, alguien puede cambiar
    # `imagen_ci` a otra serie y el gate seguiría verde porque solo compara la
    # imagen consigo misma.
    mayor = str(decl["postgres"]["version_mayor"])
    if not esperada.startswith(f"postgres:{mayor}"):
        problemas.append(
            f"`imagen_ci` es «{esperada}» pero `version_mayor` dice {mayor}. "
            f"La propia declaración se contradice."
        )

    for servicio in ("postgres", "redis"):
        if not str(decl[servicio].get("razon", "")).strip():
            problemas.append(
                f"`{servicio}` no declara por qué esa versión. Una versión sin "
                f"motivo escrito es una que nadie se atreve a cambiar."
            )

    if not decl.get("entornos"):
        problemas.append("No se declara ningún entorno.")

    if problemas:
        print("FALLA — INF-02:\n")
        for p in problemas:
            print(f"  - {p}")
        return 1

    nombres = ", ".join(e["nombre"] for e in decl["entornos"])
    print(f"OK — paridad declarada ({esperada}) y respetada por el CI. Entornos: {nombres}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
