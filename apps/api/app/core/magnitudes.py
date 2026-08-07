"""DAT-01 y DAT-02 — las magnitudes del dominio y su unidad canónica.

> **DAT-01:** «Cada magnitud del dominio DEBE tener una unidad canónica
> declarada en el glosario».
>
> **DAT-02:** «Todo identificador numérico DEBE expresar su unidad en el nombre
> o en su tipo».

## Por qué hace falta un catálogo y no basta con nombrar bien

`app/core/unidades.py` cerró DAT-04: las **conversiones** ocurren en una
frontera nombrada. Este módulo es el escalón anterior y responde a otra
pregunta: *qué* se está convirtiendo. Un `* 100` con nombre sigue sin decir si
`progress` vale 0–1 o 0–100 — solo dice que multiplicar por cien se llama
`fraccion_a_pct`.

La diferencia se ve en `project_health.py`, donde conviven un `ratio * 100` que
produce porcentaje y un `progress / 100` que lo consume, a nueve líneas. Con la
unidad declarada, leer `Mapped[Porcentaje]` contesta la pregunta sin
reconstruir nada.

## Cómo se reparte el trabajo con el glosario

El **glosario manda** (`docs/dominio/02-GLOSARIO.md` §7): DAT-01 pide que la
unidad esté declarada *ahí*. Este módulo es su reflejo ejecutable, y
`test_dat01_magnitudes.py` falla si los dos se separan — un catálogo que
puede desincronizarse de su declaración no es un catálogo.

## Lo que este módulo NO hace

**No verifica estáticamente que no se mezclen magnitudes.** Eso es DAT-07
(«tipos propios, verificados estáticamente»), es N2 y sigue abierto:
`Annotated[int, ...]` es `int` para el verificador, así que pasar un porcentaje
donde se espera una escala 1 a 5 no da error de tipos. Lo que sí da es una
anotación que se lee, y que las pruebas pueden exigir.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Annotated


@dataclass(frozen=True)
class Magnitud:
    """Una magnitud del dominio con su unidad canónica.

    `porque` no es adorno. Una unidad sin motivo escrito es la que alguien
    cambia en el siguiente sprint porque «daba igual», y el número cambia de
    significado sin que nada avise.
    """

    clave: str
    unidad: str
    rango: str
    porque: str


#: El catálogo. **El glosario §7 es la declaración normativa**; esto la refleja
#: para que el código pueda citarla, y una prueba mantiene las dos iguales.
CATALOGO: dict[str, Magnitud] = {
    "importe": Magnitud(
        clave="importe",
        unidad="peso mexicano (MXN)",
        rango="≥ 0, dos decimales",
        porque=(
            "Es la única moneda que el producto sabe presentar hoy: las diez "
            "superficies que muestran dinero la traen escrita. `settings.currency` "
            "ofrece USD y EUR y NADIE la lee fuera del formulario que la guarda, "
            "así que un inquilino en dólares ve sus importes rotulados en pesos. "
            "Se declara MXN porque es lo que el producto hace, no lo que el "
            "formulario promete; el disparador que invalida esta declaración es "
            "que la moneda del inquilino llegue a la presentación."
        ),
    ),
    "porcentaje": Magnitud(
        clave="porcentaje",
        unidad="por ciento",
        rango="0 a 100, hasta dos decimales",
        porque=(
            "Es lo que se guarda y lo que se presenta. La fracción existe solo "
            "como paso intermedio de un cálculo, y confundirlas no produce un "
            "error: produce un número plausible cien veces mayor o menor."
        ),
    ),
    "fraccion": Magnitud(
        clave="fraccion",
        unidad="parte de uno",
        rango="0 a 1",
        porque=(
            "No es unidad de ninguna columna: es la forma en que se opera "
            "dentro de un cálculo. Aparece aquí para que quede claro que NO es "
            "sinónimo de porcentaje, que es de donde vienen los errores."
        ),
    ),
    "dias": Magnitud(
        clave="dias",
        unidad="día natural",
        rango="entero; negativo en los desfases",
        porque=(
            "La planificación del producto es de grano diario: no hay hora de "
            "inicio ni de fin en una tarea. Días naturales y no hábiles porque "
            "el calendario laboral es por inquilino y aún no se modela."
        ),
    ),
    "milisegundos": Magnitud(
        clave="milisegundos",
        unidad="milisegundo",
        rango="entero ≥ 0",
        porque=(
            "Unidad técnica, no de dominio: mide lo que tarda el producto, no "
            "lo que el producto administra. Entera porque `duration_ms` es "
            "INTEGER y dejar que cada sitio redondeara producía latencias que "
            "no sumaban."
        ),
    ),
    "bytes": Magnitud(
        clave="bytes",
        unidad="byte",
        rango="entero ≥ 0",
        porque=(
            "Se guarda en bytes y se presenta en mebibytes. La conversión vive "
            "en `unidades.a_mebibytes`; la interfaz dice «MB» donde la realidad "
            "es MiB, y eso está declarado ahí."
        ),
    ),
    "conteo": Magnitud(
        clave="conteo",
        unidad="la cosa contada, y va en el nombre",
        rango="entero ≥ 0",
        porque=(
            "Un conteo no tiene unidad física: la tiene el sustantivo. "
            "`projects_total` cuenta proyectos y `tokens_in` cuenta tokens, y "
            "eso ya lo dice el identificador — que es lo que DAT-02 pide."
        ),
    ),
    "escala": Magnitud(
        clave="escala",
        unidad="punto de escala ordinal",
        rango="1 a 5",
        porque=(
            "Probabilidad, impacto y prioridad son juicios, no medidas: un 4 no "
            "es el doble de un 2. Se declara el rango porque es lo único que "
            "hace comparable un valor con otro, y los esquemas lo validan "
            "(`ge=1, le=5`)."
        ),
    ),
    "severidad": Magnitud(
        clave="severidad",
        unidad="punto de severidad (probabilidad por impacto)",
        rango="1 a 25",
        porque=(
            "Es un producto de dos escalas ordinales, así que su rango NO es "
            "1 a 5 y no se puede leer con la misma vara. Se calcula en el punto "
            "de acceso de riesgos y se guarda para poder ordenar en la base."
        ),
    ),
    "ordinal": Magnitud(
        clave="ordinal",
        unidad="posición dentro de un orden",
        rango="entero; el origen se documenta en cada campo",
        porque=(
            "`position`, `level`, `outline_level`, `version` y `last_number` no "
            "miden nada: ordenan. Sumarlos o promediarlos no significa nada, y "
            "declararlo evita que alguien saque «el nivel medio»."
        ),
    ),
    "calendario": Magnitud(
        clave="calendario",
        unidad="coordenada de calendario, en la zona del inquilino",
        rango="día 0 a 6 · hora 0 a 23 · día del mes 1 a 31",
        porque=(
            "No son duraciones: son puntos de un ciclo. La zona horaria es la "
            "parte que se olvida y la que decide si un informe programado a las "
            "07:00 sale a las 07:00 de alguien. La declara la ficha del "
            "indicador correspondiente."
        ),
    ),
}


# ---------------------------------------------------------------------------
# Los tipos. DAT-02 admite «en el nombre O EN SU TIPO»: esto es la segunda vía,
# para los campos cuyo nombre no puede cambiar sin romper contrato.
# ---------------------------------------------------------------------------

#: Importe monetario. `Decimal` y nunca coma flotante — eso es DAT-03, y no es
#: una preferencia: `0.1 + 0.2` no da `0.3` y un presupuesto que no cuadra por
#: un centavo se discute en una junta.
Importe = Annotated[Decimal, CATALOGO["importe"]]

#: Porcentaje 0–100. **No** fracción.
Porcentaje = Annotated[int, CATALOGO["porcentaje"]]

#: Porcentaje con decimales, para promedios y capacidades.
PorcentajeDecimal = Annotated[Decimal, CATALOGO["porcentaje"]]

#: Punto de una escala ordinal 1–5.
Escala = Annotated[int, CATALOGO["escala"]]

#: Producto de dos escalas: 1–25.
Severidad = Annotated[int, CATALOGO["severidad"]]
