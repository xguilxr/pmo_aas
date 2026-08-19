"""US-198 — la regla que mantiene coherente `portafolio ⊃ programa → proyecto`.

La jerarquía nueva (ADR-037) tiene una redundancia deliberada: el proyecto
guarda `portfolio_id` **y** `program_id`, y el programa guarda su propio
`portfolio_id`. Se guardan los dos porque el filtrado por portafolio tiene que
funcionar para el proyecto que cuelga directo del portafolio, sin programa; si
el portafolio del proyecto se derivara siempre del programa, ese caso no
tendría dónde vivir.

El precio de la redundancia es que puede quedar incoherente: un proyecto con el
programa A y el portafolio del programa B. Eso no es un dato raro, es un dato
**mentiroso** — la vista ejecutiva del portafolio B mostraría un proyecto que su
programa no reporta. Por eso la regla:

    program_id IS NOT NULL  ⇒  portfolio_id = program.portfolio_id

y se aplica en un solo sitio, aquí. No es un `CHECK` de base porque exige leer
otra fila (el programa), que es justo lo que un CHECK de columna no puede hacer;
un trigger lo haría, a cambio de poner lógica de negocio donde nadie la busca.

Al asignar programa, el portafolio **se autocompleta**: pedirle al cliente que
mande los dos y castigarlo si no coinciden es trabajo de la API, no del usuario.
Solo se rechaza el par explícitamente contradictorio.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import business_rule, mensaje
from app.models.organization import Portfolio, Program

#: El portafolio al que se mudaron los programas que existían antes de US-198,
#: y el que se crea al vuelo cuando alguien da de alta un programa sin decir en
#: qué portafolio va. El nombre está en español porque es un dato que el usuario
#: ve en su pantalla, no una constante técnica.
NOMBRE_PORTAFOLIO_GENERAL = "Portafolio General"


async def portafolio_general(
    db: AsyncSession,
    *,
    tenant_id: UUID | str,
    organization_id: UUID | str,
    created_by: UUID | str | None = None,
) -> Portfolio:
    """El «Portafolio General» de esa organización; lo crea si no existe.

    Es el destino por defecto, no una categoría de verdad: existe para que
    `programs.portfolio_id NOT NULL` no obligue a nadie a inventar una
    taxonomía antes de poder dar de alta su primer programa. Que se llame
    «General» y no «Sin clasificar» es a propósito — el segundo nombre invita a
    dejarlo así para siempre.

    Si el que hay está borrado en suave o inactivo, **se revive**. No es una
    licencia: el nombre es único por organización, así que crear otro chocaría
    con el índice, y devolverlo tal cual metería el programa nuevo en un
    portafolio que ninguna pantalla lista — el programa desaparecería sin que
    nada avise. Entre las tres opciones, revivir el cajón por defecto es la
    única que deja el sistema en un estado que alguien puede ver.
    """
    tid, oid = str(tenant_id), str(organization_id)
    existente = (
        await db.execute(
            select(Portfolio).where(
                Portfolio.tenant_id == tid,
                Portfolio.organization_id == oid,
                Portfolio.name == NOMBRE_PORTAFOLIO_GENERAL,
            )
        )
    ).scalar_one_or_none()
    if existente is not None:
        if existente.deleted_at is not None or not existente.is_active:
            existente.deleted_at = None
            existente.is_active = True
            await db.flush()
        return existente

    creado = Portfolio(
        tenant_id=tid,
        organization_id=oid,
        name=NOMBRE_PORTAFOLIO_GENERAL,
        description=(
            "Portafolio por defecto de la organización. Reagrupa lo que no se "
            "clasificó en un portafolio propio."
        ),
        created_by=str(created_by) if created_by else None,
    )
    db.add(creado)
    await db.flush()
    return creado


async def resolver_portafolio(
    db: AsyncSession,
    *,
    tenant_id: UUID | str,
    program_id: UUID | str | None,
    portfolio_id: UUID | str | None,
) -> str | None:
    """El `portfolio_id` que se guarda, aplicando la regla de consistencia.

    - Sin programa: se respeta el portafolio que venga (o ninguno).
    - Con programa y sin portafolio: se autocompleta con el del programa.
    - Con programa y con portafolio: tienen que coincidir, o se rechaza.

    El programa se busca **dentro del tenant**: sin ese filtro, un id de otro
    tenant resolvería un portafolio ajeno, que es la fuga que el filtrado por
    `tenant_id` existe para evitar.
    """
    tid = str(tenant_id)
    pid = str(portfolio_id) if portfolio_id else None

    if program_id is None:
        return pid

    prog = (
        await db.execute(
            select(Program).where(Program.id == str(program_id), Program.tenant_id == tid)
        )
    ).scalar_one_or_none()
    if prog is None:
        raise business_rule(
            mensaje(
                que="El programa no existe o no pertenece a tu inquilino",
                porque="La referencia apunta fuera de tu inquilino y quedaría rota.",
                accion="Elige un programa de tu propia estructura.",
            )
        )

    del_programa = str(prog.portfolio_id)
    if pid is None:
        return del_programa
    if pid != del_programa:
        raise business_rule(
            mensaje(
                que="El portafolio indicado no es el del programa elegido",
                porque=(
                    "Un proyecto no puede reportar a un programa y contar en otro "
                    "portafolio: la vista ejecutiva mostraría un proyecto que su "
                    "programa no reporta."
                ),
                accion=(
                    "Deja el portafolio vacío para que se tome el del programa, o "
                    "elige un programa de ese portafolio."
                ),
            )
        )
    return pid


async def validar_portafolio_de_organizacion(
    db: AsyncSession,
    *,
    tenant_id: UUID | str,
    organization_id: UUID | str,
    portfolio_id: UUID | str | None,
) -> None:
    """Comprueba que el portafolio exista y sea de esa organización.

    La jerarquía es un árbol: un portafolio de la organización A no puede
    agrupar programas ni proyectos de la B. Sin esta comprobación el árbol se
    convierte en un grafo y los conteos por organización dejan de sumar.
    """
    if portfolio_id is None:
        return
    pf = (
        await db.execute(
            select(Portfolio).where(
                Portfolio.id == str(portfolio_id),
                Portfolio.tenant_id == str(tenant_id),
                Portfolio.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if pf is None:
        raise business_rule(
            mensaje(
                que="El portafolio no existe o no pertenece a tu inquilino",
                porque="La referencia apunta fuera de tu inquilino y quedaría rota.",
                accion="Elige un portafolio de tu propia estructura.",
            )
        )
    if str(pf.organization_id) != str(organization_id):
        raise business_rule(
            mensaje(
                que="El portafolio pertenece a otra organización",
                porque=(
                    "La jerarquía es un árbol: un portafolio agrupa solo lo de su "
                    "propia organización."
                ),
                accion="Elige un portafolio de la organización indicada.",
            )
        )
