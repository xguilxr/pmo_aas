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
    # ENH-011: fallback del httpx timeout total de OllamaProvider cuando el
    # tenant no configuró `settings.ai.ollama.timeout_sec`. Transcripts
    # largas (1h de reunión) pueden tardar >2min en un 7B local — por eso
    # el default es generoso y el env se puede subir sin bound rígido.
    AI_TIMEOUT_S: int = 120
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"
    # US-057: IA base de la plataforma (modo "platform"). El api_key se lee
    # primero de `platform_ai_settings.groq_api_key_encrypted` (cifrada con
    # Fernet); si está vacía, cae a este env para dev/test. El modelo por
    # defecto (llama-3.1-70b-versatile) balancea calidad + free tier.
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-70b-versatile"

    STORAGE_PATH: str = "/tmp/pmo-uploads"

    MAX_FAILED_LOGIN_ATTEMPTS: int = 5
    ACCOUNT_LOCK_MINUTES: int = 15

    # US-028: email delivery via Resend. Sin API key el canal email
    # queda deshabilitado y las notificaciones viven solo in-app.
    RESEND_API_KEY: str = ""
    RESEND_FROM: str = ""  # ej. "PMO·aaS <no-reply@pmo-aas.com>"
    APP_BASE_URL: str = "https://app.pmo-aas.com"  # usado en CTA y unsubscribe links

    # US-057: Fernet para cifrar API keys BYO de tenants + Groq key de
    # plataforma. La reactivamos después de la deprecación de US-047 (CF
    # Access); US-048 solo cifraba el auth_legacy de Ollama. Ahora se usa
    # activamente en:
    # - platform_ai_settings.groq_api_key_encrypted (superadmin).
    # - tenants.settings.ai.byo.api_key_encrypted (tenant admin).
    # En producción DEBE setearse con `python -c "from cryptography.fernet
    # import Fernet; print(Fernet.generate_key().decode())"`.
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
