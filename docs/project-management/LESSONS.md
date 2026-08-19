---
tipo: gestion
responsable: propietario
estado: vigente
revisado: 2026-08-12
revisar_cada: 90d
---

# LESSONS — patrones aprendidos de correcciones del owner

> Máximo 40 líneas. Cada corrección del owner que revele un patrón repetible se
> registra aquí como una línea fechada. Una lección se borra cuando se
> convierte en regla de `CLAUDE.md`, en gate de CI o en skill. Se lee al abrir
> cada ronda (`CLAUDE.md` §1 y §14).

## Lecciones vivas

- **2026-08-19 — Una bajada que suelta columnas repone sus índices.** En Postgres
  `DROP COLUMN` se lleva los índices de la columna, y el `downgrade` de una
  migración anterior muere en su `DROP INDEX`. La suite local no lo ve (SQLite
  emula el borrado recreando la tabla, y la cadena completa solo corre en el job
  de Postgres). Trinquete: `tests/test_us199_indices_de_bajada.py`.
- **2026-08-19 — Un trinquete que lee código no ve tras una indirección.** Segunda
  vez en el mismo bloque (antes, `_AVISAR_FASE`): si un test busca llamadas en el
  fuente, esas llamadas se escriben literales, no en un bucle sobre una constante.
