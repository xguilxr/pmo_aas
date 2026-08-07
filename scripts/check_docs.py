"""DOC-01 — todo documento declara responsable, estado y régimen de revisión.

> «Todo documento DEBE declarar responsable, estado, fecha de revisión y
> periodicidad de revisión.»

La auditoría lo midió sin ambigüedad: **0 de 64 documentos** de `docs/` lo
declaraban. Hoy son 123 y el único que lo traía era `MCS-CORE`, porque llegó de
fuera con su propio encabezado.

## Por qué no es papeleo

Un documento sin estado no se puede distinguir de uno vigente. Este repositorio
ya tropezó con eso dos veces, y las dos costaron trabajo real:

- `docs/dominio/02-GLOSARIO.md` decía «borrador, nada adoptado» **en el
  cuerpo**, y `LEN-01` quedó ALTA por eso hasta que alguien lo leyó entero.
- `docs/design-system/tokens.md` describe una paleta anterior a D-7 y ADR-023.
  Está declarado obsoleto **en `SPRINT.md`**, o sea en otro archivo: quien abra
  el documento no tiene forma de saberlo.

El estado tiene que viajar **con** el documento.

## El encabezado

```yaml
---
responsable: propietario
estado: vigente
revisado: 2026-08-06
revisar_cada: 90d
---
```

Los cuatro campos son los que el requisito nombra, ni uno más: un encabezado
que pide diez campos se rellena a copiar-pegar y deja de significar nada.

**`revisado` es una declaración humana**, no la fecha del último commit. La
siembra inicial sí salió de `git log` —era el único dato honesto disponible
para 123 archivos, y mejor que inventar una fecha—, pero a partir de ahí la
mueve quien revisa. Cambiarla sin haber leído el documento es mentir en un
campo que otros usan para decidir si fiarse.

## Qué NO hace, y por qué

**No falla cuando un documento vence.** Eso es `DOC-07` («ventana de revisión y
señalización»), y sigue abierto a propósito: un gate que se pone rojo con el
paso del tiempo, sin que nadie toque nada, se desactiva la primera semana. Los
vencidos se **informan** al final de la corrida, que es la mitad que sí se
puede sostener hoy.

Uso:

    python scripts/check_docs.py            # verifica
    python scripts/check_docs.py --sembrar  # añade el encabezado que falte
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

#: Los campos exigidos. Los cuatro primeros son DOC-01; `tipo` es DOC-02.
CAMPOS = ("tipo", "responsable", "estado", "revisado", "revisar_cada")

#: MCS DOC-02 — «todo documento DEBE declarar su tipo conforme a un esquema
#: definido y respetar su propósito».
#:
#: El esquema **se derivó del árbol que ya existe**, no se inventó: son las
#: clases de documento que el repositorio ya escribía, cada una con el propósito
#: que de hecho cumple. Inventar una taxonomía y luego forzar 129 documentos
#: dentro produce etiquetas que nadie respeta.
#:
#: El propósito no es adorno. Es la mitad del requisito que un campo libre no
#: cubre: sin él, `tipo` sería una palabra y no un contrato. Que un documento lo
#: respete lo juzga quien revisa; que lo **declare** lo exige este gate.
TIPOS = {
    "epica": "Qué hace el producto, en lenguaje funcional. Viva; se actualiza con el comportamiento",
    "adr": "Una decisión arquitectónica y su porqué. Inmutable: se reemplaza, no se edita",
    "informe": "Una medición con fecha. Es expediente: no se corrige a posteriori",
    "plan": "Trabajo por hacer y en qué orden. Se mueve; queda obsoleto por diseño",
    "guia": "Cómo se hace algo aquí. Procedimiento repetible",
    "runbook": "Pasos ante una situación concreta de operación, ejecutables bajo presión",
    "referencia": "Hechos consultables: glosario, esquema, catálogo de tokens",
    "marco": "Documento normativo recibido de fuera. No se edita ni una coma",
    "gestion": "Estado del trabajo: sprint, puente entre sesiones, backlog",
    "archivo": "Retirado del uso. Se conserva por trazabilidad, no para leerse",
}

#: Estados admitidos. `historico` es para lo fechado —un informe de auditoría
#: del 2026-08-03 no se revisa, se sustituye por el siguiente— y se distingue
#: de `archivado`, que es lo que se retiró del uso.
ESTADOS = {"vigente", "borrador", "archivado", "historico", "reemplazado"}

#: Periodicidades admitidas. `nunca` es legítimo y por eso está: obligar a una
#: fecha de revisión sobre un documento inmutable produce revisiones de mentira.
PERIODOS = {"30d", "90d", "180d", "365d", "nunca"}

#: Documentos fuera del árbol de `docs/` que también son documentos.
RAIZ_INCLUIDOS = ("README.md", "CLAUDE.md", "SECURITY.md", "RAILWAY_SETUP.md")

#: Régimen por defecto al sembrar, por zona. Es el punto de partida, no una
#: verdad: quien conozca un documento ajusta el suyo.
REGIMEN = (
    ("docs/archive/", "archivado", "nunca", "archivo"),
    ("docs/adr/", "vigente", "nunca", "adr"),   # una ADR aceptada no se revisa: se reemplaza
    ("docs/project-management/", "vigente", "30d", "gestion"),
    ("docs/epics/", "vigente", "90d", "epica"),
    ("docs/dominio/", "vigente", "90d", "referencia"),
    ("docs/design-system/", "vigente", "90d", "referencia"),
    ("docs/architecture/", "vigente", "180d", "referencia"),
    ("docs/runbooks/", "vigente", "180d", "runbook"),
    ("docs/conformidad/marco/", "vigente", "90d", "marco"),
    ("docs/conformidad/plan", "vigente", "30d", "plan"),
    ("docs/conformidad/", "historico", "nunca", "informe"),  # informes fechados
    ("CLAUDE.md", "vigente", "90d", "guia"),                 # se lee en cada turno
    ("", "vigente", "180d", "guia"),                         # el resto
)

_FRONT = re.compile(r"\A---\n(.*?)\n---\n", re.S)
_CAMPO = re.compile(r"^([a-z_]+):\s*(.+?)\s*$", re.M)


def documentos() -> list[Path]:
    del_arbol = sorted(x for x in (RAIZ / "docs").rglob("*.md"))
    de_raiz = [RAIZ / n for n in RAIZ_INCLUIDOS if (RAIZ / n).is_file()]
    return sorted(del_arbol + de_raiz)


def encabezado(texto: str) -> dict[str, str] | None:
    """Los campos del front-matter, o `None` si no hay."""
    m = _FRONT.match(texto)
    return dict(_CAMPO.findall(m.group(1))) if m else None


def revisar(relativa: str, texto: str, hoy: dt.date) -> list[str]:
    """Motivos por los que el documento no cumple DOC-01. Vacío = cumple."""
    campos = encabezado(texto)
    if campos is None:
        return [
            "no declara encabezado. Sin él, quien lo abre no puede saber si "
            "sigue vigente ni a quién preguntarle"
        ]

    problemas = []
    for campo in CAMPOS:
        if not campos.get(campo):
            problemas.append(f"no declara `{campo}`")

    if (tipo := campos.get("tipo")) and tipo not in TIPOS:
        problemas.append(
            f"`tipo: {tipo}` no está en el esquema. Los definidos son "
            f"{sorted(TIPOS)}; cada uno con su propósito en `TIPOS`. Si de "
            f"verdad hace falta una clase nueva, se añade ahí con su propósito "
            f"escrito — no se cuela como texto libre."
        )
    if (estado := campos.get("estado")) and estado not in ESTADOS:
        problemas.append(f"`estado: {estado}` no es uno de {sorted(ESTADOS)}")
    if (periodo := campos.get("revisar_cada")) and periodo not in PERIODOS:
        problemas.append(f"`revisar_cada: {periodo}` no es uno de {sorted(PERIODOS)}")

    if bruto := campos.get("revisado"):
        try:
            fecha = dt.date.fromisoformat(str(bruto).strip("'\""))
        except ValueError:
            problemas.append(f"`revisado: {bruto}` no es una fecha AAAA-MM-DD")
        else:
            if fecha > hoy:
                problemas.append(
                    f"`revisado: {fecha}` está en el futuro. Una revisión que no "
                    f"ha ocurrido no se declara"
                )
    return problemas


def vencido(campos: dict[str, str], hoy: dt.date) -> int | None:
    """Días de retraso de la revisión, o `None` si no aplica o está al día."""
    periodo = campos.get("revisar_cada", "nunca")
    if periodo == "nunca" or campos.get("estado") in {"archivado", "historico"}:
        return None
    try:
        fecha = dt.date.fromisoformat(str(campos.get("revisado", "")).strip("'\""))
    except ValueError:
        return None
    retraso = (hoy - fecha).days - int(periodo.rstrip("d"))
    return retraso if retraso > 0 else None


def _ultimo_toque(ruta: Path, respaldo: dt.date) -> dt.date:
    """La fecha del último commit que tocó el archivo.

    El dato más honesto disponible para sembrar 123 encabezados: no dice que
    alguien lo revisara, dice cuándo se miró por última vez. Inventar una fecha
    habría sido peor, y poner la de hoy en todos habría vencido a todos a la vez.
    """
    salida = subprocess.run(  # noqa: S603
        ["git", "log", "-1", "--format=%ad", "--date=short", "--", str(ruta)],
        cwd=RAIZ,
        capture_output=True,
        text=True,
    ).stdout.strip()
    try:
        return dt.date.fromisoformat(salida)
    except ValueError:
        return respaldo


def _regimen(relativa: str) -> tuple[str, str, str]:
    for prefijo, estado, periodo, tipo in REGIMEN:
        if relativa.startswith(prefijo):
            return estado, periodo, tipo
    raise AssertionError("REGIMEN debe terminar con una entrada comodín")


def sembrar(hoy: dt.date) -> int:
    """Añade el encabezado que falte, y completa el campo que falte al que ya lo tiene.

    Lo segundo hizo falta al llegar DOC-02: los 129 documentos ya traían
    encabezado de DOC-01, así que una siembra que solo mirara «¿tiene
    encabezado?» no habría añadido `tipo` a ninguno. Sembrar campo a campo es lo
    que hace que ampliar el esquema no sea una tarde de edición manual.
    """
    nuevos = completados = 0
    for archivo in documentos():
        texto = archivo.read_text(encoding="utf-8")
        relativa = archivo.relative_to(RAIZ).as_posix()
        estado, periodo, tipo = _regimen(relativa)
        campos = encabezado(texto)

        if campos is None:
            cabecera = (
                "---\n"
                f"tipo: {tipo}\n"
                "responsable: propietario\n"
                f"estado: {estado}\n"
                f"revisado: {_ultimo_toque(archivo, hoy)}\n"
                f"revisar_cada: {periodo}\n"
                "---\n\n"
            )
            archivo.write_text(cabecera + texto.lstrip("\n"), encoding="utf-8")
            nuevos += 1
            continue

        faltan = [c for c in CAMPOS if not campos.get(c)]
        if not faltan:
            continue
        # `tipo` va primero: es lo que dice qué se está leyendo.
        añadir = "".join(
            f"{c}: {tipo if c == 'tipo' else estado if c == 'estado' else periodo}\n"
            for c in faltan
        )
        archivo.write_text(texto.replace("---\n", "---\n" + añadir, 1), encoding="utf-8")
        completados += 1

    print(f"encabezados nuevos: {nuevos} · campos completados en: {completados}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sembrar", action="store_true", help="añade el encabezado que falte")
    args = parser.parse_args()

    hoy = dt.date.today()
    if args.sembrar:
        return sembrar(hoy)

    fallos: list[tuple[str, list[str]]] = []
    vencidos: list[tuple[str, int]] = []
    for archivo in documentos():
        relativa = archivo.relative_to(RAIZ).as_posix()
        texto = archivo.read_text(encoding="utf-8")
        if motivos := revisar(relativa, texto, hoy):
            fallos.append((relativa, motivos))
        elif (retraso := vencido(encabezado(texto) or {}, hoy)) is not None:
            vencidos.append((relativa, retraso))

    if vencidos:
        # DOC-07, no DOC-01: se informa, no se falla. Un gate que enrojece con
        # el paso del tiempo se desactiva la primera semana.
        print(f"{len(vencidos)} documento(s) con la revisión vencida:")
        for relativa, retraso in sorted(vencidos, key=lambda x: -x[1])[:15]:
            print(f"  - {relativa} ({retraso} días de retraso)")
        print()

    if fallos:
        print(f"DOC-01 — {len(fallos)} de {len(documentos())} documentos sin declarar:\n")
        for relativa, motivos in fallos:
            print(f"  {relativa}")
            for motivo in motivos:
                print(f"    - {motivo}")
        print(
            "\nEl encabezado son cuatro campos: responsable, estado, revisado y "
            "revisar_cada. `python scripts/check_docs.py --sembrar` pone el que "
            "falte con el régimen por defecto de su zona."
        )
        return 1

    print(f"OK — {len(documentos())} documentos declaran tipo, responsable, estado y revisión")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
