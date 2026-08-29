---
tipo: guia
responsable: propietario
estado: vigente
revisado: 2026-08-29
revisar_cada: 180d
---

# Multi-Tenant Isolation — cómo se prueba de verdad

**ID:** `DOC-TEST-MT`

> **Reescrito el 2026-08-29.** La versión anterior era pseudocódigo de una
> suite que no existe: fixture `tests/fixtures/multi_tenant.py` (no está),
> pruebas Hypothesis (no hay ninguna en el repo), un canario horario en
> producción con alertas a Slack/PagerDuty (`scripts/canary/` no existe). El
> aislamiento multi-tenant sí se prueba — solo que no así. Esto describe el
> patrón real.

Un tenant nunca puede ver, editar, borrar o derivar conocimiento de otro
tenant. Es el requisito de seguridad más alto del SaaS.

## El patrón real

No hay una fixture `mt_setup` compartida. Cada suite construye sus propios
tenants con los helpers de `apps/api/tests/factories.py`
(`create_tenant`, `create_admin_role`, …) y arma el escenario cross-tenant
dentro del propio test. El archivo de referencia es
`apps/api/tests/test_seg08_aislamiento_tenants.py`; el patrón de membresía
multi-tenant (un usuario en más de un tenant, US-214) está en
`apps/api/tests/test_us214_multi_tenant.py`. Alrededor de otros 13 archivos
tocan aislamiento cross-tenant como parte de la suite de su propia US —no
hay una carpeta ni un marcador que los agrupe; se encuentran por
`grep -rl tenant_b apps/api/tests/`.

## Qué se cubre

Las mismas categorías que la versión anterior enumeraba como `TC-MT-001` a
`008` siguen siendo las correctas para pensar el problema — lecturas cruzadas,
escrituras cruzadas, reportes y enlaces públicos, administración de usuarios,
auditoría, archivos subidos, trabajos de IA. La diferencia es dónde vive cada
una:

| Categoría | Dónde se prueba hoy |
|---|---|
| Lecturas y escrituras cruzadas (proyectos y módulos) | `test_seg08_aislamiento_tenants.py` |
| Membresía multi-tenant (un usuario, dos tenants) | `test_us214_multi_tenant.py` |
| Matriz de permisos por rol | `test_permission_matrix.py` (`@pytest.mark.permissions`) |
| Guard de acciones irreversibles | `test_mca_aut01_guard.py` |
| El resto (auditoría, uploads, jobs de IA por dominio) | dentro de la suite de la US que los introdujo — no hay un archivo único |

**Sin RLS de Postgres hoy** — el aislamiento es filtrado en la capa ORM
(`tenant_id == cu.effective_tenant_id` en cada endpoint), no una política de
base de datos. Está en construcción: issues #599-#601 (US-240/241/242,
`docs/architecture/security-multitenant.md`). Hasta que exista, un endpoint
que olvide el filtro es el único punto de fallo — por eso la disciplina de
abajo importa.

## Checklist por PR

- [ ] ¿Agregué un endpoint? → agregué un test que confirme 404 (no 403, para
  no filtrar existencia) al pedir un recurso de otro tenant.
- [ ] ¿Agregué una tabla? → tiene `tenant_id` indexado y cada query la filtra.
- [ ] ¿Worker lee archivos? → valida el prefijo de tenant del path antes de
  abrir.
- [ ] ¿Log o trace nuevo? → incluye `tenant_id` (para investigación forense).
