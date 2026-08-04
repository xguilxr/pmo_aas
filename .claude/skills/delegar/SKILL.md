---
name: delegar
description: Decide si una tarea va a un sub-agente y con qué modelo, para no quemar el contexto de la sesión principal en trabajo mecánico. Úsala antes de crear muchos issues, aplicar labels en lote, explorar el codebase, actualizar epic docs tras un commit, o repartir piezas de un batch grande. NO la uses para decisiones que necesiten el contexto de la sesión, commits de código, o el resumen final al owner.
---

# Delegar a sub-agentes

**Principio:** la sesión principal cuesta más contexto que un sub-agente. Delega
lo que no requiera tu juicio en el hilo.

---

## Cuándo delegar

| Caso | Modelo | Razón |
|---|---|---|
| Crear ≥ 5 issues en GitHub | sonnet | Specs ya escritas, ejecución mecánica |
| Aplicar labels en ≥ 10 issues | sonnet o haiku | Bulk, schema simple |
| Audit / mapeo de codebase | sonnet (`Explore`) | Exploración masiva sin escritura |
| Búsqueda multi-archivo > 3 queries | sonnet (`Explore`) | Búsquedas en paralelo |
| **Actualizar epic doc tras commit** | **haiku** | Redacción técnica corta, barato y rápido |
| Refinamiento de wording / typos | haiku | Redacción, no razonamiento |
| Revisión de seguridad / arquitectura | opus | Razonamiento profundo |
| Planning multi-step de epic nueva | opus o sonnet | Decisiones arquitectónicas |

## Cuándo NO delegar

- Decisiones que requieren contexto profundo de la sesión actual.
- **Commits que tocan código** — la sesión principal es la dueña.
- Resúmenes finales al owner.
- El cierre de sesión (`handoff`): lo corre quien está cerrando.

---

## Patrón — actualizar epic doc con Haiku

Cuando un commit cambia comportamiento descrito en una epic, en vez de editarla
en la sesión principal (gasta contexto):

```
Agent({
  description: "Update epic doc post-commit",
  subagent_type: "general-purpose",
  model: "haiku",
  prompt: `
    Acabamos de pushear commit <SHA> que implementa <ID> en la branch <branch>.
    El cambio modifica el comportamiento descrito en docs/epics/EP0XX-*.md.

    Tarea: edita el epic doc para reflejar el nuevo comportamiento.
    Mantén el resto del doc intacto. Specs del cambio:
    <pega AC del issue + diff resumido>

    Reglas:
    - Mantén el tono y estructura existentes.
    - No agregues secciones nuevas salvo que sea estrictamente necesario.
    - Marca cambios con la fecha (YYYY-MM-DD) al final.
    - Si la US tiene sub-bloque dedicado en el epic, actualízalo con commit SHA
      y status DONE.
    - Commit + push al final con header docs(epic): EP0XX update for <ID>.
  `
})
```

---

## Modelo de orquestación Revamp 1.0 (decisión owner 2026-07-08/09)

**El orquestador diseña y commitea; los modelos menores ejecutan.**

- La **sesión principal** diseña la arquitectura, escribe el backend core
  (migraciones, servicios de cálculo, endpoints críticos), valida y **commitea**
  (1 ID = 1 commit, staging por paths).
- Los **sub-agentes** ejecutan piezas auto-contenidas con spec precisa (páginas
  FE, revamps de tablas, forms, exploraciones, exports) y **NO commitean**:
  dejan el working tree y la sesión principal revisa y commitea.
- **Excepción:** la actualización de epics al cierre de bloque se delega con
  commit `docs(epics)` incluido.
- **Regla anti-conflicto:** nunca dos agentes simultáneos sobre el mismo
  archivo. Batches sobre archivos compartidos van secuenciales.
