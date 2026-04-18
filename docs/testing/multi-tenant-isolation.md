# Multi-Tenant Isolation — Tests bloqueantes

**ID:** `DOC-TEST-MT`

Estos tests verifican que **un tenant nunca puede ver, editar, borrar o derivar conocimiento de otro tenant**. Son el corazón de la seguridad del SaaS. **Si alguno falla, el merge se bloquea.**

---

## Setup de fixtures

```python
# tests/fixtures/multi_tenant.py
import pytest

@pytest.fixture
async def mt_setup(db):
    """
    Crea:
      - Tenant A (slug='tenant-a') con admin_a, pm_a, project_a, risk_a, ...
      - Tenant B (slug='tenant-b') con admin_b, pm_b, project_b, risk_b, ...
      - Superadmin global
    Devuelve un objeto con todas las referencias.
    """
    ...
```

Cada TC recibe `mt_setup` y opera con tokens de A intentando tocar recursos de B.

---

## TC-MT-001 — Reads de proyectos

**Dado** un token válido del tenant A
**Cuando** intento `GET /api/v1/projects/{project_b_id}` o `/projects?organization_id={org_b_id}`
**Entonces** recibo **404 NOT_FOUND** (nunca 403, para no filtrar existencia).

```python
async def test_tenant_a_cannot_read_project_b(client, mt_setup):
    r = await client.get(f"/api/v1/projects/{mt_setup.project_b.id}",
                         headers={"Authorization": f"Bearer {mt_setup.pm_a_token}"})
    assert r.status_code == 404
    assert r.json()["code"] == "NOT_FOUND"
```

**Variantes** (todas deben fallar igual):
- `GET /projects/{id}` → 404
- `GET /projects?organization_id=B` → `items: []`
- `GET /dashboard/kpis?organization_id=B` → se ignora filtro o 404
- `GET /dashboard/plan-vs-actual?organization_id=B` → 404

---

## TC-MT-002 — Reads cross-módulo

**Para cada módulo** (`risks`, `issues`, `change-requests`, `documents`, `lessons`, `meeting-minutes`):

```python
@pytest.mark.parametrize("module", ["risks","issues","change-requests","documents","lessons","meeting-minutes"])
async def test_cross_tenant_read_module(client, mt_setup, module):
    record_b = getattr(mt_setup, f"{module}_b")
    r = await client.get(f"/api/v1/{module}/{record_b.id}",
                         headers={"Authorization": f"Bearer {mt_setup.pm_a_token}"})
    assert r.status_code == 404
```

También:
- Listado dentro de proyecto B (`/projects/{project_b_id}/{module}`) → 404 por el proyecto mismo.

---

## TC-MT-003 — Escrituras cross-tenant

Para cada recurso:

```python
async def test_cross_tenant_update(client, mt_setup):
    r = await client.patch(
        f"/api/v1/projects/{mt_setup.project_b.id}",
        json={"name":"hacked"},
        headers={"Authorization": f"Bearer {mt_setup.pm_a_token}"}
    )
    assert r.status_code == 404

async def test_cross_tenant_delete(client, mt_setup):
    r = await client.delete(
        f"/api/v1/risks/{mt_setup.risk_b.id}",
        headers={"Authorization": f"Bearer {mt_setup.pm_a_token}"}
    )
    assert r.status_code == 404
```

**Cubre:** PATCH, DELETE, POST a sub-recursos (`/projects/{id}/documents`), acciones (`/change-requests/{id}/approve`).

---

## TC-MT-004 — Reportes y share-links

Si existe un endpoint público de share (`/share/{token}`) con token generado por tenant A:

```python
async def test_share_link_scoped_to_tenant(client, mt_setup):
    # Creamos un share link en A
    r = await client.post(f"/api/v1/projects/{mt_setup.project_a.id}/share",
                          headers={"Authorization": f"Bearer {mt_setup.admin_a_token}"})
    token = r.json()["token"]

    # El token solo sirve para datos de A; intentar suplantar ID de B no funciona
    r2 = await client.get(f"/api/v1/share/{token}?project_id={mt_setup.project_b.id}")
    assert r2.status_code == 404
```

Reportes enviados: verifica que `reports.project_id` esté en tenant del sender.

---

## TC-MT-005 — Admin A no gestiona users de B

```python
async def test_admin_a_cannot_reset_b_user_password(client, mt_setup):
    r = await client.post(
        f"/api/v1/admin/users/{mt_setup.pm_b.id}/reset-password",
        headers={"Authorization": f"Bearer {mt_setup.admin_a_token}"}
    )
    assert r.status_code in (403, 404)
```

