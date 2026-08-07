"""Cookies de sesión: cómo se nombran, se fijan y se borran.

MCS SEG-01 · **ASVS 3.4.4** — «Verify that cookie-based session tokens use the
`__Host-` prefix so cookies are only sent to the host that initially set the
cookie».

## Qué compra el prefijo

`__Host-` no es decoración: el navegador **rechaza** la cookie si no cumple las
tres condiciones a la vez —`Secure`, sin `Domain`, y `Path=/`—. Y como las
impone el navegador y no el servidor, cierran un ataque que ninguna comprobación
nuestra alcanza: un subdominio comprometido (`blog.pmo-aas.com`, un panel de un
proveedor, cualquier cosa que cuelgue del dominio) **no puede sobrescribir** una
cookie `__Host-` del dominio padre. Sin el prefijo sí puede, y ahí es donde vive
la fijación de sesión: el atacante te planta su cookie de refresco y tu sesión
pasa a ser la suya.

## Por qué el nombre depende del entorno

`__Host-` exige `Secure`, y `Secure` exige HTTPS. En desarrollo se sirve por
HTTP: una cookie `__Host-` ahí **no se guardaría**, y el desarrollo se rompería
con un fallo que no dice por qué. Así que el prefijo se pone exactamente cuando
se puede poner `Secure` —en producción—, que es la misma condición que ya
gobernaba `secure=` antes de esto. Fuera de producción la cookie se llama como
se llamaba.

Se resuelve en un módulo y no en el endpoint porque hay más de una cookie de
sesión y las tres operaciones —fijar, leer, borrar— tienen que estar de acuerdo
sobre el nombre. Cuando no lo están, el síntoma es una sesión que no se cierra
al pulsar «salir».

## La ventana de compatibilidad

Al desplegar esto, los navegadores de quien ya tenía sesión traen la cookie
vieja: nombre sin prefijo y `Path=/api/v1/auth`. `leer` acepta las dos y anota
por cuál entró; `borrar` borra las dos, con los dos `Path`, porque una cookie
solo se borra desde el `Path` que la creó —y una cookie de refresco que
sobrevive a un «cerrar sesión» es exactamente lo que no puede pasar—.
"""
from __future__ import annotations

from fastapi import Request, Response

from app.core.compatibilidad import registrar_uso
from app.core.config import settings

#: Cookie de refresco. El nombre base; el prefijo lo pone `nombre`.
REFRESCO = "refresh_token"

#: Cookie de acceso (ASVS 3.2.3 / 8.2.2, ADR-033). Antes el token de acceso
#: vivía en `localStorage`, donde cualquier guion inyectado —propio o de una
#: dependencia de npm— lo lee con una línea. `HttpOnly` no hace mejor al token:
#: hace que el guion no pueda leerlo.
ACCESO = "access_token"

#: Equipo de confianza (ASVS 4.3.1, ADR-035). Dura una semana, no una sesión:
#: su razón de ser es sobrevivir a cerrar sesión, que es cuando el código
#: volvería a pedirse. Por eso `borrar` en el cierre de sesión NO la toca.
DISPOSITIVO = "dispositivo"

#: `Path` con el que se creaba la cookie de refresco antes de ASVS 3.4.4.
#: Se conserva **solo** para poder borrarla: `__Host-` obliga a `Path=/`.
_PATH_LEGADO = "/api/v1/auth"


def con_prefijo_host() -> bool:
    """¿Puede el navegador aceptar hoy una cookie `__Host-`?

    Solo si se emite `Secure`, y `Secure` solo se sostiene sobre HTTPS. Es la
    misma condición que gobernaba `secure=` antes de este módulo, escrita una
    vez en lugar de en cada endpoint.
    """
    return settings.PYTHON_ENV == "production"


def nombre(base: str) -> str:
    """Nombre real de la cookie `base` en este entorno."""
    return f"__Host-{base}" if con_prefijo_host() else base


def fijar(respuesta: Response, base: str, valor: str, *, max_age: int) -> None:
    """Emite la cookie con los atributos que `__Host-` exige.

    `path="/"` y sin `domain` no son configurables a propósito: son dos de las
    tres condiciones del prefijo, y dejarlas abiertas permitiría emitir una
    cookie llamada `__Host-…` que el navegador tira sin decir nada.
    """
    respuesta.set_cookie(
        nombre(base),
        valor,
        httponly=True,
        secure=con_prefijo_host(),
        samesite="strict",
        max_age=max_age,
        path="/",
    )


def leer(peticion: Request, base: str) -> str | None:
    """Devuelve la cookie `base`, aceptando el nombre anterior por la ventana.

    El orden importa: primero el nombre vigente. Si un navegador trae los dos
    —porque inició sesión antes del despliegue y volvió a iniciarla después—,
    el bueno es el nuevo.
    """
    valor = peticion.cookies.get(nombre(base))
    if valor is not None:
        return valor
    if not con_prefijo_host():
        return None
    heredada = peticion.cookies.get(base)
    if heredada is None:
        return None
    # Solo la de refresco existía antes del prefijo, así que es la única que
    # puede llegar con el nombre viejo desde un navegador real. La clave va
    # literal —y no compuesta— porque el trinquete de
    # `test_ventanas_compatibilidad.py` lee el código, no lo ejecuta.
    if base == REFRESCO:
        registrar_uso("cookie:refresh_token", donde="cookie de sesión sin prefijo")
    return heredada


def borrar(respuesta: Response, base: str) -> None:
    """Borra la cookie en todas las formas que pueda tener en un navegador.

    Son tres: la vigente, y la anterior con su `Path` propio. Una cookie solo se
    borra desde el `Path` con que se creó, así que un `delete_cookie` a secas
    dejaría viva la de `/api/v1/auth` —y una cookie de refresco que sobrevive a
    «cerrar sesión» es lo que este módulo existe para impedir—.
    """
    respuesta.delete_cookie(nombre(base), path="/")
    if con_prefijo_host():
        respuesta.delete_cookie(base, path="/")
    respuesta.delete_cookie(base, path=_PATH_LEGADO)
