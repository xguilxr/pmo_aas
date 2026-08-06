"""DOC-03 — el diagrama entidad-relación se genera del modelo, no se dibuja.

> «Lo que pueda generarse a partir del código DEBE generarse. El contenido
> generado NO DEBE editarse manualmente.»

`docs/architecture/database.md` llevaba un `erDiagram` escrito a mano y una
sección titulada «la tabla de tablas (**las 49 reales**)». Las tablas eran
**56**. Siete de más, y nadie lo notó — que es exactamente lo que le pasa a un
diagrama a mano: no falla, envejece.

## Cómo se genera

De `Base.metadata`, que es el mismo origen del que Alembic saca las migraciones.
No de las migraciones ni de una base viva: las migraciones son la historia y una
base viva puede ir por detrás. El modelo es lo que el código cree.

Las relaciones salen de las **claves foráneas declaradas**, y la cardinalidad de
si la columna admite nulo (`|o` opcional / `||` obligatoria) y de si es única
(`o{` muchos / `o|` uno). Nada de eso es interpretación: está en el esquema.

## Por qué un archivo entero y no un bloque marcado

«El contenido generado NO DEBE editarse manualmente» necesita una frontera que
se vea. Un bloque entre marcas dentro de un documento a mano invita a retocar
«solo esta línea», y el retoque sobrevive hasta la siguiente regeneración, que
lo borra sin avisar. Un archivo completo generado no tiene esa ambigüedad:
`database.md` explica y enlaza; `er-generado.md` se reescribe entero.

## Qué NO genera, y por qué

La descripción en prosa de cada tabla —para qué sirve, qué invariantes tiene—
no está en el modelo y no se puede derivar. Se queda en `database.md`, escrita
por personas, que es donde aporta. Generar lo generable no significa generar lo
que no lo es.

Uso:

    python scripts/generar_er.py              # reescribe el documento
    python scripts/generar_er.py --verificar  # exit 1 si quedó desfasado

La frescura la vigila `tests/test_doc03_er_generado.py`, dentro de la suite de
la API — que es donde están las dependencias del modelo, y así no hace falta
una verificación requerida más en la protección de `main`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
API = RAIZ / "apps" / "api"
DESTINO = RAIZ / "docs" / "architecture" / "er-generado.md"

CABECERA = """\
---
tipo: referencia
responsable: propietario
estado: vigente
revisado: {fecha}
revisar_cada: nunca
---

<!-- GENERADO POR scripts/generar_er.py — NO EDITAR A MANO.
     Se deriva de `Base.metadata`, el mismo origen del que Alembic saca las
     migraciones. Cualquier edición aquí la borra la siguiente regeneración.
     Para cambiar el diagrama, cambiá el modelo. -->

# Diagrama entidad-relación — generado

**No se edita a mano** (MCS DOC-03). Lo produce `scripts/generar_er.py` desde
`Base.metadata`, y `tests/test_doc03_er_generado.py` falla si queda desfasado.

La descripción en prosa de cada tabla vive en
[`database.md`](database.md): eso no está en el modelo y no se puede derivar.

**{n_tablas} tablas · {n_relaciones} relaciones declaradas por clave foránea.**

```mermaid
erDiagram
{cuerpo}
```
"""


def _cargar_metadata():
    sys.path.insert(0, str(API))
    from app.db.base import Base

    import app.models  # noqa: F401  — registra todos los modelos en el metadata

    return Base.metadata


def _cardinalidad(columna, unica: bool) -> str:
    """Lado hijo del enlace, deducido del esquema y de nada más.

    - `o{` muchos · `o|` a lo sumo uno (la clave foránea es única)
    - el prefijo `}`/`|` lo pone Mermaid al escribir el enlace completo
    """
    lado_hijo = "o|" if unica else "o{"
    lado_padre = "||" if not columna.nullable else "|o"
    return f"{lado_padre}--{lado_hijo}"


def diagrama(metadata) -> tuple[str, int, int]:
    """`(cuerpo mermaid, nº de tablas, nº de relaciones)`."""
    unicas = {
        tabla.name: {
            tuple(c.name for c in restriccion.columns)
            for restriccion in tabla.constraints
            if restriccion.__class__.__name__ == "UniqueConstraint"
        }
        | {tuple(c.name for c in indice.columns) for indice in tabla.indexes if indice.unique}
        for tabla in metadata.tables.values()
    }

    lineas = []
    for nombre in sorted(metadata.tables):
        tabla = metadata.tables[nombre]
        for columna in sorted(tabla.columns, key=lambda c: c.name):
            for foranea in sorted(columna.foreign_keys, key=lambda fk: fk.target_fullname):
                padre = foranea.column.table.name
                enlace = _cardinalidad(columna, (columna.name,) in unicas[nombre])
                lineas.append(
                    f"    {padre.upper()} {enlace} {nombre.upper()} : {columna.name}"
                )

    # Las tablas sin ninguna clave foránea no aparecerían en ningún enlace y
    # desaparecerían del diagrama. Se declaran sueltas: una tabla huérfana en el
    # modelo es información, no ruido.
    enlazadas = {p.split()[0].lower() for p in lineas} | {
        p.split()[2].lower() for p in lineas
    }
    sueltas = [n for n in sorted(metadata.tables) if n not in enlazadas]
    lineas.extend(f"    {n.upper()} {{ }}" for n in sueltas)

    return "\n".join(lineas), len(metadata.tables), len(lineas) - len(sueltas)


def render(metadata, fecha: str) -> str:
    cuerpo, n_tablas, n_relaciones = diagrama(metadata)
    return CABECERA.format(
        fecha=fecha, cuerpo=cuerpo, n_tablas=n_tablas, n_relaciones=n_relaciones
    )


def _fecha_actual(anterior: str | None) -> str:
    """Conserva la fecha si el contenido no cambia.

    Sin esto, cada corrida movería `revisado` y el documento aparecería como
    tocado en cada PR — ruido que enseña a ignorar el diff de un generado.
    """
    import datetime as dt

    return anterior or dt.date.today().isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verificar", action="store_true", help="exit 1 si está desfasado")
    args = parser.parse_args()

    metadata = _cargar_metadata()
    previo = DESTINO.read_text(encoding="utf-8") if DESTINO.is_file() else None
    fecha_previa = None
    if previo:
        for linea in previo.splitlines():
            if linea.startswith("revisado:"):
                fecha_previa = linea.split(":", 1)[1].strip()
                break

    # Se compara sin la fecha para no confundir «desfasado» con «regenerado hoy».
    nuevo_con_fecha_previa = render(metadata, _fecha_actual(fecha_previa))

    if args.verificar:
        if previo == nuevo_con_fecha_previa:
            print("OK — el diagrama ER coincide con el modelo")
            return 0
        print(
            "DOC-03 — `docs/architecture/er-generado.md` no coincide con "
            "`Base.metadata`.\n\n"
            "El modelo cambió y el generado no. Corré "
            "`python scripts/generar_er.py` y commiteá el resultado; NO lo "
            "edites a mano.",
            file=sys.stderr,
        )
        return 1

    contenido = render(metadata, _fecha_actual(fecha_previa) if previo == nuevo_con_fecha_previa else _fecha_actual(None))
    DESTINO.write_text(contenido, encoding="utf-8")
    _, n_tablas, n_relaciones = diagrama(metadata)
    print(f"escrito {DESTINO.relative_to(RAIZ)}: {n_tablas} tablas, {n_relaciones} relaciones")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
