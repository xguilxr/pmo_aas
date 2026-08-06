#!/usr/bin/env python3
"""MCS DIS-04 — los avisos destructivos pasan por la frontera, y el pasivo encoge.

«Toda acción destructiva DEBE nombrar el objeto afectado y su consecuencia, y
ofrecer confirmación o reversión».

**Lo que se midió el 2026-08-06** sobre los avisos que había:

- *Nombra el objeto:* a medias. «¿Eliminar este riesgo?» y «¿Eliminar este
  ítem?» no nombran nada — con dos pestañas abiertas nadie sabe cuál va a
  borrar.
- *Dice la consecuencia:* **cero.** Ninguno decía qué se pierde ni si se puede
  deshacer.
- *Ofrece confirmación:* sí, en su forma más pobre.

La frontera es `apps/web/lib/confirmar.ts`. Exige las tres partes **sin valor
por defecto**, igual que `errors.mensaje(que=, porque=, accion=)` en el backend:
un parámetro con defecto es un parámetro que nadie rellena.

## El pasivo está a cero

Se enchufó con 21 avisos crudos en línea base, porque eran 16 archivos y
`CLAUDE.md` §3 para a validar con el owner por encima de diez. **El owner
autorizó el barrido el mismo día** y quedaron en cero: la base existe vacía, y
su papel ahora es que un aviso nuevo se **migre** en vez de declararse.

De aquellos 21, tres eran falsos positivos —una función local llamada
`confirm`—, dieciséis se migraron, y dos se declararon fuera de alcance con su
motivo (`NO_DESTRUCTIVO`): una guarda de navegación por edición sin guardar, y
el envío de un informe por correo. Ninguna de las dos destruye nada.

Cada consecuencia se escribió mirando **si el borrado es blando o duro**:
conviven los dos —la mayoría marcan `deleted_at` y hay 52 sitios en el API que
borran de verdad—, y decir «no se puede deshacer» sobre un borrado blando es
mentir tanto como lo contrario.

Uso:

    python scripts/check_confirmaciones.py              # verifica
    python scripts/check_confirmaciones.py --regenerar  # reescribe la base
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
WEB = RAIZ / "apps" / "web"
BASE = WEB / ".dis04-baseline"

#: Zonas donde vive la interfaz. `lib/` queda fuera a propósito: ahí está la
#: frontera, que es el único sitio legítimo donde se llama al diálogo.
ZONAS = ("components", "app")

#: `window.confirm(` o un `confirm(` suelto. El `(?<![.\w])` evita casar
#: `confirmarDestructivo(` y cualquier otro identificador acabado en «confirm».
CRUDO = re.compile(r"\bwindow\.confirm\s*\(|(?<![.\w])confirm\s*\(")

#: Un archivo puede declarar SU PROPIA función `confirm`, y entonces un
#: `confirm(...)` de ese archivo no es el diálogo del navegador.
#:
#: Pasó de verdad: la primera versión del control marcó tres llamadas de
#: `import-wizard.tsx` y `superadmin/users/page.tsx` que son a una función
#: local. Un trinquete con falsos positivos se desactiva — y peor: habría
#: hecho «migrar» algo que no era un aviso destructivo.
PROPIA = re.compile(r"\b(?:async\s+)?function\s+confirm\s*\(|const\s+confirm\s*=")

#: Avisos que NO son acciones destructivas, declarados con su motivo.
#:
#: DIS-04 habla de destruir algo: «nombrar el objeto afectado y su
#: consecuencia». Estos dos no destruyen nada, y forzarlos por la frontera
#: produciría avisos que mienten sobre lo que hacen — que es peor que dejarlos
#: como están.
#:
#: Se declaran aquí y no en la línea base porque son cosas distintas: la base
#: es pasivo pendiente de migrar, esto es alcance decidido. Mezclarlos haría
#: que la base nunca llegara a cero y perdiera su sentido.
NO_DESTRUCTIVO: dict[str, str] = {
    "app/(app)/pmo/projects/[id]/reports/builder/page.tsx::if (isDirty && !window.confirm(\"Tienes cambios sin guardar. ¿Salir sin guardar la plantilla?\")) {":
        "guarda de navegación, no destrucción: avisa de que hay edición sin "
        "guardar al salir. No hay objeto que nombrar ni consecuencia sobre "
        "datos ya guardados.",
    "app/(app)/pmo/projects/[id]/reports/page.tsx::!window.confirm(":
        "envío inmediato de un informe por correo. Es irreversible hacia "
        "fuera —no se puede des-enviar— pero no destruye nada: DIS-04 pide "
        "confirmación para lo destructivo, y esto ya la tiene.",
}

CABECERA = """\
# Línea base de DIS-04 — avisos destructivos que aún no pasan por la frontera
#
# NO se edita a mano: la reescribe `python scripts/check_confirmaciones.py --regenerar`.
#
# Cada fila es la ruta y la línea. Es el pasivo del día en que se enchufó el
# control, no una lista de excepciones aprobadas: **solo puede encoger**.
#
# La frontera es `apps/web/lib/confirmar.ts`, que obliga a nombrar el objeto,
# decir la consecuencia y declarar si la acción es recuperable o definitiva.
# Migrar una fila de aquí es escribir esas tres cosas para ese caso.
"""


def crudos() -> list[str]:
    """Avisos que llaman al diálogo del navegador sin pasar por la frontera.

    Se descartan las líneas de comentario **antes** de mirar: un comentario que
    explique por qué no se usa `confirm` no es una llamada. Es el fallo que
    apareció cinco veces en la sesión del 2026-08-06 —el control marcando su
    propia documentación—, y aquí se evita por construcción.
    """
    filas = []
    for zona in ZONAS:
        for archivo in sorted((WEB / zona).rglob("*.tsx")):
            texto = archivo.read_text(encoding="utf-8")
            # Si el archivo trae su propia `confirm`, solo cuenta el
            # `window.confirm` explícito: el resto son llamadas suyas.
            patron = re.compile(r"\bwindow\.confirm\s*\(") if PROPIA.search(texto) else CRUDO
            for linea in texto.splitlines():
                desnuda = linea.lstrip()
                if desnuda.startswith(("//", "*", "/*")):
                    continue
                if patron.search(linea):
                    filas.append(
                        f"{archivo.relative_to(WEB).as_posix()}::{desnuda[:100]}"
                    )
    return filas


def tolerados() -> Counter[str]:
    """Cuenta, no conjunto.

    Hay líneas **idénticas repetidas** —el mismo `confirm("¿Eliminar…")` dos
    veces en el mismo archivo—, y con un conjunto se colapsan: pasar de uno a
    dos avisos iguales no se notaría, que es justo lo que el trinquete tiene
    que impedir. Lo destapó el propio verificador, que informó de «-2
    migrados» al regenerar sobre una base recién escrita.
    """
    if not BASE.is_file():
        return Counter()
    return Counter(
        linea
        for linea in BASE.read_text(encoding="utf-8").splitlines()
        if linea.strip() and not linea.lstrip().startswith("#")
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--regenerar", action="store_true")
    args = parser.parse_args()

    observados = crudos()
    if args.regenerar:
        BASE.write_text(CABECERA + "\n".join(observados) + "\n", encoding="utf-8")
        print(f"línea base reescrita: {len(observados)} avisos crudos")
        return 0

    conocidos = tolerados()
    observados = [f for f in observados if f not in NO_DESTRUCTIVO]
    vistos = Counter(observados)
    nuevos = [f for f, n in vistos.items() for _ in range(n - conocidos.get(f, 0))]

    if nuevos:
        print(f"FALLA — {len(nuevos)} aviso(s) destructivo(s) sin pasar por la frontera:\n")
        for f in nuevos:
            print(f"  {f}")
        print(
            "\nUsá `confirmarDestructivo` de `apps/web/lib/confirmar.ts`. Obliga a "
            "nombrar el objeto, decir la consecuencia y declarar si la acción es "
            "recuperable o definitiva — que es lo que pide DIS-04 y lo que ninguno "
            "de los avisos anteriores hacía."
        )
        return 1

    idos = sum(conocidos.values()) - len(observados)
    print(f"OK — {len(observados)} avisos crudos tolerados, ninguno nuevo")
    if idos:
        print(
            f"  {idos} migrado(s) desde la última regeneración. "
            f"Corré `--regenerar` para que la base lo refleje."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
