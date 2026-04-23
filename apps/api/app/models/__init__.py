"""Registro central de modelos ORM."""
from app.models.ai import AIJob, Report  # noqa: F401
from app.models.audit import AuditLog  # noqa: F401
from app.models.auth import RefreshToken  # noqa: F401
from app.models.modules import (  # noqa: F401
    ChangeRequest,
    Document,
    Issue,
    Lesson,
    MeetingMinute,
    Risk,
)
from app.models.organization import (  # noqa: F401
    BusinessUnit,
    Department,
    Organization,
    Program,
)
from app.models.platform_settings import PlatformAISettings  # noqa: F401
from app.models.project import Project  # noqa: F401
from app.models.project_area import ProjectArea  # noqa: F401
from app.models.project_charter import ProjectCharter  # noqa: F401
from app.models.project_member import ProjectMember  # noqa: F401
from app.models.project_request import FolioSequence, ProjectRequest  # noqa: F401
from app.models.role import Role, UserRole  # noqa: F401
from app.models.scheduled_report import ScheduledReport  # noqa: F401
from app.models.task import Task, TaskDependency  # noqa: F401
from app.models.tenant import Tenant  # noqa: F401
from app.models.user import User  # noqa: F401
