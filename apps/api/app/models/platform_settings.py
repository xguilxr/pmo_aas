"""Platform-wide settings editable por superadmin (US-054).

Tabla singleton: siempre existe 1 row con id='default'. El provider de
AI la consulta entre el tenant override y las env vars — permite al
superadmin cambiar el modelo/base_url/timeout global sin redeploy.

Diseñada como 1 row + columnas tipadas (no JSON genérico) para que las
migraciones futuras sean aditivas claras. Si se agregan más secciones
(ej. branding global, feature flags) se crearán tablas hermanas.
"""
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin

PLATFORM_SETTINGS_ID = "default"


class PlatformAISettings(Base, TimestampMixin):
    __tablename__ = "platform_ai_settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=PLATFORM_SETTINGS_ID)

    ai_mode: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # Groq como IA base de la plataforma (modo "platform").
    # La api_key se guarda cifrada con Fernet (FERNET_KEY env).
    groq_api_key_encrypted: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    groq_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
