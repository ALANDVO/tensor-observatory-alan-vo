"""Authentication: Keycloak OIDC with PKCE, HttpOnly session cookies, CSRF protection."""

import secrets
import hashlib
import base64
import json
import time
from dataclasses import dataclass
from typing import Optional, Literal
from urllib.parse import urlencode

import httpx
from jose import jwt, jwk
from jose.exceptions import JWTError, ExpiredSignatureError
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.database import get_db_context
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

settings = get_settings()

# Cookie name constants
SESSION_COOKIE_NAME = "to_session"
CSRF_COOKIE_NAME = "to_csrf"


# ===== PKCE Helpers =====

def generate_code_verifier() -> str:
    """Generate PKCE code verifier (43-128 chars)."""
    return secrets.token_urlsafe(96)[:128]


def generate_code_challenge(verifier: str) -> str:
    """Generate PKCE code challenge (S256)."""
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def generate_state() -> str:
    """Generate OAuth state parameter."""
    return secrets.token_urlsafe(32)


def generate_nonce() -> str:
    """Generate OIDC nonce."""
    return secrets.token_urlsafe(32)


# ===== Token Models =====

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    id_token: Optional[str] = None
    scope: str = ""


class UserInfo(BaseModel):
    sub: str
    email: Optional[str] = None
    name: Optional[str] = None
    preferred_username: Optional[str] = None
    realm_access: dict = Field(default_factory=dict)
    resource_access: dict = Field(default_factory=dict)


@dataclass
class SessionData:
    user_id: str
    email: Optional[str]
    name: Optional[str]
    roles: list[str]
    access_token: str
    refresh_token: Optional[str]
    expires_at: float
    created_at: float


# ===== JWKS Cache =====

_jwks_cache: dict = {}
_jwks_fetched_at: float = 0
JWKS_TTL = 3600  # 1 hour


async def fetch_jwks() -> dict:
    """Fetch and cache JWKS from Keycloak."""
    global _jwks_cache, _jwks_fetched_at
    now = time.time()
    if _jwks_cache and (now - _jwks_fetched_at) < JWKS_TTL:
        return _jwks_cache

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(settings.keycloak_jwks_url)
        resp.raise_for_status()
        _jwks_cache = resp.json()
        _jwks_fetched_at = now
        return _jwks_cache


async def get_signing_key(kid: str) -> Optional[jwk.Key]:
    """Get RSA signing key by key ID."""
    jwks = await fetch_jwks()
    for key_data in jwks.get("keys", []):
        if key_data.get("kid") == kid:
            return jwk.construct(key_data)
    return None


# ===== Token Validation =====

async def validate_id_token(id_token: str, nonce: Optional[str] = None) -> UserInfo:
    """Validate OIDC ID token: signature, issuer, audience, nonce, expiry."""
    try:
        header = jwt.get_unverified_header(id_token)
        kid = header.get("kid")
        if not kid:
            raise JWTError("Missing kid in token header")

        key = await get_signing_key(kid)
        if not key:
            raise JWTError(f"Signing key not found for kid: {kid}")

        payload = jwt.decode(
            id_token,
            key,
            algorithms=["RS256"],
            audience=settings.keycloak_client_id,
            issuer=settings.keycloak_issuer_url,
            options={"verify_at_hash": False},
        )

        if nonce and payload.get("nonce") != nonce:
            raise JWTError("Nonce mismatch")

        return UserInfo(**payload)

    except ExpiredSignatureError:
        raise JWTError("Token expired")
    except JWTError:
        raise
    except Exception as e:
        raise JWTError(f"Token validation failed: {e}")


async def exchange_code_for_tokens(code: str, code_verifier: str) -> TokenResponse:
    """Exchange authorization code for tokens at Keycloak token endpoint."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.keycloak_redirect_uri,
            "client_id": settings.keycloak_client_id,
            "client_secret": settings.keycloak_client_secret,
            "code_verifier": code_verifier,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        resp = await client.post(settings.keycloak_token_url, data=data, headers=headers)
        if resp.status_code != 200:
            raise ValueError(f"Token exchange failed: {resp.text}")
        return TokenResponse(**resp.json())


async def refresh_access_token(refresh_token: str) -> TokenResponse:
    """Refresh access token using refresh token."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": settings.keycloak_client_id,
            "client_secret": settings.keycloak_client_secret,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        resp = await client.post(settings.keycloak_token_url, data=data, headers=headers)
        if resp.status_code != 200:
            raise ValueError(f"Token refresh failed: {resp.text}")
        return TokenResponse(**resp.json())


