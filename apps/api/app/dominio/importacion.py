"""US-216 — Importación masiva: qué columnas se esperan y qué hace inválida una fila.

Nace del artboard «Onboarding masivo — Importación» y del bloque B5: «cubre la
carga inicial de 23 proyectos sin captura manual». Un cliente que llega con una
cartera hecha no la va a teclear proyecto por proyecto, y si tiene que hacerlo,
no llega.

## Qué importa esto y qué no

Dos clases: **proyectos** y **recursos**. Los **planes** ya tienen su importador
—`/projects/{id}/tasks/import`, con vista previa, mapeo de columnas y ayuda de
IA (US-070, US-188)— y es por proyecto porque un WBS es del proyecto: el `1.2` de
uno no es el `1.2` de otro. Duplicar aquí ese camino daría dos importadores de lo
mismo que divergen; lo que hace falta es lo de arriba, que no existía.

## Por qué una fila inválida no detiene el archivo

Un archivo de 23 proyectos con un error en el 7 tiene 22 filas buenas. Abortar
entero obliga a arreglar y resubir a ciegas —sin saber si hay más errores
detrás—, que es el bucle que hace abandonar una importación. Se valida **todo**,
se reporta fila por fila, y se confirma lo válido.

La consecuencia es que hay que distinguir tres estados por fila y no dos:

- **`valida`** — se va a crear.
- **`invalida`** — le falta algo obligatorio o tiene un valor que no existe. No
  se crea, y el mensaje dice qué columna y por qué.
- **`duplicada`** — ya hay una igual. No se crea **y no se actualiza**.

## Por qué una duplicada se salta y no se actualiza

Es la decisión con más consecuencias de este módulo. Una importación masiva se
corre dos veces —se cayó la red, alguien la repitió, el archivo llegó
corregido—, y las dos alternativas son peores:

- **Duplicar** convierte 23 proyectos en 46 y no hay forma barata de deshacerlo.
- **Actualizar en silencio** pisa lo que alguien editó a mano después de la
  primera corrida. El caso concreto: se importa, el PM corrige las fechas en la
  aplicación, alguien resube el Excel original y las fechas vuelven atrás sin
  que nadie se enterase.

Saltar y reportar deja el trabajo hecho intacto y la decisión en manos de quien
la puede tomar. Actualizar en masa es otra operación, con su propia
confirmación, y no se disfraza de importación.

## Por qué el nombre es la clave de un proyecto

No hay identificador externo en un Excel que alguien mantiene a mano. El folio lo
genera la plataforma, así que en la primera carga no existe. El nombre es lo que
un humano usa para referirse a un proyecto, y dos proyectos con el mismo nombre en
la misma organización son indistinguibles para las personas que los miran — que
es la definición práctica de duplicado. Se compara normalizado (sin espacios de
sobra, sin distinguir mayúsculas) porque «Migración ERP» y «migracion erp  » son
el mismo proyecto escrito por dos personas.

Para un recurso la clave es el **correo**, que sí es único por definición. Un
recurso sin correo se compara por nombre, con la misma normalización y la misma
salvedad.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from datetime import date
from typing import Literal

from app.dominio.costo import PERIODOS as PERIODOS_DE_TARIFA
from app.dominio.proyecto import FASES, TIPOS

#: Qué se está importando.
Clase = Literal["projects", "resources"]

CLASES: tuple[Clase, ...] = ("projects", "resources")

#: Qué le pasa a una fila.
Estado = Literal["valida", "invalida", "duplicada"]


@dataclass(frozen=True)
class Columna:
    """Una columna esperada del archivo.

    `alias` son los encabezados que la gente escribe de verdad. No es una
    comodidad: sin ellos, la primera pantalla del importador es un mapeo manual
    de quince columnas, y ahí es donde se abandona.
    """

    clave: str
    etiqueta: str
    obligatoria: bool
    ayuda: str
    alias: tuple[str, ...] = ()
    #: Valores admitidos, si es un vocabulario cerrado.
    valores: tuple[str, ...] = ()
    #: `texto` | `fecha` | `entero` | `decimal`
    tipo: str = "texto"


COLUMNAS_DE_PROYECTO: tuple[Columna, ...] = (
    Columna(
        "name",
        "Nombre del proyecto",
        True,
        "Es la clave: dos proyectos con el mismo nombre en la misma "
        "organización son indistinguibles para quien los mira.",
        ("nombre", "proyecto", "project", "project name"),
    ),
    Columna(
        "type",
        "Tipo",
        True,
        "Sin tipo el proyecto no entra en la distribución ni en el "
        "presupuesto por tipo.",
        ("tipo", "categoria", "categoría"),
        TIPOS,
    ),
    Columna(
        "priority",
        "Prioridad",
        True,
        "1 a 5. Sin prioridad no se puede ordenar qué se atiende antes.",
        ("prioridad", "priority"),
        tipo="entero",
    ),
    Columna(
        "portfolio",
        "Portafolio",
        True,
        "Se busca por nombre dentro de la organización; si no existe, se crea. "
        "Sin portafolio el proyecto queda fuera de los reportes de cartera.",
        ("portafolio", "cartera", "portfolio"),
    ),
    Columna(
        "program",
        "Programa",
        False,
        "Opcional. Se busca por nombre dentro del portafolio; si no existe, se crea.",
        ("programa", "program"),
    ),
    Columna(
        "sponsor",
        "Sponsor",
        False,
        "Texto libre. Es de los datos que más falta en una cartera heredada.",
        ("patrocinador", "sponsor"),
    ),
    Columna(
        "pm_email",
        "Correo del PM",
        False,
        "Se busca entre los usuarios del inquilino. Si no existe, la fila se "
        "importa sin PM en vez de fallar: el proyecto vale más que el enlace.",
        ("pm", "project manager", "correo pm", "email pm"),
    ),
    Columna(
        "phase",
        "Fase",
        False,
        "Por defecto «preparacion». Una cartera heredada suele traer proyectos "
        "en ejecución, y forzarlos a preparación falsearía el tablero.",
        ("fase", "estado", "phase"),
        FASES,
    ),
    Columna(
        "start_date",
        "Fecha de inicio",
        False,
        "AAAA-MM-DD. Sin fechas el proyecto no aparece en el roadmap ni cuenta "
        "para el costo de sus asignaciones.",
        ("inicio", "fecha inicio", "start", "start date"),
        tipo="fecha",
    ),
    Columna(
        "end_date",
        "Fecha de fin",
        False,
        "AAAA-MM-DD. Si es anterior al inicio la fila se rechaza: una de las dos "
        "está mal y no se puede saber cuál.",
        ("fin", "fecha fin", "end", "end date"),
        tipo="fecha",
    ),
    Columna(
        "budget",
        "Presupuesto",
        False,
        "Número. Cero es un dato —un proyecto sin costo—, vacío es «no se sabe».",
        ("presupuesto", "budget", "monto"),
        tipo="decimal",
    ),
    Columna(
        "currency",
        "Moneda",
        False,
        "MXN, USD o EUR. Por defecto la del inquilino.",
        ("moneda", "currency", "divisa"),
        ("MXN", "USD", "EUR"),
    ),
)

#: Las obligatorias son el «tamaño pequeño» de la plantilla que pide el artboard.
#: No es una plantilla distinta: es la misma sin las opcionales, y por eso no
#: puede divergir de la grande.
COLUMNAS_DE_RECURSO: tuple[Columna, ...] = (
    Columna(
        "name",
        "Nombre",
        True,
        "Nombre completo de la persona.",
        ("nombre", "name", "recurso"),
    ),
    Columna(
        "email",
        "Correo",
        False,
        "Es la clave cuando está: un correo identifica a una persona sin "
        "ambigüedad. Sin él se compara por nombre, que se repite.",
        ("email", "correo", "e-mail"),
    ),
    Columna(
        "company",
        "Empresa",
        False,
        "Propia o proveedor.",
        ("empresa", "company", "proveedor"),
    ),
    Columna(
        "job_title",
        "Cargo",
        False,
        "El cargo organizacional, distinto del rol en un proyecto.",
        ("cargo", "puesto", "job title", "title"),
    ),
    Columna(
        "area",
        "Área funcional",
        False,
        "Se busca por nombre; si no existe, se crea.",
        ("area", "área", "area funcional"),
    ),
    Columna(
        "project_capacity_pct",
        "Capacidad para proyectos %",
        False,
        "0 a 100. Por defecto 100. Es el % real disponible descontando BAU.",
        ("capacidad", "capacidad proyectos", "disponibilidad"),
        tipo="entero",
    ),
    Columna(
        "fte_cost_rate",
        "Tarifa",
        False,
        "Número. Sin su unidad de tiempo no se puede usar para calcular costo.",
        ("tarifa", "costo", "rate", "cost rate"),
        tipo="decimal",
    ),
    Columna(
        "cost_rate_period",
        "Unidad de la tarifa",
        False,
        "hora, dia o mes. 2.100 por hora y 2.100 por mes son dos tarifas "
        "distintas: sin esto la tarifa no significa nada.",
        ("unidad tarifa", "periodo tarifa", "unidad"),
        PERIODOS_DE_TARIFA,
    ),
)

COLUMNAS: dict[str, tuple[Columna, ...]] = {
    "projects": COLUMNAS_DE_PROYECTO,
    "resources": COLUMNAS_DE_RECURSO,
}


def _sin_acentos(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )


def normalizar(texto: str | None) -> str:
    """La forma con la que se comparan nombres y encabezados.

    Sin acentos, sin mayúsculas, sin espacios de sobra. «Migración ERP» y
    «migracion erp  » son el mismo proyecto escrito por dos personas, y tratarlos
    como distintos es cómo una importación repetida duplica media cartera.
    """
    if not texto:
        return ""
    return " ".join(_sin_acentos(texto).lower().split())


def emparejar_columnas(encabezados: list[str], clase: str) -> dict[str, str | None]:
    """`clave del sistema → encabezado del archivo`, o `None` si no se encontró.

    Empareja por nombre normalizado contra la etiqueta y contra los alias. Es un
    mapeo automático y no una adivinanza: solo acierta cuando el encabezado
    coincide exactamente con algo declarado, y lo que no reconoce lo deja en
    `None` para que una persona lo mapee. Fallar en silencio a la columna
    parecida sería peor que no emparejar.
    """
    por_norma = {normalizar(h): h for h in encabezados if h}
    salida: dict[str, str | None] = {}
    for col in COLUMNAS.get(clase, ()):
        candidatos = (col.etiqueta, col.clave, *col.alias)
        encontrado = None
        for c in candidatos:
            if normalizar(c) in por_norma:
                encontrado = por_norma[normalizar(c)]
                break
        salida[col.clave] = encontrado
    return salida


@dataclass
class Problema:
    columna: str
    mensaje: str


@dataclass
class FilaLeida:
    numero: int
    valores: dict[str, object]
    estado: Estado = "valida"
    problemas: list[Problema] = field(default_factory=list)
    #: Con qué ya existente choca, cuando el estado es `duplicada`.
    choca_con: str | None = None

    def rechazar(self, columna: str, mensaje: str) -> None:
        self.estado = "invalida"
        self.problemas.append(Problema(columna, mensaje))


def _fecha(valor: str) -> date | None:
    try:
        return date.fromisoformat(valor.strip()[:10])
    except ValueError:
        return None


def validar_fila(
    numero: int, crudos: dict[str, str | None], clase: str
) -> FilaLeida:
    """Convierte y valida una fila. Nunca lanza: los errores van en la fila.

    Que no lance es la mitad del diseño. Una excepción a mitad del archivo
    perdería la validación de las filas siguientes, y quien subió el archivo
    volvería a subirlo para descubrir el error número dos.
    """
    fila = FilaLeida(numero=numero, valores={})
    for col in COLUMNAS.get(clase, ()):
        bruto = (crudos.get(col.clave) or "").strip()
        if not bruto:
            if col.obligatoria:
                fila.rechazar(
                    col.clave, f"«{col.etiqueta}» es obligatoria y viene vacía"
                )
            continue

        if col.valores:
            # Se compara normalizado: quien exporta de otra herramienta escribe
            # «Transformación» y el vocabulario dice «transformacion».
            elegido = next(
                (v for v in col.valores if normalizar(v) == normalizar(bruto)), None
            )
            if elegido is None:
                fila.rechazar(
                    col.clave,
                    f"«{bruto}» no es un valor de «{col.etiqueta}». "
                    f"Admitidos: {', '.join(col.valores)}",
                )
                continue
            fila.valores[col.clave] = elegido
            continue

        if col.tipo == "fecha":
            f = _fecha(bruto)
            if f is None:
                fila.rechazar(
                    col.clave, f"«{bruto}» no es una fecha AAAA-MM-DD"
                )
                continue
            fila.valores[col.clave] = f
            continue

        if col.tipo in ("entero", "decimal"):
            try:
                numero_leido = (
                    int(float(bruto.replace(",", "")))
                    if col.tipo == "entero"
                    else float(bruto.replace(",", ""))
                )
            except ValueError:
                fila.rechazar(col.clave, f"«{bruto}» no es un número")
                continue
            if numero_leido < 0:
                fila.rechazar(
                    col.clave, f"«{col.etiqueta}» no puede ser negativa"
                )
                continue
            fila.valores[col.clave] = numero_leido
            continue

        fila.valores[col.clave] = bruto

    _reglas_cruzadas(fila, clase)
    return fila


def _reglas_cruzadas(fila: FilaLeida, clase: str) -> None:
    """Lo que no se puede validar mirando una sola columna."""
    if clase == "projects":
        inicio = fila.valores.get("start_date")
        fin = fila.valores.get("end_date")
        if isinstance(inicio, date) and isinstance(fin, date) and fin < inicio:
            fila.rechazar(
                "end_date",
                "La fecha de fin es anterior a la de inicio",
            )
        prioridad = fila.valores.get("priority")
        if isinstance(prioridad, int) and not 1 <= prioridad <= 5:
            fila.rechazar("priority", "La prioridad va de 1 a 5")
        return

    if clase == "resources":
        # Una tarifa sin unidad de tiempo no se puede usar para nada (US-215).
        # No invalida la fila —la persona sí se puede crear— pero se avisa.
        tarifa = fila.valores.get("fte_cost_rate")
        if tarifa is not None and not fila.valores.get("cost_rate_period"):
            fila.problemas.append(
                Problema(
                    "cost_rate_period",
                    "Hay tarifa sin unidad de tiempo: se importa la persona, "
                    "pero la tarifa no se podrá usar para calcular costo hasta "
                    "que se declare si es por hora, por día o por mes",
                )
            )
        capacidad = fila.valores.get("project_capacity_pct")
        if isinstance(capacidad, int) and capacidad > 100:
            fila.rechazar(
                "project_capacity_pct", "La capacidad no puede pasar de 100 %"
            )


def marcar_duplicadas(
    filas: list[FilaLeida], existentes: dict[str, str], clase: str
) -> None:
    """Marca como `duplicada` cada fila que choque con algo ya existente o con otra fila.

    `existentes` es `clave normalizada → cómo se llama lo que ya existe`.

    Los duplicados **dentro del archivo** se marcan igual: un Excel con la misma
    fila dos veces crearía dos proyectos, y eso es el mismo problema una línea
    antes. La primera aparición se importa y las siguientes se saltan — no al
    revés, porque quien lee el reporte espera que la de arriba sea la que entró.

    Solo se miran las filas válidas: marcar «duplicada» una fila que además le
    falta el nombre esconde el error que hay que arreglar primero.
    """
    vistas: dict[str, int] = {}
    for fila in filas:
        if fila.estado != "valida":
            continue
        clave = _clave_de_fila(fila, clase)
        if not clave:
            continue
        if clave in existentes:
            fila.estado = "duplicada"
            fila.choca_con = existentes[clave]
            continue
        if clave in vistas:
            fila.estado = "duplicada"
            fila.choca_con = f"la fila {vistas[clave]} de este mismo archivo"
            continue
        vistas[clave] = fila.numero


def _clave_de_fila(fila: FilaLeida, clase: str) -> str:
    if clase == "resources":
        correo = fila.valores.get("email")
        if isinstance(correo, str) and correo:
            return normalizar(correo)
    nombre = fila.valores.get("name")
    return normalizar(nombre) if isinstance(nombre, str) else ""


def resumen(filas: list[FilaLeida]) -> dict[str, int]:
    """Cuántas de cada estado. Los tres números van juntos siempre.

    «18 filas listas» sin decir que hay 5 inválidas es la misma mentira por
    omisión que un costo total sin las asignaciones sin tarifa (US-215).
    """
    return {
        "total": len(filas),
        "valid": sum(1 for f in filas if f.estado == "valida"),
        "invalid": sum(1 for f in filas if f.estado == "invalida"),
        "duplicate": sum(1 for f in filas if f.estado == "duplicada"),
    }
