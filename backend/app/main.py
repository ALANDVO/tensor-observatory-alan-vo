"""FastAPI application factory."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import get_settings
from app.core.database import init_db, close_db
from app.api import api_router
from app.core.auth import settings as auth_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Tensor Observatory API",
        description="High-throughput LLM inference observability platform",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Session middleware for CSRF cookie storage fallback
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret_key,
        max_age=settings.session_max_age_seconds,
        same_site=settings.session_cookie_samesite,
        https_only=settings.session_cookie_secure,
    )

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        if settings.debug:
            import traceback
            traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    # Include API routes
    app.include_router(api_router, prefix="/api")

    # Root redirect
    @app.get("/")
    async def root():
        return {"service": "tensor-observatory", "version": "1.0.0", "docs": "/docs"}

    return app


app = create_app()