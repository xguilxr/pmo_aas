"""CFG-01 — los elementos de configuración de §5.2.2 están versionados.

«Todo elemento de configuración enumerado en 5.2.2 DEBE residir en el
repositorio». El marco lista nueve categorías, y el requisito tiene además un
lado negativo que suele olvidarse: **secretos, credenciales, certificados
privados y datos personales reales NO DEBEN estar versionados**.

Las dos mitades se comprueban aquí. La positiva por presencia de artefacto; la
negativa apoyándose en gitleaks, que ya recorre el historial completo en cada
PR — un secreto borrado en un commit posterior sigue estando en el repositorio,
y mirar solo el árbol de trabajo no lo vería.

**Dos categorías se cerraron el 2026-08-06 sin buscarlo**: las fichas de métrica
(`DAT-10`) y las reglas de estilo (`LEN-03`) se escribieron por sus propios
requisitos y resultaron ser justo lo que le faltaba a este.
"""
from __future__ import annotations

from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[3]

#: Categoría de §5.2.2 → uno o más artefactos que la satisfacen.
#:
#: Se piden **rutas concretas**, no «que exista algo parecido»: una comprobación
#: que acepte cualquier fichero del árbol da verde siempre y no prueba nada.
ELEMENTOS: dict[str, tuple[str, ...]] = {
    "Código · fuente": ("apps/api/app", "apps/web/app"),
    "Código · pruebas": ("apps/api/tests",),
    "Código · scripts": ("scripts",),
    "Configuración · plantilla de entorno": (".env.example",),
    "Configuración · definición de servicio": ("apps/api/railway.toml",),
    "Infraestructura · manifiestos de despliegue": (".github/workflows/ci.yml",),
    "Datos · migraciones de esquema": ("apps/api/alembic/versions",),
    "Datos · fichas de métrica": ("docs/dominio/07-FICHAS-INDICADORES.md",),
    "Diseño · tokens": ("apps/web/app/globals.css",),
    "Lenguaje · glosario canónico": ("docs/dominio/02-GLOSARIO.md",),
    "Lenguaje · reglas de estilo": ("docs/dominio/04-GUIA-ESTILO.md",),
    "IA · prompts y herramientas": ("apps/api/app/services/ai",),
    "IA · conjunto de evaluación": ("apps/api/evaluacion",),
    "Documentación · generados y sus generadores": (
        "docs/architecture/er-generado.md",
        "scripts/generar_er.py",
    ),
    "Dependencias · archivo de bloqueo": ("pnpm-lock.yaml", "apps/api/uv.lock"),
}

#: Declarado con su motivo, no omitido: el producto es monolingüe y no tiene
#: capa de internacionalización. La categoría del marco existe; el artefacto no
#: aplica. Se escribe para que el día que se añada i18n alguien tenga que venir
#: aquí a quitarlo.
NO_APLICA = {
    "Lenguaje · cadenas de internacionalización": (
        "el producto es monolingüe: no hay catálogo de traducciones ni "
        "biblioteca de i18n en `apps/web`. Al añadir el segundo idioma, esta "
        "entrada pasa a ELEMENTOS."
    ),
}


@pytest.mark.parametrize("categoria", sorted(ELEMENTOS))
def test_cada_categoria_tiene_su_artefacto_versionado(categoria: str) -> None:
    """Una a una, no en bloque: si fallara el conjunto entero, el mensaje diría
    «falta algo» y habría que ir a buscarlo.
    """
    faltantes = [ruta for ruta in ELEMENTOS[categoria] if not (RAIZ / ruta).exists()]
    assert not faltantes, (
        f"«{categoria}» de MCS §5.2.2 no está en el repositorio: {faltantes}"
    )


def test_los_artefactos_estan_bajo_control_de_versiones() -> None:
    """Existir en el disco no es estar versionado.

    Un fichero ignorado por `.gitignore` existe para quien lo escribió y no
    llega a nadie más — que es exactamente el fallo que CFG-01 previene. Sin
    este caso, un artefacto generado localmente daría verde.
    """
    import subprocess

    versionados = set(
        subprocess.run(
            ["git", "ls-files"], cwd=RAIZ, capture_output=True, text=True, check=True
        ).stdout.split()
    )
    fuera = []
    for categoria, rutas in ELEMENTOS.items():
        for ruta in rutas:
            completa = RAIZ / ruta
            if completa.is_dir():
                if not any(v.startswith(f"{ruta}/") for v in versionados):
                    fuera.append(f"{categoria}: {ruta}/ (directorio sin archivos versionados)")
            elif ruta not in versionados:
                fuera.append(f"{categoria}: {ruta}")
    assert not fuera, f"Artefactos presentes en disco pero NO versionados: {fuera}"


def test_lo_que_no_aplica_se_declara_con_su_motivo() -> None:
    """Una categoría omitida en silencio es indistinguible de una olvidada.

    Este caso no comprueba el producto: comprueba que quien escribió la lista
    dijo por qué dejó algo fuera.
    """
    for categoria, motivo in NO_APLICA.items():
        assert len(motivo) > 40, f"«{categoria}» no explica por qué no aplica."


def test_no_hay_secretos_versionados() -> None:
    """El lado negativo del requisito, en su forma comprobable localmente.

    El control de verdad es `gitleaks` sobre el **historial completo** en cada
    PR: un secreto borrado en un commit posterior sigue estando en el
    repositorio, y mirar el árbol de trabajo no lo vería. Esto comprueba lo
    otro —que el mecanismo esté puesto— y que no se haya colado un `.env`.
    """
    import subprocess

    versionados = subprocess.run(
        ["git", "ls-files"], cwd=RAIZ, capture_output=True, text=True, check=True
    ).stdout.split()
    colados = [
        v for v in versionados
        if (v == ".env" or v.endswith("/.env") or ".env." in v)
        and "example" not in v and "sample" not in v
    ]
    assert not colados, f"Archivos de entorno versionados: {colados}"

    # Se descartan los comentarios ANTES de mirar. El workflow explica en un
    # comentario por qué hace falta `fetch-depth: 0`, así que buscar la cadena
    # en el texto crudo daba verde aunque la directiva real desapareciera: el
    # control validándose contra su propia documentación. Lo detectó la
    # mutación, no la lectura.
    flujo = "\n".join(
        linea
        for linea in (RAIZ / ".github" / "workflows" / "ci.yml")
        .read_text(encoding="utf-8")
        .splitlines()
        if not linea.lstrip().startswith("#")
    )
    assert "gitleaks" in flujo, (
        "Desapareció gitleaks del CI. Es lo único que mira el historial, y sin "
        "él la mitad negativa de CFG-01 deja de estar verificada."
    )

    # Acotado al trabajo `seguridad`, no al archivo entero: hay DOS
    # `fetch-depth: 0` en el flujo, así que buscarlo suelto daba verde aunque
    # el del checkout de gitleaks desapareciera. Lo destapó la mutación —
    # borrar la directiva real dejaba la suite en verde por el otro trabajo.
    partes = flujo.split("\n  seguridad:", 1)
    assert len(partes) == 2, "Desapareció el trabajo `seguridad` del CI."
    cuerpo = partes[1].split("\n  lint:", 1)[0]
    assert "fetch-depth: 0" in cuerpo, (
        "El checkout de `seguridad` dejó de traer el historial completo: "
        "gitleaks pasaría a revisar solo el último commit y daría verde sobre "
        "un secreto antiguo, que es justo lo que vino a buscar."
    )
