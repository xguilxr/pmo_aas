from fastapi import APIRouter

from app.api.v1.endpoints import admin_roles, admin_users, auth

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(admin_users.router)
api_router.include_router(admin_roles.router)


@api_router.get("/ping", tags=["meta"])
async def ping():
    return {"pong": True}
