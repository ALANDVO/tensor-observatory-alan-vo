"""Authentication endpoints: login, callback, logout, me."""

from typing import Optional
from fastapi import APIRouter, Request, Response, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from urllib.parse import urlencode

from app.core.auth import (
    generate_code_verifier,
    generate_code_challenge,
    generate_state,
    generate_nonce,
    exchange_code_for_tokens,
    validate_id_token,
    create_session,
    delete_session,
    generate_csrf_token,
    SESSION_COOKIE_NAME,
    CSRF_COOKIE_NAME,
    settings,
)
from app.core.config import get_settings
from app.api.deps import get_current_session, get_client_ip, get_user_agent
from app.core.auth import SessionData
from app.models import log_audit
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.get("/login")
async def login(request: Request, response: Response) -> RedirectResponse:
    """Initiate OIDC login with PKCE."""
    # Generate PKCE parameters
    code_verifier = generate_code_verifier()
    code_challenge = generate_code_challenge(code_verifier)
    state = generate_state()
    nonce = generate_nonce()

    # Store PKCE params in session (we'll use a temporary cookie since no session yet)
    # In production, use a short-lived server-side store. For simplicity, encode in state.
    # State format: base64(json({state, code_verifier, nonce}))
    import json, base64
    pkce_data = json.dumps({
        "state": state,
        "code_verifier": code_verifier,
        "nonce": nonce,
    })
    encoded_state = base64.urlsafe_b64encode(pkce_data.encode()).decode()

    # Build authorization URL
    params = {
        "client_id": settings.keycloak_client_id,
        "redirect_uri": settings.keycloak_redirect_uri,
        "response_type": "code",
        "scope": "openid profile email",
        "state": encoded_state,
        "nonce": nonce,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    auth_url = f"{settings.keycloak_auth_url}?{urlencode(params)}"

    # Set PKCE cookie (HttpOnly, short-lived)
    response.set_cookie(
        key="to_pkce",
        value=encoded_state,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        max_age=600,  # 10 minutes
        path="/",
    )

    return RedirectResponse(url=auth_url, status_code=302)


@router.get("/callback")
async def callback(
    request: Request,
    response: Response,
    code: str = "",
    state: str = "",
    error: str = "",
    error_description: str = "",
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Handle OIDC callback."""
    # Check for OAuth errors
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth error: {error} - {error_description}",
        )

    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing code or state parameter",
        )

    # Retrieve PKCE data from cookie
    pkce_cookie = request.cookies.get("to_pkce")
    if not pkce_cookie:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing PKCE cookie (session may have expired)",
        )

    # Clear PKCE cookie
    response.delete_cookie("to_pkce", path="/", httponly=True, secure=settings.session_cookie_secure, samesite=settings.session_cookie_samesite)

    # Decode state
    import json, base64
    try:
        pkce_data = json.loads(base64.urlsafe_b64decode(pkce_cookie.encode()).decode())
        original_state = pkce_data["state"]
        code_verifier = pkce_data["code_verifier"]
        nonce = pkce_data["nonce"]
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid PKCE state",
        )

    # Verify state
    if state != original_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="State mismatch",
        )

    # Exchange code for tokens
    try:
        tokens = await exchange_code_for_tokens(code, code_verifier)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Token exchange failed: {e}",
        )

    # Validate ID token
    try:
        user_info = await validate_id_token(tokens.id_token, nonce)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"ID token validation failed: {e}",
        )

    # Create session
    session_id = await create_session(user_info, tokens)

    # Set session cookie
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        max_age=settings.session_max_age_seconds,
        path="/",
    )

    # Set CSRF cookie
    csrf_token = generate_csrf_token()
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,  # Must be readable by JS for header
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        max_age=settings.session_max_age_seconds,
        path="/",
    )

    # Log audit
    await log_audit(
        db,
        action="login",
        user_id=user_info.sub,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    await db.commit()

    # Redirect to frontend
    frontend_url = "http://localhost:5173" if settings.app_env == "development" else "/"
    return RedirectResponse(url=frontend_url, status_code=302)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    session: Optional[SessionData] = Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Logout: delete session, clear cookies, redirect to Keycloak logout."""
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if session_id:
        await delete_session(session_id)

    if session:
        await log_audit(
            db,
            action="logout",
            user_id=session.user_id,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
        await db.commit()

    # Clear cookies
    response.delete_cookie(SESSION_COOKIE_NAME, path="/", httponly=True, secure=settings.session_cookie_secure, samesite=settings.session_cookie_samesite)
    response.delete_cookie(CSRF_COOKIE_NAME, path="/", httponly=False, secure=settings.session_cookie_secure, samesite=settings.session_cookie_samesite)

    # Build Keycloak logout URL
    logout_url = f"{settings.keycloak_logout_url}?{urlencode({'post_logout_redirect_uri': 'http://localhost:5173' if settings.app_env == 'development' else '/'})}"

    return {"logout_url": logout_url}


@router.get("/me")
async def get_current_user(session: SessionData = Depends(get_current_session)) -> dict:
    """Get current user info."""
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return {
        "user_id": session.user_id,
        "email": session.email,
        "name": session.name,
        "roles": session.roles,
    }


@router.get("/csrf")
async def get_csrf_token(response: Response) -> dict:
    """Get CSRF token (sets cookie)."""
    csrf_token = generate_csrf_token()
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        max_age=settings.session_max_age_seconds,
        path="/",
    )
    return {"csrf_token": csrf_token}