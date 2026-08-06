"""Catálogo de errores de la API.

**MCS LEN-02** — «Todo mensaje de error DEBE indicar qué ocurrió, por qué y qué
acción tomar.» La auditoría R1 lo dejó en PARCIAL: el envoltorio
—`{detail, code, fields}`— y los constructores estaban bien, y se usan en 75
sitios; lo que fallaba era el texto. Los valores por defecto decían solo qué
pasó: «Credenciales inválidas», «Acceso denegado», «{entidad} no encontrado».

Por eso las tres partes viven aquí como **datos y no como prosa**. Un texto
corrido cumple el requisito el día que se escribe y deja de cumplirlo en la
primera edición, sin que nada avise. Un `MensajeDeError` con tres campos no se
puede rellenar a medias: falta uno y `tests/test_len02_mensajes_de_error.py`
falla. Es la diferencia entre redactar bien una vez y que siga bien dentro de un
año.

Los constructores que **exigen** `detail` (`conflict`, `validation_error`,
`business_rule`, `service_unavailable`) no llevan defecto a propósito: un texto
genérico para una regla de negocio sería peor que ninguno, porque el sitio que
la lanza es el único que sabe qué se violó.
"""
from dataclasses import dataclass

from fastapi import HTTPException, status


@dataclass(frozen=True)
class MensajeDeError:
    """Las tres partes que LEN-02 exige, por separado.

    Se guardan sueltas y se unen al usarse. Guardar la frase ya montada
    ahorraría cuatro líneas y perdería lo único que hace verificable el
    requisito: poder mirar cada parte y comprobar que está.
    """

    que: str
    porque: str
    accion: str

    def texto(self, **campos: object) -> str:
        return " ".join(
            parte.format(**campos) for parte in (self.que, self.porque, self.accion)
        )


#: Los defectos del catálogo, indexados por el `code` que viaja al cliente.
#: El cliente reacciona por `code`; el texto es para quien lo lee.
DEFECTOS: dict[str, MensajeDeError] = {
    "UNAUTHENTICATED": MensajeDeError(
        que="No pudimos verificar tu identidad.",
        # Sin distinguir «usuario inexistente» de «contraseña incorrecta»: esa
        # distinción le confirma a quien prueba credenciales qué cuentas
        # existen.
        porque="El usuario o la contraseña no coinciden, o la sesión expiró.",
        accion="Vuelve a iniciar sesión; si no lo consigues, usa «¿Olvidaste tu contraseña?».",
    ),
    "FORBIDDEN": MensajeDeError(
        que="Tu cuenta no tiene permiso para esta acción.",
        porque="El acceso depende del rol que tengas asignado en la organización.",
        accion="Si necesitas hacerlo, pídeselo al administrador de tu organización.",
    ),
    "NOT_FOUND": MensajeDeError(
        # Dos puntos y no «No encontramos {entidad}»: los 25 sitios que llaman
        # a `not_found` pasan el nombre en mayúscula y sin artículo
        # («Documento», «Minuta»). Con esta forma leen bien tal como están, en
        # vez de exigir tocarlos todos para que concuerde el género.
        que="No encontramos: {entidad}.",
        # El aislamiento entre inquilinos devuelve 404 —no 403— ante algo de
        # otra organización, así que ese caso también cae aquí y conviene que
        # el texto lo contemple.
        porque="Puede que se haya eliminado, o que pertenezca a otra organización.",
        accion="Verifica el enlace o vuelve al listado.",
    ),
    "RATE_LIMITED": MensajeDeError(
        que="Bloqueamos temporalmente los intentos desde tu conexión.",
        # Sin decir cuántos intentos quedan ni cuándo empezó la ventana: eso le
        # da a quien prueba credenciales la información para ir justo por
        # debajo del umbral.
        porque="Se hicieron demasiados en poco tiempo.",
        accion="Espera una hora y vuelve a intentarlo; si no fuiste tú, avisa al administrador de tu organización.",
    ),
    "INTERNAL_SERVER_ERROR": MensajeDeError(
        que="La operación no se completó por un fallo de nuestro lado.",
        porque="El error quedó registrado con su detalle; no es algo que puedas corregir tú.",
        accion="Vuelve a intentarlo en unos minutos; si sigue igual, avísanos indicando la hora.",
    ),
}


def texto_por_defecto(code: str, **campos: object) -> str:
    """Texto de catálogo para `code`, con sus huecos rellenos."""
    return DEFECTOS[code].texto(**campos)


def mensaje(*, que: str, porque: str, accion: str) -> str:
    """Las tres partes de LEN-02, escritas donde se sabe qué pasó.

    Los defectos de `DEFECTOS` cubren los cinco casos genéricos. Los **201
    mensajes explícitos** del código son otra cosa: una regla de negocio la
    conoce el sitio que la viola, y un catálogo central acabaría con 201
    entradas que nadie encuentra.

    Esto da la misma garantía sin el catálogo: **son tres argumentos con
    nombre y ninguno tiene defecto**, así que no se puede rellenar dos de tres.
    Un `f"No puedes borrar un super admin"` cumple el requisito a medias y
    nada avisa; esto no compila si falta el porqué.

    `scripts/check_mensajes.py` vigila lo otro — que un sitio nuevo no vuelva a
    pasar una cadena suelta. El pasivo heredado va en su línea base, y solo
    puede encoger.
    """
    return " ".join((que, porque, accion))


class AppError(HTTPException):
    def __init__(self, status_code: int, code: str, detail: str, fields: dict | None = None):
        super().__init__(status_code=status_code, detail={"detail": detail, "code": code, "fields": fields or {}})


def unauthorized(code: str = "UNAUTHENTICATED", detail: str | None = None) -> AppError:
    return AppError(
        status.HTTP_401_UNAUTHORIZED,
        code,
        detail if detail is not None else texto_por_defecto("UNAUTHENTICATED"),
    )


def forbidden(code: str = "FORBIDDEN", detail: str | None = None) -> AppError:
    return AppError(
        status.HTTP_403_FORBIDDEN,
        code,
        detail if detail is not None else texto_por_defecto("FORBIDDEN"),
    )


def not_found(entity: str) -> AppError:
    return AppError(
        status.HTTP_404_NOT_FOUND,
        "NOT_FOUND",
        texto_por_defecto("NOT_FOUND", entidad=entity),
    )


def rate_limited(detail: str | None = None) -> AppError:
    """429 — el llamador superó su cuota (AM-09).

    Es el código correcto y no lo había: `/auth/reset-password` devolvía un 422
    con `code="RATE_LIMITED"`, que le dice a un cliente que su cuerpo está mal
    cuando lo que pasa es que fue demasiado rápido.
    """
    return AppError(
        status.HTTP_429_TOO_MANY_REQUESTS,
        "RATE_LIMITED",
        detail if detail is not None else texto_por_defecto("RATE_LIMITED"),
    )


def conflict(
    detail: str, code: str = "CONFLICT", fields: dict | None = None
) -> AppError:
    return AppError(status.HTTP_409_CONFLICT, code, detail, fields)


def validation_error(detail: str, fields: dict | None = None) -> AppError:
    return AppError(status.HTTP_400_BAD_REQUEST, "VALIDATION_ERROR", detail, fields)


def business_rule(detail: str, code: str = "BUSINESS_RULE") -> AppError:
    return AppError(status.HTTP_422_UNPROCESSABLE_ENTITY, code, detail)


def service_unavailable(
    detail: str, code: str = "SERVICE_UNAVAILABLE"
) -> AppError:
    return AppError(status.HTTP_503_SERVICE_UNAVAILABLE, code, detail)
