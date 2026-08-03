from functools import lru_cache
from typing import Literal

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

    # MCS OPS-02 — captura y notificación de errores en producción.
    # Vacío = desactivado, que es lo correcto en local y en tests. Al ponerle
    # el DSN en Railway, la instrumentación se enciende sola.
    SENTRY_DSN: str = ""
    SENTRY_TRACES_SAMPLE_RATE: float = 0.0
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

    # BUG-053 (2026-05-08): cleanup post-Ollama. Modos canónicos:
    #   - "disabled": sin IA, endpoints `/ai/*` responden 409.
    #   - "platform": Groq (llama-3.3-70b-versatile) con la key de plataforma.
    #   - "byo": tenant trae su propia key (openai/anthropic/gemini/perplexity).
    # Retro-compat: tenants viejos con mode in {ollama, gemini, claude}
    # se migraron a "platform" en la migración 0053.
    AI_MODE: Literal["disabled", "platform", "byo"] = "platform"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"
    # IA base de la plataforma (modo "platform"). La api_key se lee primero
    # de `platform_ai_settings.groq_api_key_encrypted` (cifrada con Fernet);
    # si está vacía, cae a este env para dev/test.
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # Solo desarrollo local. En producción `STORAGE_BACKEND=s3` y este valor no
    # se usa (ver US-066). bandit marca la ruta fija en /tmp por riesgo de
    # enlace simbólico; se acepta porque nunca es la ruta de producción.
    STORAGE_PATH: str = "/tmp/pmo-uploads"  # nosec B108

    # US-066: backend de storage para documentos uploaded por tenants y
    # PDFs generados por el worker. `local` usa filesystem (solo dev /
    # branding); `s3` usa object storage S3-compatible (Cloudflare R2
    # en prod). Ver docs/runbooks/infra/uploads-storage.md.
    STORAGE_BACKEND: str = "local"  # "local" | "s3"
    S3_BUCKET: str = ""
    S3_ENDPOINT_URL: str = ""  # ej. https://<account>.r2.cloudflarestorage.com
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""
    S3_REGION: str = "auto"  # "auto" para R2; región concreta para B2/AWS

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
