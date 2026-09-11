---
tipo: gestion
responsable: propietario
estado: vigente
revisado: 2026-09-11
revisar_cada: 30d
---

# Runbooks del revamp v2 — una fase por archivo

**Qué es.** La versión ejecutable de [`../REVAMP-V2-PLAN.md`](../REVAMP-V2-PLAN.md)
§6: cada fase con archivos, líneas, pasos numerados, criterios de
aceptación (TC) y commits. Escritos para que un modelo pequeño los siga
sin interpretar. Los hechos (archivo:línea) se verificaron el 2026-09-11;
si el código cambió, el runbook dice dónde mirar con `grep`.

**Qué hacer.** Abrir **solo** el archivo de la fase que toca. No leer los
demás. Seguir los pasos en orden. Si un paso no coincide con el código
(línea movida, función renombrada), buscar con el `grep` indicado y seguir;
si no aparece, parar y preguntar al owner.

| Fase | Archivo | Puntos | Tamaño | Gate |
|---|---|---|---|---|
| 0 | [FASE-0.md](FASE-0.md) — bugs visibles | 13, 2.4 | S | ninguno |
| 1 | [FASE-1.md](FASE-1.md) — navegación y header | 2.1, 2.2, 2.4 | M | fase 0 |
| 2 | [FASE-2.md](FASE-2.md) — filtro por organización | 2.3 | M | D2 |
| 3 | [FASE-3.md](FASE-3.md) — dashboard | 1, 3 | L | W1 |
| 4 | [FASE-4.md](FASE-4.md) — PMO y config | 2.2, 4 | XL | W2, W3, D3 |
| 5 | [FASE-5.md](FASE-5.md) — proyectos | 8 | S | W6 |
| 6 | [FASE-6.md](FASE-6.md) — recursos | 5 | L | W4, D1 |
| 7 | [FASE-7.md](FASE-7.md) — admin y cuenta | 9, 10 | L | W7, W8, D4 |
| 8 | [FASE-8.md](FASE-8.md) — reportes | 7 | L | W5, D6 |
| 9 | [FASE-9.md](FASE-9.md) — code review | 14 | L | fases 1–8 |

**Qué esperar.** Cada fase termina con CI verde, PR mergeado por el owner y
el punto del feedback marcado `hecho`. Las decisiones D1–D7 y los
wireframes W1–W8 están en el plan (§5 y §7).

**Convenciones comunes a todas las fases.**

1. Rama: `claude/revamp-v2-f<N>-<tema>` desde `origin/main`.
2. IDs: `python scripts/proximo_id.py` al empezar; una US o BUG por commit
   (CLAUDE.md §7). Los runbooks usan `US-A`, `US-B`… como marcadores; se
   sustituyen por los IDs reales.
3. Verificación mínima antes de push: `tsc --noEmit`, `check_tokens.py`,
   `check_contexto.py`; con backend, además `ruff` y `pytest -m "not heavy"`.
   Todo con `exit 0` (skill `verificar`).
4. Documentación en el mismo bloque: epic tocada, `DB-CHANGES.md` si hay
   migración, `DECISIONS.md` si se cierra una D, `navigation.md` si cambia
   una ruta.
5. Cierre: skill `cerrar-item` por US; el owner cierra el issue.
