"""MCS SEG-01 · ASVS 3.2.3 y 8.2.2 — el token de sesión sale de `localStorage`.

- 3.2.3: «the application only stores session tokens in the browser using
  secure methods such as appropriately secured cookies».
- 8.2.2: «data stored in browser storage (such as localStorage, sessionStorage,
  IndexedDB, or cookies) does not contain sensitive data».

Decisión en ADR-033. Son el mismo cambio visto desde dos sitios.

## Qué cierra

El token de acceso vivía en `localStorage`, donde cualquier guion inyectado
—propio, o de cualquier dependencia de npm que entre en el paquete— lo lee con
una línea, y con él tiene la sesión completa hasta que caduque. `HttpOnly` no
hace mejor al token: hace que el guion no pueda leerlo.

## Lo que esta suite fija

§1 — que el token salga por cookie con los atributos que lo protegen.
§2 — que el API la **acepte**, porque si no la acepta el navegador se queda
fuera y el cambio se revierte en una hora.
§3 — que `Authorization` siga funcionando. El SDK y las integraciones de
servidor a servidor no son un navegador y no tienen el problema que esto
resuelve; romperlas sería cambiar un agujero por una avería.
§4 — que cerrar sesión borre la cookie. Una sesión que sobrevive a «salir» es
peor que la que estaba en `localStorage`, porque encima no se puede borrar
desde el propio navegador.
"""
from __future__ import annotations

import pytest

from app.core import cookies


async def _usuario(db, sufijo: str):
    from tests.factories import create_tenant, create_user

    tenant = await create_tenant(db, slug=f"tok{sufijo}", name=f"Tok{sufijo}")
    return await create_user(
        db, tenant=tenant, username=f"tok{sufijo}",
        email=f"tok{sufijo}@acme.example.com", password="Zx9-Correcta-Larga!",
    )


# ---------------------------------------------------------------------------
# §1 — El token sale por cookie, y protegida
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_asvs323_el_login_emite_el_token_en_cookie(client, db_session, monkeypatch):
    monkeypatch.setattr(cookies.settings, "PYTHON_ENV", "production")
    await _usuario(db_session, "1")

    r = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "tok1@acme.example.com", "password": "Zx9-Correcta-Larga!"},
    )
    assert r.status_code == 200, r.text

    galletas = [c for c in r.headers.get_list("set-cookie") if "access_token" in c]
    assert len(galletas) == 1, f"Se esperaba la cookie de acceso: {galletas}"
    cabecera = galletas[0]

    assert cabecera.startswith("__Host-access_token="), cabecera
    assert "HttpOnly" in cabecera, "Sin HttpOnly el guion la lee igual que localStorage"
    assert "Secure" in cabecera, cabecera
    assert "samesite=strict" in cabecera.lower(), cabecera


@pytest.mark.asyncio
async def test_asvs323_el_cambio_de_inquilino_reemite_la_cookie(
    client, db_session, monkeypatch
):
    """El token nuevo lleva otro inquilino activo, así que la cookie tiene que
    cambiar con él. Sin esto el navegador seguiría mandando el anterior y el
    cambio no surtiría efecto en la siguiente petición."""
    from tests.factories import create_tenant, create_user, login

    monkeypatch.setattr(cookies.settings, "PYTHON_ENV", "production")
    t1 = await create_tenant(db_session, slug="tok-a", name="TokA")
    t2 = await create_tenant(db_session, slug="tok-b", name="TokB")
    await create_user(
        db_session, tenant=t1, username="raiztok", email="raiztok@pmoaas.example.com",
        password="Zx9-Correcta-Larga!", is_superadmin=True,
    )
    sesion = await login(client, "raiztok@pmoaas.example.com", "Zx9-Correcta-Larga!")

    r = await client.post(
        "/api/v1/auth/switch-tenant",
        json={"tenant_id": str(t2.id)},
        headers=sesion["_authz"],
    )
    assert r.status_code == 200, r.text
    assert any(
        c.startswith("__Host-access_token=") for c in r.headers.get_list("set-cookie")
    ), f"switch-tenant no reemitió la cookie: {r.headers.get_list('set-cookie')}"


# ---------------------------------------------------------------------------
# §2 — El API acepta la cookie
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_asvs323_la_cookie_autentica_sin_cabecera(client, db_session):
    """Sin esto el navegador se queda fuera y el cambio se revierte en una hora.

    Se comprueba con el frasco de cookies del propio cliente: inicia sesión, y
    la siguiente petición va **sin** `Authorization`.
    """
    await _usuario(db_session, "2")

    r = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "tok2@acme.example.com", "password": "Zx9-Correcta-Larga!"},
    )
    assert r.status_code == 200, r.text

    # Ni una cabecera: solo la cookie que el cliente guardó del login.
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 200, (
        f"La cookie no autentica: {r.status_code} {r.text}. "
        f"Cookies del cliente: {dict(client.cookies)}"
    )
    assert r.json()["email"] == "tok2@acme.example.com"


@pytest.mark.asyncio
async def test_asvs323_sin_cookie_ni_cabecera_no_se_entra(client):
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_asvs323_una_cookie_falsificada_no_entra(client, db_session):
    """La cookie no es una llave de paso: sigue siendo un JWT firmado."""
    await _usuario(db_session, "3")
    client.cookies.set("access_token", "no.soy.un.token")
    try:
        r = await client.get("/api/v1/auth/me")
        assert r.status_code == 401
    finally:
        client.cookies.clear()


