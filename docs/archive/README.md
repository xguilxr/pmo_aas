---
tipo: archivo
responsable: propietario
estado: archivado
revisado: 2026-08-12
revisar_cada: nunca
---

# docs/archive — documentación histórica

Contenido que ya **no es la fuente de verdad** pero se conserva en git
para trazabilidad. Para el estado actual del producto usa `docs/epics/` +
`docs/architecture/` + `docs/runbooks/`, **no** los archivos de aquí.

| Carpeta / archivo | Origen | Por qué se archivó |
|---|---|---|
| `initial-epics-es/` | Carpeta `pmo_aas_init/` (raíz del repo) | Versión temprana de los epics en español. Superseded por `docs/epics/EP00X-*.md`. |
| `cancelled-epics/EP012-db-migration.md` | `docs/epics/` | EP012 cancelado por **DEC-013** (2026-04-21): productivo se queda en Railway Postgres. |
| `cancelled-epics/EP016-local-ai-tunnel.md` | `docs/epics/` | EP016 archivada: superseded por DEC-017; código eliminado en BUG-053 (2026-05-08). |
| `docs-ai-legacy/` | `docs/ai/` | Era Ollama/Gemini/Tailscale, retirada por DEC-017/DEC-019 y BUG-053. |
| `runbooks-ai-legacy/` | `docs/runbooks/ai/` y `networking/` | Runbooks de la misma era de IA local; mismo motivo. |
| `project-management/` | `docs/project-management/` | Handoffs puntuales y análisis cerrados (detalle en su README). Archivado 2026-08-12. |
| `epics/` | `docs/epics/` | Epics entregadas completas: EP011, EP013, EP014, EP015 (detalle en su README). Archivado 2026-08-12. |
| `PENDING-ADDITIONS.md` | `docs/epics/` | Análisis pre-implementación de adiciones al MVP; lo útil quedó como US. |
| `glossary.md` · `setup-dev.md` · `seed-demo.md` | `docs/` raíz | Guías tempranas; lo vigente vive en `docs/dominio/` y los runbooks. |
| `agents-skills-proposals.md` · `agents-skills-generic-proposals.md` | `docs/` raíz | Propuestas de skills ya ejecutadas o descartadas; las skills viven en `.claude/skills/`. |
| `Reporte de Seguimiento.html` | mock de diseño | Plantilla que consume `html_report_renderer.py` — **no borrar**. |
| `raid-detail-denso-mock-2026-05-06.html` | mock de diseño | Referencia visual del RAID denso (ver `docs/design-system/raid-detail-denso.md`). |

## Política

- **No editar** archivos dentro de `docs/archive/`. Si detectas algo
  obsoleto o incorrecto, anótalo en el epic/decisión activo, no aquí.
- Para traer algo de vuelta: `git mv docs/archive/<path>
  docs/<destino>` + commit explicando por qué reingresa.
- Este README se actualiza **cada vez** que se archiva o desarchiva
  algo.
