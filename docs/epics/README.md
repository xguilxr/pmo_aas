# Épicas

**ID:** `DOC-EPICS`

Cada épica es un archivo autosuficiente con:

1. **Meta** (prioridad, dependencias, estado, módulo).
2. **Objetivo de negocio** y roles involucrados.
3. **User Stories** detalladas (formato "Como … quiero … para …") con **criterios de aceptación**.
4. **Test Cases** numerados (TC-XXX) ligados a cada US (unit / integration / E2E).
5. **Notas técnicas** (modelos de BD, endpoints, dependencias de librerías).
6. **Definition of Done** por épica.

| # | Épica | Estado | Dependencias |
|---|---|---|---|
| [EP001](./EP001-auth-users.md) | Login y gestión de usuarios | MVP | — |
| [EP002](./EP002-org-hierarchy.md) | Jerarquía de clientes/proyectos | MVP | EP001 |
| [EP003](./EP003-project-requests.md) | Solicitud y aprobación de proyectos | MVP | EP001, EP002 |
| [EP004](./EP004-dashboard.md) | Dashboard del Project Manager | MVP | EP001, EP002, EP005 |
| [EP005](./EP005-projects.md) | Gestión de proyectos | MVP | EP001, EP002, EP003 |
| [EP006](./EP006-project-modules.md) | 6 módulos del proyecto (risks/issues/changes/docs/lessons/minutes) | MVP | EP005 |
| [EP007](./EP007-admin.md) | Panel de administración | MVP | EP001, EP002 |
| [EP008](./EP008-ai.md) | IA: minutas y reportes | MVP | EP005, EP006 |
| [EP009](./EP009-ms-project.md) | Integración con Microsoft Project | MVP | EP005 |

---

## Convenciones de identificación

- **EP-XXX** — épica (3 dígitos).
- **US-XXX** — user story global, única en todo el producto.
- **TC-XXX** — test case, único global.
- **TC-MT-XXX** — test case de multi-tenant isolation (transversal).

La matriz de trazabilidad Épica ↔ US ↔ TC está en [`../testing/test-matrix.md`](../testing/test-matrix.md).
