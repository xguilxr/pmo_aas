---
responsable: propietario
estado: archivado
revisado: 2026-05-08
revisar_cada: nunca
---

# Testing — cobertura 100% de la app

Esta carpeta es la **fuente de verdad** de qué funcionalidad cubre la app y
cómo se valida. Sigue la cadena:

```
Epic  →  User Story  →  Test (pytest + Playwright)  →  Issue (si falla)
```

## Estructura

```
docs/testing/
├── README.md              (este archivo)
├── test-matrix.md         (traceability épica → historia → test id)
├── user-stories/
│   ├── US001-auth.md
│   ├── US002-superadmin.md
│   ├── US003-projects.md
│   ├── US004-requests.md
│   ├── US005-risks-issues-changes.md
│   ├── US006-docs-lessons-minutes.md
│   ├── US007-reports-dashboard.md
│   ├── US008-admin-panel.md
│   └── US009-ai-and-mpp.md
└── ../../backend/tests/   (pytest suite, IDs TC-XXX)
```

## Convenciones

- **Épicas** `EP001..EP00N` ya existen en `docs/epics/`. Son el **qué**.
- **User stories** `USNNN` viven en `user-stories/`. Son el **cómo lo vive el usuario**.
- **Tests** `TC-NNN` (Test Case) viven en `backend/tests/` (API) y
  `frontend/tests/e2e/` (Playwright, cuando exista). El ID está en el
  docstring y en el nombre del archivo (ej. `test_tc001_login_success.py`).
- La `test-matrix.md` es la tabla que une los tres IDs y marca estado
  (✅ pasa, ❌ falla con issue `#NN`, ⏳ pendiente de implementar).

## Flujo de trabajo del agente

1. Tomar una user story pendiente del matrix.
2. Escribir el test (`backend/tests/test_tcNNN_*.py`).
3. Correr `pytest backend/tests/test_tcNNN_*.py -v`.
4. Si falla:
   - Diagnosticar root cause.
   - Abrir issue en GitHub con label severidad (C/H/L) y referenciar el test.
   - Arreglar.
   - Correr de nuevo hasta verde.
5. Marcar ✅ en el matrix y cerrar el issue.

## Alcance por pantalla

Cada página de la SPA tiene una user story dedicada con estas secciones
obligatorias:

- **Rutas** — URL y quién puede acceder (roles).
- **Carga inicial** — qué GETs dispara, qué espera.
- **Interacciones** — cada botón, link, filtro, modal.
- **CRUD** — crear, leer, editar, borrar (soft-delete donde aplica).
- **Edge cases** — campos vacíos, permisos, aislamiento multi-tenant.
- **Regresiones conocidas** — bugs históricos + test que los cubre.

## Multi-tenant isolation

Toda user story que crea/lee/modifica datos de negocio **debe** incluir al
menos un test de aislamiento: tenant A nunca ve datos de tenant B. Esto es
la regresión principal de los C1–C4 del roadmap.

## Super Admin como herramienta de onboarding

El panel `/superadmin` se documenta como **quick-onboarding de tenants**:

- crear tenant + admin inicial
- subir logo, configurar colores/branding
- poblar con usuarios/programas/proyectos iniciales
- validar que el tenant es usable "straight away"

Cualquier fricción en ese flujo = issue severidad **C** (bloquea onboarding).
