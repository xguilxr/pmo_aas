"""DIS-04 — un aviso destructivo nombra el objeto y dice su consecuencia.

«Toda acción destructiva DEBE nombrar el objeto afectado y su consecuencia, y
ofrecer confirmación o reversión».

Medido el 2026-08-06: de los avisos que había, **ninguno decía la
consecuencia** y varios no nombraban el objeto —«¿Eliminar este ítem?»—. La
tercera parte, la confirmación, sí estaba: en su forma más pobre.

La suite vive en el proyecto de API aunque comprueba código de web porque es
donde corre el CI de pruebas; el gate real es `scripts/check_confirmaciones.py`.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
FRONTERA = RAIZ / "apps" / "web" / "lib" / "confirmar.ts"

sys.path.insert(0, str(RAIZ / "scripts"))
from check_confirmaciones import NO_DESTRUCTIVO, crudos, tolerados  # noqa: E402


def test_la_frontera_exige_las_tres_partes() -> None:
    """Sin valor por defecto en ninguna, igual que `errors.mensaje()`.

    Un parámetro opcional es un parámetro que nadie rellena, y el aviso vuelve
    a quedarse a medias sin que nada chille. Es lo que pasó con los 21
    anteriores: la consecuencia no estaba prohibida, simplemente no la escribía
    nadie.
    """
    fuente = FRONTERA.read_text(encoding="utf-8")
    tipo = re.search(r"export type AvisoDestructivo = \{(.*?)\n\};", fuente, re.S)
    assert tipo, "Desapareció el tipo `AvisoDestructivo`."
    cuerpo = tipo.group(1)
    for campo in ("objeto", "consecuencia", "reversibilidad"):
        assert re.search(rf"^\s+{campo}:", cuerpo, re.M), (
            f"`{campo}` dejó de ser obligatorio en el aviso destructivo."
        )
        assert not re.search(rf"^\s+{campo}\?:", cuerpo, re.M), (
            f"`{campo}` pasó a opcional. DIS-04 pide las tres partes; una "
            f"opcional es una que no se escribe."
        )


def test_distingue_lo_recuperable_de_lo_definitivo() -> None:
    """En este producto conviven los dos borrados y el aviso no puede mentir.

    La mayoría marcan `deleted_at`; hay 52 sitios en el API que borran de
    verdad. Decir «no se puede deshacer» sobre un borrado blando asusta sin
    motivo; decir «se puede recuperar» sobre uno duro es peor.
    """
    fuente = FRONTERA.read_text(encoding="utf-8")
    assert '"recuperable"' in fuente and '"definitiva"' in fuente
    assert "no se puede deshacer" in fuente.lower()
    assert "recuperar" in fuente.lower()


def test_el_aviso_redactado_nombra_y_advierte() -> None:
    """El texto que sale, no solo la forma del tipo.

    Comprobar la firma y no el resultado dejaría pasar una implementación que
    ignorase `consecuencia` — el campo obligatorio y el mensaje sin él.
    """
    fuente = FRONTERA.read_text(encoding="utf-8")
    plantilla = re.search(r"return `(.+?)`;", fuente, re.S)
    assert plantilla, "No encontré la plantilla del aviso."
    texto = plantilla.group(1)
    for parte in ("${objeto}", "${consecuencia}", "CIERRE[reversibilidad]"):
        assert parte in texto, (
            f"El aviso redactado no usa `{parte}`: el campo se exige y no se "
            f"muestra, que es peor que no exigirlo."
        )


def test_ningun_aviso_crudo_nuevo() -> None:
    """El trinquete. Tolera el pasivo declarado; falla ante el 22.

    Quedaban 16 archivos con avisos crudos y `CLAUDE.md` §3 para a validar por
    encima de diez, así que se aplica el molde de `.mypy-baseline` y
    `.len02-baseline`: el pasivo solo encoge.
    """
    from collections import Counter

    observados = Counter(f for f in crudos() if f not in NO_DESTRUCTIVO)
    conocidos = tolerados()
    nuevos = [f for f, n in observados.items() if n > conocidos.get(f, 0)]
    assert not nuevos, (
        f"Avisos destructivos nuevos sin pasar por la frontera: {nuevos}. "
        f"Usá `confirmarDestructivo` de `apps/web/lib/confirmar.ts`."
    )


def test_no_queda_pasivo() -> None:
    """El pasivo llegó a **cero** el 2026-08-06, con el owner autorizando el
    barrido de los 16 archivos.

    El cero está escrito y no derivado de la base: derivarlo de lo que vigila
    haría que subirlo pasara desapercibido — el defecto que ya apareció con
    `MAX_ASUNTO` y con `CAMPOS` en esta misma sesión.
    """
    assert sum(tolerados().values()) == 0, (
        "Reapareció pasivo en la línea base de DIS-04. Ya estaba a cero: un "
        "aviso nuevo se migra, no se declara."
    )


def test_lo_que_queda_fuera_dice_por_que() -> None:
    """Dos avisos no son destrucción y están declarados, no tolerados.

    La distinción no es cosmética: la línea base es pasivo pendiente y el
    alcance decidido es otra cosa. Mezclarlos haría que la base nunca llegara a
    cero y perdiera su sentido — que es justo lo que acaba de pasar hoy.
    """
    assert len(NO_DESTRUCTIVO) == 2
    for aviso, motivo in NO_DESTRUCTIVO.items():
        assert len(motivo) > 60, f"«{aviso[:40]}…» no explica por qué queda fuera."


def test_los_avisos_migrados_de_verdad_pasan_por_la_frontera() -> None:
    """Los tres que no nombraban nada, comprobados uno a uno.

    Un trinquete que solo cuenta demuestra «no creció». Esto demuestra que los
    peores casos concretos se arreglaron — incluido el de informes programados,
    cuyo borrado es DURO (`db.delete` en el API) y cuyo aviso no lo decía.
    """
    web = RAIZ / "apps" / "web" / "app" / "(app)" / "pmo" / "projects" / "[id]"
    raid = (web / "raid" / "page.tsx").read_text(encoding="utf-8")
    informes = (web / "reports" / "page.tsx").read_text(encoding="utf-8")

    assert "¿Eliminar este riesgo?" not in raid
    assert "¿Eliminar este ítem?" not in raid
    assert raid.count("confirmarDestructivo({") == 2

    # El más caro del producto: la importación con estrategia REPLACE borra
    # TODAS las tareas del proyecto. Era el único aviso que ya decía su
    # consecuencia, y no decía que fuera irreversible.
    asistente = (RAIZ / "apps" / "web" / "components" / "import-wizard.tsx").read_text(
        encoding="utf-8"
    )
    assert asistente.count("confirmarDestructivo({") == 3
    assert "TODAS las tareas actuales" in asistente

    assert "¿Eliminar esta programación?" not in informes
    assert 'reversibilidad: "definitiva"' in informes, (
        "El aviso de informes programados dejó de declararse definitivo. El "
        "API hace `db.delete`: no hay `deleted_at` que recuperar."
    )


def test_el_gate_corre_de_verdad() -> None:
    """De extremo a extremo, como lo invoca el CI.

    Sin esto, el script podría estar roto con la suite en verde: las de arriba
    importan sus funciones, no lo ejecutan.
    """
    r = subprocess.run(
        [sys.executable, str(RAIZ / "scripts" / "check_confirmaciones.py")],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "OK" in r.stdout
