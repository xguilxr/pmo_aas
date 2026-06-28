"""BUG-080 — el export CSV de auditoría incluye la columna `details` (el
contexto del evento: job_id, errores, conteos), necesaria para ver el detalle
de un job desde el CSV exportado.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.models.audit import AuditLog
from tests.factories import create_admin_role, create_tenant, create_user, login


@pytest.mark.asyncio
async def test_bug080_audit_csv_includes_details(client, db_session):
    t = await create_tenant(db_session)
    admin_role = await create_admin_role(db_session, t)
    await create_user(
        db_session, tenant=t, username="admin",
        email="admin@acme.example.com", password="Str0ng-Admin-1!",
        roles=[admin_role],
    )
    auth = await login(client, "admin", "Str0ng-Admin-1!")

    db_session.add(AuditLog(
        tenant_id=str(t.id), action="ai.minute.generate", module="minutes",
        entity_type="ai_job", entity_id="job-123",
        details={"job_id": "job-123", "error": "boom", "count": 3},
        occurred_at=datetime.now(UTC),
    ))
    await db_session.commit()

    r = await client.get(
        "/api/v1/admin/audit-logs/export.csv", headers=auth["_authz"]
    )
    assert r.status_code == 200, r.text
    text = r.text
    header = text.splitlines()[0]
    assert "details" in header
    # El JSON de details aparece serializado en la fila.
    assert "job-123" in text
    assert "boom" in text
