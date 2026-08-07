"""REQ-01 — los cierres que se apoyaban en un documento, ahora con prueba.

«Todo requisito funcional DEBE tener criterio de aceptación verificable».

La regla está en `docs/project-management/CRITERIOS-DE-ACEPTACION.md`: **el
criterio de aceptación de un cambio es la prueba que lo nombra**. Al enchufar
`scripts/check_criterios.py` salieron **doce** requisitos declarados CONFORME a
los que ninguna prueba nombraba.

Y salieron por poco. La primera versión del barrido decía «59 de 59» porque
incluía `registro_conformidad.py` en el corpus donde buscaba: cada requisito se
encontraba a sí mismo en la línea que lo declaraba conforme. **Es la sexta vez
en este expediente que un control se valida contra su propia documentación**, y
la única razón de haberlo visto fue la verificación por mutación — añadir un
cierre inventado sin prueba pasaba en verde.

Este archivo cubre los ocho que sí se pueden comprobar desde el repositorio.
Los otros cuatro son hechos de GitHub y de Railway, que este repositorio no
puede consultar; quedan declarados en el barrido con su motivo, que es la
diferencia entre «no se puede verificar aquí» y «se nos pasó».
"""
from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
CI = RAIZ / ".github" / "workflows" / "ci.yml"
ADR = RAIZ / "docs" / "adr"


def _ci_sin_comentarios() -> str:
    """El workflow sin sus comentarios.

    El archivo explica en prosa qué hace cada herramienta, así que buscar
    `gitleaks` en el texto crudo encontraría la explicación y no el paso. Es el
    modo de fallo que este archivo entero documenta.
    """
    return "\n".join(
        linea
        for linea in CI.read_text(encoding="utf-8").splitlines()
        if not linea.lstrip().startswith("#")
    )


# --------------------------------------------------------------------------
# CFG-02 e INT-02 — herramientas que corren de verdad en la canalización
# --------------------------------------------------------------------------


def test_cfg02_gitleaks_corre_sobre_el_historial_completo() -> None:
    """«NO DEBEN existir secretos en el repositorio».

    `fetch-depth: 0` es la mitad que se olvida: sin él, gitleaks solo mira el
    último commit y un secreto borrado hace tres meses sigue en el historial y
    sigue siendo válido.
    """
    flujo = _ci_sin_comentarios()
    assert "gitleaks/gitleaks-action" in flujo, "gitleaks dejó de correr en el CI."
    seguridad = flujo[flujo.index("  seguridad:") :]
    seguridad = seguridad[: seguridad.index("\n  lint:")]
    assert "fetch-depth: 0" in seguridad, (
        "El trabajo de seguridad dejó de pedir el historial completo. gitleaks "
        "pasaría a mirar solo el último commit."
    )


def test_int02_las_tres_herramientas_de_dependencias_corren() -> None:
    """«Las dependencias DEBEN analizarse en busca de vulnerabilidades»."""
    flujo = _ci_sin_comentarios()
    for herramienta in ("bandit", "pip-audit", "pnpm audit"):
        assert herramienta in flujo, (
            f"`{herramienta}` dejó de ejecutarse en el CI. INT-02 se cerró con "
            f"las tres, no con dos."
        )


# --------------------------------------------------------------------------
# ARQ-01, ARQ-02 y GOB-02 — las decisiones están escritas y se encuentran
# --------------------------------------------------------------------------


def test_arq02_y_gob02_los_adr_existen_y_estan_indexados() -> None:
    """«Toda decisión irreversible DEBE estar en un ADR» y su gobierno.

    Se comprueba lo que se puede comprobar: que los archivos existan, que el
    índice los liste y que **no haya huecos** — un ADR que existe y no está en
    el índice es un ADR que nadie encuentra, que para el caso es no tenerlo.
    """
    archivos = sorted(p for p in ADR.glob("ADR-*.md"))
    indice = (ADR / "README.md").read_text(encoding="utf-8")

    numerados = {re.match(r"ADR-(\d+)", p.name).group(1) for p in archivos} if archivos else set()
    en_indice = set(re.findall(r"ADR-(\d{3})", indice))

    assert len(en_indice) >= 29, (
        f"El índice de ADR lista {len(en_indice)} decisiones. ARQ-02 y GOB-02 "
        f"se cerraron con 29; una lista que encoge es una decisión que se borró."
    )
    sin_indexar = sorted(numerados - en_indice)
    assert not sin_indexar, (
        f"Estos ADR existen y el índice no los lista: {sin_indexar}. Un ADR que "
        f"nadie encuentra es un ADR que no está."
    )


