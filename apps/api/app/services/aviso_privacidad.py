"""MCS SEG-01 · ASVS 8.3.3 — qué se recoge, para qué, y que la persona lo acepte.

«Verify that users are provided clear language regarding collection and use of
supplied personal information and that users have provided opt-in consent for
the use of that data before it is used in any way.»

## Dónde va el consentimiento cuando no hay registro

En este producto **no existe el alta por autoservicio**: las cuentas las crea un
administrador del inquilino y la contraseña llega por correo. Así que el
consentimiento no cabe en un formulario de registro, porque no hay ninguno.

El sitio es el **primer inicio de sesión** —decisión del owner—, junto al cambio
de contraseña que ya se fuerza ahí. Es el primer momento en que la persona
existe frente a la plataforma y puede decir que sí o que no.

## Por qué se versiona, y no basta una fecha

Guardar solo «aceptó el 7 de agosto» responde *cuándo* y no *qué*. El día que
cambie lo que se recoge, no habría forma de saber a quién hay que volver a
preguntarle sin cruzar fechas a mano contra el historial del documento.

Con `VERSION` al lado, la pregunta se responde con una comparación: quien tenga
una versión distinta de la vigente vuelve a ver la pantalla. Es también lo que
pidió el owner —«y si hay algún cambio»— y lo que convierte el consentimiento
en algo vivo en vez de una casilla que se marcó una vez.

## Por qué el texto vive aquí y no en la base

Es parte del producto, no dato de un inquilino: cambia con el código, se revisa
en un PR y queda en `git log`. Un aviso de privacidad editable desde un panel es
un aviso del que nadie puede decir qué decía el martes pasado.

El contenido se deriva del inventario real de `docs/dominio/05-DATOS-PERSONALES.md`.
Si ese inventario cambia, **este texto cambia con él y sube de versión** — es la
misma regla que CLAUDE.md §0.2 aplica a las epics.
"""
from __future__ import annotations

from dataclasses import dataclass

#: Versión del aviso. **Se sube cuando cambia lo que se recoge o para qué**, no
#: cuando se corrige una tilde: cada subida hace que todo el mundo vuelva a ver
#: la pantalla, y un aviso que reaparece por nada enseña a aceptarlo sin leerlo.
VERSION = "2026-08-07"


@dataclass(frozen=True)
class Apartado:
    titulo: str
    cuerpo: str


#: El aviso, por apartados. En estructura y no en un bloque de texto para que la
#: pantalla pueda presentarlo legible sin volver a maquetarlo, y para que se vea
#: de un vistazo si un apartado se quedó vacío.
APARTADOS: tuple[Apartado, ...] = (
    Apartado(
        titulo="Qué se guarda de ti",
        cuerpo=(
            "Tu nombre, tu correo, tu nombre de usuario y el rol que tienes en tu "
            "organización. Además, el registro de lo que haces dentro de la "
            "plataforma —qué creaste, qué cambiaste y cuándo— con tu dirección IP "
            "y el navegador desde el que entraste."
        ),
    ),
    Apartado(
        titulo="Para qué se usa",
        cuerpo=(
            "Para que puedas entrar y para que la plataforma sepa qué puedes ver: "
            "PMO·aaS gestiona proyectos de tu organización, y quién hizo qué forma "
            "parte de esa gestión. El registro de actividad existe para poder "
            "reconstruir qué pasó ante un error o una disputa."
        ),
    ),
    Apartado(
        titulo="Quién lo ve",
        cuerpo=(
            "Las personas de tu propia organización, según su rol. Ningún otro "
            "cliente de la plataforma puede ver nada tuyo. El equipo que opera "
            "PMO·aaS accede solo para dar soporte, y ese acceso también queda "
            "registrado."
        ),
    ),
    Apartado(
        titulo="Qué NO se hace",
        cuerpo=(
            "No se vende tu información, no se usa para publicidad, y no se "
            "entrena ningún modelo de inteligencia artificial con ella. Cuando "
            "una función usa IA, el texto va al proveedor configurado por tu "
            "organización solo para resolver esa petición concreta."
        ),
    ),
    Apartado(
        titulo="Qué puedes hacer",
        cuerpo=(
            "Pedir una copia de todo lo que la plataforma guarda sobre ti, y "
            "pedir que se borre. Al borrarlo, tus datos personales se sustituyen "
            "por un marcador anónimo y el historial de los proyectos se conserva "
            "sin poder atribuirse a ti — es lo que permite atender tu petición "
            "sin romper la trazabilidad que tu organización necesita. Las dos "
            "cosas están en tu página de cuenta."
        ),
    ),
    Apartado(
        titulo="Cuánto se conserva",
        cuerpo=(
            "Mientras tu cuenta exista. El registro de actividad no se borra "
            "—es de solo añadir, por diseño— pero deja de apuntar a ti en cuanto "
            "pides la supresión."
        ),
    ),
)


def acepto_lo_vigente(version_aceptada: str | None) -> bool:
    """¿Esta persona aceptó **la versión que está en vigor**?

    `None` es «nunca aceptó» —cuentas anteriores al aviso—, y una versión
    distinta es «aceptó otra cosa». Los dos casos llevan a la misma pantalla, y
    eso es deliberado: desde el punto de vista del control no hay diferencia
    entre no haber consentido nunca y haber consentido a un texto que ya no es
    el que se aplica.
    """
    return version_aceptada == VERSION


def como_json() -> dict[str, object]:
    """El aviso tal y como lo consume la pantalla."""
    return {
        "version": VERSION,
        "apartados": [{"titulo": a.titulo, "cuerpo": a.cuerpo} for a in APARTADOS],
    }
