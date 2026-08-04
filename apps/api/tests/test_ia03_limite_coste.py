"""IA-03 — límites de iteraciones y de coste por ejecución.

Auditoría MCS 2026-08-03. El límite de ITERACIONES ya existía
(`_AI_CALL_MAX_RETRIES = 3`); lo que faltaba era el de COSTE. Un proyecto con
cientos de minutas genera un contexto que crece sin techo, y los reintentos lo
multiplican por tres.

El tope se aplica ANTES de llamar al proveedor: después, el gasto ya ocurrió.
"""
import pytest

from app.core.config import settings
from app.services.ai.tenant_ai import TenantAIConfig
from app.workers.tasks.ai import _AI_CALL_MAX_RETRIES, _call_ai_for_tenant


def test_ia03_existe_limite_de_iteraciones():
    assert _AI_CALL_MAX_RETRIES > 0
    assert _AI_CALL_MAX_RETRIES <= 5, "más de 5 reintentos multiplica el coste sin ganar fiabilidad"


def test_ia03_existe_limite_de_coste_declarado():
    assert settings.AI_MAX_PROMPT_CHARS > 0, (
        "AI_MAX_PROMPT_CHARS en 0 desactiva el tope de coste por ejecución"
    )


@pytest.mark.asyncio
async def test_ia03_rechaza_prompt_que_supera_el_tope(monkeypatch):
    """El rechazo ocurre sin llamar al proveedor: no se gasta nada."""
    monkeypatch.setattr(settings, "AI_MAX_PROMPT_CHARS", 100)
    with pytest.raises(RuntimeError, match="ai_prompt_demasiado_grande"):
        await _call_ai_for_tenant(
            "x" * 101,
            system=None,
            tenant_cfg=TenantAIConfig(mode="platform", byo=None),
            platform_groq_config=None,
            tenant_id="t",
            job_id="j",
        )


@pytest.mark.asyncio
async def test_ia03_un_prompt_normal_no_se_bloquea(monkeypatch):
    """Control negativo: el tope no debe estorbar al uso legítimo.

    Se comprueba que NO lanza el error de coste. Que luego falle por no haber
    proveedor configurado es esperado y distinto.
    """
    monkeypatch.setattr(settings, "AI_MAX_PROMPT_CHARS", 100_000)
    try:
        await _call_ai_for_tenant(
            "contexto de tamaño razonable",
            system=None,
            tenant_cfg=TenantAIConfig(mode="platform", byo=None),
            platform_groq_config=None,
            tenant_id="t",
            job_id="j",
        )
    except RuntimeError as exc:
        assert "ai_prompt_demasiado_grande" not in str(exc)
    except Exception:
        pass
