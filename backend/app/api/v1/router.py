from fastapi import APIRouter

from app.api.v1.endpoints import concepts, users

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(users.router)
api_v1_router.include_router(concepts.router)
