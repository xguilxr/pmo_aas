"""B5 · MCS SEG-06 — el modelo de amenazas no puede caducar en silencio.

SEG-06 pide un modelo de amenazas «derivado de la arquitectura, **revisado ante
cambios significativos**». La primera mitad la cumple un documento; la segunda
no la cumple ningún documento, porque un control confiado a que alguien se
acuerde no es un control (MCA-CORE §6.1). Esta suite es la segunda mitad.

Lo que vigila, y por qué justo esto:

1. **Rutas que no exigen identidad** (§1). Es el cambio más significativo
   posible en la frontera con internet. Hoy son nueve y cada una está declarada
   con su motivo en `docs/architecture/amenazas.yaml`.
2. **Destinos externos** (§2). Un egreso nuevo saca datos del proyecto de
   nuestra infraestructura; un destino nuevo cualquiera amplía la superficie.
3. **Que el documento y el inventario no se contradigan** (§3).

Lo que NO vigila, deliberadamente: una huella del código entero. Un gate que se
pone rojo con cada edición se desactiva en dos días, y entonces no vigila nada.
Se vigila lo que de verdad amplía la superficie de ataque.

Cuando esta suite falle, la respuesta correcta **no** es añadir la línea que
falta al YAML. Es leer `modelo-amenazas.md`, decidir qué amenaza introduce el
cambio, y entonces declararla. El fichero es el recordatorio, no el trámite.
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[3]
INVENTARIO = RAIZ / "docs" / "architecture" / "amenazas.yaml"
MODELO = RAIZ / "docs" / "architecture" / "modelo-amenazas.md"

INV = yaml.safe_load(INVENTARIO.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# §1 — Rutas que no exigen identidad
# ---------------------------------------------------------------------------


def _exige_identidad(dep, visto: set[int] | None = None) -> bool:
    """¿La ruta exige identidad, mirando el árbol ENTERO de dependencias?

    Mirar solo el primer nivel da 37 rutas «abiertas» donde hay 7, porque
    `get_superadmin` no es `get_current_user` pero depende de él. Una primera
    versión de esta comprobación se equivocó justo así, y el susto de ver el
    panel de superadministrador en la lista de rutas públicas es la razón de
    que esto lleve un comentario.
    """
    visto = visto if visto is not None else set()
    for sub in dep.dependencies:
        f = getattr(sub, "call", None)
        if f is None or id(f) in visto:
            continue
        visto.add(id(f))
        if f.__name__ in {"get_current_user", "get_superadmin"}:
            return True
        if _exige_identidad(sub, visto):
            return True
    return False


def _superficie_abierta_real() -> set[str]:
    from app.main import app

    abiertas: set[str] = set()
    for r in app.routes:
        if not hasattr(r, "dependant") or _exige_identidad(r.dependant):
            continue
        for metodo in sorted(r.methods - {"HEAD", "OPTIONS"}):
            abiertas.add(f"{metodo} {r.path}")
    return abiertas


def _superficie_abierta_declarada() -> set[str]:
    return {e["ruta"] for e in INV["superficie_abierta"]}


def test_seg06_no_hay_rutas_abiertas_sin_declarar():
    """El fallo que importa: alguien publica un endpoint sin autenticación y
    nadie lo mira desde el punto de vista de un atacante."""
    sin_declarar = _superficie_abierta_real() - _superficie_abierta_declarada()
    assert not sin_declarar, (
        "estas rutas no exigen identidad y no están en el modelo de amenazas:\n  "
        + "\n  ".join(sorted(sin_declarar))
        + "\n\nAntes de declararlas en docs/architecture/amenazas.yaml, decidí qué "
        "amenaza introducen y anotala en modelo-amenazas.md."
    )


def test_seg06_no_quedan_rutas_declaradas_que_ya_no_existen():
    """El otro lado: una ruta que se cerró y sigue declarada abierta hace que
    el inventario describa un sistema que ya no es este."""
    fantasmas = _superficie_abierta_declarada() - _superficie_abierta_real()
    assert not fantasmas, (
        f"declaradas como abiertas pero ya no lo son (o no existen): {sorted(fantasmas)}"
    )


def test_seg06_cada_ruta_abierta_declara_su_motivo():
    sin_motivo = [
        e["ruta"] for e in INV["superficie_abierta"] if not (e.get("motivo") or "").strip()
    ]
    assert not sin_motivo, (
        f"una ruta abierta sin motivo escrito no está evaluada, solo tolerada: {sin_motivo}"
    )


# ---------------------------------------------------------------------------
# §2 — Destinos externos
# ---------------------------------------------------------------------------

_RE_HOST = re.compile(r"https?://([a-zA-Z0-9._-]+)")


def _hosts_en_codigo() -> set[str]:
    hosts: set[str] = set()
    for f in (RAIZ / "apps" / "api" / "app").rglob("*.py"):
        for m in _RE_HOST.finditer(f.read_text(encoding="utf-8")):
            host = m.group(1).lower().rstrip(".")
            if host:
                hosts.add(host)
    return hosts


def test_seg06_no_hay_destinos_externos_sin_declarar():
    declarados = {d["host"] for d in INV["destinos_externos"]}
    sin_declarar = _hosts_en_codigo() - declarados
    assert not sin_declarar, (
        "estos destinos externos aparecen en el código y no están en el modelo "
        f"de amenazas: {sorted(sin_declarar)}\n"
        "Si le mandamos datos, es `clase: egreso` y hay que releer AM-05. Si solo "
        "es un enlace de documentación, es `clase: referencia`."
    )


def test_seg06_todo_destino_declara_clase_y_dato():
    malos = [
        d.get("host")
        for d in INV["destinos_externos"]
        if d.get("clase") not in {"egreso", "referencia"} or not (d.get("dato") or "").strip()
    ]
    assert not malos, f"destinos sin clase válida o sin describir qué viaja: {malos}"


def test_seg06_todo_egreso_esta_atado_a_una_amenaza():
    """Un destino al que le mandamos datos y que no aparece en ninguna amenaza
    es un camino de salida que nadie evaluó."""
    huerfanos = [
        d["host"]
        for d in INV["destinos_externos"]
        if d["clase"] == "egreso" and not d.get("amenazas")
    ]
    assert not huerfanos, f"egresos sin amenaza asociada: {huerfanos}"


# ---------------------------------------------------------------------------
# §3 — El documento y el inventario hablan del mismo sistema
# ---------------------------------------------------------------------------

_RE_AMENAZA = re.compile(r"\bAM-\d{2}\b")


def test_seg06_el_modelo_existe_y_documenta_toda_amenaza_referenciada():
    assert MODELO.is_file(), f"falta {MODELO}"
    texto = MODELO.read_text(encoding="utf-8")
    documentadas = set(_RE_AMENAZA.findall(texto))
    referenciadas: set[str] = set()
    for grupo in ("superficie_abierta", "destinos_externos"):
        for e in INV[grupo]:
            referenciadas |= set(e.get("amenazas") or [])
    faltan = referenciadas - documentadas
    assert not faltan, (
        f"el inventario apunta a amenazas que el modelo no describe: {sorted(faltan)}"
    )


def test_seg06_toda_amenaza_declara_su_estado():
    """Una amenaza listada sin estado es una amenaza que nadie decidió qué
    hacer con ella. Los estados válidos son los de la tabla del documento."""
    texto = MODELO.read_text(encoding="utf-8")
    estados = {"CERRADA", "CONTROLADA", "PARCIAL", "SIN CONTROL", "ACEPTADA"}
    for amenaza in sorted(set(_RE_AMENAZA.findall(texto))):
        bloque = texto.split(f"### {amenaza}")
        if len(bloque) < 2:
            continue  # solo se la menciona; su ficha está en otro sitio
        ficha = bloque[1].split("\n### ")[0]
        assert any(e in ficha for e in estados), (
            f"{amenaza} no declara estado; los válidos son {sorted(estados)}"
        )


def test_seg06_la_fecha_de_revision_es_una_fecha():
    assert isinstance(INV["revisado"], date), (
        f"`revisado` debe ser una fecha, no {INV['revisado']!r}"
    )


def test_seg06_avisa_si_el_modelo_esta_fuera_de_ventana():
    """DOC-07: un documento fuera de su ventana de revisión debe señalarse.

    Esto **avisa**, no falla. Que pase el tiempo no hace el código menos
    seguro hoy; lo que lo hace menos seguro es superficie nueva sin evaluar, y
    de eso se ocupan §1 y §2. Un gate que se pone rojo por el calendario un
    lunes cualquiera se desactiva ese mismo lunes.
    """
    meses = (date.today() - INV["revisado"]).days / 30.44
    if meses > INV["revision_maxima_meses"]:
        pytest.skip(
            f"AVISO SEG-06: el modelo de amenazas se revisó hace {meses:.0f} meses "
            f"(ventana: {INV['revision_maxima_meses']}). Toca releerlo."
        )
