"""ENH-202 — una sola fuente para todo lo que el usuario se lleva.

US-193 puso Helvetica en el Excel del plan y dejó escrito que era «el primer
cambio masivo de fuente». Este módulo es el resto: los XLSX del backend, los PDF,
los DOCX y el Excel del portafolio salían cada uno con la suya —Calibri en Excel,
el default de Word en los DOCX y, en los PDF, **ni siquiera la que declaraban**—.

**El hallazgo del PDF, medido y no supuesto.** `templates/pdf/base.html` pedía
`"DM Sans", "Helvetica Neue", Helvetica, Arial, sans-serif` y la imagen solo
instala `fonts-dejavu-core`, así que ninguna de las cuatro existía y fontconfig
caía a DejaVu Sans. Comprobado con WeasyPrint 68.1: con solo DejaVu disponible,
`fc-match Helvetica` devuelve `DejaVuSans.ttf`; con `fonts-urw-base35` instalado
—el paquete que trae Nimbus Sans, el clon de Helvetica— el PDF incrusta
`NimbusSans`. Por eso ENH-202 no es solo cambiar cadenas de CSS: sin el paquete
en el `Dockerfile`, declarar Helvetica no la trae.

Todo apunta aquí para que la próxima vez sea un archivo y no cinco.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from docx.document import Document as DocxDocument
    from openpyxl import Workbook

#: El nombre, tal cual se escribe en Excel y en Word.
#:
#: En Windows, Excel sustituye Helvetica por Arial automáticamente y las métricas
#: coinciden, así que el documento se ve igual. Es la razón por la que US-193 la
#: eligió en vez de la fuente de marca (DM Sans), que el cliente no tiene
#: instalada y Office reemplazaría por cualquier cosa.
FUENTE = "Helvetica"

#: La pila para CSS y SVG. `Nimbus Sans` va explícita porque es lo que de verdad
#: hay en la imagen: si algún día se cae el alias de fontconfig, el PDF sigue
#: saliendo con métricas de Helvetica en vez de con la sans genérica.
PILA_CSS = 'Helvetica, "Nimbus Sans", Arial, sans-serif'


def aplicar_a_workbook(wb: Workbook) -> None:
    """Deja Helvetica como fuente de **todas** las celdas del libro.

    Se sustituye la **fuente número 0** del libro y no se recorre celda por
    celda: todo lo que no declara un estilo propio apunta a esa, que es la
    inmensa mayoría de un export. Recorrer las celdas sería tanto trabajo como
    olvidarse de una.

    Dos trampas, las dos comprobadas leyendo el `xl/styles.xml` generado:

    1. **Asignar `NamedStyle.font = Font(...)` no basta.** openpyxl lo *añade*
       a la tabla —queda como la número 1— mientras el `cellXf` por defecto
       sigue apuntando a la 0, que es Calibri. El archivo sale con Helvetica
       declarada y ninguna celda usándola.
    2. **Mutar `wb._fonts[0].name` funciona… y contamina.** El `Font` por
       defecto es **el mismo objeto en todos los libros** del proceso
       (`Workbook()._fonts[0] is Workbook()._fonts[0]` → `True`), así que
       cambiarle el nombre se lo cambia a cualquier Excel que se genere
       después, aunque no haya pasado por aquí. Peor todavía: hace que una
       prueba de esto pase por el motivo equivocado.

    De ahí la sustitución del elemento de la lista, que es local al libro.

    Las celdas que sí traen su `Font` —cabeceras en negrita, semáforos de
    color— siguen mandando, y por eso llevan el nombre puesto a mano.
    """
    from openpyxl.styles import Font

    wb._fonts[0] = Font(name=FUENTE, sz=wb._fonts[0].sz or 11)


def aplicar_a_docx(doc: DocxDocument) -> None:
    """Deja Helvetica como fuente del estilo `Normal` del documento.

    El `w:eastAsia` no es decorativo: sin él, Word usa la fuente asiática por
    defecto para cualquier carácter que considere de ese rango y el documento
    sale con dos tipografías mezcladas.
    """
    from docx.oxml.ns import qn

    estilo = doc.styles["Normal"]
    estilo.font.name = FUENTE
    estilo.element.rPr.rFonts.set(qn("w:eastAsia"), FUENTE)
