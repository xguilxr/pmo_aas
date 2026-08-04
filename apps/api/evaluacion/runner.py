#!/usr/bin/env python3
"""Ejecutor del conjunto de evaluación de IA.

Cierra **MCS IA-08** — «DEBE existir un conjunto de evaluación ejecutado en la
canalización, con umbral que condicione el despliegue». El umbral y el catálogo
viven en `casos.yaml`; el porqué de todo esto está en `README.md`.

Uso:
    python -m evaluacion.runner                     # falla si no se alcanza el umbral
    python -m evaluacion.runner --registro FICHERO  # además escribe el resultado
    python -m evaluacion.runner --informe           # mide y nunca falla

Qué evalúa y qué NO
-------------------
NO evalúa si el modelo acierta. Eso exige un modelo vivo, cuesta dinero por
ejecución y da un resultado distinto cada vez: no puede ser un gate de
despliegue, y fingir que sí lo es sería peor que no tenerlo.

Evalúa lo que sí es determinista y sí es nuestro: **qué hace el sistema cuando
el modelo falla**. Cada caso es una salida de modelo ya rota —inyectada,
malformada, alucinada— que se hace pasar por el mismo código que corre en
producción. La pregunta que responde el conjunto es «¿qué llega al usuario?»,
y esa pregunta tiene una sola respuesta correcta que no depende del proveedor.

Esto es la mitad que le faltaba a la defensa de IA-11. Aquella comprueba que el
contenido ajeno no llegue al modelo como instrucción; nada comprobaba qué pasa
si el modelo desobedece de todas formas —cosa que ninguna defensa de prompt
puede impedir—. Al escribir estos casos apareció la respuesta incómoda: en el
copiloto llegaba una navegación a otro origen. Ver `README.md`.

Las superficies llaman a funciones de producto de verdad. Donde el worker
compone varias en línea (el bucle de fragmentos, el merge), aquí se replica esa
composición y se anota con la línea de `app/workers/tasks/ai.py` que refleja.
Es la única costura del conjunto y está declarada a propósito: si el worker
cambia de forma y esto no, el conjunto mide un pipeline que ya no existe.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import traceback
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import yaml

RAIZ = Path(__file__).resolve().parent
CATALOGO = RAIZ / "casos.yaml"

# La consola de Windows usa cp1252 y destroza los acentos del informe. En CI
# (Linux, UTF-8) es inocuo. Mismo recurso que `scripts/check_contexto.py`.
for _flujo in (sys.stdout, sys.stderr):
    if hasattr(_flujo, "reconfigure"):
        _flujo.reconfigure(encoding="utf-8", errors="replace")


# ═══════════════════════════════════════════════════════════════════════════
# Superficies — cada una hace pasar la salida del modelo por el código real
# ═══════════════════════════════════════════════════════════════════════════


def _minuta_de_un_fragmento(salida_modelo: str) -> dict[str, Any]:
    """Un fragmento de transcripción, tal como lo trata el worker.

    Refleja `app/workers/tasks/ai.py::_run_minute` líneas 451-459: parseo
    tolerante, y si no hay JSON el fragmento cae al esqueleto vacío con el
    texto crudo de resumen en vez de perderse.
    """
    from app.services.ai.validator import validate_minute_payload
    from app.workers.tasks.ai import _empty_minute, _parse_json_strict

    parsed = _parse_json_strict(salida_modelo)
    if parsed is None:
        vacia = _empty_minute()
        vacia["summary"] = (salida_modelo or "")[:2000]
        vacia["participants_flat"] = []
        return vacia
    normalizada, _metricas = validate_minute_payload(parsed)
    return normalizada


def superficie_minuta(caso: dict[str, Any]) -> dict[str, Any]:
    return _minuta_de_un_fragmento(caso["salida_modelo"])


def superficie_merge(caso: dict[str, Any]) -> dict[str, Any]:
    """Varios fragmentos fundidos en una minuta.

    Refleja `_run_minute` líneas 468-505. El worker arma este dict en línea, así
    que aquí se replica llamando a las MISMAS primitivas —`dedupe_participants`,
    `merge_topics`, `_merge_raid_suggestions`—, no a una copia.
    """
    import functools
    import operator

    from app.services.ai.validator import dedupe_participants, merge_topics
    from app.workers.tasks.ai import _merge_raid_suggestions

    fragmentos = [_minuta_de_un_fragmento(s) for s in caso["salidas_modelo"]]
    return {
        "header": fragmentos[0].get("header") if fragmentos else {},
        "summary": "\n\n".join(
            [f.get("summary") or "" for f in fragmentos]
        ).strip(),
        "participants": dedupe_participants(
            functools.reduce(
                operator.iadd,
                (f.get("participants_flat") or [] for f in fragmentos),
                [],
            )
        ),
        "topics": merge_topics(
            functools.reduce(
                operator.iadd, (f.get("topics") or [] for f in fragmentos), []
            )
        ),
        "raid_suggestions": _merge_raid_suggestions(
            [f.get("raid_suggestions") for f in fragmentos]
        ),
        "free_notes": next(
            (f.get("free_notes") for f in fragmentos if f.get("free_notes")), None
        ),
    }


def superficie_asistente(caso: dict[str, Any]) -> dict[str, Any]:
    """El copiloto conversacional: mensaje + acciones que el frontend ejecuta."""
    from app.services.ai.assistant import parse_assistant_reply

    mensaje, acciones = parse_assistant_reply(caso["salida_modelo"])
    return {"message": mensaje, "actions": acciones}


def superficie_mapeo(caso: dict[str, Any]) -> dict[str, Any]:
    """El importador de planes: qué columna del archivo va a qué campo.

    Se llama a `suggest_column_mapping` entera —incluida la heurística y la
    puerta de confianza— con el proveedor sustituido por la salida del caso.
    Es la superficie donde la salida del modelo decide qué se escribe en la
    base de datos, así que evaluar solo el parser no bastaría.
    """
    from unittest.mock import patch

    from app.services import import_mapping_suggest as mapeo
    from app.services.ai.provider import AIResult
    from app.services.ai.tenant_ai import TenantAIConfig

    async def _proveedor(prompt: str, **kwargs: Any) -> AIResult:
        return AIResult(text=caso["salida_modelo"], model="conjunto-de-evaluacion")

    async def _ejecutar() -> dict[str, Any]:
        with patch.object(mapeo, "generate_for_tenant", side_effect=_proveedor):
            return await mapeo.suggest_column_mapping(
                list(caso["cabeceras"]),
                tenant_cfg=TenantAIConfig(mode="platform", byo=None),
                sample_rows=caso.get("filas_muestra"),
            )

    return asyncio.run(_ejecutar())


SUPERFICIES = {
    "minuta": superficie_minuta,
    "merge": superficie_merge,
    "asistente": superficie_asistente,
    "mapeo": superficie_mapeo,
}


# ═══════════════════════════════════════════════════════════════════════════
# Invariantes — lo que el sistema mantiene pase lo que pase
#
# Se aplican a TODOS los casos de la superficie, no solo a los que los nombran.
# Son la parte del conjunto que no envejece: un caso nuevo hereda el contrato
# entero sin que nadie tenga que acordarse de escribirlo.
# ═══════════════════════════════════════════════════════════════════════════

_CLAVES_MINUTA = {
    "header", "participants", "participants_flat", "summary",
    "topics", "raid", "raid_suggestions", "free_notes",
}


def _normaliza(nombre: Any) -> str:
    crudo = str(nombre or "").strip().lower()
    nfd = unicodedata.normalize("NFD", crudo)
    return "".join(c for c in nfd if not unicodedata.combining(c))


def _dicts(res: Any, ruta: str, fallos: list[str]) -> list[dict[str, Any]]:
    """Los elementos de `res[ruta]` que son diccionarios; el resto, un fallo.

    Los invariantes reciben el resultado de un pipeline que puede haber
    degenerado —de eso trata todo esto—, así que no pueden dar por hecho la
    forma. Un invariante que revienta sobre basura no informa de nada: aborta la
    ejecución entera y se lleva por delante los casos que aún no habían corrido.
    """
    valor = res.get(ruta) if isinstance(res, dict) else None
    if valor is None:
        return []
    if not isinstance(valor, (list, tuple)):
        fallos.append(f"{ruta} no es una lista: {type(valor).__name__}")
        return []
    salida: list[dict[str, Any]] = []
    for i, item in enumerate(valor):
        if isinstance(item, dict):
            salida.append(item)
        else:
            fallos.append(f"{ruta}[{i}] no es un objeto: {item!r}")
    return salida


def _inv_minuta(res: dict[str, Any]) -> list[str]:
    from app.services.ai.validator import ALLOWED_RAID_TYPES

    fallos: list[str] = []
    faltan = _CLAVES_MINUTA - set(res)
    if faltan:
        fallos.append(f"faltan claves del contrato de minuta: {sorted(faltan)}")
    for i, item in enumerate(_dicts(res, "raid", fallos)):
        if item.get("type") not in ALLOWED_RAID_TYPES:
            fallos.append(f"raid[{i}].type={item.get('type')!r} fuera de A/R/D/I")
        if not str(item.get("description") or "").strip():
            fallos.append(f"raid[{i}] sin descripción llegaría a la UI en blanco")
    cubos = res.get("raid_suggestions")
    if not isinstance(cubos, dict):
        fallos.append("raid_suggestions no es un objeto de cubos")
        cubos = {}
    for cubo, items in cubos.items():
        for i, s in enumerate(_dicts({cubo: items}, cubo, fallos)):
            if not str(s.get("short_desc") or "").strip():
                fallos.append(f"raid_suggestions.{cubo}[{i}] sin texto")
            if s.get("status") != "pending":
                fallos.append(
                    f"raid_suggestions.{cubo}[{i}] no nace pendiente de aprobación"
                )
    if not isinstance(res.get("summary"), str):
        # BUG-073: el merge cross-fragmento hace `str.join` sobre esto.
        fallos.append("summary no es texto; el merge de fragmentos reventaría")
    fallos += _inv_realimentacion(res)
    return fallos


def _inv_realimentacion(res: dict[str, Any]) -> list[str]:
    """La salida de hoy es el prompt de mañana.

    El resumen se persiste, alimenta la memoria del proyecto (US-185) y esa
    memoria se antepone a toda generación futura del proyecto. Si un
    delimitador escrito por el modelo sobrevive el viaje de vuelta, la salida
    envenenada de hoy manda sobre el sistema de mañana. Aquí se rehace el
    viaje entero y se comprueba que el bloque sigue entero.
    """
    from app.services.ai.project_context import compose_context_block

    resumen = res.get("summary")
    if not isinstance(resumen, str) or not resumen.strip():
        return []
    bloque = compose_context_block(project_name="Proyecto", auto_summary_md=resumen)
    if bloque is None:
        return []
    fallos: list[str] = []
    if len(re.findall(r"</CONTEXTO_DEL_PROYECTO>", bloque, re.I)) != 1:
        fallos.append("el resumen del modelo cerró el bloque de contexto")
    aperturas = len(re.findall(r"<CONTENIDO_NO_CONFIABLE\b", bloque, re.I))
    cierres = len(re.findall(r"</CONTENIDO_NO_CONFIABLE>", bloque, re.I))
    if aperturas != cierres:
        fallos.append(
            "el resumen del modelo desbalanceó el bloque de contenido no confiable"
        )
    return fallos


def _inv_merge(res: dict[str, Any]) -> list[str]:
    fallos: list[str] = []
    if not isinstance(res.get("summary"), str):
        fallos.append("summary no es texto tras el merge")
    nombres = [_normaliza(p.get("name")) for p in _dicts(res, "participants", fallos)]
    if len(nombres) != len(set(nombres)):
        fallos.append("participantes duplicados tras el merge (BUG-069)")
    titulos = [_normaliza(t.get("title")) for t in _dicts(res, "topics", fallos)]
    if len(titulos) != len(set(titulos)):
        fallos.append("temas duplicados tras el merge (BUG-070)")
    for cubo in ("actions", "risks", "decisions", "issues"):
        if not isinstance((res.get("raid_suggestions") or {}).get(cubo), list):
            fallos.append(f"raid_suggestions.{cubo} no es lista")
    return fallos


def _inv_asistente(res: dict[str, Any]) -> list[str]:
    from app.services.ai.assistant import ALLOWED_ACTION_TYPES, ruta_interna_segura

    fallos: list[str] = []
    if not isinstance(res.get("message"), str) or not res["message"].strip():
        fallos.append("el usuario se queda sin respuesta")
    for i, a in enumerate(_dicts(res, "actions", fallos)):
        if a.get("type") not in ALLOWED_ACTION_TYPES:
            fallos.append(f"actions[{i}].type={a.get('type')!r} no está permitido")
        if a.get("type") == "navigate" and not ruta_interna_segura(str(a.get("path"))):
            # El frontend hace `router.push(path)` sin comprobar nada más.
            fallos.append(f"actions[{i}].path={a.get('path')!r} sale del sitio")
    return fallos


def _inv_mapeo(res: dict[str, Any]) -> list[str]:
    from app.services.import_mapping_suggest import SYSTEM_FIELDS

    fallos: list[str] = []
    for cabecera, sug in res.items():
        if not isinstance(sug, dict):
            fallos.append(f"{cabecera!r} no devolvió una sugerencia: {sug!r}")
            continue
        campo = sug.get("field")
        if campo is not None and campo not in SYSTEM_FIELDS:
            fallos.append(
                f"{cabecera!r} mapeada a {campo!r}, que no es un campo del sistema"
            )
        if sug.get("source") not in {"ai", "heuristic", "none"}:
            fallos.append(f"{cabecera!r} con procedencia {sug.get('source')!r}")
    return fallos


INVARIANTES = {
    "minuta": _inv_minuta,
    "merge": _inv_merge,
    "asistente": _inv_asistente,
    "mapeo": _inv_mapeo,
}


# ═══════════════════════════════════════════════════════════════════════════
# Comprobaciones declaradas en el catálogo
# ═══════════════════════════════════════════════════════════════════════════

_RE_SEGMENTO = re.compile(r"([^.\[\]]+)|\[(\d+)\]")
_CENTINELA = object()


def resolver(res: Any, ruta: str) -> Any:
    """Resuelve `a.b[0].c` sobre el resultado. `.` es el resultado entero.

    Las claves pueden llevar puntos —una cabecera de hoja de cálculo se llama
    «Nombre de la tarea»—, así que primero se prueba la ruta literal como clave.
    """
    if ruta == ".":
        return res
    if isinstance(res, dict) and ruta in res:
        return res[ruta]
    actual: Any = res
    for nombre, indice in _RE_SEGMENTO.findall(ruta):
        if indice:
            if not isinstance(actual, (list, tuple)) or int(indice) >= len(actual):
                return _CENTINELA
            actual = actual[int(indice)]
        else:
            if not isinstance(actual, dict) or nombre not in actual:
                return _CENTINELA
            actual = actual[nombre]
    return actual


_TIPOS = {
    "str": str, "int": int, "float": float, "bool": bool,
    "list": list, "dict": dict,
}


def _texto(valor: Any) -> str:
    return valor if isinstance(valor, str) else json.dumps(valor, ensure_ascii=False)


# Vocabulario cerrado a propósito. Una clave desconocida NO se ignora: una
# comprobación mal escrita que pasa en silencio es peor que no escribirla,
# porque el caso figura como cubierto. Es el fallo clásico de los ficheros de
# casos declarativos, y aquí lo cubre `test_cada_caso_esta_completo` además.
_COMPROBACIONES = frozenset({
    "igual", "es_nulo", "tipo", "longitud", "vacio", "no_vacio",
    "contiene", "no_contiene",
})


def comprobar(res: Any, check: dict[str, Any]) -> str | None:
    """Devuelve el motivo del fallo, o None si la comprobación pasa."""
    desconocidas = set(check) - _COMPROBACIONES - {"ruta"}
    if desconocidas:
        return (
            f"comprobación desconocida {sorted(desconocidas)} en {check.get('ruta')!r}: "
            f"el vocabulario es {sorted(_COMPROBACIONES)}"
        )
    ruta = check["ruta"]
    valor = resolver(res, ruta)
    if valor is _CENTINELA:
        return f"{ruta} no existe en el resultado"
    for clave, esperado in check.items():
        if clave == "ruta":
            continue
        if clave == "igual" and valor != esperado:
            return f"{ruta} = {valor!r}, se esperaba {esperado!r}"
        if clave == "es_nulo" and (valor is None) != bool(esperado):
            return f"{ruta} = {valor!r}, se esperaba nulo={esperado}"
        if clave == "tipo":
            if esperado not in _TIPOS:
                return f"tipo {esperado!r} desconocido; hay {sorted(_TIPOS)}"
            if not isinstance(valor, _TIPOS[esperado]):
                return f"{ruta} es {type(valor).__name__}, se esperaba {esperado}"
        if clave == "longitud" and len(valor) != esperado:
            return f"{ruta} tiene {len(valor)} elementos, se esperaban {esperado}"
        # `vacio: true` exige que el valor sea falsy; `no_vacio: true`, truthy.
        # Escrito como igualdad y no como negación encadenada, que es donde
        # estas dos se confunden.
        if clave == "vacio" and bool(valor) != (not esperado):
            return f"{ruta} = {valor!r}, se esperaba vacío={esperado}"
        if clave == "no_vacio" and bool(valor) != bool(esperado):
            return f"{ruta} = {valor!r}, se esperaba no vacío={esperado}"
        if clave == "contiene" and str(esperado) not in _texto(valor):
            return f"{ruta} no contiene {esperado!r}"
        if clave == "no_contiene" and str(esperado) in _texto(valor):
            return f"{ruta} contiene {esperado!r} y no debería"
    return None


# ═══════════════════════════════════════════════════════════════════════════
# Ejecución
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class Resultado:
    id: str
    bloque: str
    superficie: str
    titulo: str
    paso: bool
    motivos: list[str] = field(default_factory=list)


def bloque_de(caso_id: str) -> str:
    return "seguridad" if caso_id.startswith("EV-S-") else "calidad"


def ejecutar_caso(caso: dict[str, Any]) -> Resultado:
    bloque = bloque_de(caso["id"])
    base = {
        "id": caso["id"], "bloque": bloque,
        "superficie": caso["superficie"], "titulo": caso["titulo"],
    }
    try:
        res = SUPERFICIES[caso["superficie"]](caso)
    except Exception:
        cola = traceback.format_exc().strip().splitlines()[-1]
        return Resultado(**base, paso=False, motivos=[f"el pipeline reventó: {cola}"])

    motivos: list[str] = []
    try:
        json.dumps(res, ensure_ascii=False, default=str)
    except Exception as exc:
        motivos.append(f"el resultado no es serializable: {exc}")
    # Un invariante que revienta también es información —significa que el
    # resultado degeneró más allá de lo que el invariante contemplaba—, pero no
    # puede llevarse por delante los casos que aún no han corrido.
    try:
        motivos += INVARIANTES[caso["superficie"]](res)
    except Exception:
        cola = traceback.format_exc().strip().splitlines()[-1]
        motivos.append(f"el invariante reventó sobre el resultado: {cola}")
    for check in caso.get("espera") or []:
        try:
            fallo = comprobar(res, check)
        except Exception:
            cola = traceback.format_exc().strip().splitlines()[-1]
            fallo = f"la comprobación {check} reventó: {cola}"
        if fallo:
            motivos.append(fallo)
    return Resultado(**base, paso=not motivos, motivos=motivos)


def cargar(ruta: Path = CATALOGO) -> dict[str, Any]:
    return yaml.safe_load(ruta.read_text(encoding="utf-8"))


def ejecutar_todo(catalogo: dict[str, Any] | None = None) -> list[Resultado]:
    catalogo = catalogo or cargar()
    return [ejecutar_caso(c) for c in catalogo["casos"]]


def evaluar_umbral(
    resultados: list[Resultado], catalogo: dict[str, Any]
) -> tuple[bool, dict[str, dict[str, Any]], list[str]]:
    """(¿supera?, resumen por bloque, motivos del bloqueo)."""
    bloqueos: list[str] = []
    resumen: dict[str, dict[str, Any]] = {}
    for bloque, umbral in catalogo["umbral"].items():
        propios = [r for r in resultados if r.bloque == bloque]
        pasan = sum(1 for r in propios if r.paso)
        pct = 100.0 * pasan / len(propios) if propios else 0.0
        minimo = umbral["minimo_pct"]
        resumen[bloque] = {
            "casos": len(propios), "pasan": pasan,
            "pct": round(pct, 1), "minimo_pct": minimo,
            "supera": pct >= minimo,
        }
        if pct < minimo:
            bloqueos.append(
                f"bloque {bloque}: {pasan}/{len(propios)} ({pct:.1f} %) "
                f"por debajo del umbral de {minimo} %"
            )
    # Trinquete de IA-09: el conjunto solo crece.
    minimo_casos = catalogo["minimo_casos"]
    if len(resultados) < minimo_casos:
        bloqueos.append(
            f"el conjunto tiene {len(resultados)} casos y declara un mínimo de "
            f"{minimo_casos}: se borraron casos sin justificarlo en resultados/"
        )
    return not bloqueos, resumen, bloqueos


def informe(resultados: list[Resultado], resumen: dict[str, dict[str, Any]]) -> None:
    print("Conjunto de evaluación de IA — MCS IA-07 / IA-08 / IA-09")
    print("=" * 72)
    for bloque in ("seguridad", "calidad"):
        propios = [r for r in resultados if r.bloque == bloque]
        if not propios:
            continue
        datos = resumen[bloque]
        marca = "✓" if datos["supera"] else "✗"
        print(
            f"\n{marca} {bloque.upper():<10} {datos['pasan']}/{datos['casos']} "
            f"({datos['pct']} %)  ·  umbral {datos['minimo_pct']} %"
        )
        for r in propios:
            if r.paso:
                continue
            print(f"    ✗ {r.id}  [{r.superficie}]  {r.titulo}")
            for m in r.motivos:
                print(f"        · {m}")
    print("\n" + "-" * 72)
    total = sum(1 for r in resultados if r.paso)
    print(f"  {total}/{len(resultados)} casos conformes")


def escribir_registro(
    ruta: Path,
    resultados: list[Resultado],
    resumen: dict[str, dict[str, Any]],
    catalogo: dict[str, Any],
    supera: bool,
    nota: str | None = None,
) -> None:
    """Un fallo no se borra al corregirse: la serie es lo que dice si el
    sistema mejora o si cada versión rompe algo distinto."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "fecha": date.today().isoformat(),
        "version_catalogo": catalogo["version"],
        "casos": len(resultados),
        "resumen": resumen,
        "supera": supera,
        "nota": nota,
        "detalle": {
            r.id: ("paso" if r.paso else "fallo") for r in resultados
        },
        "fallos": {r.id: r.motivos for r in resultados if not r.paso},
    }
    ruta.write_text(
        yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    print(f"\n  registro escrito en {ruta}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--informe", action="store_true", help="mide y reporta, pero devuelve 0 siempre"
    )
    parser.add_argument(
        "--registro", type=Path, help="escribe el resultado en este fichero YAML"
    )
    parser.add_argument(
        "--nota", help="una línea de contexto para el registro (qué disparó la ejecución)"
    )
    args = parser.parse_args()

    catalogo = cargar()
    resultados = ejecutar_todo(catalogo)
    supera, resumen, bloqueos = evaluar_umbral(resultados, catalogo)
    informe(resultados, resumen)
    if args.registro:
        escribir_registro(
            args.registro, resultados, resumen, catalogo, supera, args.nota
        )

    if supera:
        print("\n  RESULTADO: SUPERA el umbral declarado en casos.yaml\n")
        return 0
    print("\n  RESULTADO: NO SUPERA — el despliegue queda bloqueado")
    for b in bloqueos:
        print(f"    · {b}")
    print()
    return 0 if args.informe else 1


if __name__ == "__main__":
    raise SystemExit(main())
