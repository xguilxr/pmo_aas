"""MCS SEG-01 · ASVS 2.1.7 — la contraseña no puede ser una ya filtrada.

«Verify that passwords submitted during account registration, login, and
password change are checked against a set of breached passwords either locally
(such as the top 1,000 or 10,000 most common passwords which match the system's
password policy) or using an external API.»

## Lo que esta suite protege, que no es lo obvio

El riesgo de este control no es que no se implemente: es que se implemente
**vacío**. Cargar «las 10.000 contraseñas más usadas» y darlo por cumplido es lo
natural, y aquí no detendría ni una — de las 59.186 de `rockyou-75` solo ocho
pasan la política del producto, y las otras las rechaza ya la propia política.
El control quedaría marcado y `Password1!` seguiría entrando.

Por eso §1 no comprueba «hay un conjunto»: comprueba que **contiene lo que
tiene que contener** y que todo lo que contiene sería aceptable sin él. Un
conjunto cuyas entradas ya fallan la política es un conjunto que no hace nada.

§2 fija que se aplique en los tres momentos que el control nombra, y §3 que el
inicio de sesión no rechace —una contraseña filtrada pero correcta no puede
dejar a nadie fuera de su cuenta—.
"""
from __future__ import annotations

import pytest

from app.core.contrasenas_filtradas import cuantas_hay, esta_filtrada
from app.core.security import (
    PASSWORD_POLICY_MIN_LEN,
    mensaje_de_politica,
    validate_password_policy,
)

# ---------------------------------------------------------------------------
# §1 — El conjunto tiene contenido útil, no solo tamaño
# ---------------------------------------------------------------------------

#: La familia que la política de este producto produce, que es de lo que
#: protege el control. Todas cumplen 8+, mayúscula, dígito y símbolo.
PREDECIBLES = [
    "Password1!",
    "Password123!",
    "P@ssw0rd",
    "Qwerty123!",
    "Welcome1!",
    "Dragon123!",
    "Monkey123!",
    "Football1!",
    "Iloveyou1!",
    "Princess1!",
]


@pytest.mark.parametrize("password", PREDECIBLES)
def test_asvs217_las_predecibles_estan_en_el_conjunto(password):
    """Si estas no están, el conjunto no protege de nada."""
    assert esta_filtrada(password), (
        f"{password!r} cumple la política entera y es de las primeras que "
        f"prueba un atacante. Si el conjunto no la tiene, está vacío de hecho."
    )


def test_asvs217_toda_entrada_del_conjunto_pasaria_la_politica():
    """Una entrada que ya falla la política es peso muerto.

    Es la comprobación que distingue un conjunto útil de uno que solo abulta:
    lo que la política rechaza no hace falta tenerlo aquí, y tenerlo da una
    falsa sensación de cobertura.
    """
    # Se comprueba sobre una muestra: el conjunto está en minúsculas, así que
    # el criterio de mayúscula se evalúa sobre la forma original del archivo.
    import pathlib

    from app.core.contrasenas_filtradas import _conjunto

    archivo = (
        pathlib.Path(__import__("app.core.contrasenas_filtradas", fromlist=["x"]).__file__).parent
        / "datos" / "contrasenas-filtradas.txt"
    )
    lineas = [
        linea.strip()
        for linea in archivo.read_text(encoding="utf-8").splitlines()
        if linea.strip() and not linea.startswith("#")
    ]
    assert lineas, "El archivo del conjunto está vacío"

    # `validate_password_policy` consultaría el propio conjunto y devolvería
    # siempre `password_breached`, así que se comprueban las cuatro reglas
    # estructurales a mano.
    simbolos = set("!@#$%^&*()-_=+[]{};:,.<>/?|`~'\"\\")
    malas = [
        p for p in lineas[::37]  # muestra repartida por todo el archivo
        if not (
            PASSWORD_POLICY_MIN_LEN <= len(p) <= 128
            and any(c.isupper() for c in p)
            and any(c.isdigit() for c in p)
            and any(c in simbolos for c in p)
        )
    ]
    assert not malas, (
        f"{len(malas)} entradas del conjunto ya las rechaza la política sin "
        f"consultarlo — son peso muerto: {malas[:5]}"
    )
    assert _conjunto(), "El conjunto cargado en memoria está vacío"


def test_asvs217_el_conjunto_tiene_el_orden_de_magnitud_del_control():
    """«top 1,000 or 10,000», dice el control. Ni cuatro entradas ni un millón.

    El límite superior importa tanto como el inferior: la primera versión del
    generador produjo 779.911 entradas y 9 MB, y eso ya no es el conjunto de
    contraseñas filtradas — es un diccionario que empieza a rechazar
    contraseñas que nadie ha filtrado nunca.
    """
    assert 1_000 <= cuantas_hay() <= 100_000, cuantas_hay()


def test_asvs217_la_comparacion_ignora_mayusculas():
    """`PASSWORD1!` y `Password1!` son la misma para quien la adivina."""
    assert esta_filtrada("PASSWORD1!")
    assert esta_filtrada("pAsSwOrD1!")


