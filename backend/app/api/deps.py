"""FastAPI dependencies."""

from typing import Optional
from fastapi import Depends, Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import (
    get_session,
    SessionData,
    verify_csrf_token,
    ROLE_VIEWER,
    ROLE_OPERATOR,
    ROLE_ADMIN,
    has_role,
)
from app.core.config import get_settings

settings = get_settings()

# Cookie names
SESSION_COOKIE_NAME = settings.session_cookie_name
CSRF_COOKIE_NAME = settings.csrf_cookie_name
CSRF_HEADER_NAME = settings.csrf_header_name


async def get_current_session(request: Request) -> Optional[SessionData]:
    """Get current session from cookie (no exception if missing)."""
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id:
        return None
    return await get_session(session_id)


async def require_session(request: Request) -> SessionData:
    """Require valid session (raises 401 if missing/invalid)."""
    session = await get_current_session(request)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    # Refresh token if needed
    from app.core.auth import refresh_session_if_needed
    return await refresh_session_if_needed(session)


async def require_csrf(request: Request, session: SessionData = Depends(require_session)) -> SessionData:
    """Verify CSRF token on state-changing requests."""
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
        header_token = request.headers.get(CSRF_HEADER_NAME)
        if not cookie_token or not header_token or not verify_csrf_token(cookie_token, header_token):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid CSRF token",
            )
    return session


def require_role_dependency(required_role: str):
    """Factory for role-based access control."""
    async def _check(session: SessionData = Depends(require_session)) -> SessionData:
        if not has_role(session.roles, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {required_role}",
            )
        return session
    return _check


# Common role dependencies
require_viewer = require_role_dependency(ROLE_VIEWER)
require_operator = require_role_dependency(ROLE_OPERATOR)
require_admin = require_role_dependency(ROLE_ADMIN)


def get_client_ip(request: Request) -> Optional[str]:
    """Extract client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def get_user_agent(request: Request) -> Optional[str]:
    """Extract user agent from request."""
    return request.headers.get("User-Agent")