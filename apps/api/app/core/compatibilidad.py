"""Las ventanas de compatibilidad abiertas, y cómo saber cuándo cerrarlas.

Los renombrados de vocabulario del glosario —D-2 (`support` → `hypercare`), D-8
(`portfolio_function` → `discipline`) y el que viene, D-3— salen con una
**ventana**: el API sigue aceptando el nombre viejo a la entrada para no romper
una pestaña abierta desde antes del despliegue, un filtro guardado o el script
de un cliente.

El problema de una ventana no es abrirla, es que **nadie decide cuándo se
cierra**. Sin fecha ni criterio se vuelve permanente, y entonces cada renombrado
deja una traducción para siempre — deuda con apariencia de solución.

**Decisión del owner (2026-08-05): instrumentar y cerrar con dato**, no con
corazonada ni con fecha inventada. Cada vez que llega un nombre retirado se deja
rastro; a los dos meses se mira el contador. En cero, se quita la ventana. Si no,
al menos se sabe **quién** la usa antes de romperle nada.

Cómo se cuenta, en los registros o en Sentry:

    compat.nombre_viejo

Todas las líneas llevan ese prefijo, el campo viejo, el nuevo y dónde entró.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

log = logging.getLogger("pmoaas.compat")


@dataclass(frozen=True)
class Ventana:
    """Un nombre retirado que todavía se acepta a la entrada."""

    viejo: str
    nuevo: str
    desde: date
    adr: str


#: Las ventanas abiertas. **Se añade una fila al abrir cada ventana**, no
#: después: una ventana sin declarar es exactamente la que nadie recuerda cerrar.
#: `tests/test_ventanas_compatibilidad.py` comprueba que cada `registrar_uso`
#: del código tenga la suya.
VENTANAS: dict[str, Ventana] = {
    "phase=support": Ventana(
        viejo="phase=support", nuevo="phase=hypercare",
        desde=date(2026, 8, 5), adr="ADR-019",
    ),
    "portfolio_function": Ventana(
        viejo="portfolio_function", nuevo="discipline",
        desde=date(2026, 8, 5), adr="ADR-021",
    ),
}


def registrar_uso(clave: str, *, donde: str) -> None:
    """Deja rastro de que alguien usó el nombre retirado `clave`.

    `donde` dice por qué puerta entró —«cuerpo de creación», «parámetro de
    consulta»— porque una ventana puede tener varias y no siempre se cierran a
    la vez: el cuerpo lo manda un cliente que se actualiza; un enlace guardado
    en un marcador puede sobrevivir años.

    Nunca lanza. Una ventana de compatibilidad que rompe la petición que venía
    a salvar sería peor que no tenerla.
    """
    ventana = VENTANAS.get(clave)
    if ventana is None:
        # Nombre retirado sin declarar. Se registra igual —el dato vale— y el
        # trinquete de la suite se encargará de que alguien lo declare.
        log.info("compat.nombre_viejo campo=%s nuevo=? donde=%s adr=?", clave, donde)
        return
    log.info(
        "compat.nombre_viejo campo=%s nuevo=%s donde=%s adr=%s desde=%s",
        ventana.viejo, ventana.nuevo, donde, ventana.adr, ventana.desde.isoformat(),
    )
