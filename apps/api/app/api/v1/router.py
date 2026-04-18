from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin_panel,
    admin_roles,
    admin_users,
    ai,
    auth,
    dashboard,
    modules,
    organizations,
    project_requests,
    projects,
    superadmin,
    superadmin_panel,
    tasks,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(admin_users.router)
api_router.include_router(admin_roles.router)
api_router.include_router(admin_panel.router)
api_router.include_router(organizations.router)
api_router.include_router(organizations.programs_router)
api_router.include_router(project_requests.router)
api_router.include_router(projects.router)
api_router.include_router(modules.risks_router)
api_router.include_router(modules.issues_router)
api_router.include_router(modules.chg_router)
api_router.include_router(modules.docs_router)
api_router.include_router(modules.lessons_router)
api_router.include_router(modules.minutes_router)
api_router.include_router(dashboard.router)
api_router.include_router(ai.router)
api_router.include_router(tasks.router)
api_router.include_router(superadmin.router)
api_router.include_router(superadmin_panel.router)


@api_router.get("/ping", tags=["meta"])
async def ping():
    return {"pong": True}
