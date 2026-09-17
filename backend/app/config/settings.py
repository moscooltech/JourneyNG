"""Application configuration via environment variables.

Follows 12-factor / environment-based configuration. Secrets are never
hard-coded; a development-only fallback JWT secret is generated when
APP_ENV=development so local/CI runs need no manual secret.
"""

from __future__ import annotations

import secrets
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_VALUES = ("development", "staging", "production")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    app_env: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    # --- Datastores ---
    database_url: str = "postgresql+asyncpg://journey:journey_dev_password@localhost:5432/journey"
    redis_url: str = "redis://localhost:6379/0"
    db_pool_size: int = 10
    db_max_overflow: int = 10

    # --- Auth ---
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_access_expires_minutes: int = 30
    jwt_refresh_expires_days: int = 14

    # --- Guest / invitations ---
    guest_token_expires_hours: int = 12
    invitation_expires_minutes: int = 120
    invitation_max_uses_default: int = 10

    # --- Journey bounds ---
    journey_min_duration_minutes: int = 15
    journey_max_duration_hours: int = 24
    max_active_participants: int = 20

    # --- Live location ---
    location_upload_min_interval_ms: int = 2500
    location_stale_after_seconds: int = 30
    location_offline_after_seconds: int = 90
    location_max_accuracy_m: float = 200.0
    location_max_clock_skew_seconds: int = 120
    location_max_age_seconds: int = 600
    arrival_radius_m: float = 75.0
    arrival_stability_count: int = 3
    location_retention_hours: int = 24

    # --- Rate limits (per minute) ---
    rate_limit_login_per_min: int = 10
    rate_limit_register_per_min: int = 5
    rate_limit_invitation_create_per_min: int = 20
    rate_limit_join_per_min: int = 10
    rate_limit_location_per_min: int = 60
    rate_limit_ws_per_min: int = 30
    rate_limit_api_per_min: int = 120

    # --- CORS ---
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    # --- Third parties (optional at dev time) ---
    mapbox_server_token: str = ""
    fcm_project_id: str = ""
    fcm_client_email: str = ""
    fcm_private_key: str = ""
    sentry_dsn: str = ""

    @field_validator("app_env")
    @classmethod
    def _check_env(cls, v: str) -> str:
        if v not in ENV_VALUES:
            raise ValueError(f"APP_ENV must be one of {ENV_VALUES}")
        return v

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors(cls, v: object) -> object:
        if isinstance(v, str):
            import json

            return json.loads(v)
        return v

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def effective_jwt_secret(self) -> str:
        """Development/CI fallback so tests and docker-compose run without config.

        Production refuses to boot without an explicitly configured secret.
        """
        if self.jwt_secret:
            return self.jwt_secret
        if self.is_production:
            raise RuntimeError("JWT_SECRET must be configured in production")
        return secrets.token_urlsafe(48)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
