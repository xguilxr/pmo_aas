---
tipo: gestion
responsable: propietario
estado: vigente
revisado: 2026-09-11
revisar_cada: 30d
---

# FASE 9 — Code review transversal: descargas, completitud de formularios, consistencia

**Qué es.** Tres pasadas de revisión sobre todo el sistema, estilo Pull
Request Review de GitHub, con corrección en el mismo PR. Punto 14 de
`../REVAMP-V2-FEEDBACK.md`.
**Tamaño:** L. **Gate:** fases 1–8 mergeadas. **Epics:** la que toque cada
hallazgo.

**Reglas.** Un PR por pasada (tres PRs). Dentro de cada PR, un commit por
hallazgo corregido. Los hallazgos que no se corrigen quedan como issue con
`triage`. Método: skill `code-review` a nivel `high` con `--comment` sobre
el PR de la pasada; cada comentario se resuelve con un commit o con una
respuesta que diga por qué no.

## Preparación

```bash
git fetch origin main
git checkout -b claude/revamp-v2-f9-descargas origin/main   # pasada 1
python scripts/proximo_id.py
```

## Pasada 1 — descargas (PR `Revamp v2 — fase 9a: descargas`)

**Hechos verificados.** Quedan cuatro generadores CSV y tres descargas sin
nombre de archivo.

| # | Dónde | Hoy | Debe quedar |
|---|---|---|---|
| 1 | `apps/api/app/api/v1/endpoints/admin_panel.py:640-644` + `apps/web/lib/api/admin-panel.ts:82-84` (`auditLogsCsvUrl`) | `text/csv`, `audit_logs.csv` | XLSX con `openpyxl` + `tipografia.aplicar_a_workbook`; `auditoria-<tenant-slug>-<YYYY-MM-DD>.xlsx`; la función del front pasa a `auditLogsXlsxUrl` y el botón de `/admin/audit-logs` la usa |
| 2 | `apps/api/app/api/v1/endpoints/dashboard.py:1000-1004` + `apps/web/lib/api/dashboard.ts:269` (`planVsActualCsvUrl`) | `text/csv`, `plan_vs_actual.csv` | XLSX, `plan-vs-real-<organizacion-slug>-<YYYY-MM-DD>.xlsx`; renombrar a `planVsActualXlsxUrl` y actualizar sus usos (`grep -rn planVsActualCsvUrl apps/web`) |
| 3 | `components/importador.tsx` (plantilla, heredado de `imports/page.tsx:124-134`) | CSV en cliente | Ya XLSX desde la fase 6; **verificar**, si sigue en CSV corregir aquí |
| 4 | `apps/web/lib/api/project-charters.ts:136-139` | descarga con nombre `""` | `charter-<folio>.pdf` (o la extensión real del blob) |
| 5 | `apps/web/app/(app)/pmo/projects/[id]/documents/page.tsx:95-98` | `fallbackName` | nombre real del documento (`d.name` o `filename` del header) |
| 6 | `apps/web/lib/api/modules.ts:554-564` | comentario reconoce el bug del nombre | mismo arreglo que 4 y 5: leer `Content-Disposition`; helper único `nombreDeDescarga(res, fallback)` en `lib/api/index.ts` |

