---
tipo: epica
responsable: propietario
estado: vigente
revisado: 2026-08-12
revisar_cada: 90d
---

# EP018 — Documentos / Artefactos por proyecto

| Campo | Valor |
|---|---|
| **ID** | EP018 |
| **Prioridad** | Alta — Sprint 18 |
| **Dependencias** | EP005 (projects), EP006 (project modules), EP009 (MS Project import), EP017 (Áreas/Actores) |
| **Módulo** | `projects.artifacts`, `plan.master`, `charter`, `raid.export`, `org.chart` |
| **Estado** | # PENDING |
| **Versión objetivo** | v1.17 |

## Objetivo de negocio

Cierra el catálogo de documentos vivos por proyecto. Hoy los usuarios pueden subir cualquier cosa; queremos un set **estricto y curado** de artefactos con semántica clara y sincronización automática:

1. **Project Charter** — auto-creado al crear proyecto, backfilleado para los existentes.
2. **Plan** — un único archivo vivo (.mpp / .xlsx / .csv / plantilla); DB es fuente de verdad, archivo se regenera preservando formato origen.
3. **RAIDs** — export Excel siempre actualizado, 4 hojas dedicadas en español (Riesgos / Acciones / Incidencias / Decisiones) con columnas legibles (Folio · Título · Descripción · Severidad/Prioridad · Estado · Responsable área · Responsable · Fecha creación). *(ENH-152, 2026-06-05: taxonomía RAID canónica + nombres resueltos a texto + filename `RAID-[Nombre Proyecto].xlsx`; mismo archivo para el botón de /raid y el de Documentos. Reemplaza Risks/Issues/Lessons/Changes.)*
4. **Organigrama** — lista de recursos asignados al proyecto (depende del catálogo Áreas/Actores de EP017).

## Decisiones arquitectónicas asociadas (a registrar en DECISIONS.md)

- **DEC-Plan-source-of-truth** — DB es la fuente de verdad para el Plan. El archivo descargable se reconstruye on-demand en el formato original detectado al subir (.mpp / .xlsx / .csv). Si nunca se subió uno, se descarga la plantilla XLSX.
- **DEC-Artifacts-whitelist** — Solo los 4 tipos de artefactos definidos pueden vivir en un proyecto. Subidas fuera del whitelist se rechazan en el endpoint.
- **DEC-Charter-backfill** — Proyectos sin solicitud previa reciben un Charter stub con campos vacíos para que el PM complete; proyectos creados desde solicitud heredan los datos de la solicitud.

## US iniciales (Sprint 18)

- **US-106** — Sistema de Artefactos por proyecto (whitelist + storage + UI tabs Charter/Plan/RAID/Organigrama).
- **US-150** (2026-05-26) — Organigrama cableado: `GET /projects/{id}/organigrama/export` genera un Excel con 4 hojas (Áreas, Equipos, Roles, Recursos) vía `app/services/organigrama_export.py` (openpyxl, mismo estilo que RAID export). El scope de áreas/recursos sigue la cascada de `area_assignments` (global/org/programa/proyecto); Roles es el catálogo tenant. El tab Organigrama deja de ser placeholder (`available=true`).
- **ENH-080** — Plan vivo: sync DB ↔ archivo maestro preservando formato origen.
- **ENH-081** — Charter: auto-creación al crear proyecto + backfill de existentes.

## US diferidas (post-redefinición Áreas/Recursos)

- **US-105** — Import Plan/Excel: matching wizard a Actor existente o auto-crear (post-import, no bloquea carga). Postergada 2026-05-08: depende del shape final del catálogo Actores que salga de la redefinición pendiente.
- ~~**US-106 — Tab Organigrama (parte funcional)**~~ — entregado en US-150 (2026-05-26): export Excel de Áreas/Equipos/Roles/Recursos.

## Migraciones Alembic previstas

- `project_artifacts` (project_id, type, source_format, content/storage_url, created_by, updated_at) — 1 fila por (project_id, type) único.
- `charters` — backfill stub para proyectos sin solicitud previa.

## Out of scope EP018

- Versionado completo de artefactos (solo última versión vive; histórico vía R2).
- Comparación visual entre versiones del Plan.
- Aprobaciones de Charter (vive en EP019 si aplica).
