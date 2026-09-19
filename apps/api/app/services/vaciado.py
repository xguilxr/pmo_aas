"""US-274 — vaciar los datos de un inquilino sin borrar el inquilino.

## Qué resuelve

Desactivar y borrar un inquilino ya existían (`superadmin.py`). Faltaba la
operación de en medio: dejarlo como recién aprovisionado —con su gente, su
marca y su configuración— y sin nada de lo que se cargó dentro.

## Por qué un inventario declarado y no reflexión

Recorrer las tablas por reflexión («borra todo lo que tenga `tenant_id`»)
parece más corto y es peor: la tabla que alguien agregue mañana no aparece en
ninguna revisión, y un vaciado incompleto deja un inquilino que **parece**
limpio. El error no se ve al vaciar; se ve semanas después, cuando un folio
repetido o un reporte huérfano sale de datos que se creían borrados.

Aquí las dos listas están escritas a mano y el trinquete
(`tests/test_us274_vaciado_inventario.py`) compara lo declarado contra el
metadata de SQLAlchemy: una tabla nueva rompe la suite hasta que alguien
decida, por escrito, de qué lado va.

## Qué sobrevive (DEC-045)

El inquilino, su `settings`, su marca, sus usuarios y sus membresías. Y
`audit_log`, que no es una decisión de producto sino una imposibilidad: AM-08
lo hace de solo anexado con disparadores de PostgreSQL (migración 0097), así
que un `DELETE` sobre él se rechaza en la base. Vale la pena que esté escrito
en `SOBREVIVEN` con ese motivo, porque leer la lista y no encontrarlo llevaría
a alguien a «arreglar» el olvido.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import ColumnElement, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

#: Orden de borrado: las hijas antes que sus padres. La lista se generó una vez
#: desde el grafo de dependencias y desde entonces se mantiene a mano; el
#: trinquete comprueba que sigue siendo válida, así que un FK nuevo que la
#: invalide falla en la suite y no en producción.
#:
#: El grupo `actors` / `teams` / `areas` va junto y tarde a propósito: entre los
#: tres hay un ciclo de claves foráneas (`areas.lead_actor_id` apunta a un actor
#: que apunta a un área), así que ningún orden los resuelve solo. Se rompen antes
#: con `FKS_A_ANULAR`. Y van después de `portfolios` porque
#: `portfolios.owner_actor_id` también los referencia.
TABLAS_A_VACIAR: tuple[str, ...] = (
    "risk_action_assignees",
    "report_history",
    "task_dependencies",
    "scheduled_reports",
    "risk_actions",
    "plan_baseline_tasks",
    "change_approvers",
    "approval_tokens",
    "tasks",
    "scheduled_minutes",
    "risks",
    "report_builder_templates",
    "project_participations",
    "project_members",
    "project_health_evaluations",
    "project_charters",
    "project_artifacts",
    "project_ai_contexts",
    "plan_baselines",
    "meeting_minutes",
    "lessons",
    "issues",
    "documents",
    "change_requests",
    "area_assignments",
    "ai_report_templates",
    "projects",
    "project_requests",
    "programs",
    "departments",
    "assistant_messages",
    "user_scope_assignments",
    "tenant_role_permission_overrides",
    "stakeholders",
    "reports",
    "report_templates",
    "portfolios",
    "permission_change_requests",
    "organization_user_exclusions",
    "notifications",
    "business_units",
    "assistant_conversations",
    "ai_jobs",
    "project_roles",
    "actors",
    "teams",
    "areas",
    "organizations",
    "metric_snapshots",
    "folio_sequences",
)

#: Lo que el vaciado no toca, y por qué. El motivo es parte del dato: sin él,
#: la siguiente persona no sabe si una tabla está aquí por decisión o por
#: descuido.
SOBREVIVEN: dict[str, str] = {
    "tenants": "es el inquilino: se vacía, no se borra (DEC-045).",
    "users": "las personas del inquilino sobreviven (DEC-045).",
    "user_tenant_memberships": "a qué inquilinos pertenece cada persona (US-214).",
    "roles": "catálogo de roles legacy (DEC-024), atado a los usuarios que quedan.",
    "user_roles": "la asignación de esos roles.",
    "refresh_tokens": "sesión abierta de un usuario que sobrevive.",
    "password_reset_tokens": "restablecimiento en curso de un usuario que sobrevive.",
    "admin_otp_codes": "segundo factor en curso (ASVS 4.3.1).",
    "dispositivos_confiables": "dispositivos recordados de un usuario que sobrevive.",
    "audit_log": (
        "no se puede borrar: AM-08 lo hace de solo anexado con disparadores de "
        "PostgreSQL (migración 0097). No es una decisión de producto."
    ),
    "platform_ai_settings": "configuración de plataforma, no de un inquilino.",
    "report_sections": "catálogo global de secciones de reporte.",
}

#: Tablas sin `tenant_id` que igual son datos del inquilino: se alcanzan por su
#: padre. Cada par es (columna, tabla padre); con varios pares, basta que
#: cualquiera apunte al inquilino.
#:
#: `task_dependencies` y `risk_action_assignees` llevan dos porque sus dos
#: extremos pueden colgar de padres distintos, y quedarse con uno dejaría filas
#: que después bloquean el borrado del otro extremo.
HIJAS_POR_PADRE: dict[str, tuple[tuple[str, str], ...]] = {
    "assistant_messages": (("conversation_id", "assistant_conversations"),),
    "project_members": (("project_id", "projects"),),
    "plan_baseline_tasks": (("baseline_id", "plan_baselines"),),
    "task_dependencies": (("predecessor_id", "tasks"), ("successor_id", "tasks")),
    "risk_action_assignees": (
        ("risk_action_id", "risk_actions"),
        ("actor_id", "actors"),
    ),
    "organization_user_exclusions": (("organization_id", "organizations"),),
}

#: Las referencias que se ponen en nulo antes de borrar, para romper el ciclo
#: `actors` ↔ `areas` y la autorreferencia de `actors`. Las dos columnas son
#: nulables; si alguna dejara de serlo, el trinquete lo dice.
FKS_A_ANULAR: tuple[tuple[str, str], ...] = (
    ("areas", "lead_actor_id"),
    ("actors", "manager_actor_id"),
)


def _condicion(tabla: str, tenant_id: UUID | str) -> ColumnElement[bool]:
    """Qué filas de `tabla` son de este inquilino."""
    t = Base.metadata.tables[tabla]
    tid = str(tenant_id)
    if "tenant_id" in t.c:
        return t.c.tenant_id == tid
    pares = HIJAS_POR_PADRE[tabla]
    condiciones = []
    for columna, padre in pares:
        p = Base.metadata.tables[padre]
        condiciones.append(
            t.c[columna].in_(select(p.c.id).where(p.c.tenant_id == tid))
        )
    return or_(*condiciones) if len(condiciones) > 1 else condiciones[0]


async def contar(db: AsyncSession, tenant_id: UUID | str) -> dict[str, int]:
    """Filas por tabla que se borrarían. No toca nada.

    Devuelve **todas** las tablas del inventario, incluidas las que están en
    cero: un preview que solo liste lo que tiene filas se lee como «esto es
    todo lo que hay», y lo que interesa comprobar antes de vaciar es que el
    inventario completo se está mirando.
    """
    fuera: dict[str, int] = {}
    for tabla in TABLAS_A_VACIAR:
        t = Base.metadata.tables[tabla]
        n = (
            await db.execute(
                select(func.count()).select_from(t).where(_condicion(tabla, tenant_id))
            )
        ).scalar_one()
        fuera[tabla] = int(n)
    return fuera


async def vaciar(db: AsyncSession, tenant_id: UUID | str) -> dict[str, int]:
    """Borra los datos del inquilino. **No** hace commit: lo hace el llamador.

    Devuelve las filas borradas por tabla. El conteo sale de `rowcount`, o sea
    de lo que la base dice que borró, y no de un conteo previo: si algo no se
    fue, el número lo delata.
    """
    tid = str(tenant_id)
    for tabla, columna in FKS_A_ANULAR:
        t = Base.metadata.tables[tabla]
        await db.execute(
            update(t).where(t.c.tenant_id == tid).values({columna: None})
        )
    borradas: dict[str, int] = {}
    for tabla in TABLAS_A_VACIAR:
        t = Base.metadata.tables[tabla]
        res = await db.execute(delete(t).where(_condicion(tabla, tenant_id)))
        borradas[tabla] = int(res.rowcount or 0)
    return borradas
