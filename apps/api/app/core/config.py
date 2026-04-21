from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    VERSION: str = "0.1.0"
    PYTHON_ENV: Literal["development", "production", "test"] = "development"
    LOG_LEVEL: str = "INFO"

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/pmoaas"
    REDIS_URL: str = "redis://localhost:6379/0"

    JWT_SECRET: str = "dev_change_me_dev_change_me_dev_"
    JWT_REFRESH_SECRET: str = "dev_refresh_change_me_dev_refresh"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_TTL_SEC: int = 3600
    REFRESH_TOKEN_TTL_SEC: int = 2592000
    BCRYPT_ROUNDS: int = 12

    ALLOWED_ORIGINS: str = "http://localhost:3000"
    SEED_ON_STARTUP: bool = True

    AI_MODE: Literal["ollama", "gemini", "claude", "disabled"] = "disabled"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b-instruct-q4_K_M"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"

    STORAGE_PATH: str = "/tmp/pmo-uploads"

    MAX_FAILED_LOGIN_ATTEMPTS: int = 5
    ACCOUNT_LOCK_MINUTES: int = 15

    # DEPRECATED US-NEW-047 (2026-04-21): Cifrado de secretos IA por-tenant.
    # Se introdujo en US-NEW-045 para guardar el CF-Access-Client-Secret del
    # tenant. El pivote a Tailscale (DEC-011) elimina la necesidad de
    # secrets — el canal se asegura por tailnet privado. La key se mantiene
    # únicamente para que `decrypt_secret()` pueda leer valores legacy
    # archivados bajo `settings.ai.ollama.auth_legacy.*`. No se escribe más
    # desde el flujo nuevo. Remover la key cuando todos los tenants
    # productivos tengan `auth_legacy` purgado.
    AI_SECRETS_FERNET_KEY: str = "dev-ai-secrets-fernet-key-change-me-0000="

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def database_url_async(self) -> str:
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and "+" not in url.split("://")[0]:
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql+psycopg"):
            url = url.replace("postgresql+psycopg", "postgresql+asyncpg", 1)
        return url


@lru_cache
def _get_settings() -> Settings:
    return Settings()


settings: Settings = _get_settings()
