#!/usr/bin/env python3
"""CTX-07 — el conocimiento del repositorio se indexa por sección, no por archivo.

## El problema que resuelve

`CLAUDE.md` §1 enruta ocho destinos. El resto del corpus —91 documentos vivos,
1.34 millones de caracteres— depende de que un documento ya cargado enlace al
siguiente. Medido el 2026-08-28: **40 documentos vivos no tienen ninguna ruta
de entrada** desde el contexto permanente. Entre ellos, las fichas de indicador
firmadas por el owner y el glosario del negocio, que son exactamente los dos
que evitan re-derivar una definición desde el código.

Un documento que nadie encuentra no está en la memoria del proyecto: está en el
disco. La diferencia cuesta una sesión entera de re-exploración cada vez.

## Por qué léxico y no embeddings

Un índice vectorial necesita un servicio que lo sirva, una canalización que lo
reconstruya y una clave de API; y sobre todo **no se puede revisar en un PR**:
un vector cambiado no se lee. Este corpus además juega a favor del léxico —
está en español técnico con vocabulario controlado (`docs/dominio/02-GLOSARIO.md`
fija el término preferente y veta los sinónimos), así que la palabra que alguien
busca es, por diseño, la palabra que el documento usa.

El índice de aquí es determinista, cabe en un archivo versionado, se difiere en
un PR como cualquier otro código y funciona sin red. Si algún día el corpus
crece hasta donde el léxico falle, este índice es el conjunto de evaluación con
el que se mediría el reemplazo.

## Grano de sección

La unidad es el encabezado, no el archivo. Buscar «sobreasignación» y recibir
«abre `02-GLOSARIO.md`» cuesta 442 líneas de lectura; recibir
«`02-GLOSARIO.md` líneas 148-207, §2.4 Estado de salud» cuesta 59. El índice
guarda el rango de líneas de cada sección precisamente para que la respuesta
sea un `sed -n`, y no una invitación a leer el documento entero.

## Un artefacto versionado, ninguno binario

Se escribe **solo** `docs/INDICE.md`: 19 KB legibles, que se revisan en un PR
como cualquier otro documento y le dicen a una persona qué archivo abrir.

El índice que usa `buscar` —2 633 secciones con su vocabulario— **no se guarda**.
Se construye en memoria en cada consulta, en dos segundos. Serializarlo daba
3,4 MB de JSON que nadie puede revisar y que quedaría desfasado en cuanto
alguien editara un documento sin regenerarlo. Un índice desfasado es peor que
ninguno: responde con confianza sobre texto que ya no existe. Construirlo cada
vez cuesta dos segundos y esa clase de fallo deja de ser posible.

`INDICE.md` sí es un artefacto generado, con el criterio de `generar_er.py`
(DOC-03): se reescribe entero, no se edita a mano, y `--verificar` falla si
quedó desfasado.

Uso:

    python scripts/indexar.py                      # regenera docs/INDICE.md
    python scripts/indexar.py --verificar          # exit 1 si quedó desfasado
    python scripts/indexar.py buscar "sobreasignacion"   # consulta el índice
    python scripts/indexar.py buscar "rls tenant" -n 5
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DOCS = RAIZ / "docs"
MD_SALIDA = DOCS / "INDICE.md"

# La consola de Windows usa cp1252 y destroza los acentos. En CI es inocuo.
for _flujo in (sys.stdout, sys.stderr):
    if hasattr(_flujo, "reconfigure"):
        _flujo.reconfigure(encoding="utf-8", errors="replace")

# Estados que marcan un documento como no vigente. Se indexan igual —un
# archivado sigue siendo la respuesta a «¿por qué se canceló EP012?»— pero
# nunca compiten con uno vivo: ver `_PENALIZACION_ARCHIVO`.
ESTADOS_MUERTOS = frozenset({"archivado", "historico"})
_PENALIZACION_ARCHIVO = 0.25

# Palabras que aparecen en casi toda sección y no discriminan nada.
VACIAS = frozenset(
    """
    a al algo ante antes aqui asi aun aunque cada como con contra cual cuando
    de del desde donde dos el ella ellas ello ellos en entre era eran es esa
    ese eso esta estan este esto estos ha hace hacer hasta hay la las le les lo
    los mas me mi mientras muy no nos o para pero poco por porque que se ser si
    sin sobre solo son su sus tambien tiene todo todos un una uno y ya
    """.split()
)

# Encabezado markdown: nivel + texto. Se ignoran los que van dentro de un
# bloque de código — un `# comentario` de Python no es una sección.
_RE_ENCABEZADO = re.compile(r"^(#{1,4})\s+(.*\S)\s*$")
_RE_CERCA = re.compile(r"^\s*(```|~~~)")


def _normalizar(texto: str) -> str:
    """Minúsculas sin acentos: «Sobreasignación» y «sobreasignacion» son la misma."""
    descompuesto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def _tokens(texto: str) -> list[str]:
    return [
        t
        for t in re.findall(r"[a-z0-9_]{2,}", _normalizar(texto))
        if t not in VACIAS
    ]


@dataclass
class Seccion:
    """Un encabezado y todo lo que cuelga de él hasta el siguiente del mismo nivel."""

    ruta: str
    titulo: str
    nivel: int
    linea_inicio: int
    linea_fin: int
    ruta_titulos: list[str] = field(default_factory=list)

    @property
    def lineas(self) -> int:
        return self.linea_fin - self.linea_inicio + 1


def _frontmatter(texto: str) -> dict[str, str]:
    if not texto.startswith("---\n"):
        return {}
    cierre = texto.find("\n---", 4)
    if cierre == -1:
        return {}
    campos: dict[str, str] = {}
    for linea in texto[4:cierre].split("\n"):
        if ":" in linea:
            clave, valor = linea.split(":", 1)
            campos[clave.strip()] = valor.strip()
    return campos


def _secciones(ruta_rel: str, lineas: list[str]) -> list[Seccion]:
    """Parte un documento en secciones por encabezado, con su rango de líneas."""
    encontrados: list[tuple[int, int, str]] = []
    dentro_de_codigo = False
    for i, linea in enumerate(lineas, start=1):
        if _RE_CERCA.match(linea):
            dentro_de_codigo = not dentro_de_codigo
            continue
        if dentro_de_codigo:
            continue
        m = _RE_ENCABEZADO.match(linea)
        if m:
            encontrados.append((i, len(m.group(1)), m.group(2)))

    if not encontrados:
        # Un documento sin encabezados es una sola sección: el archivo entero.
        return [
            Seccion(
                ruta=ruta_rel,
                titulo=Path(ruta_rel).stem,
                nivel=1,
                linea_inicio=1,
                linea_fin=len(lineas),
            )
        ]

    secciones: list[Seccion] = []
    pila: list[str] = []
    for idx, (linea_ini, nivel, titulo) in enumerate(encontrados):
        fin = (
            encontrados[idx + 1][0] - 1
            if idx + 1 < len(encontrados)
            else len(lineas)
        )
        del pila[nivel - 1 :]
        while len(pila) < nivel - 1:
            pila.append("")
        pila.append(titulo)
        secciones.append(
            Seccion(
                ruta=ruta_rel,
                titulo=titulo,
                nivel=nivel,
                linea_inicio=linea_ini,
                linea_fin=fin,
                ruta_titulos=[t for t in pila if t],
            )
        )
    return secciones


def construir() -> dict:
    """Recorre `docs/` y devuelve el índice completo, listo para serializar."""
    documentos: list[dict] = []
    for archivo in sorted(DOCS.rglob("*.md")):
        ruta_rel = archivo.relative_to(RAIZ).as_posix()
        if ruta_rel in {
            MD_SALIDA.relative_to(RAIZ).as_posix(),
        }:
            continue
        texto = archivo.read_text(encoding="utf-8", errors="replace")
        lineas = texto.split("\n")
        campos = _frontmatter(texto)
        estado = campos.get("estado", "")

        secs = _secciones(ruta_rel, lineas)
        # Términos por sección: título + su ruta de títulos + el cuerpo. El
        # cuerpo se recorta: las primeras 1200 palabras de una sección ya
        # contienen su vocabulario, y guardar el resto engorda el índice sin
        # mejorar el acierto.
        secciones_json = []
        for s in secs:
            cuerpo = "\n".join(lineas[s.linea_inicio : s.linea_fin])
            terminos = sorted(
                set(_tokens(" ".join(s.ruta_titulos)) + _tokens(cuerpo[:9000]))
            )
            secciones_json.append(
                {
                    "titulo": s.titulo,
                    "nivel": s.nivel,
                    "ruta_titulos": s.ruta_titulos,
                    "desde": s.linea_inicio,
                    "hasta": s.linea_fin,
                    "lineas": s.lineas,
                    "terminos": terminos,
                }
            )

        documentos.append(
            {
                "ruta": ruta_rel,
                "tipo": campos.get("tipo", ""),
                "estado": estado,
                "revisado": campos.get("revisado", ""),
                "revisar_cada": campos.get("revisar_cada", ""),
                "claves": [
                    c.strip()
                    for c in campos.get("claves", "").split(",")
                    if c.strip()
                ],
                "vivo": estado not in ESTADOS_MUERTOS,
                "lineas": len(lineas),
                "titulo": next(
                    (s.titulo for s in secs if s.nivel == 1),
                    Path(ruta_rel).stem,
                ),
                "secciones": secciones_json,
            }
        )

    vivos = [d for d in documentos if d["vivo"]]
    return {
        "version": 1,
        "generado_por": "scripts/indexar.py",
        "documentos_total": len(documentos),
        "documentos_vivos": len(vivos),
        "secciones_total": sum(len(d["secciones"]) for d in documentos),
        "documentos": documentos,
    }


# --------------------------------------------------------------------------
# Consulta
# --------------------------------------------------------------------------
def buscar(indice: dict, consulta: str, limite: int = 8) -> list[dict]:
    """Devuelve las secciones que mejor responden a `consulta`, ya ordenadas.

    La puntuación pondera dónde aparece el término, no cuántas veces: un
    término en el título de la sección dice mucho más que el mismo término
    suelto en el cuerpo, y contar repeticiones premia a los documentos largos
    justamente donde queremos premiar a los precisos.
    """
    pedidos = _tokens(consulta)
    if not pedidos:
        return []

    resultados: list[dict] = []
    for doc in indice["documentos"]:
        toks_ruta = set(_tokens(doc["ruta"]))
        toks_claves = set(_tokens(" ".join(doc["claves"])))
        for sec in doc["secciones"]:
            toks_titulo = set(_tokens(" ".join(sec["ruta_titulos"]) or sec["titulo"]))
            toks_cuerpo = set(sec["terminos"])

            puntos = 0.0
            aciertos = 0
            for t in pedidos:
                encontrado = False
                if t in toks_titulo:
                    puntos += 5.0
                    encontrado = True
                if t in toks_claves:
                    puntos += 4.0
                    encontrado = True
                if t in toks_ruta:
                    puntos += 3.0
                    encontrado = True
                if t in toks_cuerpo:
                    puntos += 1.0
                    encontrado = True
                aciertos += encontrado

            if not aciertos:
                continue
            # Cubrir todos los términos vale más que acertar mucho en uno.
            puntos *= aciertos / len(pedidos)
            # Una sección de 400 líneas que menciona el término no es una
            # respuesta; es otro documento que hay que leer entero.
            if sec["lineas"] > 120:
                puntos *= 0.7
            if not doc["vivo"]:
                puntos *= _PENALIZACION_ARCHIVO

            resultados.append(
                {
                    "puntos": round(puntos, 2),
                    "ruta": doc["ruta"],
                    "titulo_doc": doc["titulo"],
                    "seccion": " > ".join(sec["ruta_titulos"]) or sec["titulo"],
                    "desde": sec["desde"],
                    "hasta": sec["hasta"],
                    "lineas": sec["lineas"],
                    "estado": doc["estado"],
                    "vivo": doc["vivo"],
                }
            )

    resultados.sort(key=lambda r: (-r["puntos"], r["ruta"], r["desde"]))
    return resultados[:limite]


def _imprimir_resultados(resultados: list[dict], consulta: str) -> None:
    if not resultados:
        print(f"Sin resultados para «{consulta}».")
        print("Prueba con el término preferente del glosario "
              "(docs/dominio/02-GLOSARIO.md).")
        return
    print(f"{len(resultados)} sección(es) para «{consulta}»:\n")
    for r in resultados:
        marca = "" if r["vivo"] else f"  [{r['estado']}]"
        print(f"  {r['puntos']:>6.2f}  {r['seccion']}{marca}")
        print(f"          sed -n '{r['desde']},{r['hasta']}p' {r['ruta']}"
              f"   ({r['lineas']} líneas)")
    print()


# --------------------------------------------------------------------------
# Serialización
# --------------------------------------------------------------------------
def _md_texto(indice: dict) -> str:
    """El índice legible: qué documento vivo existe, de qué trata y qué tan fresco es."""
    vivos = [d for d in indice["documentos"] if d["vivo"]]
    por_tipo: dict[str, list[dict]] = {}
    for d in vivos:
        por_tipo.setdefault(d["tipo"] or "sin-tipo", []).append(d)

    orden = ["gestion", "epica", "referencia", "guia", "runbook", "adr", "marco",
             "informe", "plan", "sin-tipo"]
    claves_ordenadas = sorted(
        por_tipo, key=lambda t: (orden.index(t) if t in orden else 99, t)
    )

    out: list[str] = []
    out.append("---")
    out.append("tipo: referencia")
    out.append("responsable: propietario")
    out.append("estado: vigente")
    out.append("revisado: 2026-08-28")
    out.append("revisar_cada: nunca")
    out.append("---")
    out.append("")
    out.append("# INDICE.md — mapa del conocimiento")
    out.append("")
    out.append("> **Generado por `scripts/indexar.py`. No se edita a mano.**")
    out.append("> Se abre bajo demanda para saber qué documento abrir; para ir a la")
    out.append("> sección exacta, `python scripts/indexar.py buscar \"<términos>\"`.")
    out.append("")
    out.append(
        f"{indice['documentos_vivos']} documentos vivos · "
        f"{indice['documentos_total'] - indice['documentos_vivos']} archivados · "
        f"{indice['secciones_total']} secciones indexadas."
    )
    out.append("")

    for tipo in claves_ordenadas:
        docs = sorted(por_tipo[tipo], key=lambda d: d["ruta"])
        out.append(f"## {tipo}")
        out.append("")
        out.append("| Documento | De qué trata | Revisado | Líneas |")
        out.append("|---|---|---|---|")
        for d in docs:
            # El «de qué trata» sale de los encabezados de nivel 2, que es lo
            # más cercano a un resumen que el documento declara de sí mismo.
            h2 = [s["titulo"] for s in d["secciones"] if s["nivel"] == 2][:4]
            resumen = " · ".join(h2) if h2 else d["titulo"]
            if len(resumen) > 110:
                resumen = resumen[:107] + "…"
            resumen = resumen.replace("|", "\\|")
            ruta = d["ruta"].removeprefix("docs/")
            out.append(
                f"| [`{ruta}`]({ruta}) | {resumen} | {d['revisado'] or '—'} "
                f"| {d['lineas']} |"
            )
        out.append("")

    out.append("## Archivados")
    out.append("")
    muertos = sorted(
        (d for d in indice["documentos"] if not d["vivo"]), key=lambda d: d["ruta"]
    )
    out.append(
        f"{len(muertos)} documentos con estado `archivado` o `historico`. Se "
        "indexan y se pueden consultar, pero nunca compiten con uno vivo en la "
        "búsqueda: responden «por qué se decidió aquello», no «cómo funciona esto»."
    )
    out.append("")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="comando")
    p_buscar = sub.add_parser("buscar", help="consulta el índice")
    p_buscar.add_argument("consulta", nargs="+")
    p_buscar.add_argument("-n", type=int, default=8, help="cuántas secciones")
    ap.add_argument(
        "--verificar",
        action="store_true",
        help="no escribe; exit 1 si los artefactos quedaron desfasados",
    )
    args = ap.parse_args()

    if args.comando == "buscar":
        # Se construye en memoria a propósito: ver el encabezado del módulo.
        indice = construir()
        consulta = " ".join(args.consulta)
        _imprimir_resultados(buscar(indice, consulta, args.n), consulta)
        return 0

    indice = construir()
    md_nuevo = _md_texto(indice)

    if args.verificar:
        actual = MD_SALIDA.read_text(encoding="utf-8") if MD_SALIDA.is_file() else ""
        if actual != md_nuevo:
            print(f"Desfasado: {MD_SALIDA.relative_to(RAIZ).as_posix()}")
            print("Corre `python scripts/indexar.py` y súbelo con el cambio.")
            return 1
        print(
            f"OK — índice al día ({indice['documentos_vivos']} documentos vivos, "
            f"{indice['secciones_total']} secciones)."
        )
        return 0

    MD_SALIDA.write_text(md_nuevo, encoding="utf-8")
    print(
        f"Escrito {MD_SALIDA.relative_to(RAIZ)}: "
        f"{indice['documentos_vivos']} documentos vivos, "
        f"{indice['secciones_total']} secciones."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