**Variantes:**
- Admin A edita user B → falla.
- Admin A bulk-activa user B → ese user se ignora silenciosamente (no afecta) + audit warning.

---

## TC-MT-006 — Audit log aislado

```python
async def test_admin_a_cannot_read_b_audit(client, mt_setup):
    # Provocamos un evento en B
    await client.post(
        "/api/v1/auth/login",
        json={"identifier": mt_setup.pm_b.email, "password": "wrong"}
    )
    # A intenta leer logs
    r = await client.get("/api/v1/admin/audit-logs",
                         headers={"Authorization": f"Bearer {mt_setup.admin_a_token}"})
    logs = r.json()["items"]
    # Ningún log tiene user_id de B ni tenant_id de B
    assert all(l["tenant_id"] == str(mt_setup.tenant_a.id) for l in logs)
    assert not any(l.get("user_id") == str(mt_setup.pm_b.id) for l in logs)
```

---

## TC-MT-007 — Uploads aislados

```python
async def test_upload_isolated_by_slug(client, mt_setup, tmp_path):
    # A sube documento
    upload = {"file": ("plan.pdf", b"%PDF-...", "application/pdf")}
    r = await client.post(
        f"/api/v1/projects/{mt_setup.project_a.id}/documents",
        files=upload,
        data={"category":"plan"},
        headers={"Authorization": f"Bearer {mt_setup.pm_a_token}"}
    )
    download_url = r.json()["download_url"]

    # B intenta descargar por URL directa (sin token) → 403/404
    r2 = await client.get(download_url)  # URL firmada es válida
    # pero si B intenta con su propio token y el id del doc de A
    doc_id = r.json()["id"]
    r3 = await client.get(f"/api/v1/documents/{doc_id}/download",
                          headers={"Authorization": f"Bearer {mt_setup.pm_b_token}"})
    assert r3.status_code == 404

    # Filesystem: el archivo vive en tenant-a/, no en tenant-b/
    expected = storage.path / "tenants" / "tenant-a" / "documents" / f"{doc_id}.pdf"
    assert expected.exists()
    forbidden = storage.path / "tenants" / "tenant-b" / "documents" / f"{doc_id}.pdf"
    assert not forbidden.exists()
```

---

## TC-MT-008 — Jobs de IA aislados

```python
async def test_ai_job_worker_respects_tenant_context(mt_setup, worker_client):
    # Encolar job fake con `tenant_id=A` pero path a archivo de B (simulación de tampering)
    fake_job = {
        "tenant_id": str(mt_setup.tenant_a.id),
        "project_id": str(mt_setup.project_a.id),
        "input_path": f"/data/uploads/tenants/tenant-b/requests/{mt_setup.request_b.id}/file.txt"
    }
    # Worker debe rechazar paths que no empiecen con /tenants/{slug_a}/
    with pytest.raises(PermissionError):
        await worker.process_ai_job(fake_job)
```

El worker **valida siempre** que el `input_path` esté bajo el directorio del tenant del job antes de abrir archivos.

---

## Invariantes automáticos (property-based)

Complementar con pruebas Hypothesis:

```python
from hypothesis import given, strategies as st

@given(tenant_id_attacker=st.uuids(), tenant_id_victim=st.uuids(), endpoint=st.sampled_from(ENDPOINTS))
def test_no_cross_tenant_reads_property(client, tenant_id_attacker, tenant_id_victim, endpoint):
    # si endpoint usa tenant header, nunca debe retornar data de otro tenant
    ...
```

---

## Monitoring en producción

Aun con tests, corremos un **canario** cada hora en producción:

- Un tenant "canary" con data específica.
- Un bot simula ser otro tenant y hace 5 queries cross-tenant.
- Si alguna devuelve 200 con data, **alerta crítica** a Slack + PagerDuty.

Script: `scripts/canary/mt_isolation.py`.

---

## Checklist por PR (aparte de CI)

- [ ] ¿Agregué un endpoint? → agregué test `TC-MT-XXX` correspondiente.
- [ ] ¿Agregué una tabla? → habilité RLS + policy + test.
- [ ] ¿Worker lee archivos? → valida prefix del path.
- [ ] ¿Cache por key compartida? → la key incluye `tenant_id`.
- [ ] ¿Log/trace incluye `tenant_id`? → sí (para detección forense).
