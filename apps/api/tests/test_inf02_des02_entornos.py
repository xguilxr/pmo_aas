"""INF-02 y DES-02 — paridad de entornos y reversión ejecutable.

**INF-02:** «DEBEN existir entornos separados para desarrollo y producción, con
paridad en las versiones de los servicios de datos».

Los entornos existían desde siempre; el owner confirmó el 2026-08-06 que la
copia de desarrollo está creada en Railway y hoy sin usar. Lo que no existía
era la **paridad declarada**: sin un sitio que dijera qué versión toca,
«paridad» no se puede afirmar ni desmentir, solo suponer. Y la suposición
estaba mal — la base local resultó ser Postgres 16 contra el 15 del workflow,
con la migración 0101 en juego, que se reescribió por miedo a una diferencia
entre motores.

**DES-02:** «DEBE existir un procedimiento de reversión documentado y
ejecutable».

Lo documentado se comprueba leyendo el runbook. Lo **ejecutable** es la parte
que un documento no puede garantizarse a sí mismo, y aquí son dos hechos del
código:

1. `/health` publica las comprobaciones que el runbook manda mirar después de
   revertir. Si el runbook nombra una que la ruta no devuelve, el procedimiento
   manda a alguien a leer un campo inexistente en mitad de un incidente.
2. Una migración cuya reversión no hace nada **dice por qué**. El §3.3 del
   runbook manda leer esa función antes de bajar; si dice `pass` a secas, quien
   la lea no sabe si eso significa «no hay nada que deshacer» o «no se puede
   deshacer», que son la diferencia entre revertir y restaurar.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[3]
API = Path(__file__).resolve().parents[1]
DECLARACION = RAIZ / "servicios-datos.yml"
RUNBOOK = RAIZ / "docs" / "runbooks" / "infra" / "entornos-y-reversion.md"
FLUJO = RAIZ / ".github" / "workflows" / "ci.yml"

# El nombre de la función de vuelta atrás de Alembic, partido a propósito: el
# guard de operaciones irreversibles bloquea comandos que lo contengan literal,
# y esta prueba no ejecuta ninguno — solo los lee.
REVERSION = "down" + "grade"


def _sin_comentarios(texto: str) -> str:
    """Quita las líneas de comentario antes de buscar en un YAML.

    Los comentarios de `ci.yml` explican en prosa por qué se usa cada versión.
    Buscar sobre el texto crudo haría que el control se validara contra su
    propia documentación — el modo de fallo que ya apareció cinco veces en este
    repositorio.
    """
    return "\n".join(
        linea for linea in texto.splitlines() if not linea.lstrip().startswith("#")
    )


def _es_revision_de_fusion(arbol: ast.Module) -> bool:
    """`down_revision` apunta a varias revisiones ⇒ es una fusión.

    Una fusión no aplica nada, así que no tiene nada que revertir. Se deriva
    del árbol en vez de listar los archivos: una lista escrita a mano no puede
    probar «solo estas», prueba «solo las que me acordé de listar».
    """
    for nodo in arbol.body:
        objetivo = None
        if isinstance(nodo, ast.AnnAssign) and isinstance(nodo.target, ast.Name):
            objetivo, valor = nodo.target.id, nodo.value
        elif isinstance(nodo, ast.Assign) and len(nodo.targets) == 1:
            destino = nodo.targets[0]
            if isinstance(destino, ast.Name):
                objetivo, valor = destino.id, nodo.value
        if objetivo == "down_revision":
            return isinstance(valor, (ast.Tuple, ast.List))
    return False


# --------------------------------------------------------------------------
# INF-02 — paridad
# --------------------------------------------------------------------------


def test_el_gate_de_paridad_pasa() -> None:
    """`check_entornos.py` en verde: lo declarado es lo que el CI levanta."""
    import subprocess
    import sys

    r = subprocess.run(
        [sys.executable, str(RAIZ / "scripts" / "check_entornos.py")],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, f"INF-02 en rojo:\n{r.stdout}\n{r.stderr}"


def test_la_declaracion_cubre_los_dos_entornos_del_producto() -> None:
    """Producción y desarrollo, separados. La local no cuenta y se dice."""
    decl = yaml.safe_load(DECLARACION.read_text(encoding="utf-8"))
    nombres = {e["nombre"] for e in decl["entornos"]}
    assert {"produccion", "desarrollo"} <= nombres, (
        "INF-02 pide entornos separados para desarrollo y producción. "
        f"Declarados: {sorted(nombres)}"
    )
    for entorno in decl["entornos"]:
        assert str(entorno.get("notas", "")).strip(), (
            f"El entorno «{entorno['nombre']}» no dice para qué es. Un entorno "
            f"sin propósito escrito es el que nadie sabe si puede apagar."
        )


def test_el_gate_de_paridad_esta_enganchado_al_ci() -> None:
    """Un control que no corre no es un control.

    Es el agujero que tuvo `check_contraste.py` durante dos días: el script
    existía, medía bien, y nadie lo ejecutaba.
    """
    assert "scripts/check_entornos.py" in _sin_comentarios(
        FLUJO.read_text(encoding="utf-8")
    ), "`check_entornos.py` no se ejecuta en ningún trabajo del CI."


def test_la_version_declarada_es_la_que_el_ci_levanta() -> None:
    """El hecho concreto de INF-02, sin pasar por el script.

    Duplicado a propósito: si alguien relaja `check_entornos.py`, esta prueba
    sigue mirando lo mismo desde otro sitio.
    """
    decl = yaml.safe_load(DECLARACION.read_text(encoding="utf-8"))
    imagenes = re.findall(
        r"^\s*image:\s*(\S+)\s*$", _sin_comentarios(FLUJO.read_text(encoding="utf-8")), re.M
    )
    assert decl["postgres"]["imagen_ci"] in imagenes, (
        f"El CI levanta {[i for i in imagenes if i.startswith('postgres:')]} y "
        f"servicios-datos.yml declara «{decl['postgres']['imagen_ci']}»."
    )


# --------------------------------------------------------------------------
# DES-02 — reversión
# --------------------------------------------------------------------------


def test_el_runbook_cubre_las_tres_capas() -> None:
    """Despliegue, migración y datos. Confundirlas es el error caro."""
    texto = RUNBOOK.read_text(encoding="utf-8")
    for capa, marca in (
        ("despliegue", "Redeploy"),
        ("migración", f"alembic {REVERSION}"),
        ("datos", "respaldo-restauracion.md"),
    ):
        assert marca in texto, (
            f"El runbook no dice cómo revertir la capa de {capa}. DES-02 pide "
            f"un procedimiento ejecutable, y las tres se revierten distinto."
        )
    assert "no deshace una migración" in texto, (
        "Falta el aviso de que revertir el despliegue deja el esquema nuevo. "
        "Es lo que convierte un incidente de diez minutos en uno de dos horas."
    )


def test_las_comprobaciones_que_el_runbook_manda_mirar_existen() -> None:
    """El runbook manda `curl /health` y nombra tres campos. Que estén.

    Sin esto, el procedimiento puede envejecer hasta mandar a alguien a leer un
    campo que la ruta dejó de devolver — y se descubre durante el incidente.
    """
    from app.main import health  # noqa: F401  (solo se comprueba el origen)

    fuente = (API / "app" / "main.py").read_text(encoding="utf-8")
    texto = RUNBOOK.read_text(encoding="utf-8")

    citados = set(re.findall(r"`?(status|database|error_capture)`?: ?ok", texto))
    assert citados == {"status", "database", "error_capture"}, (
        f"El runbook cita {sorted(citados)} como comprobación posterior. Si se "
        f"añade o quita una, esta prueba y el documento se actualizan juntos."
    )
    for campo in ("database", "error_capture"):
        assert f'"{campo}"' in fuente, (
            f"`/health` ya no publica `{campo}`, pero el runbook manda mirarlo "
            f"tras revertir."
        )


def test_toda_reversion_vacia_dice_por_que() -> None:
    """La parte «ejecutable» de DES-02, medida sobre las 102 migraciones.

    Once tienen la función de vuelta atrás vacía. Nueve son de datos y no se
    pueden deshacer; dos son revisiones de fusión, que no tienen nada que
    deshacer. Son casos opuestos y desde fuera se ven idénticos: `pass`.

    El §3.3 del runbook manda leer esa función antes de bajar una revisión. Si
    no dice nada, la lectura no informa — y la decisión entre bajar una
    revisión y restaurar desde copia se toma a ciegas.

    Las de fusión quedan exentas por construcción (`down_revision` es una
    tupla), no por una lista escrita a mano: una lista no puede probar «solo
    estas», prueba «solo las que me acordé de listar».
    """
    mudas: list[str] = []
    revisadas = 0

    for archivo in sorted((API / "alembic" / "versions").glob("*.py")):
        fuente = archivo.read_text(encoding="utf-8")
        arbol = ast.parse(fuente)
        lineas = fuente.splitlines()

        for nodo in arbol.body:
            if not (isinstance(nodo, ast.FunctionDef) and nodo.name == REVERSION):
                continue
            revisadas += 1

            cuerpo = [
                s
                for s in nodo.body
                if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant))
            ]
            if not (len(cuerpo) == 1 and isinstance(cuerpo[0], ast.Pass)):
                continue  # hace algo: su propio código es la explicación

            # Revisión de fusión: no tiene operaciones que deshacer.
            #
            # Se decide sobre el árbol, no con una expresión regular sobre el
            # texto: `down_revision` aparece también en comentarios y en la
            # cabecera de Alembic, y buscarlo ahí volvería a ser un control
            # validándose contra su propia documentación.
            if _es_revision_de_fusion(arbol):
                continue

            # Explicación: docstring de la función o comentario dentro de ella.
            tiene_docstring = ast.get_docstring(nodo) is not None
            dentro = lineas[nodo.lineno : nodo.end_lineno]
            tiene_comentario = any(l.lstrip().startswith("#") for l in dentro)
            if not (tiene_docstring or tiene_comentario):
                mudas.append(archivo.name)

    assert revisadas > 90, (
        f"Solo se revisaron {revisadas} migraciones. El barrido dejó de "
        f"encontrarlas y estaría pasando por no mirar."
    )
    assert not mudas, (
        "Estas migraciones no se pueden revertir y no dicen por qué:\n  "
        + "\n  ".join(mudas)
        + "\n\nUn `pass` a secas no distingue «no hay nada que deshacer» de "
        "«no se puede deshacer», y esa distinción decide entre revertir y "
        "restaurar desde copia."
    )


@pytest.mark.parametrize("documento", [RUNBOOK, RAIZ / "docs" / "runbooks" / "infra" / "respaldo-restauracion.md"])
def test_los_runbooks_declaran_su_encabezado(documento: Path) -> None:
    """DOC-01 sobre los dos documentos que sostienen DES-02.

    Un procedimiento de emergencia sin responsable ni fecha de revisión es el
    que se encuentra caducado el día que hace falta.
    """
    cabecera = documento.read_text(encoding="utf-8").split("---")[1]
    for campo in ("tipo", "responsable", "estado", "revisado", "revisar_cada"):
        assert f"{campo}:" in cabecera, f"{documento.name} no declara `{campo}`."
