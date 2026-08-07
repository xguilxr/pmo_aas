"""REQ-02 — los cuatro escenarios de calidad, con su medida y sin inventarla.

«DEBEN definirse al menos cuatro escenarios de calidad con medida de respuesta
numérica».

La primera versión de `08-ESCENARIOS-CALIDAD.md` declaraba uno y dejaba tres
pendientes «a falta de dato de producción». La postura era correcta —declarar
cuatro con números inventados cierra el requisito y no mejora el producto— y el
atasco también.

Lo desatascó volver a leer el requisito: **pide una medida de respuesta
numérica, no un percentil de latencia.** El producto ya hacía cumplir tres
números que nadie había escrito como escenario — el tope del análisis de un
plan, la ventana de pérdida de la copia diaria y el retardo creciente del inicio
de sesión.

Son mejores que un P95 improvisado por dos motivos: **ya se cumplen** —el código
los impone— y **se comprueban sin esperar tráfico**, que es lo que hace este
archivo.

## Lo que se comprueba y lo que no

Se comprueba que **el número del documento sea el número del código**. Es la
mitad que se pudre sola: alguien sube el tope de 60 a 120 segundos por una
razón buena y el escenario sigue prometiendo 60, sin que nada avise.

No se comprueba la disponibilidad de E-1: la mide quien observa el servicio
desde fuera, y ninguna prueba de este repositorio puede hacerlo. Queda dicho en
el propio documento.
"""
from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
DOC = RAIZ / "docs" / "dominio" / "08-ESCENARIOS-CALIDAD.md"


def _texto() -> str:
    return DOC.read_text(encoding="utf-8")


def test_hay_al_menos_cuatro_escenarios() -> None:
    """La cifra literal del requisito, contada sobre el documento."""
    escenarios = re.findall(r"^## E-\d+ — ", _texto(), re.M)
    assert len(escenarios) >= 4, (
        f"El documento declara {len(escenarios)} escenarios y REQ-02 pide "
        f"cuatro. Uno menos y el requisito vuelve a estar abierto."
    )


def test_cada_escenario_declara_las_cuatro_partes() -> None:
    """Estímulo, entorno, respuesta y medida. Sin medida no es un escenario.

    Se comprueba por escenario y no sobre el archivo entero: con una búsqueda
    global, tres escenarios completos taparían a un cuarto vacío — el mismo
    error de medida que tuvo el barrido de DIS-03.
    """
    texto = _texto()
    bloques = re.split(r"^## E-\d+ — ", texto, flags=re.M)[1:]
    assert bloques
    for bloque in bloques:
        titulo = bloque.splitlines()[0]
        cuerpo = bloque.split("\n## ")[0]
        for parte in ("Atributo", "Estímulo", "Entorno", "Respuesta", "Medida"):
            assert f"**{parte}**" in cuerpo, (
                f"El escenario «{titulo}» no declara «{parte}»."
            )
        medida = next(
            (l for l in cuerpo.splitlines() if l.startswith("| **Medida**")), ""
        )
        assert re.search(r"\d", medida), (
            f"La medida de «{titulo}» no tiene ningún número: «{medida}». "
            f"REQ-02 pide medida de respuesta NUMÉRICA; sin cifra es un deseo."
        )


def test_e2_promete_el_tope_que_el_codigo_impone() -> None:
    """El escenario del análisis de plan cita `MPP_PARSE_TIMEOUT_SECONDS`.

    Si alguien sube el tope por una razón buena, el documento tiene que
    enterarse. Un escenario que promete 60 s sobre un proceso que ahora admite
    120 es peor que no tenerlo: da por medido lo que dejó de serlo.
    """
    from app.core.config import settings

    tope = settings.MPP_PARSE_TIMEOUT_SECONDS
    assert tope > 0
    assert f"{tope} s" in _texto(), (
        f"El código impone {tope} s de tope al análisis de un plan y el "
        f"escenario E-2 no dice ese número."
    )
    assert "MPP_PARSE_TIMEOUT_SECONDS" in _texto(), (
        "El escenario no cita el ajuste que lo impone, así que nadie sabe "
        "dónde mirar para comprobarlo."
    )


