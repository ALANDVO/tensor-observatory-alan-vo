"""Application configuration loaded from environment."""

from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, computed_field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "tensor-observatory"
    app_env: Literal["development", "production", "demo"] = "development"
    debug: bool = True
    host: str = "127.0.0.1"
    port: int = 8000

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/tensor_observatory.db"

    # Auth - Keycloak OIDC
    keycloak_server_url: str = "http://localhost:8080"
    keycloak_realm: str = "tensor-observatory"
    keycloak_client_id: str = "tensor-observatory-backend"
    keycloak_client_secret: str = ""
    keycloak_redirect_uri: str = "http://localhost:8000/auth/callback"

    # Session
    session_secret_key: str = "dev-secret-change-in-production"
    session_cookie_name: str = "to_session"
    session_cookie_secure: bool = False
    session_cookie_httponly: bool = True
    session_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    session_max_age_seconds: int = 86400  # 24 hours

    # CSRF
    csrf_secret_key: str = "dev-csrf-secret-change-in-production"
    csrf_cookie_name: str = "to_csrf"
    csrf_header_name: str = "X-CSRF-Token"

    # LLM (opt-in advisory)
    llm_api_key: str = ""
    llm_provider: Literal["openai-compatible", "anthropic", "gemini", "ollama"] = "openai-compatible"
    llm_model: str = ""
    llm_base_url: str = ""
    llm_timeout_seconds: int = 30

    # Demo mode
    demo_mode: bool = False
    demo_user_email: str = "demo@tensor-observatory.local"
    demo_user_name: str = "Demo User"

    @computed_field
    @property
    def keycloak_issuer_url(self) -> str:
        return f"{self.keycloak_server_url}/realms/{self.keycloak_realm}"

    @computed_field
    @property
    def keycloak_jwks_url(self) -> str:
        return f"{self.keycloak_issuer_url}/protocol/openid-connect/certs"

    @computed_field
    @property
    def keycloak_auth_url(self) -> str:
        return f"{self.keycloak_issuer_url}/protocol/openid-connect/auth"

    @computed_field
    @property
    def keycloak_token_url(self) -> str:
        return f"{self.keycloak_issuer_url}/protocol/openid-connect/token"

    @computed_field
    @property
    def keycloak_logout_url(self) -> str:
        return f"{self.keycloak_issuer_url}/protocol/openid-connect/logout"

    def validate_production(self) -> None:
        """Validate required settings for production."""
        if self.app_env == "production":
            if self.demo_mode:
                raise ValueError("Demo mode MUST be disabled in production")
            if self.session_secret_key == "dev-secret-change-in-production":
                raise ValueError("SESSION_SECRET_KEY must be set in production")
            if self.csrf_secret_key == "dev-csrf-secret-change-in-production":
                raise ValueError("CSRF_SECRET_KEY must be set in production")
            if self.session_cookie_secure is False:
                raise ValueError("SESSION_COOKIE_SECURE must be true in production")
            if not self.keycloak_client_secret:
                raise ValueError("KEYCLOAK_CLIENT_SECRET must be set in production")


@lru_cache
def get_settings() -> Settings:
    return Settings()