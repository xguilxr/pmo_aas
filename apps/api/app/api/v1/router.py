from fastapi import APIRouter

api_router = APIRouter()
# Epic routers are registered here as they are implemented.


@api_router.get("/ping", tags=["meta"])
async def ping():
    return {"pong": True}
