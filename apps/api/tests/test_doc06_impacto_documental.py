"""DOC-06 — el cruce zona-tocada / epic-no-tocada, y sus exenciones.

Trinquete de `scripts/check_impacto_documental.py`. Lo que importa defender:

- que el cruce detecte una zona mapeada sin su epic (el caso que motivó el
  script: EP017/EP018/EP019/EP020 seguían `# PENDING` con la funcionalidad ya
  en producción, y nada lo señalaba);
- que tocar la epic en el mismo rango la saque de la lista de faltantes;
- que los commits `refactor`/`chore`/`style`/`test` puros no generen aviso,
  porque §7 ya los exime de tocar una epic;
- que el prefijo más largo gane, para que un archivo específico pueda afinar
  lo que dice un directorio general;
- que el script **nunca falle** — es informativo, mismo argumento que DOC-07.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parents[3]
SCRIPT = RAIZ / "scripts" / "check_impacto_documental.py"


def _cargar():
    spec = importlib.util.spec_from_file_location("check_impacto_documental", SCRIPT)
    assert spec and spec.loader
    modulo = importlib.util.module_from_spec(spec)
    sys.modules["check_impacto_documental"] = modulo
    spec.loader.exec_module(modulo)
    return modulo


cid = _cargar()


def test_zona_tocada_sin_su_epic_se_reporta() -> None:
    with mock.patch.object(
        cid, "_archivos_cambiados",
        return_value=["apps/api/app/models/project.py", "apps/api/tests/test_x.py"],
    ):
        faltantes = cid.evaluar("dummy")
    assert faltantes == {"EP005": ["apps/api/app/models/project.py"]}


def test_tocar_la_epic_en_el_mismo_rango_la_saca_de_faltantes() -> None:
    with mock.patch.object(
        cid, "_archivos_cambiados",
        return_value=[
            "apps/api/app/models/project.py",
            "docs/epics/EP005-projects.md",
        ],
    ):
        assert cid.evaluar("dummy") == {}


def test_migracion_sin_db_changes_se_reporta() -> None:
    with mock.patch.object(
        cid, "_archivos_cambiados",
        return_value=["apps/api/alembic/versions/20260901_0116_x.py"],
    ):
        assert cid.evaluar("dummy") == {
            "DB-CHANGES": ["apps/api/alembic/versions/20260901_0116_x.py"]
        }


def test_migracion_con_db_changes_tocado_no_se_reporta() -> None:
    with mock.patch.object(
        cid, "_archivos_cambiados",
        return_value=[
            "apps/api/alembic/versions/20260901_0116_x.py",
            "docs/epics/DB-CHANGES.md",
        ],
    ):
        assert cid.evaluar("dummy") == {}


def test_ruta_sin_mapear_no_genera_falso_positivo() -> None:
    with mock.patch.object(
        cid, "_archivos_cambiados",
        return_value=["apps/api/app/models/audit.py", "README.md"],
    ):
        assert cid.evaluar("dummy") == {}


def test_prefijo_mas_largo_gana() -> None:
    assert cid._zona_de("apps/api/app/services/ai/catalogo.py") == ("EP021",)
    assert cid._zona_de("apps/api/app/services/ai/provider.py") == ("EP008",)


def test_dos_epics_para_una_misma_zona() -> None:
    assert cid._zona_de("apps/api/app/models/modules.py") == ("EP006", "EP019")


def test_commits_refactor_puro_exime_el_chequeo() -> None:
    with mock.patch.object(
        cid, "_git",
        return_value="refactor(api): reordena imports\nchore(deps): bump ruff\n",
    ):
        assert cid._solo_commits_exentos("dummy") is True


def test_un_solo_feat_entre_refactors_rompe_la_exencion() -> None:
    with mock.patch.object(
        cid, "_git",
        return_value="refactor(api): reordena imports\nfeat(api): US-999 — nuevo endpoint\n",
    ):
        assert cid._solo_commits_exentos("dummy") is False


def test_merge_y_revert_no_cuentan_para_la_exencion() -> None:
    with mock.patch.object(
        cid, "_git",
        return_value="Merge pull request #1 from x/y\nrefactor(api): limpieza\n",
    ):
        assert cid._solo_commits_exentos("dummy") is True


def test_rango_vacio_no_es_exento_ni_falla() -> None:
    """Sin commits en el rango, `evaluar` no encuentra archivos y no reporta nada."""
    with mock.patch.object(cid, "_git", return_value=""):
        assert cid._solo_commits_exentos("dummy") is False
    with mock.patch.object(cid, "_archivos_cambiados", return_value=[]):
        assert cid.evaluar("dummy") == {}


def test_main_nunca_devuelve_distinto_de_cero() -> None:
    """DOC-06 es informativo: ni con hallazgos, el proceso sale con código de error."""
    with (
        mock.patch.object(cid, "_solo_commits_exentos", return_value=False),
        mock.patch.object(
            cid, "_archivos_cambiados",
            return_value=["apps/api/app/models/project.py"],
        ),
        mock.patch.object(sys, "argv", ["check_impacto_documental.py"]),
    ):
        assert cid.main() == 0
