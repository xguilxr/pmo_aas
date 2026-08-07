from functools import lru_cache
from typing import Literal

from pydantic import model_validator
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

    # MCS IA-03 — límite de coste por ejecución de IA.
    # El límite de iteraciones ya vive en `_AI_CALL_MAX_RETRIES`; esto acota lo
    # otro que puede dispararse: el tamaño del contexto. Un proyecto con
    # cientos de minutas lo hace crecer sin techo, y los reintentos lo
    # multiplican. 0 = sin límite (no recomendado en producción).
    AI_MAX_PROMPT_CHARS: int = 120_000
    LOG_LEVEL: str = "INFO"

    # MCS OPS-01 — los registros DEBEN ser estructurados y salir por la salida
    # estándar. `json` es el default y el único valor que vale en producción:
    # `consola` es una comodidad de desarrollo (una línea coloreada y legible)
    # y `configurar_registro` la ignora si `PYTHON_ENV == "production"`.
    # Dejar que una variable de entorno apague el formato estructurado en
    # producción convertiría el requisito en una recomendación.
    LOG_FORMAT: Literal["json", "consola"] = "json"

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/pmoaas"
    REDIS_URL: str = "redis://localhost:6379/0"

    JWT_SECRET: str = "dev_change_me_dev_change_me_dev_"
    JWT_REFRESH_SECRET: str = "dev_refresh_change_me_dev_refresh"
    JWT_ALGORITHM: str = "HS256"
    # MCS SEG-01 · ASVS 12.4.2 — motor antivirus para lo que se sube.
    # Vacío = no hay motor: la verificación de firma sigue corriendo (no
    # necesita motor) y lo demás se anota según `POLITICA_SIN_MOTOR`.
    # Formato: `tcp://host:3310` — protocolo INSTREAM de clamd.
    CLAMAV_URL: str = ""

    # MCS SEG-01 · ASVS 4.3.1 — segundo factor por correo para las interfaces de
    # administración. Interruptor y no constante porque las pruebas necesitan
    # poder apagarlo: con él encendido, cada inicio de sesión de administración
    # de la suite tendría que pasar por un buzón.
    #
    # **Por defecto encendido.** Un control de seguridad cuyo valor por defecto
    # es «apagado» está apagado en producción el día que a alguien se le olvida
    # encenderlo, que es siempre.
    ADMIN_MFA_REQUIRED: bool = True

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

    # AM-10 (2026-08-05): a partir de este número de fallos, cada intento
    # siguiente espera el doble que el anterior. **No hay bloqueo duro.**
    #
    # Antes eran 15 minutos fijos, y ese era el problema: quien conociera un
    # nombre de usuario dejaba esa cuenta fuera un cuarto de hora, y con una
    # lista de usuarios, al inquilino entero. El retardo creciente frena igual
    # la adivinación —12 intentos por hora con el tope puesto— y **nunca deja a
    # nadie fuera**: quien tecleó mal espera segundos, no minutos.
    #
    # `ACCOUNT_LOCK_MINUTES` desapareció. Si sigue puesta en el entorno, queda
    # inerte: `extra="ignore"`.
    MAX_FAILED_LOGIN_ATTEMPTS: int = 5
    LOGIN_BACKOFF_BASE_SECONDS: int = 2
    LOGIN_BACKOFF_MAX_SECONDS: int = 300

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

    # ARQ-04 — configuración en el entorno, y **toda** en esta clase.
    #
    # Las cinco de abajo se leían con `os.environ` sueltas por el código. No es
    # cosmético: `Settings` lee además de `.env`, así que un valor puesto solo
    # en el fichero llegaba a unos sitios y a otros no.
    #
    # El caso feo era `APPROVAL_TOKEN_SECRET`: `change_approvals.py` resolvía el
    # secreto con `os.environ.get("JWT_SECRET")` y, si no estaba en el entorno
    # del proceso, caía a un literal de desarrollo. Con el secreto declarado
    # solo en `.env`, los tokens de aprobación se habrían firmado con la cadena
    # pública mientras la autenticación usaba la real — el mismo secreto
    # resuelto de dos maneras.
    APPROVAL_TOKEN_SECRET: str = ""  # vacío = usa JWT_SECRET, que sí está aquí
    MPXJ_CLI_CP: str = "/opt/mpxj/lib/*:/opt/mpxj/cli"
    MPP_PARSE_TIMEOUT_SECONDS: int = 60
    CELERY_BROKER_URL: str = ""  # vacío = usa REDIS_URL
    CELERY_RESULT_BACKEND: str = ""  # vacío = usa REDIS_URL
    # Los dos nombres con los que se venía resolviendo la URL pública. Se
    # aceptan por compatibilidad; el valor efectivo cae a `APP_BASE_URL`, que
    # ya traía el dominio de producción. El fallback anterior era
    # `http://localhost:3000`, así que sin ninguna de las dos puestas los
    # correos de aprobación salían con enlaces a la máquina de quien los leía.
    APP_PUBLIC_URL: str = ""
    NEXT_PUBLIC_BASE_URL: str = ""

    @model_validator(mode="after")
    def _produccion_sin_estado_local(self) -> "Settings":
        """MCS ARQ-04 — «procesos sin estado». Se comprueba al arrancar.

        `STORAGE_BACKEND` vale `local` por defecto, que es lo correcto en
        desarrollo y **rompe los doce factores en producción**: los archivos
        caen en `/tmp` del contenedor, así que se pierden en cada despliegue y
        una segunda réplica no ve lo que subió la primera.

        Y falla de la peor manera: sin ruido. La subida devuelve 200, el
        documento aparece en la lista, y desaparece cuando Railway recicla el
        proceso. Nadie asocia lo segundo con lo primero.

        Es la misma forma que OPS-01 —el código lee conforme y producción
        puede estar mal en silencio porque falta una variable—, y se cierra
        igual: haciendo que **no arranque**. Un despliegue que no levanta se
        arregla en cinco minutos; documentos que se evaporan se descubren
        cuando alguien busca el que necesitaba.
        """
        if self.PYTHON_ENV == "production" and self.STORAGE_BACKEND == "local":
            raise ValueError(
                "STORAGE_BACKEND='local' en producción: los archivos irían al "
                "disco del contenedor y se perderían en cada despliegue. "
                "Definí STORAGE_BACKEND=s3 con las variables S3_*."
            )
        return self

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
