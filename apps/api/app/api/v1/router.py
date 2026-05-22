from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin_ai,
    admin_panel,
    admin_users,
    ai,
    areas,
    auth,
    branding,
    change_approvals,
    dashboard,
    entity_history,
    modules,
    notifications,
    organizations,
    permission_requests,
    project_artifacts,
    project_charters,
    project_directory,
    project_requests,
    projects,
    report_builder_chat,
    report_builder_render,
    report_builder_templates,
    report_sections,
    report_templates,
    reports,
    risk_actions,
    scheduled_minutes,
    scheduled_reports,
    stakeholders,
    superadmin,
    superadmin_ai,
    superadmin_panel,
    tasks,
    tenant_cross,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(admin_users.router)
api_router.include_router(admin_panel.router)
api_router.include_router(admin_ai.router)
api_router.include_router(branding.router)
api_router.include_router(organizations.router)
api_router.include_router(organizations.programs_router)
api_router.include_router(organizations.business_units_router)
api_router.include_router(organizations.departments_router)
api_router.include_router(project_requests.router)
api_router.include_router(projects.router)
api_router.include_router(project_charters.router)
api_router.include_router(project_artifacts.router)
api_router.include_router(areas.areas_router)
api_router.include_router(areas.teams_router)
api_router.include_router(areas.actors_router)
api_router.include_router(areas.assignments_router)
api_router.include_router(project_directory.roles_router)
api_router.include_router(project_directory.participations_router)
api_router.include_router(project_directory.eligible_router)
api_router.include_router(reports.router)
api_router.include_router(report_templates.router)
api_router.include_router(report_sections.router)
api_router.include_router(report_builder_templates.router)
api_router.include_router(report_builder_render.router)
api_router.include_router(report_builder_chat.router)
api_router.include_router(change_approvals.router)
api_router.include_router(change_approvals.public_router)
api_router.include_router(scheduled_reports.router)
api_router.include_router(scheduled_minutes.router)
api_router.include_router(stakeholders.router)
api_router.include_router(modules.risks_router)
api_router.include_router(risk_actions.router)
api_router.include_router(modules.issues_router)
api_router.include_router(modules.chg_router)
api_router.include_router(modules.docs_router)
api_router.include_router(modules.lessons_router)
api_router.include_router(modules.minutes_router)
api_router.include_router(notifications.router)
api_router.include_router(dashboard.router)
api_router.include_router(ai.router)
api_router.include_router(tasks.router)
api_router.include_router(superadmin.router)
api_router.include_router(superadmin_ai.router)
api_router.include_router(superadmin_panel.router)
api_router.include_router(permission_requests.router)
api_router.include_router(permission_requests.sa_router)
api_router.include_router(tenant_cross.router)
api_router.include_router(entity_history.router)


@api_router.get("/ping", tags=["meta"])
async def ping():
    return {"pong": True}