# ===== Session Management =====

async def create_session(user_info: UserInfo, tokens: TokenResponse) -> str:
    """Create server-side session, return session ID."""
    session_id = secrets.token_urlsafe(32)
    roles = user_info.realm_access.get("roles", [])
    resource_roles = user_info.resource_access.get(settings.keycloak_client_id, {}).get("roles", [])
    all_roles = list(set(roles + resource_roles))

    session_data = SessionData(
        user_id=user_info.sub,
        email=user_info.email,
        name=user_info.name or user_info.preferred_username,
        roles=all_roles,
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_at=time.time() + tokens.expires_in,
        created_at=time.time(),
    )

    from app.models.session import Session as SessionModel

    async with get_db_context() as db:
        db_session = SessionModel(
            id=session_id,
            user_id=user_info.sub,
            email=user_info.email,
            name=session_data.name,
            roles=json.dumps(all_roles),
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token or "",
            expires_at=int(session_data.expires_at),
            created_at=int(session_data.created_at),
        )
        db.add(db_session)
        await db.commit()

    return session_id


async def get_session(session_id: str) -> Optional[SessionData]:
    """Retrieve and validate session by ID."""
    from app.models.session import Session as SessionModel

    async with get_db_context() as db:
        result = await db.execute(select(SessionModel).where(SessionModel.id == session_id))
        db_session = result.scalar_one_or_none()

    if not db_session:
        return None

    if db_session.expires_at < time.time():
        await delete_session(session_id)
        return None

    return SessionData(
        user_id=db_session.user_id,
        email=db_session.email,
        name=db_session.name,
        roles=json.loads(db_session.roles),
        access_token=db_session.access_token,
        refresh_token=db_session.refresh_token or None,
        expires_at=db_session.expires_at,
        created_at=db_session.created_at,
    )


async def delete_session(session_id: str) -> None:
    """Delete session from database."""
    from app.models.session import Session as SessionModel

    async with get_db_context() as db:
        result = await db.execute(select(SessionModel).where(SessionModel.id == session_id))
        db_session = result.scalar_one_or_none()
        if db_session:
            await db.delete(db_session)
            await db.commit()


async def refresh_session_if_needed(session_data: SessionData) -> SessionData:
    """Refresh access token if near expiry."""
    if session_data.expires_at - time.time() < 300:  # 5 min buffer
        if session_data.refresh_token:
            tokens = await refresh_access_token(session_data.refresh_token)
            session_data.access_token = tokens.access_token
            session_data.expires_at = time.time() + tokens.expires_in
            if tokens.refresh_token:
                session_data.refresh_token = tokens.refresh_token
            await update_session_tokens(session_data)
    return session_data


async def update_session_tokens(session_data: SessionData) -> None:
    """Update session tokens in database."""
    from app.models.session import Session as SessionModel

    async with get_db_context() as db:
        result = await db.execute(select(SessionModel).where(SessionModel.id == session_data.user_id))
        db_session = result.scalar_one_or_none()
        if db_session:
            db_session.access_token = session_data.access_token
            db_session.refresh_token = session_data.refresh_token or ""
            db_session.expires_at = int(session_data.expires_at)
            await db.commit()


# ===== CSRF Protection =====

def generate_csrf_token() -> str:
    """Generate CSRF token."""
    return secrets.token_urlsafe(32)


def verify_csrf_token(cookie_token: str, header_token: str) -> bool:
    """Verify CSRF token (constant-time comparison)."""
    return secrets.compare_digest(cookie_token, header_token)


# ===== Authorization =====

ROLE_VIEWER = "viewer"
ROLE_OPERATOR = "operator"
ROLE_ADMIN = "admin"

ROLE_HIERARCHY = {
    ROLE_VIEWER: 1,
    ROLE_OPERATOR: 2,
    ROLE_ADMIN: 3,
}


def has_role(user_roles: list[str], required_role: str) -> bool:
    """Check if user has required role or higher."""
    user_max = max((ROLE_HIERARCHY.get(r, 0) for r in user_roles), default=0)
    required_level = ROLE_HIERARCHY.get(required_role, 0)
    return user_max >= required_level


def require_role(required_role: str):
    """FastAPI dependency factory for role-based access."""
    from fastapi import Depends, HTTPException, status
    from app.api.deps import get_current_session

    async def _check(session: SessionData = Depends(get_current_session)) -> SessionData:
        if not has_role(session.roles, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {required_role}",
            )
        return session

    return _check