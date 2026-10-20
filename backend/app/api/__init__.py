"""API router aggregation."""

from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.models import router as models_router
from app.api.benchmarks import router as benchmarks_router
from app.api.hardware import router as hardware_router, compat_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(models_router)
api_router.include_router(benchmarks_router)
api_router.include_router(hardware_router)
api_router.include_router(compat_router)