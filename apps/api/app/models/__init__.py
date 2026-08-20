"""Registro central de modelos ORM."""
from app.models.ai import AIJob, Report  # noqa: F401
from app.models.ai_report_template import AIReportTemplate  # noqa: F401
from app.models.area import Actor, Area, AreaAssignment, Team  # noqa: F401
from app.models.assistant import (  # noqa: F401
    AssistantConversation,
    AssistantMessage,
)
from app.models.audit import AuditLog  # noqa: F401
from app.models.auth import PasswordResetToken, RefreshToken  # noqa: F401
from app.models.change_approval import (  # noqa: F401
    ApprovalToken,
    ChangeApprover,
)
from app.models.metric_snapshot import MetricSnapshot  # noqa: F401
from app.models.modules import (  # noqa: F401
    ChangeRequest,
    Document,
    Issue,
    Lesson,
    MeetingMinute,
    Risk,
)
from app.models.notification import Notification  # noqa: F401
from app.models.organization import (  # noqa: F401
    BusinessUnit,
    Department,
    Organization,
    Portfolio,
    Program,
)
from app.models.organization_user_exclusion import (  # noqa: F401
    OrganizationUserExclusion,
)
from app.models.permission_request import PermissionChangeRequest  # noqa: F401
from app.models.plan_baseline import PlanBaseline, PlanBaselineTask  # noqa: F401
from app.models.platform_settings import PlatformAISettings  # noqa: F401
from app.models.project import Project  # noqa: F401
from app.models.project_ai_context import ProjectAIContext  # noqa: F401
from app.models.project_artifact import ProjectArtifact  # noqa: F401
from app.models.project_charter import ProjectCharter  # noqa: F401
from app.models.project_member import ProjectMember  # noqa: F401
from app.models.project_participation import ProjectParticipation  # noqa: F401
from app.models.project_request import FolioSequence, ProjectRequest  # noqa: F401
from app.models.project_role import ProjectRole  # noqa: F401
from app.models.report_builder_template import ReportBuilderTemplate  # noqa: F401
from app.models.report_history import ReportHistory  # noqa: F401
from app.models.report_section import ReportSection  # noqa: F401
from app.models.report_template import ReportTemplate  # noqa: F401
from app.models.risk_action import RiskAction, RiskActionAssignee  # noqa: F401
from app.models.role import Role, UserRole  # noqa: F401
from app.models.scheduled_minute import ScheduledMinute  # noqa: F401
from app.models.scheduled_report import ScheduledReport  # noqa: F401
from app.models.stakeholder import Stakeholder  # noqa: F401
from app.models.task import Task, TaskDependency  # noqa: F401
from app.models.tenant import Tenant  # noqa: F401
from app.models.tenant_permission import TenantRolePermissionOverride  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.user_scope_assignment import UserScopeAssignment  # noqa: F401
