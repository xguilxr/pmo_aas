"""ENH-212 — las factories obligan a que recurso y proyecto compartan organización.

No había factory de `Actor`, `Project` ni `ProjectParticipation`, así que cada
suite inventaba su fixture y ninguna cuidaba la organización. Ocho suites pasan
hoy porque el actor se crea sin `organization_id`, lo que lo vuelve global: verde
por accidente, no por diseño.

Estas pruebas son del andamio, no del producto. Están porque un andamio que
promete una garantía y no la cumple es peor que no tenerlo: quien lo use va a
dejar de comprobar a mano lo que cree que la factory ya comprueba.
"""
import pytest

from tests.factories import (
    create_actor,
    create_organization,
    create_participation,
    create_project,
    create_tenant,
)


async def _dos_organizaciones(db_session):
    tenant = await create_tenant(db_session)
    a = await create_organization(db_session, tenant_id=tenant.id, name="Org A")
    b = await create_organization(db_session, tenant_id=tenant.id, name="Org B")
    return tenant, a, b


@pytest.mark.asyncio
async def test_enh212_el_caso_normal_es_el_que_comparte(db_session):
    tenant, org_a, _org_b = await _dos_organizaciones(db_session)
    proyecto = await create_project(
        db_session, tenant_id=tenant.id, organization_id=org_a.id
    )
    actor = await create_actor(
        db_session, tenant_id=tenant.id, organization_id=org_a.id, name="Ana"
    )

    part = await create_participation(
        db_session, tenant_id=tenant.id, project=proyecto, actor=actor
    )
    assert part.project_id == str(proyecto.id)
    assert part.actor_id == str(actor.id)


@pytest.mark.asyncio
async def test_enh212_el_recurso_global_participa_en_cualquiera(db_session):
    """`organization_id=None` es una decisión, y la factory la respeta."""
    tenant, _org_a, org_b = await _dos_organizaciones(db_session)
    proyecto = await create_project(
        db_session, tenant_id=tenant.id, organization_id=org_b.id
    )
    global_ = await create_actor(
        db_session, tenant_id=tenant.id, organization_id=None, name="Gabriel"
    )

    part = await create_participation(
        db_session, tenant_id=tenant.id, project=proyecto, actor=global_
    )
    assert part.actor_id == str(global_.id)


@pytest.mark.asyncio
async def test_enh212_el_cruce_falla_y_el_mensaje_dice_como_hacerlo_a_proposito(
    db_session,
):
    """El caso que esto existe para evitar.

    El mensaje tiene que nombrar a los dos y decir la salida: un test que de
    verdad necesita el cruce —para probar datos heredados— inserta la fila a
    mano y deja escrito por qué.
    """
    tenant, org_a, org_b = await _dos_organizaciones(db_session)
    proyecto = await create_project(
        db_session, tenant_id=tenant.id, organization_id=org_a.id, name="Proyecto A"
    )
    ajeno = await create_actor(
        db_session, tenant_id=tenant.id, organization_id=org_b.id, name="Beto"
    )

    with pytest.raises(AssertionError) as fallo:
        await create_participation(
            db_session, tenant_id=tenant.id, project=proyecto, actor=ajeno
        )
    texto = str(fallo.value)
    assert "Beto" in texto
    assert "Proyecto A" in texto
    assert "DEC-044" in texto
    assert "db.add(ProjectParticipation" in texto
