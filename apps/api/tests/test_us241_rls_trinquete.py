"""US-241 / ADR-003 — dos trinquetes de la oleada W3 (RLS).

1. **Cobertura de tablas.** Toda tabla tenant-scoped nueva tiene que
   clasificarse: o entra al dominio protegido por una migración de RLS, o se
   declara explícitamente pendiente (y de qué oleada). Lo que no puede pasar
   es que aparezca sin que nadie la mire — que es justo el defecto que
   `DOC-03` (`test_doc03_er_generado.py`) vino a cerrar para el diagrama ER.
   Esto corre en SQLite igual que en Postgres: no depende de que RLS exista
   en el motor, solo de que el modelo declare `tenant_id`.

2. **El centinela no se escribe desde cualquier lado.** `alcance_plataforma=
   True` es el único argumento que hace que `fijar_tenant_actual()` fije
   `app.tenant_id = '*'` (ver `app/core/tenant_context.py`). Un grep literal
   sobre el árbol de `app/` — no una lista de nombres de archivo, no un bucle
   sobre módulos importados — porque la lección del 2026-08-19
   (`LESSONS.md`) es exactamente esa: un trinquete que lee código no ve tras
   una indirección.
"""
from __future__ import annotations

import re
from pathlib import Path

RAIZ_APP = Path(__file__).resolve().parents[1] / "app"

#: Dominio jerarquía, protegido desde `20260827_0117_rls_jerarquia.py`. No se
#: importa esa migración (su nombre de archivo empieza con dígitos — no es
#: un identificador válido para `import`, y Alembic la carga con su propio
#: mecanismo dinámico). Se repite acá a propósito: si diverge de la
#: migración real, lo nota quien lea el diff de esta lista contra la de
#: `alembic/versions/20260827_0117_rls_jerarquia.py::TABLAS_JERARQUIA`, no
#: un import silencioso que podría cargar la migración equivocada.
TABLAS_JERARQUIA = frozenset({
    "organizations", "portfolios", "business_units", "departments",
    "programs", "projects",
})

#: Tenant-scoped, todavía sin RLS. Cada una vuelve a mirarse cuando su oleada
#: llegue (`reestructura-modelo-datos.md` §8) — no es "no importa", es
#: "todavía no". Sacar una de acá sin agregarle una policy real rompe este
#: trinquete por la otra punta: se detecta en la próxima corrida porque deja
#: de aparecer ni en `TABLAS_JERARQUIA` ni en esta lista.
ALLOWLIST_PENDIENTE_RLS = frozenset({
    # W4/W7 — actores, áreas, catálogo de recursos.
    "actors", "areas", "area_assignments", "teams", "stakeholders",
    # US-242 (W3, dominio proyectos) — _ModuleBase y afines.
    "risks", "issues", "change_requests", "documents", "lessons",
    "meeting_minutes", "risk_actions", "tasks",
    # US-242 — resto de proyectos.
    "project_artifacts", "project_charters", "project_requests",
    "project_participations", "project_roles", "project_ai_contexts",
    "project_health_evaluations", "change_approvers", "approval_tokens",
    "plan_baselines",
    # W7 — catálogo IA, reportes, scheduling.
    "ai_jobs", "ai_report_templates", "reports", "report_history",
    "report_templates", "report_builder_templates", "scheduled_reports",
    "scheduled_minutes", "metric_snapshots",
    # W7 — resto: identidad, permisos, notificaciones, folios.
    "users", "roles", "user_scope_assignments", "user_tenant_memberships",
    "tenant_role_permission_overrides", "permission_change_requests",
    "notifications", "assistant_conversations", "folio_sequences",
    # Excepción declarada aparte, no de RLS: `audit_log` es de solo
    # anexado (AM-08) y `tenant_id` es nullable (eventos platform-wide) —
    # su FK ya es `ON DELETE SET NULL` (`20260827_0116`), pero RLS sobre un
    # log que el superadmin necesita leer cross-tenant sin excepción es una
    # decisión de diseño propia, no un olvido. Se evalúa junto con W7.
    "audit_log",
})


def _tablas_tenant_scoped() -> frozenset[str]:
    import app.models  # noqa: F401 — registra los modelos en el metadata
    from app.db.base import Base

    return frozenset(
        nombre for nombre, tabla in Base.metadata.tables.items()
        if "tenant_id" in tabla.columns
    )


def test_toda_tabla_tenant_scoped_esta_clasificada() -> None:
    reales = _tablas_tenant_scoped()
    declaradas = TABLAS_JERARQUIA | ALLOWLIST_PENDIENTE_RLS

    sin_clasificar = reales - declaradas
    assert not sin_clasificar, (
        f"Tabla(s) tenant-scoped nueva(s) sin clasificar: {sorted(sin_clasificar)}. "
        "Agrégala a TABLAS_JERARQUIA (con su migración de RLS) o a "
        "ALLOWLIST_PENDIENTE_RLS (con la oleada que la va a cubrir) en este "
        "archivo."
    )

    fantasmas = declaradas - reales
    assert not fantasmas, (
        f"Tabla(s) declarada(s) acá que ya no existen: {sorted(fantasmas)}. "
        "Poda la lista — una entrada fantasma esconde que algo se borró sin "
        "que este trinquete se enterara."
    )


def test_centinela_solo_en_los_call_sites_permitidos() -> None:
    # `tenant_context.py` define el parámetro y lo documenta en su propio
    # docstring — no es un call site, es la implementación. El único call
    # site real es `get_superadmin` en `deps.py`.
    permitidos = {RAIZ_APP / "api" / "deps.py", RAIZ_APP / "core" / "tenant_context.py"}
    patron = re.compile(r"alcance_plataforma\s*=\s*True")

    encontrados: dict[Path, int] = {}
    for archivo in RAIZ_APP.rglob("*.py"):
        if archivo in permitidos:
            continue
        texto = archivo.read_text(encoding="utf-8")
        if patron.search(texto):
            encontrados[archivo] = len(patron.findall(texto))

    assert not encontrados, (
        f"`alcance_plataforma=True` (el centinela de RLS) aparece fuera de "
        f"los call sites permitidos: {sorted(str(p) for p in encontrados)}. "
        "Si es un caso nuevo que de verdad necesita ver todos los tenants, "
        "la decisión es de ADR-003, no de un `if` suelto — y agrega el "
        "archivo a `permitidos` acá arriba con la razón."
    )

    # El call site permitido tiene que EXISTIR y usar el patrón — si alguien
    # lo reescribe para que ya no diga `alcance_plataforma=True` literal
    # (ej. lo mueve a una variable), este trinquete deja de verlo y hay que
    # enterarse por acá, no en producción.
    deps_py = (RAIZ_APP / "api" / "deps.py").read_text(encoding="utf-8")
    assert patron.search(deps_py), (
        "`api/deps.py` ya no tiene `alcance_plataforma=True` literal — "
        "¿se movió el call site del centinela? Actualiza `permitidos` acá y "
        "confirma que `get_superadmin` lo sigue fijando."
    )
