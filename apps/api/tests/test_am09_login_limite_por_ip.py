"""AM-09 · MCS SEG-01 — el inicio de sesión tiene límite por IP.

`docs/architecture/modelo-amenazas.md` AM-09: el bloqueo por cuenta detiene a
quien adivina la contraseña de **una** cuenta, y no hace nada contra el rociado
—una contraseña probada contra mil cuentas desde la misma IP, sin tocar el
umbral de ninguna—. El limitador ya existía y se aplicaba en recuperación y
reseteo de contraseña; faltaba justo en el login.

El detalle que decide el diseño: **se cuentan los fallos, no los intentos.** Una
oficina detrás de un NAT comparte IP, y si contáramos los aciertos se quedaría
fuera sin haber hecho nada. Las dos pruebas que fijan eso son
`test_los_aciertos_no_gastan_cuota` y `test_los_fallos_si_la_gastan`.

Redis se sustituye por un doble en memoria: la suite no levanta Redis, y con el
cliente real ausente el limitador abre fail-open y estas pruebas medirían el
fail-open en vez del límite.
"""
from __future__ import annotations

import pytest

from app.services import rate_limit


class RedisDeMentira:
    """Lo justo de la interfaz de Redis que usa `rate_limit`."""

    def __init__(self):
        self.valores: dict[str, int] = {}
        self.expiraciones: dict[str, int] = {}

    def incr(self, clave):
        self.valores[clave] = self.valores.get(clave, 0) + 1
        return self.valores[clave]

    def expire(self, clave, segundos):
        self.expiraciones[clave] = segundos

    def get(self, clave):
        valor = self.valores.get(clave)
        return None if valor is None else str(valor)

    def delete(self, clave):
        self.valores.pop(clave, None)


@pytest.fixture
def redis_falso(monkeypatch):
    doble = RedisDeMentira()
    monkeypatch.setattr(rate_limit, "_get_client", lambda: doble)
    return doble


async def _crear_usuario(db_session):
    """Un usuario real contra el que acertar. Devuelve `(identificador, clave)`."""
    from uuid import uuid4

    from tests.factories import create_tenant, create_user

    sufijo = uuid4().hex[:8]
    inquilino = await create_tenant(db_session, slug=f"am09{sufijo}", name="AM-09")
    clave = "Correcta-123!"
    usuario = await create_user(
        db_session,
        tenant=inquilino,
        username=f"am09_{sufijo}",
        email=f"am09_{sufijo}@ejemplo.test",
        password=clave,
    )
    return usuario.username, clave


@pytest.mark.asyncio
async def test_el_rociado_se_corta_al_llegar_al_umbral(client, redis_falso):
    """Mil cuentas distintas desde una IP: ninguna se bloquea, la IP sí."""
    from app.api.v1.endpoints.auth import _LOGIN_MAX_FAILS_PER_HOUR_IP

    cabeceras = {"x-forwarded-for": "203.0.113.7"}
    for i in range(_LOGIN_MAX_FAILS_PER_HOUR_IP):
        r = await client.post(
            "/api/v1/auth/login",
            json={"identifier": f"victima{i}@ejemplo.test", "password": "Verano2026!"},
            headers=cabeceras,
        )
        assert r.status_code == 401, f"intento {i} debería seguir siendo un 401"

    r = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "victima9999@ejemplo.test", "password": "Verano2026!"},
        headers=cabeceras,
    )
    assert r.status_code == 429
    assert r.json()["detail"]["code"] == "RATE_LIMITED"


@pytest.mark.asyncio
async def test_el_limite_es_por_ip_y_no_global(client, redis_falso):
    """Si fuera global, el primer atacante dejaría fuera a todo el producto."""
    from app.api.v1.endpoints.auth import _LOGIN_MAX_FAILS_PER_HOUR_IP

    for i in range(_LOGIN_MAX_FAILS_PER_HOUR_IP + 1):
        await client.post(
            "/api/v1/auth/login",
            json={"identifier": f"v{i}@ejemplo.test", "password": "x"},
            headers={"x-forwarded-for": "203.0.113.8"},
        )

    r = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "alguien@ejemplo.test", "password": "x"},
        headers={"x-forwarded-for": "198.51.100.4"},
    )
    assert r.status_code == 401, "otra IP no debería arrastrar el bloqueo"


@pytest.mark.asyncio
async def test_los_aciertos_no_gastan_cuota(client, db_session, redis_falso):
    """Una oficina tras un NAT comparte IP: si contáramos los éxitos, caería."""
    identificador, clave = await _crear_usuario(db_session)
    cabeceras = {"x-forwarded-for": "203.0.113.9"}

    for _ in range(5):
        r = await client.post(
            "/api/v1/auth/login",
            json={"identifier": identificador, "password": clave},
            headers=cabeceras,
        )
        assert r.status_code == 200

    assert redis_falso.valores.get("rl:login:ip:203.0.113.9") is None


@pytest.mark.asyncio
async def test_los_fallos_si_la_gastan(client, redis_falso):
    cabeceras = {"x-forwarded-for": "203.0.113.10"}

    for esperado in (1, 2, 3):
        await client.post(
            "/api/v1/auth/login",
            json={"identifier": "nadie@ejemplo.test", "password": "x"},
            headers=cabeceras,
        )
        assert redis_falso.valores["rl:login:ip:203.0.113.10"] == esperado


@pytest.mark.asyncio
async def test_la_ventana_caduca(client, redis_falso):
    """Sin EXPIRE el bloqueo sería permanente y el primer error, definitivo."""
    from app.api.v1.endpoints.auth import _WINDOW_SEC

    await client.post(
        "/api/v1/auth/login",
        json={"identifier": "nadie@ejemplo.test", "password": "x"},
        headers={"x-forwarded-for": "203.0.113.11"},
    )

    assert redis_falso.expiraciones["rl:login:ip:203.0.113.11"] == _WINDOW_SEC


@pytest.mark.asyncio
async def test_sin_redis_el_login_sigue_funcionando(client, db_session, monkeypatch):
    """Fail-open deliberado: no poder contar es mejor que nadie pueda entrar.

    Es la decisión que ya tomaba `rate_limit.py` para recuperación y reseteo, y
    el límite nuevo no la cambia — vale la pena que una prueba lo fije, porque
    es justo el tipo de comportamiento que un refactor «endurece» sin querer.
    """
    monkeypatch.setattr(rate_limit, "_get_client", lambda: None)
    identificador, clave = await _crear_usuario(db_session)

    r = await client.post(
        "/api/v1/auth/login",
        json={"identifier": identificador, "password": clave},
        headers={"x-forwarded-for": "203.0.113.12"},
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_el_mensaje_no_dice_cuantos_intentos_quedan(client, redis_falso):
    """Decirlo le da a quien prueba credenciales cómo ir bajo el umbral."""
    from app.api.v1.endpoints.auth import _LOGIN_MAX_FAILS_PER_HOUR_IP

    cabeceras = {"x-forwarded-for": "203.0.113.13"}
    for _ in range(_LOGIN_MAX_FAILS_PER_HOUR_IP + 1):
        r = await client.post(
            "/api/v1/auth/login",
            json={"identifier": "nadie@ejemplo.test", "password": "x"},
            headers=cabeceras,
        )

    texto = r.json()["detail"]["detail"]
    assert str(_LOGIN_MAX_FAILS_PER_HOUR_IP) not in texto
    # LEN-02: aun siendo un mensaje de seguridad, dice qué hacer.
    assert "Espera" in texto
