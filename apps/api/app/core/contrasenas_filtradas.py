"""MCS SEG-01 · ASVS 2.1.7 — la contraseña no puede ser una ya filtrada.

«Verify that passwords submitted during account registration, login, and
password change are checked against a set of breached passwords either locally
(such as the top 1,000 or 10,000 most common passwords which match the system's
password policy) or using an external API.»

## Por qué el conjunto es local y no una API externa

El control admite las dos. Se elige local por tres motivos, en este orden:

1. **No se manda la contraseña de nadie a un tercero.** Ni siquiera un prefijo
   de su hash. Añadir un destino externo en la ruta de autenticación obligaría
   además a pasar por el modelo de amenazas —lo comprueba
   `test_seg06_modelo_amenazas`— y a explicar en el inventario de datos
   personales qué sale de aquí.
2. **No falla.** Una API externa en el cambio de contraseña tiene dos finales
   malos: si falla abierto, el control no protege justo cuando alguien lo tira;
   si falla cerrado, nadie puede cambiar su contraseña porque un tercero está
   caído.
3. El control nombra el conjunto local primero, y con el tamaño que aquí se usa.

## Qué contiene el conjunto, que no es lo que parece

**No** son «las 10.000 contraseñas más usadas». Eso aquí no protegería de nada:
de las 59.186 de `rockyou-75`, solo **ocho** pasan la política del producto —8
caracteres con mayúscula, dígito y símbolo—; las demás las rechaza ya
`validate_password_policy`. Una lista así sería un archivo grande, un control
marcado y cero contraseñas detenidas.

Lo que contiene es lo que **esta política produce**: la familia predecible de
`Password1!`. Es el argumento de NIST que ADR-032 dejó aceptado como residual —
las reglas de composición generan contraseñas adivinables, porque casi todo el
mundo las satisface igual—. Cómo se deriva, en el docstring de
`scripts/genera_contrasenas_filtradas.py`.

## La comparación es en minúsculas

`PASSWORD1!` y `Password1!` son la misma contraseña para quien la adivina: un
ataque de diccionario prueba las variantes de mayúsculas sin coste. Comparar en
minúsculas cubre esa familia sin meterla en el archivo.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

log = logging.getLogger(__name__)

_ARCHIVO = Path(__file__).parent / "datos" / "contrasenas-filtradas.txt"


@lru_cache(maxsize=1)
def _conjunto() -> frozenset[str]:
    """Carga el conjunto una vez, en minúsculas.

    Si el archivo falta, se registra y se devuelve vacío en vez de reventar: un
    despliegue mal empaquetado no puede dejar a nadie sin poder cambiar su
    contraseña. Que el archivo esté es cosa de `test_seg01_asvs217_filtradas.py`,
    no del arranque.
    """
    try:
        lineas = _ARCHIVO.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        log.error(
            "ASVS 2.1.7 — no se pudo leer %s (%s). El control queda INACTIVO.",
            _ARCHIVO, exc,
        )
        return frozenset()
    return frozenset(
        linea.strip().lower()
        for linea in lineas
        if linea.strip() and not linea.startswith("#")
    )


def esta_filtrada(password: str) -> bool:
    """¿Aparece esta contraseña en el conjunto de filtradas?"""
    return password.strip().lower() in _conjunto()


def cuantas_hay() -> int:
    """Tamaño del conjunto cargado. Para pruebas y diagnóstico."""
    return len(_conjunto())