def test_e3_promete_la_ventana_que_la_copia_sostiene() -> None:
    """RPO, retención y tope del volcado, los tres del servicio de copias."""
    from app.services.respaldo import RETENCION_DIAS, TIEMPO_MAXIMO_SEGUNDOS

    texto = _texto()
    assert f"retención {RETENCION_DIAS} días" in texto, (
        f"La copia conserva {RETENCION_DIAS} días y el escenario dice otra "
        f"cosa. La retención acota hasta cuándo se puede volver: un borrado "
        f"descubierto después ya no tiene copia."
    )
    assert f"{TIEMPO_MAXIMO_SEGUNDOS} s" in texto, (
        f"El volcado se aborta a los {TIEMPO_MAXIMO_SEGUNDOS} s y el escenario "
        f"no lo dice."
    )
    assert "RPO ≤ 24 h" in texto and "03:30 UTC" in texto, (
        "Falta la ventana de pérdida máxima o la hora que la sostiene. El RPO "
        "de este escenario ES la periodicidad de la copia."
    )


def test_e4_promete_el_retardo_que_el_inicio_de_sesion_aplica() -> None:
    """Los cuatro números de la política de intentos fallidos."""
    from app.api.v1.endpoints.auth import _LOGIN_MAX_FAILS_PER_HOUR_IP
    from app.core.config import settings

    texto = _texto()
    for numero, que in (
        (settings.MAX_FAILED_LOGIN_ATTEMPTS, "el intento a partir del cual empieza el retardo"),
        (settings.LOGIN_BACKOFF_BASE_SECONDS, "la base del retardo"),
        (settings.LOGIN_BACKOFF_MAX_SECONDS, "el tope del retardo"),
        (_LOGIN_MAX_FAILS_PER_HOUR_IP, "el máximo de fallos por hora y por IP"),
    ):
        assert re.search(rf"\*\*{numero}\b|\b{numero} s\b|\b{numero} fallos", texto), (
            f"El escenario E-4 no declara {que} ({numero}), que es lo que el "
            f"código aplica."
        )
    assert "sin dejar a nadie fuera" in texto, (
        "Falta la parte que distingue esta política del bloqueo fijo anterior: "
        "quien tecleó mal espera segundos, no minutos, y nadie puede dejar "
        "fuera a una cuenta ajena a propósito."
    )


def test_lo_que_falta_esta_declarado_como_falta() -> None:
    """Los percentiles siguen abiertos, y eso se dice en vez de rellenarse.

    Es la mitad honesta del cierre: REQ-02 pide cuatro y hay cuatro, pero el
    análisis de rendimiento con dato real no se ha hecho. Darlo por hecho
    sería la conformidad de papel que este expediente lleva seis recuentos
    evitando.
    """
    texto = _texto()
    assert "Lo que queda abierto" in texto
    # Se mira DENTRO de la sección, no en todo el archivo: «P95» aparece
    # también en la prosa que explica por qué no está, y buscarlo suelto haría
    # que la explicación tapara la desaparición de la deuda. La mutación de
    # borrar la fila pasaba en verde por eso.
    seccion = texto[texto.index("## Lo que queda abierto") :]
    seccion = seccion.split("\n## ")[0]
    for pendiente in ("P95", "Latencia del tablero", "Capacidad por inquilino"):
        assert pendiente in seccion, (
            f"«{pendiente}» dejó de figurar en la tabla de pendientes. O se "
            f"resolvió —y entonces es un escenario más— o se borró la deuda "
            f"sin pagarla."
        )
    assert "no en lugar de ninguno" in texto or "no en lugar de" in texto, (
        "Falta la promesa de que los percentiles se AÑADEN y no sustituyen a "
        "los cuatro declarados."
    )