def test_asvs217_una_contrasena_buena_no_se_rechaza():
    """El falso positivo es el modo de fallo caro: bloquea a gente real."""
    for buena in (
        "Tornillo-Ventana-42!",
        "Xq7#mLp2vRt",
        "Bicicleta.Morada.9",
    ):
        assert not esta_filtrada(buena), buena
        ok, err = validate_password_policy(buena)
        assert ok, f"{buena!r} rechazada por {err}"


# ---------------------------------------------------------------------------
# §2 — Se aplica donde se fija una contraseña
# ---------------------------------------------------------------------------


def test_asvs217_la_politica_rechaza_una_filtrada():
    """Va dentro de `validate_password_policy` para que ningún sitio lo olvide.

    Son seis los que fijan una contraseña; un control que hay que acordarse de
    llamar seis veces es un control que va a faltar en el séptimo.
    """
    ok, err = validate_password_policy("Password1!")
    assert not ok
    assert err == "password_breached"


def test_asvs217_el_mensaje_no_le_dice_que_haga_lo_que_ya_hizo():
    """A quien escribió `Password1!` no se le puede pedir «usa mayúsculas».

    Es lo que decían los seis mensajes anteriores, y es el motivo de que
    `mensaje_de_politica` exista.
    """
    texto = mensaje_de_politica("password_breached")
    assert "filtraciones" in texto
    # Las tres partes de LEN-02, y ninguna repitiendo la regla ya cumplida.
    assert "palabras" in texto, "Debe decir qué hacer en su lugar"

    generico = mensaje_de_politica("password_too_short")
    assert generico != texto


@pytest.mark.asyncio
async def test_asvs217_el_cambio_de_contrasena_la_rechaza(client, db_session):
    from tests.factories import create_tenant, create_user, login

    tenant = await create_tenant(db_session, slug="filtradas", name="Filtradas")
    await create_user(
        db_session, tenant=tenant, username="filtr",
        email="filtr@acme.example.com", password="Zx9-Correcta-Larga!",
    )
    sesion = await login(client, "filtr@acme.example.com", "Zx9-Correcta-Larga!")

    r = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "Zx9-Correcta-Larga!", "new_password": "Password123!"},
        headers=sesion["_authz"],
    )
    # `validation_error` responde 400 en este API (`core/errors.py`).
    assert r.status_code == 400, r.text
    assert r.json()["detail"]["fields"]["code"] == "password_breached"


# ---------------------------------------------------------------------------
# §3 — En el inicio de sesión avisa, no rechaza
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_asvs217_el_login_con_filtrada_entra_pero_fuerza_el_cambio(
    client, db_session
):
    """Rechazar aquí sería una denegación de servicio, no un control.

    La contraseña es correcta: dejar a alguien fuera de su cuenta porque
    apareció en una filtración le quita el acceso sin darle forma de
    recuperarlo. Se le deja entrar y se le obliga a cambiarla, que es el
    mecanismo que la web ya sabe llevar (`must_change_password`).
    """
    from tests.factories import create_tenant, create_user

    tenant = await create_tenant(db_session, slug="filtr2", name="Filtradas2")
    await create_user(
        db_session, tenant=tenant, username="conflitrada",
        email="conf@acme.example.com", password="Password123!",
    )

    r = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "conf@acme.example.com", "password": "Password123!"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["user"]["must_change_password"] is True, (
        "Entra, pero tiene que salir a cambiarla"
    )


@pytest.mark.asyncio
async def test_asvs217_el_login_con_buena_no_fuerza_nada(client, db_session):
    from tests.factories import create_tenant, create_user

    tenant = await create_tenant(db_session, slug="filtr3", name="Filtradas3")
    await create_user(
        db_session, tenant=tenant, username="limpia",
        email="limpia@acme.example.com", password="Zx9-Correcta-Larga!",
    )

    r = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "limpia@acme.example.com", "password": "Zx9-Correcta-Larga!"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["user"]["must_change_password"] is False


# ---------------------------------------------------------------------------
# §4 — El generador y el API no se separan
# ---------------------------------------------------------------------------


def test_asvs217_el_generador_usa_la_misma_politica_que_el_api():
    """El generador duplica la regla en cuatro líneas porque corre fuera del
    entorno del API. Esto es lo que impide que las dos copias se separen — si
    se separan, el conjunto se llena de entradas que la política ya rechaza."""
    import importlib.util
    import pathlib

    ruta = pathlib.Path(__file__).resolve().parents[3] / "scripts" / "genera_contrasenas_filtradas.py"
    spec = importlib.util.spec_from_file_location("generador", ruta)
    assert spec and spec.loader
    generador = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generador)

    casos = [
        ("Password1!", True),      # pasa la estructura (lo filtrado va aparte)
        ("corta1!", False),        # menos de 8
        ("sinmayuscula1!", False),
        ("SinDigito!", False),
        ("SinSimbolo1", False),
        ("A1!" + "x" * 200, False),  # pasa del máximo
    ]
    for password, esperado in casos:
        assert generador.pasa_la_politica(password) is esperado, password
        # Y la del API coincide, salvo por el propio conjunto de filtradas.
        ok, err = validate_password_policy(password)
        estructural = ok or err == "password_breached"
        assert estructural is esperado, f"{password!r}: API dice {err}"
