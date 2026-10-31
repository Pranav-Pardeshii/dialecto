from fastapi import APIRouter

from app.api.v1.endpoints import (
    authoring,
    concepts,
    diagnostic,
    diagrams,
    learner,
    ops,
    practice,
    review,
    speech,
    teachback,
    teacher,
    users,
)

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(users.router)
api_v1_router.include_router(concepts.router)
api_v1_router.include_router(diagnostic.router)
api_v1_router.include_router(practice.router)
api_v1_router.include_router(learner.router)
api_v1_router.include_router(teachback.router)
api_v1_router.include_router(review.router)
api_v1_router.include_router(teacher.router)
api_v1_router.include_router(speech.router)
api_v1_router.include_router(ops.router_api)
api_v1_router.include_router(authoring.router)
api_v1_router.include_router(diagrams.router)
