"""US-185 — Memoria de proyecto para IA: composición e inyección.

Compone el bloque <CONTEXTO_DEL_PROYECTO> que se antepone a los prompts
de generación (minutas en workers/tasks/ai.py, reportes en
endpoints/reports.py). Sigue el patrón de bloques <...> ya usado por el
generador de reportes.

Presupuesto de tamaño: el bloque se trunca a `max_chars` (default 6000)
priorizando: instrucciones > contexto curado > resumen acumulativo.

B2 (MCS IA-11) — este bloque es el canal de inyección INDIRECTA, y es el peor
de los dos. `auto_summary_md` lo escribe el modelo a partir de las minutas del
proyecto, y luego se antepone a TODA generación posterior: minutas nuevas y
reportes. Una sola minuta envenenada deja de ser un incidente aislado y pasa a
ser una instrucción permanente del proyecto. Por eso el resumen viaja envuelto
como contenido no confiable, y todo lo demás se neutraliza.

`instructions_md` y `context_md` los escribe el PM a propósito para dirigir al
modelo: son un canal de instrucción legítimo y NO se envuelven. Se neutralizan
igual, para que no puedan forjar el cierre del bloque.

R1 (MCS CON-04) — «las cifras vivas NO DEBEN residir en el corpus». Aquí no se
puede impedir: los tres campos son texto libre y nada evita que un PM escriba
«vamos al 40 %». Ese texto se guarda una vez y se inyecta en cada consulta, así
que a los seis meses el modelo sigue afirmando el 40 % con total confianza —y no
miente: está leyendo lo que le dimos.

Lo que sí se puede es **fechar el corpus y decirlo**. Cada sección viaja con la
fecha en que se escribió y la cabecera avisa de que son textos guardados, no
datos en vivo. El modelo puede entonces relativizar una cifra vieja en vez de
presentarla como actual. No cierra CON-04 —las cifras siguen ahí— pero quita lo
que lo hacía peligroso: que fueran indistinguibles de un dato calculado.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.project_ai_context import ProjectAIContext
from app.services.ai.untrusted import envolver_no_confiable, neutralizar

DEFAULT_MAX_CHARS = 6000


async def get_or_none(
    db: AsyncSession, tenant_id: str, project_id: str
) -> ProjectAIContext | None:
    return (
        await db.execute(
            select(ProjectAIContext).where(
                ProjectAIContext.tenant_id == str(tenant_id),
                ProjectAIContext.project_id == str(project_id),
            )
        )
    ).scalar_one_or_none()


def _clip(text: str | None, limit: int) -> str:
    if not text:
        return ""
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: max(limit - 1, 0)].rstrip() + "…"


def _fechado(momento: datetime | None, verbo: str = "escrito") -> str:
    """Sufijo con la fecha del texto. Vacío si no se sabe cuándo se escribió."""
    if momento is None:
        return ""
    return f", {verbo} el {momento:%Y-%m-%d}"


# CON-04: la cabecera es lo que convierte una cifra vieja en una cita fechada.
_AVISO_CORPUS = (
    "Lo que sigue son textos guardados por el equipo del proyecto, no datos en "
    "vivo. Cualquier cifra que aparezca aquí es la que había cuando se escribió "
    "y puede estar desactualizada; las cifras vigentes te llegan calculadas "
    "aparte. Ante una diferencia, gana el dato calculado."
)


def compose_context_block(
    *,
    project_name: str | None = None,
    project_description: str | None = None,
    context_md: str | None = None,
    instructions_md: str | None = None,
    auto_summary_md: str | None = None,
    context_updated_at: datetime | None = None,
    auto_summary_updated_at: datetime | None = None,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> str | None:
    """Arma el bloque de contexto. None si no hay nada que inyectar."""
    sections: list[str] = []
    if project_name:
        # El nombre y la descripción los teclea un usuario. Que aparezcan en la
        # cabecera del bloque, entre prosa de la plataforma, es justo lo que
        # los hace peligrosos: el modelo lee esa zona como nuestra.
        head = project_name
        if project_description:
            head += f"\nDescripción: {_clip(project_description, 600)}"
        sections.append(
            "Proyecto:\n"
            + envolver_no_confiable(
                head, origen="nombre y descripción del proyecto, escritos por usuarios"
            )
        )
    # Prioridad de presupuesto: instrucciones > contexto > resumen.
    # El aviso de CON-04 se descuenta del presupuesto en vez de sumarse encima:
    # es texto que viaja en cada llamada y IA-03 acota el prompt por coste.
    remaining = max_chars - len(_AVISO_CORPUS) - sum(len(s) for s in sections)
    fecha_pm = _fechado(context_updated_at)
    if instructions_md and remaining > 200:
        block = _clip(instructions_md, min(remaining, 1500))
        sections.append(
            f"Instrucciones permanentes del PM{fecha_pm}:\n{neutralizar(block)}"
        )
        remaining -= len(block)
    if context_md and remaining > 200:
        block = _clip(context_md, min(remaining, 3000))
        sections.append(
            f"Contexto y reglas de negocio del proyecto{fecha_pm}:"
            f"\n{neutralizar(block)}"
        )
        remaining -= len(block)
    if auto_summary_md and remaining > 200:
        # El único de los tres que NO lo escribió una persona autorizada: sale
        # del modelo resumiendo minutas subidas por cualquiera. Va envuelto.
        block = _clip(auto_summary_md, remaining)
        fecha_resumen = (
            _fechado(auto_summary_updated_at, "actualizado") or ", sin fecha"
        )
        sections.append(
            f"Resumen acumulado del proyecto (minutas previas{fecha_resumen}):\n"
            + envolver_no_confiable(
                block, origen="resumen derivado de minutas subidas por usuarios"
            )
        )

    has_memory = any((instructions_md, context_md, auto_summary_md))
    if not has_memory and not project_description:
        return None
    body = "\n\n".join(sections)
    return f"<CONTEXTO_DEL_PROYECTO>\n{_AVISO_CORPUS}\n\n{body}\n</CONTEXTO_DEL_PROYECTO>"


async def load_context_block(
    db: AsyncSession,
    tenant_id: str,
    project_id: str,
    *,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> str | None:
    """Carga proyecto + memoria y compone el bloque (None si no aplica)."""
    project = (
        await db.execute(
            select(Project.name, Project.description).where(
                Project.id == str(project_id)
            )
        )
    ).one_or_none()
    ctx = await get_or_none(db, tenant_id, project_id)
    return compose_context_block(
        project_name=project.name if project else None,
        project_description=project.description if project else None,
        context_md=ctx.context_md if ctx else None,
        instructions_md=ctx.instructions_md if ctx else None,
        auto_summary_md=ctx.auto_summary_md if ctx else None,
        # CON-04: `updated_at` cubre las dos secciones que teclea el PM; el
        # resumen tiene marca propia porque lo reescribe el worker por su cuenta.
        context_updated_at=ctx.updated_at if ctx else None,
        auto_summary_updated_at=ctx.auto_summary_updated_at if ctx else None,
        max_chars=max_chars,
    )
