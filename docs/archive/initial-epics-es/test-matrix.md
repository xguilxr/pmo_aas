---
responsable: propietario
estado: archivado
revisado: 2026-05-08
revisar_cada: nunca
---

# Test Matrix — trazabilidad épica → historia → test

Leyenda de estado:

- ✅ verde (pasa en CI)
- ❌ rojo (falla, issue abierto)
- ⏳ pendiente (test aún no escrito)
- 🔄 refactor (cambió el flujo, revisar)

| Epic  | Historia | Test ID   | Archivo                                              | Estado | Issue |
| ----- | -------- | --------- | ---------------------------------------------------- | :----: | ----- |
| EP001 | US001-A  | TC-001    | backend/tests/api/test_tc001_login_success.py        | ✅     |       |
| EP001 | US001-B  | TC-002    | backend/tests/api/test_tc002_login_failed_audit.py   | ⏳     |       |
| EP001 | US001-C  | TC-003    | backend/tests/api/test_tc003_login_lockout.py        | ✅     |       |
| EP001 | US001-D  | TC-004    | backend/tests/api/test_tc004_change_password.py      | ⏳     |       |
| EP002 | US002-A  | TC-010    | backend/tests/api/test_tc010_superadmin_tenants_list.py | ⏳  |       |
| EP002 | US002-B  | TC-011    | backend/tests/api/test_tc011_superadmin_tenant_detail.py | ✅ | fixed |
| EP002 | US002-C  | TC-012    | backend/tests/api/test_tc012_tenant_provision.py     | ⏳     |       |
| EP002 | US002-D  | TC-013    | backend/tests/api/test_tc013_tenant_soft_delete.py   | ⏳     |       |
| EP002 | US002-E  | TC-014    | backend/tests/api/test_tc014_tenant_logo_upload.py   | ⏳     |       |
| EP002 | US002-F  | TC-015    | backend/tests/api/test_tc015_login_events.py         | ✅     |       |
| EP003 | US003-A  | TC-020    | backend/tests/api/test_tc020_request_create.py       | ⏳     |       |
| EP003 | US003-B  | TC-021    | backend/tests/api/test_tc021_request_approve.py      | ⏳     |       |
| EP003 | US003-C  | TC-022    | backend/tests/api/test_tc022_request_reject.py       | ⏳     |       |
| EP004 | US004-A  | TC-030    | backend/tests/api/test_tc030_dashboard_metrics.py    | ⏳     |       |
| EP004 | US004-B  | TC-031    | backend/tests/api/test_tc031_dashboard_share_link.py | ⏳     |       |
| EP005 | US005-A  | TC-040    | backend/tests/api/test_tc040_project_crud.py         | ⏳     |       |
| EP005 | US005-B  | TC-041    | backend/tests/api/test_tc041_project_tenant_isolation.py | ⏳ |      |
| EP005 | US005-C  | TC-042    | backend/tests/api/test_tc042_project_closure.py      | ⏳     |       |
| EP005 | US005-D  | TC-043    | backend/tests/api/test_tc043_project_status_snapshot.py | ⏳  |      |
| EP006 | US006-A  | TC-050    | backend/tests/api/test_tc050_tasks_crud.py           | ⏳     |       |
| EP006 | US006-B  | TC-051    | backend/tests/api/test_tc051_risks_crud.py           | ⏳     |       |
| EP006 | US006-C  | TC-052    | backend/tests/api/test_tc052_issues_crud.py          | ⏳     |       |
| EP006 | US006-D  | TC-053    | backend/tests/api/test_tc053_changes_crud.py         | ⏳     |       |
| EP006 | US006-E  | TC-054    | backend/tests/api/test_tc054_documents_crud.py       | ⏳     |       |
| EP006 | US006-F  | TC-055    | backend/tests/api/test_tc055_lessons_crud.py         | ⏳     |       |
| EP006 | US006-G  | TC-056    | backend/tests/api/test_tc056_minutes_crud.py         | ⏳     |       |
| EP006 | US006-H  | TC-057    | backend/tests/api/test_tc057_areas_objectives.py     | ⏳     |       |
| EP006 | US006-I  | TC-058    | backend/tests/api/test_tc058_resources_crud.py       | ⏳     |       |
| EP006 | US006-J  | TC-059    | backend/tests/api/test_tc059_resources_tenant_isolation.py | ⏳ |  |
| EP007 | US007-A  | TC-070    | backend/tests/api/test_tc070_admin_users.py          | ⏳     |       |
| EP007 | US007-B  | TC-071    | backend/tests/api/test_tc071_admin_roles.py          | ⏳     |       |
| EP007 | US007-C  | TC-072    | backend/tests/api/test_tc072_admin_project_types.py  | ⏳     |       |
| EP007 | US007-D  | TC-073    | backend/tests/api/test_tc073_admin_variables.py      | ⏳     |       |
| EP007 | US007-E  | TC-074    | backend/tests/api/test_tc074_audit_log_view.py       | ⏳     |       |
| EP008 | US008-A  | TC-080    | backend/tests/api/test_tc080_ai_minutes_generate.py  | ⏳     |       |
| EP008 | US008-B  | TC-081    | backend/tests/api/test_tc081_ai_report_generate.py   | ⏳     |       |
| EP009 | US009-A  | TC-090    | backend/tests/api/test_tc090_mpp_export.py           | ⏳     |       |
| EP009 | US009-B  | TC-091    | backend/tests/api/test_tc091_mpp_import.py           | ⏳     |       |

## Multi-tenant isolation (transversal)

Estos tests son **no-negociables** y corren como smoke antes de cada release:

| Test ID    | Descripción                                               | Estado |
| ---------- | --------------------------------------------------------- | :----: |
| TC-MT-001  | Tenant A no lee proyectos de Tenant B                      | ✅     |
| TC-MT-002  | Tenant A no lee risks/issues/changes de Tenant B           | ⏳     |
| TC-MT-003  | Tenant A no edita/borra recursos de Tenant B               | ✅ (H11) |
| TC-MT-004  | Tenant A no accede a /dashboard/share-links de Tenant B    | ⏳     |
| TC-MT-005  | Tenant admin no resetea password de user en otro tenant    | ⏳     |
| TC-MT-006  | Audit log filtra estrictamente por organization_id          | ⏳     |

## Regresiones recientes

- **2026-04-17**: TC-011 reproduce el 500 de `/superadmin/tenants/{id}/detail`
  (Pydantic v2 validation error: `programs.0 Input should be a valid dictionary`).
  Root cause: `TenantDetailResponse.model_validate(org)` jalaba las relaciones
  `programs`/`projects` de SQLAlchemy y las intentaba validar como `list[dict]`.
  Fix: construir la response explícitamente sin `model_validate`.
- **2026-04-17**: Superadmin veía `"Super admin debe especificar X-Tenant-ID"`
  al entrar a `/superadmin/tenants/{id}`. Root cause: `TopBar` polleaba
  `/notifications/unread-count` cada 30s, endpoint tenant-scoped. Fix:
  skip fetch cuando no hay `pmo_tenant_id` en localStorage.
- **2026-04-17**: Login no se auditaba. `auth/login` ahora escribe filas en
  `audit_log` (plataforma + una por org del usuario) y nuevo endpoint
  `/superadmin/login-events` expone la vista platform-wide.
