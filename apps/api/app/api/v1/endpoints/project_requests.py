from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_authenticated
from app.core.errors import business_rule, conflict, forbidden, mensaje, not_found, validation_error
from app.db.session import get_db
from app.models.organization import BusinessUnit, Department, Organization
from app.models.project_request import ProjectRequest
from app.schemas.project_request import (
    CreateProjectFromRequest,
    ProjectRequestCreate,
    ProjectRequestRead,
    ProjectRequestUpdate,
    ReviewRequest,
)
from app.services.audit import write_audit
from app.services.charter_generator import generate_charter_docx
from app.services.folio import next_folio
from app.services.moneda_tenant import preferida as moneda_preferida

router = APIRouter(prefix="/project-requests", tags=["project_requests"])


def _tenant(cu: CurrentUser) -> UUID:
    if cu.effective_tenant_id is None:
        raise forbidden()
    return cu.effective_tenant_id


@router.post("", response_model=ProjectRequestRead, status_code=201)
async def create_request(
    body: ProjectRequestCreate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    # BUG-092 — una consulta por petición, no una por fila.
    ctx_moneda = {"moneda_preferida": await moneda_preferida(db, cu.effective_tenant_id)}
    tenant_id = _tenant(cu)
    # US-085: si el solicitante eligió "Otra…", crear org inactiva.
    new_org_created = False
    if body.organization_id is None:
        if not (body.organization_name_new and body.organization_name_new.strip()):
            raise business_rule(
                mensaje(
                    que="Selecciona una organización o captura una nueva (Otra…)",
                    porque="Una solicitud sin organización no se puede encaminar a nadie.",
                    accion="Elige una del desplegable, o escribe una nueva con la opción «Otra…».",
                )
            )
        new_name = body.organization_name_new.strip()
        # 409 si ya existe una org con ese nombre (case-sensitive,
        # cubre el unique constraint a nivel DB también).
        existing = (
            await db.execute(
                select(Organization).where(
                    Organization.tenant_id == tenant_id,
                    Organization.name == new_name,
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            raise conflict(
                mensaje(
                    que=f"Ya existe una organización con el nombre '{new_name}'",
                    porque="El nombre identifica la organización y no puede repetirse.",
                    accion="Elígela del desplegable en vez de crearla, o usa otro nombre.",
                ),
                code="ORG_NAME_DUPLICATE",
            )
        org = Organization(
            tenant_id=tenant_id, name=new_name, is_active=False
        )
        db.add(org)
        await db.flush()
        new_org_created = True
    else:
        org = (
            await db.execute(
                select(Organization).where(
                    Organization.id == str(body.organization_id),
                    Organization.tenant_id == tenant_id,
                )
            )
        ).scalar_one_or_none()
        if org is None:
            raise business_rule(mensaje(
                que="La organización no existe en tu tenant",
                porque="La referencia apunta fuera de tu organización y quedaría rota.",
                accion="Elige una organización de tu tenant.",
            ))

    # Validar FKs BU/Depto si vienen (US-011).
    if body.business_unit_id is not None:
        bu = (
            await db.execute(
                select(BusinessUnit).where(
                    BusinessUnit.id == str(body.business_unit_id),
                    BusinessUnit.tenant_id == tenant_id,
                    BusinessUnit.organization_id == str(body.organization_id),
                    BusinessUnit.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if bu is None:
            raise business_rule(
                mensaje(
                    que="La unidad de negocio no pertenece a la organización indicada",
                    porque="La estructura tiene que ser coherente: la unidad cuelga de su organización.",
                    accion="Elige una unidad de esa organización, o cambia la organización.",
                )
            )
    if body.department_id is not None:
        dept = (
            await db.execute(
                select(Department).where(
                    Department.id == str(body.department_id),
                    Department.tenant_id == tenant_id,
                    Department.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if dept is None:
            raise business_rule(mensaje(
                que="El departamento no existe o no pertenece al tenant",
                porque="La referencia apunta fuera de tu organización y quedaría rota.",
                accion="Elige un departamento de tu tenant.",
            ))
        if (
            body.business_unit_id is not None
            and str(dept.business_unit_id) != str(body.business_unit_id)
        ):
            raise business_rule(
                mensaje(
                    que="El departamento no pertenece a la unidad de negocio indicada",
                    porque="La estructura tiene que ser coherente: el departamento cuelga de su unidad.",
                    accion="Elige un departamento de esa unidad, o cambia la unidad.",
                )
            )

    folio = await next_folio(db, tenant_id=tenant_id, prefix="SOL")
    pr = ProjectRequest(
        tenant_id=tenant_id,
        folio=folio,
        title=body.title,
        description=body.description,
        objective=body.objective,
        organization_id=str(org.id),
        business_unit=body.business_unit,
        department=body.department,
        business_unit_id=(
            str(body.business_unit_id) if body.business_unit_id else None
        ),
        department_id=str(body.department_id) if body.department_id else None,
        sponsor=body.sponsor,
        sponsor_email=str(body.sponsor_email),
        benefits=body.benefits,
        budget=body.budget,
        scope=body.scope,
        entregables=body.entregables,
        key_people=body.key_people,
        if_not_done=body.if_not_done,
        observations=body.observations,
        requester_name=body.requester_name or cu.user.full_name,
        requester_email=(
            str(body.requester_email) if body.requester_email else cu.user.email
        ),
        requested_by=cu.id,
        requested_at=datetime.now(UTC),
        delivery_constraint_date=body.delivery_constraint_date,
        status="in_review",
        attachments=[a.model_dump() for a in body.attachments],
    )
    db.add(pr)
    await db.flush()
    await write_audit(
        db, action="project_request.create", module="project_requests",
        user_id=cu.id, tenant_id=tenant_id, entity_type="project_request",
        entity_id=str(pr.id), details={"folio": folio},
    )
    # US-085: notificar al admin del tenant si la org se creó como
    # inactiva por "Otra…" (la activación es manual).
    if new_org_created:
        from app.models.user import User as _User  # local import: ciclo
        from app.services.notifications import (
            ORGANIZATION_PENDING_SETUP,
            enqueue_notification,
        )
        admins = (
            await db.execute(
                select(_User).where(
                    _User.tenant_id == str(tenant_id),
                    _User.role_type == "admin",
                )
            )
        ).scalars().all()
        for adm in admins:
            await enqueue_notification(
                db,
                tenant_id=tenant_id,
                user_id=adm.id,
                type=ORGANIZATION_PENDING_SETUP,
                title=f"Configura la nueva organización: {org.name}",
                body=(
                    "Una nueva solicitud capturó esta organización. "
                    "Está inactiva — actívala desde su pantalla de configuración."
                ),
                entity_type="organization",
                entity_id=str(org.id),
                link=f"/admin/organizations/{org.id}",
                meta={"created_via": "project_request", "request_id": str(pr.id)},
            )
    await db.commit()
    return ProjectRequestRead.model_validate(pr, context=ctx_moneda)


@router.get("", response_model=list[ProjectRequestRead])
async def list_requests(
    status: str | None = Query(default=None),
    organization_id: UUID | None = Query(default=None),
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    # BUG-092 — una consulta por petición, no una por fila.
    ctx_moneda = {"moneda_preferida": await moneda_preferida(db, cu.effective_tenant_id)}
    tenant_id = _tenant(cu)
    stmt = select(ProjectRequest).where(ProjectRequest.tenant_id == tenant_id)
    if status:
        stmt = stmt.where(ProjectRequest.status == status)
    if organization_id:
        stmt = stmt.where(ProjectRequest.organization_id == str(organization_id))
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(func.lower(ProjectRequest.title).like(like))
    rows = (
        await db.execute(stmt.order_by(ProjectRequest.requested_at.desc()).offset((page - 1) * limit).limit(limit))
    ).scalars().all()
    return [ProjectRequestRead.model_validate(r, context=ctx_moneda) for r in rows]


@router.get("/{request_id}", response_model=ProjectRequestRead)
async def get_request(
    request_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    # BUG-092 — una consulta por petición, no una por fila.
    ctx_moneda = {"moneda_preferida": await moneda_preferida(db, cu.effective_tenant_id)}
    tenant_id = _tenant(cu)
    pr = (
        await db.execute(
            select(ProjectRequest).where(
                ProjectRequest.id == str(request_id), ProjectRequest.tenant_id == tenant_id
            )
        )
    ).scalar_one_or_none()
    if pr is None:
        raise not_found("Solicitud")
    return ProjectRequestRead.model_validate(pr, context=ctx_moneda)


@router.patch("/{request_id}", response_model=ProjectRequestRead)
async def update_request(
    request_id: UUID,
    body: ProjectRequestUpdate,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    # BUG-092 — una consulta por petición, no una por fila.
    ctx_moneda = {"moneda_preferida": await moneda_preferida(db, cu.effective_tenant_id)}
    tenant_id = _tenant(cu)
    pr = (
        await db.execute(
            select(ProjectRequest).where(
                ProjectRequest.id == str(request_id), ProjectRequest.tenant_id == tenant_id
            )
        )
    ).scalar_one_or_none()
    if pr is None:
        raise not_found("Solicitud")
    if pr.status not in {"in_review", "needs_info"}:
        raise conflict(mensaje(
            que="No editable en este estado",
            porque="La solicitud ya salió de tus manos y editarla cambiaría lo que otros están revisando.",
            accion="Pide que te la devuelvan como «necesita información» para poder corregirla.",
        ), code="STATE_TRANSITION")
    for f, v in body.model_dump(exclude_none=True).items():
        setattr(pr, f, v)
    await write_audit(
        db, action="project_request.update", module="project_requests",
        user_id=cu.id, tenant_id=tenant_id, entity_type="project_request", entity_id=str(pr.id),
    )
    await db.commit()
    return ProjectRequestRead.model_validate(pr, context=ctx_moneda)


@router.post("/{request_id}/review", response_model=ProjectRequestRead)
async def review_request(
    request_id: UUID,
    body: ReviewRequest,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    # BUG-092 — una consulta por petición, no una por fila.
    ctx_moneda = {"moneda_preferida": await moneda_preferida(db, cu.effective_tenant_id)}
    tenant_id = _tenant(cu)
    pr = (
        await db.execute(
            select(ProjectRequest).where(
                ProjectRequest.id == str(request_id), ProjectRequest.tenant_id == tenant_id
            )
        )
    ).scalar_one_or_none()
    if pr is None:
        raise not_found("Solicitud")
    if pr.status not in {"in_review", "needs_info"}:
        raise conflict(mensaje(
            que="Transición de estado inválida",
            porque="El flujo de la solicitud no permite pasar de un estado al otro directamente.",
            accion="Llévala al estado intermedio que corresponda.",
        ), code="STATE_TRANSITION")
    if body.decision in {"reject", "needs_info"} and not (body.comment and body.comment.strip()):
        raise validation_error(mensaje(
            que="comment obligatorio para reject/needs_info",
            porque="Quien recibe la solicitud necesita saber qué corregir; sin motivo, la devolución no informa.",
            accion="Escribe qué falta o por qué se rechaza.",
        ))

    status_map = {"approve": "approved", "reject": "rejected", "needs_info": "needs_info"}
    pr.status = status_map[body.decision]
    pr.reviewed_by = cu.id
    pr.reviewed_at = datetime.now(UTC)
    pr.review_comment = body.comment
    await write_audit(
        db, action=f"project_request.{body.decision}", module="project_requests",
        user_id=cu.id, tenant_id=tenant_id, entity_type="project_request", entity_id=str(pr.id),
        details={"comment": body.comment},
    )

    # US-027/028: notificar al solicitante del resultado de la revisión.
    # Si no hay `requested_by` (p. ej. solicitudes importadas) no hacemos
    # nada — la notificación requiere user_id.
    if pr.requested_by:
        from app.services.notifications import (
            REQUEST_APPROVED,
            REQUEST_NEEDS_INFO,
            REQUEST_REJECTED,
            enqueue_notification,
        )

        type_map = {
            "approve": (REQUEST_APPROVED, "Solicitud aprobada"),
            "reject": (REQUEST_REJECTED, "Solicitud rechazada"),
            "needs_info": (REQUEST_NEEDS_INFO, "Solicitud requiere información"),
        }
        ntype, title = type_map[body.decision]
        await enqueue_notification(
            db,
            tenant_id=tenant_id,
            user_id=pr.requested_by,
            type=ntype,
            title=f"{title}: {pr.title}",
            body=body.comment,
            entity_type="project_request",
            entity_id=str(pr.id),
            link=f"/admin/requests/{pr.id}",
        )

    await db.commit()
    return ProjectRequestRead.model_validate(pr, context=ctx_moneda)


@router.post("/{request_id}/resubmit", response_model=ProjectRequestRead)
async def resubmit_request(
    request_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    # BUG-092 — una consulta por petición, no una por fila.
    ctx_moneda = {"moneda_preferida": await moneda_preferida(db, cu.effective_tenant_id)}
    tenant_id = _tenant(cu)
    pr = (
        await db.execute(
            select(ProjectRequest).where(
                ProjectRequest.id == str(request_id), ProjectRequest.tenant_id == tenant_id
            )
        )
    ).scalar_one_or_none()
    if pr is None:
        raise not_found("Solicitud")
    if pr.status != "needs_info":
        raise conflict(mensaje(
            que="Solo se puede re-someter si status=needs_info",
            porque="Reenviar solo tiene sentido cuando te han pedido corregir algo.",
            accion="Espera la revisión, o abre una solicitud nueva.",
        ), code="STATE_TRANSITION")
    pr.status = "in_review"
    await write_audit(
        db, action="project_request.resubmit", module="project_requests",
        user_id=cu.id, tenant_id=tenant_id, entity_type="project_request", entity_id=str(pr.id),
    )
    await db.commit()
    return ProjectRequestRead.model_validate(pr, context=ctx_moneda)


@router.post("/{request_id}/reopen", response_model=ProjectRequestRead)
async def reopen_request(
    request_id: UUID,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    """ENH-016: reabrir una solicitud aprobada sólo si todavía no se
    materializó un proyecto. Devuelve la solicitud a `in_review`."""
    # BUG-092 — una consulta por petición, no una por fila.
    ctx_moneda = {"moneda_preferida": await moneda_preferida(db, cu.effective_tenant_id)}
    tenant_id = _tenant(cu)
    pr = (
        await db.execute(
            select(ProjectRequest).where(
                ProjectRequest.id == str(request_id),
                ProjectRequest.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if pr is None:
        raise not_found("Solicitud")
    if pr.status != "approved":
        raise conflict(
            mensaje(
                que="Solo se puede reabrir una solicitud aprobada",
                porque="Reabrir revierte una aprobación, así que tiene que haber una.",
                accion="Si fue rechazada, abre una solicitud nueva.",
            ),
            code="STATE_TRANSITION",
        )
    if pr.project_id:
        raise business_rule(
            mensaje(
                que="No se puede reabrir: ya existe un proyecto creado desde esta solicitud",
                porque="La solicitud ya cumplió su función y el trabajo vive en el proyecto.",
                accion="Trabaja sobre el proyecto, o abre una solicitud nueva.",
            )
        )
    pr.status = "in_review"
    pr.reviewed_by = None
    pr.reviewed_at = None
    pr.review_comment = None
    await write_audit(
        db,
        action="project_request.reopen",
        module="project_requests",
        user_id=cu.id,
        tenant_id=tenant_id,
        entity_type="project_request",
        entity_id=str(pr.id),
    )
    await db.commit()
    return ProjectRequestRead.model_validate(pr, context=ctx_moneda)


@router.post("/{request_id}/create-project")
async def create_project_from_request(
    request_id: UUID,
    body: CreateProjectFromRequest,
    cu: CurrentUser = Depends(require_authenticated()),
    db: AsyncSession = Depends(get_db),
):
    from app.models.project import Project  # import diferido
    from app.models.project_charter import ProjectCharter

    tenant_id = _tenant(cu)
    pr = (
        await db.execute(
            select(ProjectRequest).where(
                ProjectRequest.id == str(request_id), ProjectRequest.tenant_id == tenant_id
            )
        )
    ).scalar_one_or_none()
    if pr is None:
        raise not_found("Solicitud")
    if pr.status != "approved":
        raise business_rule(mensaje(
            que="Solo se puede crear proyecto desde una solicitud 'approved'",
            porque="Crear el proyecto es lo que ejecuta la aprobación, así que tiene que haberla.",
            accion="Consigue la aprobación de la solicitud y vuelve a intentarlo.",
        ))

    # Idempotencia
    if pr.project_id:
        return {"project_id": str(pr.project_id), "idempotent": True}

    folio = await next_folio(db, tenant_id=tenant_id, prefix="PRJ")
    project = Project(
        tenant_id=tenant_id,
        organization_id=pr.organization_id,
        business_unit_id=pr.business_unit_id,
        department_id=pr.department_id,
        folio=folio,
        name=pr.title,
        description=pr.description,
        sponsor=pr.sponsor,
        budget=pr.budget,
        # BUG-092 — el proyecto hereda la moneda de la solicitud. Si la
        # solicitud no eligió, se queda en nulo y aplica la preferida del
        # inquilino: copiarla resuelta aquí congelaría la de hoy.
        currency=pr.currency,
        phase="planning",
        pm_id=str(body.pm_id),
        request_id=pr.id,
    )
    db.add(project)
    await db.flush()
    pr.project_id = project.id

    # Auto-crear Charter pre-llenado desde solicitud (US-012).
    # Líder de negocio y líder técnico quedan en blanco para completar.
    charter = ProjectCharter(
        tenant_id=tenant_id,
        project_id=project.id,
        request_id=pr.id,
        project_name=project.name,
        description=pr.description,
        organization_id=pr.organization_id,
        business_unit_id=pr.business_unit_id,
        department_id=pr.department_id,
        sponsor=pr.sponsor,
        sponsor_email=pr.sponsor_email,
        pm_id=str(body.pm_id),
        project_type=None,
        priority=None,
        objective=pr.objective,
        scope=pr.scope,
        key_people=pr.key_people,
        benefits=pr.benefits,
        restrictions=None,
        risks_summary=None,
        created_by=cu.id,
    )
    db.add(charter)
    await db.flush()

    # BUG-028: al aprobar una solicitud, generamos el .docx real del
    # charter y lo subimos al storage persistente (R2 en prod). El
    # Document se crea dentro del generator.
    charter_doc = await generate_charter_docx(
        db,
        tenant_id=tenant_id,
        project=project,
        charter=charter,
        created_by=cu.id,
    )

    await write_audit(
        db, action="project.created_from_request", module="projects",
        user_id=cu.id, tenant_id=tenant_id, entity_type="project", entity_id=str(project.id),
        details={
            "request_id": str(pr.id),
            "folio": folio,
            "charter_id": str(charter.id),
            "charter_doc_id": str(charter_doc.id),
        },
    )

    # US-027/028: notificar al PM asignado.
    from app.services.notifications import PM_ASSIGNED, enqueue_notification

    await enqueue_notification(
        db,
        tenant_id=tenant_id,
        user_id=str(body.pm_id),
        type=PM_ASSIGNED,
        title=f"Te asignaron como PM de {project.name}",
        body=f"Folio {folio}. Complementa el Project Charter antes de arrancar.",
        entity_type="project",
        entity_id=str(project.id),
        link=f"/admin/projects/{project.id}/charter",
    )

    await db.commit()
    return {
        "project_id": str(project.id),
        "folio": folio,
        "charter_id": str(charter.id),
        "charter_doc_id": str(charter_doc.id),
        "idempotent": False,
    }
