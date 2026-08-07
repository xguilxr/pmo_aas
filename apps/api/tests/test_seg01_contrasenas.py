"""SEG-01 / ADR-032 — la política de contraseñas, con su defecto arreglado.

El mapeo completo contra ASVS L1 (2026-08-07) sacó cuatro controles del
capítulo 2.1, y **no todos eran lo mismo**:

- `2.1.1` (mínimo 12) y `2.1.9` (sin reglas de composición) son **postura**.
  ASVS los pide juntos porque para NIST son la misma medida: las reglas
  producen contraseñas predecibles —«Password1!» las cumple todas— y la
  longitud es lo que encarece adivinarlas. **El owner decidió el 2026-08-07
  quedarse en 8 con reglas** (ADR-032), y en el mapeo figuran ACEPTADO, no
  CUMPLE.
- `2.1.2` y `2.1.3` eran **defecto**, y este archivo los cierra.

## El defecto, que no era teórico

bcrypt trunca a 72 bytes **en silencio**. Comprobado antes de arreglarlo: una
contraseña de 103 caracteres y otra de 108 que compartían los primeros 72
abrían la misma cuenta. Nadie lo habría notado nunca, porque el fallo es que
funciona de más.

`bcrypt_sha256` resume con HMAC-SHA256 antes de pasar por bcrypt, así que no
queda longitud que truncar. `bcrypt` se conserva **deprecado y no retirado**:
retirarlo dejaría fuera a todo el mundo de golpe. Los hashes existentes siguen
verificando y se reescriben al esquema nuevo la próxima vez que su dueño inicia
sesión, que es el único momento en que la contraseña en claro existe y se ha
demostrado correcta.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from passlib.context import CryptContext

from app.core.security import (
    PASSWORD_POLICY_MAX_LEN,
    PASSWORD_POLICY_MIN_LEN,
    hash_password,
    necesita_rehash,
    validate_password_policy,
    verify_password,
)

RAIZ = Path(__file__).resolve().parents[3]
API = Path(__file__).resolve().parents[1]


# --------------------------------------------------------------------------
# 2.1.3 — el truncamiento silencioso
# --------------------------------------------------------------------------


def test_dos_contrasenas_largas_distintas_no_abren_la_misma_cuenta() -> None:
    """El defecto que había, escrito como el caso que lo destapó.

    Los primeros 72 bytes coinciden y el resto no. Con bcrypt a secas esto
    devolvía `True`, y ninguna prueba lo miraba porque el síntoma es que
    funciona de más.
    """
    suya = "A1!" + "x" * 100
    ajena = "A1!" + "x" * 97 + "DISTINTO"
    assert suya[:72] == ajena[:72], "El caso pierde sentido si no comparten prefijo."
    assert suya != ajena

    guardado = hash_password(suya)
    assert verify_password(suya, guardado) is True
    assert verify_password(ajena, guardado) is False, (
        "Una contraseña distinta abre la cuenta. bcrypt volvió a truncar a 72 "
        "bytes: el esquema tiene que ser `bcrypt_sha256`."
    )


def test_una_contrasena_de_128_no_se_recorta() -> None:
    """El tope declarado tiene que ser el tope real, también con acentos.

    Con bcrypt a secas, 128 caracteres con eñes pasan de 72 **bytes** mucho
    antes de llegar a 72 caracteres, así que el recorte llegaba antes de lo que
    nadie habría supuesto.
    """
    larga = "Añ1!" + "ñ" * 124
    assert len(larga) == 128
    assert verify_password(larga, hash_password(larga)) is True
    assert verify_password(larga[:-1], hash_password(larga)) is False


# --------------------------------------------------------------------------
# 2.1.2 — el máximo, declarado en vez de implícito
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "contrasena,codigo",
    [
        ("A1!abcde", None),
        ("A1!abcd", "password_too_short"),
        ("A1!" + "x" * 126, "password_too_long"),
        ("A1!" + "x" * 125, None),
        ("a1!abcdefg", "password_missing_uppercase"),
        ("A!abcdefg", "password_missing_digit"),
        ("A1abcdefg", "password_missing_symbol"),
    ],
)
def test_la_politica_declara_sus_dos_extremos(
    contrasena: str, codigo: str | None
) -> None:
    """Antes solo había mínimo. «Sin máximo» sonaba generoso mientras por
    detrás había uno de 72 bytes sin declarar y sin avisar."""
    ok, error = validate_password_policy(contrasena)
    assert error == codigo
    assert ok is (codigo is None)


def test_los_extremos_son_los_que_asvs_admite() -> None:
    assert PASSWORD_POLICY_MIN_LEN == 8, (
        "ADR-032 fija 8. Si cambia, el ADR cambia con él y el mapeo ASVS deja "
        "de decir ACEPTADO."
    )
    assert PASSWORD_POLICY_MAX_LEN == 128, "ASVS 2.1.2 pide denegar por encima de 128."


# --------------------------------------------------------------------------
# La ventana de compatibilidad
# --------------------------------------------------------------------------


def test_un_hash_del_esquema_viejo_sigue_abriendo_su_cuenta() -> None:
    """Retirar `bcrypt` en vez de deprecarlo dejaría fuera a todo el mundo.

    Es la parte que convierte esto en una migración y no en una ruptura.
    """
    antiguo = CryptContext(schemes=["bcrypt"], bcrypt__rounds=4).hash("Vieja1!")
    assert verify_password("Vieja1!", antiguo) is True
    assert verify_password("Otra1!x", antiguo) is False


def test_el_hash_viejo_se_marca_para_reescritura_y_el_nuevo_no() -> None:
    antiguo = CryptContext(schemes=["bcrypt"], bcrypt__rounds=4).hash("Vieja1!")
    assert necesita_rehash(antiguo) is True
    assert necesita_rehash(hash_password("Vieja1!")) is False


def test_el_inicio_de_sesion_reescribe_el_hash_viejo() -> None:
    """La migración se cablea donde la contraseña en claro existe, o no ocurre.

    Se comprueba sobre el árbol y no ejecutando el punto de acceso: lo que
    puede perderse en un refactor es la llamada, no el comportamiento de la
    función.
    """
    fuente = (API / "app" / "api" / "v1" / "endpoints" / "auth.py").read_text(
        encoding="utf-8"
    )
    assert "necesita_rehash(user.password_hash)" in fuente, (
        "El inicio de sesión dejó de reescribir los hashes del esquema viejo. "
        "Sin eso la migración no ocurre nunca: nadie va a pedirle la contraseña "
        "otra vez a nadie para esto."
    )
    posicion = fuente.index("necesita_rehash(user.password_hash)")
    assert "hash_password(body.password)" in fuente[posicion : posicion + 200], (
        "Se comprueba si hace falta reescribir y no se reescribe."
    )


# --------------------------------------------------------------------------
# La decisión, y que siga escrita
# --------------------------------------------------------------------------


def test_la_decision_del_owner_esta_en_un_adr() -> None:
    """`ACEPTADO` sin decisión detrás es un hueco con la etiqueta cambiada."""
    adr = (RAIZ / "docs" / "adr" / "README.md").read_text(encoding="utf-8")
    bloque = adr[adr.index("## ADR-032") :]
    for pieza in ("2.1.1", "2.1.9", "NIST", "owner"):
        assert pieza in bloque, f"ADR-032 no menciona «{pieza}»."
    assert "ACEPTADO" in bloque, (
        "El ADR no dice que el mapeo los declara ACEPTADO y no CUMPLE. Esa "
        "distinción es la mitad de la decisión."
    )


def test_el_mapeo_asvs_no_los_pinta_como_cumplidos() -> None:
    """Lo que un auditor externo mira primero."""
    import yaml

    mapeo = yaml.safe_load(
        (RAIZ / "docs" / "conformidad" / "asvs-l1.yaml").read_text(encoding="utf-8")
    )["controles"]
    for control in ("2.1.1", "2.1.9"):
        assert mapeo[control]["estado"] == "ACEPTADO", (
            f"{control} figura como {mapeo[control]['estado']}. El producto no "
            f"lo cumple; hay una decisión, y eso se llama ACEPTADO."
        )
        assert re.search(r"ADR-032", mapeo[control]["evidencia"])
    for control in ("2.1.2", "2.1.3"):
        assert mapeo[control]["estado"] == "CUMPLE"
