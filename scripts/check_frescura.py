#!/usr/bin/env python3
"""MCS DAT-11 — todo número presentado declara su periodo y su frescura.

«Todo número presentado DEBE indicar su periodo y su marca de actualización».

## Lo que se midió, y por qué la cifra no es la de la auditoría

La auditoría R1 lo resumió así: «hay exactamente una marca de actualización en
todo el producto». Nueve archivos mencionaban «actualizado» y **ocho eran
avisos de guardado** —«Perfil actualizado.»—, que no son marcas de frescura
sino confirmaciones. La única real acompañaba a un texto, no a un número.

El plan de remediación anotó «10 de 87 superficies» contando cualquier archivo
con algo parecido a un número. Aquí se cuenta distinto y se dice por qué:
**DAT-11 vive en §5.7.2, «Métricas y presentación»**, entre DAT-10 (fichas de
indicador) y DAT-12 (ausencia frente a cero). El sujeto del apartado es el
indicador. Un contador de caracteres «1.234 / 8.000» y un «página 1 de 5» son
números en pantalla y no tienen periodo que declarar: son el estado del control
que el usuario está tocando.

Así que la superficie se deriva de **los indicadores con ficha** (DAT-10), más
las tarjetas de KPI y los gráficos. Es una definición comprobable y atada a un
documento firmado, no a una intuición sobre qué cuenta como número.

## Lo que este control NO comprueba

Que el periodo declarado sea **el correcto**. `periodo="vivo"` en una pantalla
que pinta una instantánea pasaría este barrido. Lo que impide ese error es que
la propiedad **no tiene valor por defecto**: quien la escribe tiene que elegir
del vocabulario cerrado de `lib/frescura.ts`, y elegir mal es una decisión, no
un descuido.

Uso:

    python scripts/check_frescura.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
WEB = RAIZ / "apps" / "web"

#: Los indicadores con ficha en `docs/dominio/07-FICHAS-INDICADORES.md`, más el
#: vocabulario de conteos que el producto presenta como cifra de cartera.
INDICADORES = (
    "avg_progress|progress_avg|on_time_pct|overdue_pct|overdue_days|"
    "delayed_count|allocation_pct|capacity_pct|over_pct|budget_plan|"
    "budget_actual|budget_total|burn_index|health_green|health_yellow|"
    "health_red|active_projects|open_risks|severe_risks|open_issues|"
    "requests_in_review|change_requests_in_review|tasks_total|tasks_done|"
    "project_count|program_count|organization_count|users_total|tenants_total|"
    "task_count|portfolio_count|unquantified_count"
)

PRESENTA_NUMEROS = re.compile(rf"KpiCard|<(Bar|Line|Pie|Area|Radial)Chart|{INDICADORES}")

#: Superficies que casan el patrón y **no** son números de indicador. Cada una
#: con su motivo escrito: la diferencia entre «no aplica» y «se nos pasó» no se
#: ve desde fuera, y es lo primero que preguntaría un auditor.
FUERA_DE_ALCANCE: dict[str, str] = {
    "components/vista-maestra.tsx": (
        "Declara la frescura **por fila**, que es más preciso que un marcador "
        "de pantalla: la columna «Últ. act.» dice cuándo cambió ese proyecto, "
        "no cuándo se cargó la tabla. El periodo lo pone `/pmo` con su "
        "`MarcaDeDatos`, y los números de la fila son lecturas vivas."
    ),
    "components/tablero-ejecutivo.tsx": (
        "Son las piezas del tablero, no la pantalla: la misma tarjeta de salud "
        "sirve para un dato vivo y para uno de corte, igual que `KpiCard`. El "
        "periodo lo declara `/dashboard` con su `MarcaDeDatos`, y el semáforo "
        "recibe además su propio pie de corte por la prop `corte`."
    ),
    "components/kpi-card.tsx": (
        "Es la tarjeta, no la pantalla. El periodo lo declara la superficie que "
        "la usa: la misma tarjeta sirve para un dato vivo y para uno de corte."
    ),
    "components/directory/DirectoryView.tsx": (
        "`allocation_pct` es un valor DECLARADO de la participación, no un "
        "cálculo: la ficha lo dice («valor declarado, no se calcula»). Un campo "
        "de una fila no tiene periodo, igual que no lo tiene un nombre."
    ),
    "components/directory/TenantActorsPanel.tsx": (
        "`project_capacity_pct` es un atributo declarado del recurso, igual que "
        "el anterior. Su periodo sería el de la fila, que no existe."
    ),
    "components/import-wizard.tsx": (
        "`task_count` es la previsualización del archivo que la persona acaba "
        "de elegir. Su «frescura» es el propio acto de elegirlo."
    ),
    "components/tenant-settings-form.tsx": (
        "`task_count` aparece en un umbral configurable, no en una medición."
    ),
}


def superficies() -> dict[str, str]:
    """Ruta relativa → contenido, de todo lo que presenta números de indicador."""
    halladas: dict[str, str] = {}
    for base in ("app", "components"):
        for archivo in sorted((WEB / base).rglob("*.tsx")):
            texto = archivo.read_text(encoding="utf-8")
            if PRESENTA_NUMEROS.search(texto):
                halladas[str(archivo.relative_to(WEB))] = texto
    return halladas


def main() -> int:
    halladas = superficies()
    problemas: list[str] = []

    sin_marca = [
        ruta
        for ruta, texto in halladas.items()
        if ruta not in FUERA_DE_ALCANCE and "<MarcaDeDatos" not in texto
    ]
    for ruta in sorted(sin_marca):
        problemas.append(
            f"{ruta} presenta números de indicador y no declara periodo ni "
            f"frescura. Añade `<MarcaDeDatos periodo=… actualizado={{leido}} />` "
            f"con `useLectura`, o decláralo fuera de alcance con su motivo."
        )

    # La exclusión tampoco puede envejecer: una entrada que sobrevive al archivo
    # que excusaba hace pasar el control por un motivo falso.
    fantasmas = sorted(set(FUERA_DE_ALCANCE) - set(halladas))
    for ruta in fantasmas:
        problemas.append(
            f"{ruta} está declarado fuera de alcance y ya no presenta números "
            f"(o ya no existe). Quita la entrada."
        )

    for ruta, motivo in FUERA_DE_ALCANCE.items():
        if len(motivo.strip()) < 40:
            problemas.append(f"{ruta} se excluye sin un motivo que se pueda discutir.")

    if problemas:
        print("FALLA — DAT-11:\n")
        for p in problemas:
            print(f"  - {p}")
        return 1

    con_marca = len(halladas) - len(FUERA_DE_ALCANCE)
    print(
        f"OK — {con_marca} superficies de indicador declaran periodo y frescura; "
        f"{len(FUERA_DE_ALCANCE)} fuera de alcance con motivo escrito."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
