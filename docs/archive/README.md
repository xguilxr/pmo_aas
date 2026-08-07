---
tipo: archivo
responsable: propietario
estado: archivado
revisado: 2026-05-08
revisar_cada: nunca
---

# docs/archive — documentación histórica

Contenido que ya **no es la fuente de verdad** pero se conserva en git
para trazabilidad. Cuando revises el estado actual del producto usa
`docs/epics/` + `docs/architecture/` + `docs/ai/` + `docs/infra/`, **no**
los archivos de aquí.

| Carpeta / archivo | Origen | Por qué se archivó |
|---|---|---|
| `initial-epics-es/` | Carpeta `pmo_aas_init/` (raíz del repo) | Versión temprana de los epics en español (`EP001-login-usuarios.md`, etc.). Superseded por `docs/epics/EP00X-*.md` que es la fuente activa. |
| `cancelled-epics/EP012-db-migration.md` | `docs/epics/EP012-db-migration.md` | EP012 cancelado por **DEC-013** (2026-04-21). Productivo v1.0 se queda en Railway Postgres; no se planea migrar a MySQL HostGator. |
| `PENDING-ADDITIONS.md` | `docs/epics/PENDING-ADDITIONS.md` | Documento de análisis pre-implementación de adiciones al MVP. La mayoría quedaron reflejadas como US en el SPRINT o descartadas; el archivo completo como referencia ya no se consulta. |

## Política

- **No editar** archivos dentro de `docs/archive/`. Si detectas algo
  obsoleto o incorrecto, anótalo en el epic/decisión activo, no aquí.
- Para traer algo de vuelta: `git mv docs/archive/<path>
  docs/<destino>` + commit explicando por qué reingresa.
- Este README se actualiza **cada vez** que se archiva o desarchiva
  algo.
