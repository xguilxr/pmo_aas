"""DAT-06 — un concepto, un término. El semáforo se dice `yellow`, y nada más.

> «NO DEBEN emplearse sinónimos ni adjetivos acumulados para designar un mismo
> concepto.»

El glosario ya había tomado la decisión y la había escrito (D-1, 2026-08-04):
el valor es **`yellow`**, `amber` queda **vetado**, y la UI dice «Amarillo».
RAG —*Red, Amber, Green*— es el término de P3O y PRINCE2, y este producto se
aparta de él a conciencia: `yellow` es el contrato de la API, la migración 0091
convirtió los datos, y los snapshots históricos ya guardan `health_yellow`.

Y aun así quedaban cinco restos, cuatro de ellos donde menos se miran:

- `reports/engine.py` **traducía `yellow` → `amber`** para hablarle a la
  plantilla. Ese es el mecanismo por el que un vocabulario retirado sobrevive
  para siempre: no se usa en el dominio, se reintroduce en el borde.
- `s-03.html` ponía `amber` de valor por defecto y, peor, **la etiqueta que ve
  el cliente decía «Ámbar»**. El sinónimo no estaba en el código: estaba en el
  PDF que se le manda al cliente.
- `base.html` llevaba una clase `.dot.amber`.
- `charter_generator.py` llevaba una clave `amber` alias de `yellow`.
- Y el quinto, el de contrato: **`task_load_thresholds.amber_max`**, una llave
  guardada en `tenant.settings` de inquilinos reales. Se cerró el 2026-08-06
  con el molde de `wbs` → `wbs_code`: migración 0101 sobre los datos y ventana
  de compatibilidad a la entrada (ADR-030).

Un alias que nadie usa no es tolerancia: es el sitio por donde el término
vuelve la próxima vez que alguien copie el diccionario. Por eso esta suite
mira el **árbol**, no una lista de sitios conocidos.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ_API = Path(__file__).resolve().parents[1]

#: `amber`, sin excepciones. La tenía —`task_load_thresholds.amber_max`, una
#: llave guardada en `tenant.settings` de inquilinos reales— y se cerró el
#: 2026-08-06 con el molde de `wbs` → `wbs_code`: migración 0101 sobre los datos
#: existentes y ventana de compatibilidad a la entrada (ADR-030).
#:
#: **Sin fronteras de palabra, y las dos costaron una mutación cada una.**
#: `\bamber\b` no casa con `amber_max` —después de «amber» viene `_`, que es
#: carácter de palabra— así que el veto parecía absoluto y dejaba pasar
#: exactamente el resto que se acababa de cerrar. Quitar solo la de la derecha
#: tampoco bastó: `_amber_legacy` se escapaba por la izquierda.
#:
#: El coste de no poner fronteras es un falso positivo en «chamber» o «camber»,
#: que no aparecen en este producto y se resolverían con una línea aquí. El
#: coste de ponerlas ya se pagó dos veces.
VETADO = re.compile(r"amber", re.I)

#: Los tres archivos que IMPLEMENTAN la ventana de compatibilidad, únicos donde
#: el nombre retirado puede aparecer. No es una lista de perdones: la prueba
#: comprueba además que cada uno de verdad hace de ventana —declararla o dejar
#: rastro—, así que añadir un archivo aquí sin implementar nada no sirve de
#: pase libre.
VENTANA = {
    "app/core/compatibilidad.py": "declara la ventana",
    "app/services/tenant_settings.py": "acepta el nombre viejo a la lectura",
    "app/api/v1/endpoints/admin_panel.py": "acepta el nombre viejo a la entrada",
}

#: Lo que ve el cliente. «Ámbar» es la traducción del término del que el
#: producto se aparta; la palabra en la interfaz es «Amarillo».
VETADO_VISIBLE = re.compile(r"Ámbar", re.I)

RUTAS = [
    RAIZ_API / "app",
]
EXTENSIONES = ("*.py", "*.html")


def _fuentes() -> list[Path]:
    return sorted(
        archivo
        for raiz in RUTAS
        for patron in EXTENSIONES
        for archivo in raiz.rglob(patron)
    )


def _sin_comentarios(texto: str, sufijo: str) -> str:
    """Quita comentarios y docstrings; explicar el veto no es incumplirlo.

    Sin esto, la única forma de documentar por qué `amber` se fue sería no
    documentarlo — que es exactamente el incentivo contrario al que interesa.
    """
    if sufijo == ".html":
        return re.sub(r"\{#.*?#\}|<!--.*?-->", "", texto, flags=re.S)
    sin_docstrings = re.sub(r'"""(?:.|\n)*?"""|\'\'\'(?:.|\n)*?\'\'\'', "", texto)
    return re.sub(r"#[^\n]*", "", sin_docstrings)


def test_el_termino_vetado_no_esta_en_el_codigo() -> None:
    """El caso general, y por eso mira el árbol y no una lista de sitios.

    Una prueba que enumerara `engine.py`, `s-03.html`, `base.html` y
    `charter_generator.py` quedaría verde el día que el término reaparezca en
    un quinto archivo — que es como volvió tres veces ya.
    """
    culpables = []
    for archivo in _fuentes():
        relativa = archivo.relative_to(RAIZ_API).as_posix()
        if relativa in VENTANA:
            continue
        cuerpo = _sin_comentarios(archivo.read_text(encoding="utf-8"), archivo.suffix)
        for n, linea in enumerate(cuerpo.splitlines(), 1):
            if VETADO.search(linea):
                culpables.append(f"{relativa}:{n}: {linea.strip()[:80]}")
    assert not culpables, (
        "`amber` está vetado como valor del semáforo (glosario §6, D-1). El "
        "valor es `yellow`.\n" + "\n".join(culpables)
    )


def test_la_etiqueta_que_ve_el_cliente_dice_amarillo() -> None:
    """El resto más caro de los cuatro, y el que ninguna búsqueda de código
    encuentra: estaba en el PDF, no en una variable.
    """
    culpables = [
        str(archivo.relative_to(RAIZ_API))
        for archivo in _fuentes()
        if VETADO_VISIBLE.search(_sin_comentarios(archivo.read_text(encoding="utf-8"), archivo.suffix))
    ]
    assert not culpables, (
        "La interfaz dice «Amarillo», no «Ámbar» — «Ámbar» traduce el término "
        f"RAG del que el producto se aparta (D-1). En: {culpables}"
    )


def test_el_motor_de_informes_no_traduce_el_vocabulario() -> None:
    """Traducir en el borde es lo que mantiene vivo un término retirado.

    El dominio hablaba `yellow` y la plantilla `amber`, con una tabla en medio.
    Mientras esa tabla exista, retirar el término del dominio no lo retira del
    producto — solo lo mueve a la mitad que nadie audita.
    """
    from app.services.reports import engine

    fuente = Path(engine.__file__).read_text(encoding="utf-8")
    assert not re.search(r'"yellow"\s*:\s*"[^y]', fuente), (
        "Alguien volvió a mapear `yellow` a otro término en el motor de informes."
    )


@pytest.mark.parametrize(
    ("salud", "esperado"),
    [("green", "green"), ("yellow", "yellow"), ("red", "red"), ("lo que sea", "yellow")],
)
def test_el_semaforo_del_informe_sale_en_el_vocabulario_canonico(salud: str, esperado: str) -> None:
    """Comprueba el comportamiento, no el texto del archivo.

    Una prueba que fijara el literal de la fuente no puede fallar — este
    expediente ya se comió tres. Esta llama a la función y mira lo que sale,
    incluido el caso por defecto, que era el que ponía `amber` cuando la salud
    llegaba con un valor inesperado.
    """
    from app.services.reports.engine import _build_s03_rag

    class _Proyecto:
        health_status = salud
        health_reason = None
        health_source = "auto"

    class _Ctx:
        project = _Proyecto()

    assert _build_s03_rag(_Ctx(), None, None)["status_rag"] == esperado


# ---------------------------------------------------------------------------
# El quinto resto: la llave de `tenant.settings` (ADR-030, migración 0101)
# ---------------------------------------------------------------------------

def test_la_ventana_de_compatibilidad_esta_declarada() -> None:
    """Una ventana sin declarar es la que nadie recuerda cerrar.

    `core/compatibilidad.py` lo dice en su encabezado: se añade la fila **al
    abrirla**, no después.
    """
    from app.core.compatibilidad import VENTANAS

    ventana = VENTANAS["amber_max"]
    assert ventana.nuevo.endswith("yellow_max")
    assert ventana.adr == "ADR-030"


def test_el_nombre_viejo_sigue_entrando_y_deja_rastro(caplog) -> None:
    """La razón de ser de la ventana, en un caso.

    Una pestaña abierta desde antes del despliegue —o una copia restaurada de
    antes— sigue mandando `amber_max`. Perder su umbral en silencio sería peor
    que aceptarlo: el semáforo de carga pasaría a los valores por defecto y
    nadie lo notaría hasta ver un informe con los colores cambiados.
    """
    import logging

    from app.models.tenant import Tenant
    from app.services.tenant_settings import get_task_load_thresholds

    t = Tenant(
        name="Con la llave vieja",
        slug="llave-vieja",
        settings={"report_builder": {"task_load_thresholds": {"green_max": 3, "amber_max": 7}}},
    )
    with caplog.at_level(logging.INFO, logger="pmoaas.compat"):
        umbrales = get_task_load_thresholds(t)

    assert umbrales == {"green_max": 3, "yellow_max": 7}, (
        "El umbral del inquilino se perdió al leer el nombre retirado."
    )
    assert any("compat.nombre_viejo" in r.message for r in caplog.records), (
        "La ventana aceptó el nombre viejo sin dejar rastro. Sin el contador no "
        "hay forma de saber cuándo se puede cerrar, y se vuelve permanente."
    )


def test_el_nombre_nuevo_gana_si_llegan_los_dos() -> None:
    """Un cliente a medio actualizar puede mandar los dos.

    Si ganara el viejo, actualizar el cliente no tendría efecto y el equipo
    concluiría que el renombrado no funciona.
    """
    from app.models.tenant import Tenant
    from app.services.tenant_settings import get_task_load_thresholds

    t = Tenant(
        name="Los dos",
        slug="los-dos",
        settings={
            "report_builder": {
                "task_load_thresholds": {"green_max": 3, "yellow_max": 9, "amber_max": 7}
            }
        },
    )
    assert get_task_load_thresholds(t)["yellow_max"] == 9


def test_lo_que_se_guarda_ya_es_el_nombre_nuevo() -> None:
    """La ventana es de ENTRADA. Si al guardar volviera a escribir el nombre
    viejo, la migración se desharía sola con el primer cambio de ajustes.
    """
    from app.models.tenant import Tenant
    from app.services.tenant_settings import set_task_load_thresholds

    t = Tenant(name="Guardado", slug="guardado", settings={})
    guardado = set_task_load_thresholds(t, 4, 8)["report_builder"]["task_load_thresholds"]
    assert guardado == {"green_max": 4, "yellow_max": 8}
    assert "amber_max" not in guardado


def test_los_archivos_de_la_ventana_de_verdad_hacen_de_ventana() -> None:
    """Sin esto, `VENTANA` sería una lista de perdones.

    Añadir un archivo ahí lo dejaría escribir `amber` libremente. Se exige que
    cada uno haga su parte: declararla, o registrar el uso del nombre viejo.
    """
    for relativa, papel in VENTANA.items():
        fuente = (RAIZ_API / relativa).read_text(encoding="utf-8")
        hace_de_ventana = "VENTANAS" in fuente or "registrar_uso" in fuente
        assert hace_de_ventana, (
            f"`{relativa}` figura en la ventana de compatibilidad («{papel}») "
            f"pero no la declara ni deja rastro. Es un pase libre para escribir "
            f"el término vetado."
        )


def test_la_ventana_no_crece_sin_que_se_note() -> None:
    """Tres archivos. Un cuarto significa que el nombre viejo se está
    extendiendo en vez de retirándose, que es lo contrario de una ventana.
    """
    assert len(VENTANA) == 3, f"La ventana pasó a {len(VENTANA)} archivos: {sorted(VENTANA)}"