Además, en las 18 descargas del inventario (`../REVAMP-V2-PLAN.md` fuentes;
lista completa en el output del inventario 2026-09-11, sección "Botones de
descarga"), comprobar a mano:

1. El botón usa `Button variant="secondary" size="sm"` con
   `<Icono nombre="download" size={14} />` a la izquierda y está en la
   cabecera de la sección (patrón de `pmo/page.tsx:376-386`).
2. El nombre del archivo sigue `<que>-<contexto>-<YYYY-MM-DD>.<ext>` en
   minúsculas y sin espacios. Los que hoy usan espacios
   (`plan/page.tsx:1864`, `PLAN - {Proyecto} - {fecha}.xlsx`) se
   normalizan.
3. Todo XLSX pasa por `aplicarFuente` (front) o `aplicar_a_workbook`
   (back). Los que no (`plan/page.tsx:1864-1869`, `raid`, `changes`,
   `lessons`, `organigrama`): verificar en el backend que el servicio
   llame `aplicar_a_workbook`; si no, agregarlo.

Un commit por fila de la tabla + un commit "chore(web): botones de
descarga alineados y nombres normalizados" para el punto 1-2.

**TC-F9-01.** `grep -rn "text/csv" apps/api/app apps/web --include=*.py --include=*.ts --include=*.tsx`
devuelve vacío (salvo tests que lo verifiquen a propósito). Cada descarga
abre en Excel con la fuente corporativa.

## Pasada 2 — completitud de formularios (PR `fase 9b: formularios`)

**Hechos verificados** (tabla "Dónde no hay formulario hoy" del plan §3).
Para cada hueco: si una fase anterior ya lo cerró, marcar y seguir; si no,
corregir aquí.

| Entidad | Hueco | Fase que lo cierra | Si sigue abierto |
|---|---|---|---|
| Portfolio | sin alta/edición | 4 (commit 5) | crear `portfolio-form.tsx` con los 5 campos de `PortfolioCreateBody` (`organizations.ts:328`) |
| Program | sin edición | 4 (commit 5) | `program-modal.tsx` con `updateProgram` |
| Risk | `category` no se pide al crear | — | `raid-create-modal.tsx`: agregar `category` (mismo control que `raid-edit-fields.tsx`) |
| Change | sin edición | — | `changes/[changeId]/page.tsx`: formulario con `ChangeRequestUpdateBody` (`title`, `description`, `impact`) mientras `status = draft` |
| Actor | sin alta/baja | 6 (commit 2) | ver FASE-6 |
| User | `deleteUser` desactiva | 7 (commit 2) | ver FASE-7 |
| Request | edición desde `requests/[id]` no verificada | — | abrir `pmo/requests/[id]/page.tsx`; si solo permite revisar, agregar edición de los campos del solicitante mientras `status ∈ {in_review, needs_info}` |

Método general por entidad:

1. Abre el tipo en `apps/web/lib/api/<entidad>.ts` y lista sus campos.
2. Abre cada formulario (crear, editar, inline) y lista los campos que
   manda.
3. Diferencia = campos del modelo que ningún formulario pide. Para cada
   uno decide: *derivado* (folio, timestamps, `progress`, `health_source`,
   `manually_edited_fields`) → no se pide, se documenta en el PR;
   *configurable* → se agrega al formulario que corresponda.
4. Un commit por entidad.

**TC-F9-02.** Tabla en el PR: entidad · campo · dónde se pide ahora. Sin
filas "en ningún lado" salvo las derivadas.

## Pasada 3 — consistencia entre pantallas (PR `fase 9c: consistencia`)

**Hecho verificado.** `excluded_organization_ids` se manda en el body al
crear usuario (`admin/users/new/page.tsx`) y con `setExcludedOrganizations`
aparte al editar (`admin/users/[id]/page.tsx`).

1. Unificar: el edit manda el campo en el mismo `updateUser` body, o el
   create usa la llamada aparte; elegir lo que el backend ya soporte en
   `PATCH /admin/users/{id}` (revisa `admin_users.py`).
2. Para cada entidad con más de un formulario (Project: create/edit/inline;
   Risk/Issue: create/edit; User: create/edit; Minute: create/inline):
   misma etiqueta, mismo control, misma validación para el mismo campo.
   Tabla en el PR con las diferencias encontradas y el commit que las
   cerró.
3. Vocabulario: etiquetas de fase/tipo/salud siempre desde
   `PHASE_LABEL`/`HEALTH_LABEL`/tipo de `lib/api/projects.ts`; ninguna
   cadena literal repetida (`grep -rn '"Preparación"\|"En ejecución"' apps/web`
   debe apuntar solo al diccionario).

**TC-F9-03.** Los tres greps de arriba limpios; tabla del PR sin filas
abiertas.

## Cómo correr cada pasada

```bash
# en la rama de la pasada, con los commits hechos:
/code-review high --comment        # skill code-review sobre el PR
# resolver cada comentario: commit o respuesta
pnpm --filter @pmoaas/web exec tsc --noEmit
python scripts/check_tokens.py
cd apps/api && .venv/bin/python -m ruff check . && .venv/bin/python -m pytest -q -n auto -m "not heavy"
```

## Cierre

Tres PRs mergeados → punto 14 `hecho`. `SPRINT.md`: la línea de fases se
cierra; quedan "Mobile" y "Plan e IA (D5)". Skill `handoff`.

## Qué NO hacer

- No refactorizar más allá del hallazgo (CLAUDE.md §14: el cambio más
  pequeño).
- No cambiar contratos de API sin actualizar `packages/sdk` y la epic.
- No borrar código que otra pasada vaya a tocar: coordina por el orden
  9a → 9b → 9c.