def test_arq01_los_diagramas_de_arquitectura_estan() -> None:
    """«DEBE existir documentación de arquitectura con sus vistas»."""
    candidatos = list((RAIZ / "docs").rglob("*.md"))
    con_diagrama = [
        p
        for p in candidatos
        if "```mermaid" in p.read_text(encoding="utf-8", errors="replace")
    ]
    assert con_diagrama, (
        "No queda ningún diagrama en la documentación. ARQ-01 se cerró sobre "
        "los del §C4."
    )


# --------------------------------------------------------------------------
# CON-03, DEV-03 y REQ-03 — cierres que se apoyan en un documento firmado
# --------------------------------------------------------------------------


def test_con03_la_postura_sobre_afirmaciones_normativas_sigue_escrita() -> None:
    """CON-03 se cerró con un razonamiento, no con una lista de fuentes.

    El razonamiento es que **el producto no emite afirmaciones normativas**, así
    que no hay ninguna a la que exigirle fuente y vigencia. Si esa frase
    desaparece del documento, el cierre se queda sin sostén — y hay que volver a
    medirlo, no darlo por bueno.
    """
    doc = (RAIZ / "docs" / "dominio" / "06-COMPETENCIA.md").read_text(encoding="utf-8")
    assert "no emite afirmaciones" in doc, (
        "`06-COMPETENCIA.md` dejó de declarar que el producto no emite "
        "afirmaciones normativas. Ese era el argumento entero de CON-03."
    )
    assert "deja de ser\nválida" in doc or "deja de ser válida" in doc, (
        "Falta la condición que invalida la lectura («si en el futuro el "
        "producto emite afirmaciones normativas, esta sección deja de ser "
        "válida»). Un cierre por ausencia sin condición de revisión es un "
        "cierre que nunca se revisa."
    )


def test_dev03_el_alcance_de_pruebas_declarado_es_el_que_se_sostiene() -> None:
    """DEV-03 cerró con alcance reducido **declarado**, no fingido.

    Lo que sostiene el cierre es que los niveles declarados existan de verdad y
    que la ausencia del tercero esté escrita con su consecuencia. Si el ADR deja
    de decirlo, el cierre pasa a afirmar una cobertura que no hay.
    """
    adr = (ADR / "README.md").read_text(encoding="utf-8")
    assert "ADR-031" in adr
    texto = "\n".join(
        p.read_text(encoding="utf-8", errors="replace") for p in ADR.glob("*.md")
    )
    assert "extremo a extremo" in texto, (
        "El ADR dejó de declarar la ausencia del nivel de extremo a extremo. "
        "DEV-03 se cerró declarándola, no resolviéndola."
    )
    suite = RAIZ / "apps" / "api" / "tests"
    assert len(list(suite.glob("test_*.py"))) > 50, (
        "Los niveles unitario y de integración son los que DEV-03 declara "
        "sostenidos. La suite se vació."
    )


def test_req03_el_inventario_cubre_las_tablas_con_datos_personales() -> None:
    """El inventario se derivó del esquema; que siga cubriéndolo.

    Si mañana entra una tabla con correos o direcciones IP y el documento no la
    nombra, el inventario deja de ser el inventario — y esa es exactamente la
    forma en que un registro de tratamiento se queda obsoleto sin que nadie lo
    note.
    """
    doc = (RAIZ / "docs" / "dominio" / "05-DATOS-PERSONALES.md").read_text(encoding="utf-8")
    for tabla in ("users", "stakeholders", "actors", "audit_log", "password_reset_tokens"):
        assert tabla in doc, (
            f"El inventario de datos personales dejó de nombrar `{tabla}`, que "
            f"guarda información de personas identificables."
        )
    assert "ip" in doc.lower() and "user_agent" in doc, (
        "Faltan los identificadores indirectos. Una dirección IP identifica "
        "tanto como un nombre cuando se cruza con la hora."
    )
