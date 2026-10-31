from fastapi import APIRouter

from app.api.v1.endpoints import concepts, diagnostic, learner, ops, practice, users

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(users.router)
api_v1_router.include_router(concepts.router)
api_v1_router.include_router(diagnostic.router)
api_v1_router.include_router(practice.router)
api_v1_router.include_router(learner.router)
api_v1_router.include_router(ops.router_api)
