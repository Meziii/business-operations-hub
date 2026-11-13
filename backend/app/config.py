from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_SECRET = "dev-only-secret-change-me-before-any-deployment"


class Settings(BaseSettings):
    """Configuration lue dans les variables d'environnement (voir .env.example)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "postgresql+psycopg://boh:boh@localhost:5434/boh"
    jwt_secret: str = DEV_SECRET
    jwt_expire_minutes: int = 480
    cookie_secure: bool = False
    ai_provider: str = "mock"
    ai_model: str = "claude-opus-5-5"
    anthropic_api_key: str = ""
    storage_dir: str = "storage"
    max_upload_mb: int = 10
    demo_password: str = ""
    demo_profile: str = "generic"

    def check(self) -> None:
        if len(self.jwt_secret) < 32:
            raise RuntimeError("JWT_SECRET doit faire au moins 32 caractères.")
        if self.app_env == "production" and self.jwt_secret == DEV_SECRET:
            raise RuntimeError("JWT_SECRET doit être défini en production.")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.check()
    return settings