# ---------------------------------------------------------------------------
# §3 — `Authorization` sigue valiendo para lo que no es un navegador
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_asvs323_la_cabecera_sigue_funcionando(client, db_session):
    """El SDK y las integraciones de servidor a servidor no son un navegador y
    no tienen el problema que esto resuelve. Romperlas sería cambiar un agujero
    por una avería."""
    from tests.factories import login

    await _usuario(db_session, "4")
    sesion = await login(client, "tok4@acme.example.com", "Zx9-Correcta-Larga!")
    client.cookies.clear()  # como un cliente que no guarda cookies

    r = await client.get("/api/v1/auth/me", headers=sesion["_authz"])
    assert r.status_code == 200, r.text
    assert r.json()["email"] == "tok4@acme.example.com"


@pytest.mark.asyncio
async def test_asvs323_la_cabecera_gana_a_la_cookie(client, db_session):
    """Quien manda `Authorization` a propósito está diciendo con qué identidad
    quiere operar. Que ganara una cookie que el navegador arrastra sería
    sorprendente — y en una herramienta de depuración, confuso."""
    from tests.factories import login

    await _usuario(db_session, "5")
    await _usuario(db_session, "6")
    # La sesión de tok5 queda en las cookies del cliente…
    await login(client, "tok5@acme.example.com", "Zx9-Correcta-Larga!")
    # …y se manda la cabecera de tok6.
    sesion6 = await login(client, "tok6@acme.example.com", "Zx9-Correcta-Larga!")
    client.cookies.clear()
    await client.post(
        "/api/v1/auth/login",
        json={"identifier": "tok5@acme.example.com", "password": "Zx9-Correcta-Larga!"},
    )

    r = await client.get("/api/v1/auth/me", headers=sesion6["_authz"])
    assert r.status_code == 200
    assert r.json()["email"] == "tok6@acme.example.com", (
        "Ganó la cookie sobre la cabecera explícita"
    )


# ---------------------------------------------------------------------------
# §4 — Cerrar sesión borra la cookie
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_asvs323_el_logout_borra_la_cookie_de_acceso(client, db_session):
    """Una sesión que sobrevive a «salir» es peor que la de `localStorage`:
    encima no se puede borrar desde el propio navegador.

    **Sin forzar `production` a propósito.** Con el prefijo puesto la cookie
    sale `Secure`, y el cliente de pruebas habla `http://`, así que no la
    devolvería: el `logout` llegaría sin sesión y la prueba mediría el 401 en
    vez del borrado. Los atributos del prefijo los fija
    `test_seg01_asvs344_cookie_host.py`; aquí lo que importa es que se borre.
    """
    await _usuario(db_session, "7")
    r = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "tok7@acme.example.com", "password": "Zx9-Correcta-Larga!"},
    )
    assert r.status_code == 200

    r = await client.post("/api/v1/auth/logout")
    assert r.status_code == 204, r.text

    borradas = [
        c for c in r.headers.get_list("set-cookie")
        if "access_token" in c
        and ("max-age=0" in c.lower() or "01 jan 1970" in c.lower())
    ]
    assert borradas, (
        f"El cierre de sesión no borró la cookie de acceso: "
        f"{r.headers.get_list('set-cookie')}"
    )


# ---------------------------------------------------------------------------
# §5 — El navegador ya no guarda el token (lado web)
# ---------------------------------------------------------------------------


def test_asvs822_el_front_no_escribe_el_token_en_localstorage():
    """Trinquete sobre el código de la web.

    El cambio de verdad no está en el API sino en que el navegador **deje de
    guardarlo**, y eso no lo puede comprobar ninguna prueba de este proceso. Lo
    que sí se puede es leer el código: `auth-storage.ts` no debe volver a
    escribir el token ni el perfil.
    """
    import pathlib
    import re

    raiz = pathlib.Path(__file__).resolve().parents[3]
    almacen = raiz / "apps" / "web" / "lib" / "auth-storage.ts"
    texto = almacen.read_text(encoding="utf-8")

    escrituras = re.findall(r"localStorage\.setItem\(\s*([A-Za-z_]+)", texto)
    assert set(escrituras) <= {"SESION_ABIERTA_KEY", "ACTIVE_TENANT_KEY"}, (
        f"`auth-storage.ts` escribe en localStorage algo nuevo: {escrituras}. "
        f"Solo pueden ir ahí el indicador de sesión —que no autoriza nada— y el "
        f"inquilino activo, que el servidor vuelve a comprobar en cada petición."
    )

    # Y que nadie vuelva a componer el token a mano en el resto de la web.
    web = raiz / "apps" / "web"
    # `auth-storage.ts` se excluye de la búsqueda del nombre de la clave: la
    # cita a propósito, en `CLAVES_RETIRADAS`, para **borrarla** del navegador
    # de quien ya tenía sesión.
    culpables = [
        str(p.relative_to(raiz))
        for p in web.rglob("*.ts*")
        if "node_modules" not in p.parts and ".next" not in p.parts and p != almacen
        and re.search(r"Bearer \$\{token\}|pmoaas\.access_token", p.read_text(encoding="utf-8"))
    ]
    assert not culpables, f"Vuelve a haber token en el navegador: {culpables}"
