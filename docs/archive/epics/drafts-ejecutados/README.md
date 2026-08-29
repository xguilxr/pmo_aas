---
tipo: archivo
responsable: propietario
estado: archivado
revisado: 2026-08-29
revisar_cada: nunca
---

# Archivo — planes de `docs/epics/drafts/` ya ejecutados

Ocho planes de `docs/epics/drafts/` cuyo contenido está **100 % construido**,
verificado contra el código y `git log` en la auditoría de indexación del
2026-08-29. Un plan cuyo propósito ya se cumplió no ordena trabajo: solo
ocupa espacio de búsqueda. Se conservan aquí por trazabilidad, no para
consultarse como referencia — para eso está el epic o la sección de
arquitectura que absorbió su contenido.

| Archivo | Qué proponía | Dónde vive hoy | Verificado con |
|---|---|---|---|
| `reestructura-fase2-plan.md` | Oleada 2 de la reestructura de jerarquía (US-203 a US-222) | `docs/epics/EP002-org-hierarchy.md`, migraciones `0112`-`0115` | El propio doc marca ✅ en todas las US; commit «cierre de Fase 2 — US-203 a US-222» |
| `reestructura-inventario.md` | Foto «antes de construir» de Fase 0 (migración cabeza `0107`) | Superado por el código: migraciones `0108`-`0115` | Todo lo marcado brecha P0 ya está construido |
| `reestructura-navegacion.md` | Mapa objetivo del sidebar, header y vistas nuevas | `apps/web/components/{app-shell,switcher-de-organizacion,vista-maestra}.tsx`, rutas `/pmo/board`, `/pmo/resources` | Commits US-203 a US-209 y US-219; componentes presentes con esos nombres |
| `auto-wbs-position.md` | MVP de posición automática en el WBS al importar/reordenar | US-176, en producción | El propio doc declara el MVP implementado; v2 queda diferida como trabajo nuevo si se retoma |
| `feedback-16jul-mejoras.md` | 8 items de una retro (BUG-091, ENH-195-198, US-190-192) | Cada uno con su commit en `main` | `git log` tiene un commit por ID, todos con el mismo identificador |
| `minute-gold-standard.md` | Caso de referencia "Highlander EAM-BNF" para calibrar la extracción de minutas por IA | `apps/api/tests/fixtures/minutes/` (fixture de test) + ENH-102/103/105/106/107 | Fixture presente; `services/minutes/participant_matcher.py` implementa la lógica descrita |
| `plan-import-revamp.md` | 9 items de mejora al importador de MS Project (BUG-088-090, ENH-191-194, US-188-189) | Cada uno con su commit en `main` | `git log` tiene un commit por ID |
| `EP020-secciones-atomicas.md` | Catálogo de secciones atómicas del Report Builder, antes de promoverse a epic oficial | `docs/epics/EP020-report-builder.md` | El propio doc declara la promoción; `services/reports/engine.py` es el motor descrito |

## Lo que no se archivó

Cuatro planes de la misma carpeta (`reestructura-plan.md`,
`reestructura-conceptos.md`, `reestructura-modelo-datos.md`,
`portfolio-recursos-capacidad.md`) siguen en `docs/epics/drafts/` porque
tienen un resto real sin construir (RLS de Postgres, catálogo de IA con
roles propios, enforcement del plan de suscripción, clasificación de
recursos). Se recortaron el 2026-08-29 para dejar solo esa parte — la que
ya se ejecutó se retiró de ahí también, con nota de dónde quedó.

## Política

Igual que el resto de `docs/archive/`: no se edita. Para saber qué se
entregó de cada uno, la fuente de verdad es la columna «Dónde vive hoy», no
el archivo mismo.
