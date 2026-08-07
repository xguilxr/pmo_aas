"""MCS SEG-01 · ASVS 4.3.1 — segundo factor para las interfaces de administración.

«Verify administrative interfaces use appropriate multi-factor authentication to
prevent unauthorized use.»

Decisión del owner (2026-08-07), ADR-035: **código de seis dígitos por correo**,
con la infraestructura de Resend que ya existe. Sin dependencia nueva, sin
enrolamiento previo y sin que nadie tenga que instalar una aplicación.

## Lo que este factor sí resuelve

La amenaza realista contra una cuenta de administración no es alguien que
intercepta un correo: es una contraseña reutilizada que aparece en una
filtración, o adivinada. Contra eso, pedir algo que solo llega al buzón de la
persona es una barrera real — el atacante necesita además la cuenta de correo.

## Lo que NO resuelve, y va escrito

El correo es un factor **débil**. NIST 800-63B §5.1.3.1 dice que no debe usarse
para autenticación fuera de banda, porque no demuestra posesión de un
dispositivo: quien controle el buzón —o el proveedor de correo— completa el
segundo paso. Por eso `2.7.1` queda **ACEPTADO** y no CUMPLE: ese control pide
ofrecer primero una alternativa más fuerte, y aquí no hay ninguna que ofrecer.

Escribirlo es la diferencia entre un residual aceptado y uno escondido.

## Los tres requisitos que el correo activa

Al añadir un factor fuera de banda dejan de «no aplicar» tres controles, y los
tres imponen algo concreto que este módulo cumple por construcción:

* **2.7.2** — caduca a los diez minutos. `VIDA_MINUTOS = 10`, y no es
  configurable: subirlo es exactamente lo que alguien haría para que «no
  molestara».
* **2.7.3** — un solo uso, y **solo para la petición que lo pidió**. Eso es
  `desafio`: sin él, un código pedido en una pestaña serviría para completar el
  inicio de sesión que otra persona empezó en otra parte.
* **2.7.4** — canal independiente. El correo sale por HTTPS a Resend y llega por
  el buzón de la persona, que es un canal distinto del navegador donde escribió
  la contraseña.

## Por qué se limitan los intentos

Seis dígitos es un millón de combinaciones, y eso se prueba entero en minutos
contra un endpoint sin freno. `INTENTOS_MAXIMOS` es lo que convierte el código
en un factor: sin él, el segundo paso se salta por fuerza bruta más rápido que
el primero.
"""
from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import AdminOtpCode
from app.models.user import User

log = logging.getLogger(__name__)

#: ASVS 2.7.2, literal. No es configurable a propósito.
VIDA_MINUTOS = 10

#: Seis dígitos: lo que cabe en la cabeza entre el correo y el formulario. La
#: entropía la aporta el límite de intentos, no la longitud.
DIGITOS = 6

#: Tras esto el desafío muere. Cinco deja margen a teclear mal y no deja margen
#: a probar un millón.
INTENTOS_MAXIMOS = 5


def _resumen(codigo: str) -> str:
    return hashlib.sha256(codigo.encode("utf-8")).hexdigest()


def necesita_segundo_factor(user: User) -> bool:
    """¿Esta cuenta llega a una interfaz de administración?

    El control habla de «administrative interfaces», así que se exige a quien
    puede alcanzarlas: superadministradores y cuentas con rol equivalente a
    administrador. A un usuario normal no se le pide —no tendría nada que
    proteger con ello y sería fricción a cambio de nada.
    """
    if user.is_superadmin:
        return True
    return getattr(user, "role_type", None) in {"admin", "pm_sr"}


async def emite(db: AsyncSession, *, user: User) -> tuple[str, str]:
    """Crea un desafío y su código. Devuelve `(desafio, codigo_en_claro)`.

    El código en claro sale de aquí una sola vez, para el correo; en la base
    solo queda su resumen.
    """
    desafio = secrets.token_urlsafe(24)
    codigo = f"{secrets.randbelow(10**DIGITOS):0{DIGITOS}d}"
    db.add(
        AdminOtpCode(
            desafio=desafio,
            code_hash=_resumen(codigo),
            user_id=user.id,
            expires_at=datetime.now(UTC) + timedelta(minutes=VIDA_MINUTOS),
        )
    )
    await db.flush()
    return desafio, codigo


async def verifica(db: AsyncSession, *, desafio: str, codigo: str) -> User | None:
    """Consume el desafío. Devuelve el usuario si el código es correcto.

    `None` para **todos** los motivos de fallo —no existe, caducó, ya se usó,
    código incorrecto, demasiados intentos— y es deliberado: distinguirlos le
    diría a quien prueba si va por buen camino.

    El intento se cuenta **antes** de comparar, y el contador se persiste aunque
    la comparación falle. Contarlo después dejaría la puerta abierta a probar sin
    coste si la comparación lanza.
    """
    fila = (
        await db.execute(select(AdminOtpCode).where(AdminOtpCode.desafio == desafio))
    ).scalar_one_or_none()
    if fila is None or fila.used_at is not None:
        return None

    caduca = fila.expires_at
    if caduca is not None and caduca.tzinfo is None:
        caduca = caduca.replace(tzinfo=UTC)
    if caduca is None or caduca < datetime.now(UTC):
        return None

    if fila.intentos >= INTENTOS_MAXIMOS:
        return None

    fila.intentos += 1
    if not secrets.compare_digest(fila.code_hash, _resumen(codigo)):
        await db.flush()
        return None

    fila.used_at = datetime.now(UTC)
    return (
        await db.execute(select(User).where(User.id == str(fila.user_id)))
    ).scalar_one_or_none()


def cuerpo_del_correo(codigo: str) -> str:
    """El texto que recibe la persona.

    Dice el código, cuánto dura y qué hacer si no fue ella — esto último es lo
    que convierte el correo en una alerta de intrusión además de un factor: si
    alguien tiene la contraseña, este mensaje es lo primero que avisa.
    """
    return (
        f"Tu código para entrar es {codigo}. Caduca en {VIDA_MINUTOS} minutos y "
        f"solo sirve una vez.\n\n"
        f"Si no has intentado entrar, alguien tiene tu contraseña: cámbiala ahora "
        f"y avisa a quien administre tu organización."
    )


def anonimiza_referencias(user_id: UUID | str) -> None:
    """Marcador de que aquí no queda nada personal.

    Los códigos caducan solos a los diez minutos y solo guardan un resumen, así
    que la anonimización de `8.3.2` no tiene nada que limpiar en esta tabla.
    """
    return None


def envia_codigo(destino: str, codigo: str) -> None:
    """Manda el código por correo. **Nunca lanza.**

    Se reutiliza la tarea de avisos de seguridad: no pasa por la ventana de
    supresión ni por las preferencias de notificación, que es justo lo que hace
    falta — un segundo factor que alguien puede apagar desde sus ajustes no es un
    segundo factor.

    Si el envío falla, quien intenta entrar no recibe código y no entra. Es
    incómodo y es lo correcto: la alternativa sería dejarle pasar sin el segundo
    factor porque el correo no salió.
    """
    try:
        from app.workers.tasks.notifications import send_security_email

        send_security_email.delay(
            destino, "Tu código para entrar a PMO·aaS", cuerpo_del_correo(codigo)
        )
    except Exception:
        log.exception("no se pudo encolar el código de segundo factor")


