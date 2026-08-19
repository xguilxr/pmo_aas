from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_org_tenant_name"),)

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    reason_social: Mapped[str | None] = mapped_column(String(200))
    industry: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str | None] = mapped_column(String(100))
    contact_email: Mapped[str | None] = mapped_column(String(200))
    # BUG-068: Text (no String(500)) para admitir data-URLs base64 de logos
    # subidos directamente (PNG/JPG/SVG/WEBP), además de URLs externas.
    logo_url: Mapped[str | None] = mapped_column(Text)
    # ENH-100: logo del *cliente* de esta organización (separado de `logo_url`,
    # que es la marca del propio tenant/PMO). Lo consume el header de los
    # reportes generados por EP020 Report Builder.
    client_logo_url: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Portfolio(Base, TimestampMixin):
    """US-198 — el agrupador ejecutivo de la jerarquía nueva.

    `organizacion → portafolio ⊃ programa → proyecto` (ADR-037). El
    portafolio es donde se decide *qué se hace*; el programa, *cómo se
    coordina*. Reemplaza a `business_units`/`departments`, que modelaban el
    organigrama del cliente y no la cartera de inversión — la diferencia por
    la que ninguna PMO llegó a usarlos.

    **Sin métricas propias a propósito.** Salud, presupuesto y conteos se
    derivan de los proyectos, igual que hoy los deriva el panel de
    organización. Una columna `health_status` aquí sería un valor que hay que
    recalcular y que se queda viejo entre cálculos.
    """

    __tablename__ = "portfolios"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "organization_id", "name", name="uq_portfolio_tenant_org_name"
        ),
    )

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    organization_id: Mapped[UUID] = mapped_column(
        String(36),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # Código corto para reportes y filtros guardados ("TRX-26"), opcional: el
    # nombre ya identifica; el código es para quien lo necesita en una tabla
    # estrecha.
    code: Mapped[str | None] = mapped_column(String(32))
    description: Mapped[str | None] = mapped_column(String(2000))
    # El dueño del portafolio es un actor del catálogo, no un `users.id`: el
    # sponsor ejecutivo del cliente casi nunca tiene cuenta en la plataforma.
    owner_actor_id: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("actors.id", ondelete="SET NULL"), index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[UUID | None] = mapped_column(String(36), ForeignKey("users.id"))


class BusinessUnit(Base, TimestampMixin):
    """RETIRADA (US-198 / ADR-037) — la sustituye `Portfolio`.

    Sigue en el esquema porque el drop de una tabla es irreversible y va en
    W8, cuando el contador de compat confirme que nadie la lee. Sin uso
    productivo (owner 2026-08-19): no hubo datos que migrar.
    """

    __tablename__ = "business_units"
    __table_args__ = (
        UniqueConstraint("tenant_id", "organization_id", "name", name="uq_bu_tenant_org_name"),
    )

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    organization_id: Mapped[UUID] = mapped_column(
        String(36),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[UUID | None] = mapped_column(String(36), ForeignKey("users.id"))


class Department(Base, TimestampMixin):
    """RETIRADA (US-198 / ADR-037) — la sustituye `Program` bajo `Portfolio`.

    Igual que `BusinessUnit`: vive hasta W8. Ver ADR-037.
    """

    __tablename__ = "departments"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "business_unit_id", "name", name="uq_dept_tenant_bu_name"
        ),
    )

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    business_unit_id: Mapped[UUID] = mapped_column(
        String(36),
        ForeignKey("business_units.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[UUID | None] = mapped_column(String(36), ForeignKey("users.id"))


class Program(Base, TimestampMixin):
    """El coordinador de proyectos, ahora **dentro de un portafolio** (US-198).

    `portfolio_id` es NOT NULL: un programa sin portafolio es un programa que
    no aparece en ninguna vista ejecutiva, y esa fue exactamente la forma en
    que la jerarquía vieja se volvió invisible. Los programas que existían al
    migrar quedaron en el «Portafolio General» de su organización
    (migración 0108).

    `organization_id` se conserva aunque `portfolio_id` ya la implique: todo
    el filtrado existente —panel, dashboard, visibilidad— consulta por
    organización, y quitarla obligaría a un join en cada consulta para no
    ganar nada. La consistencia entre ambas la sostiene
    `services/jerarquia.py`, no un CHECK.

    `department_id` se retiró en US-199, junto con los sub-routers de
    BU/departamentos que lo leían (migración 0109).
    """

    __tablename__ = "programs"

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    organization_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    portfolio_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("portfolios.id"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000))
    strategic_alignment: Mapped[str | None] = mapped_column(String(2000))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
