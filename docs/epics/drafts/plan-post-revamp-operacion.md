---
tipo: gestion
responsable: propietario
estado: borrador
revisado: 2026-08-27
revisar_cada: 30d
---

# Post-revamp · Bloque O — Contrato del CLI `pmo` y skills de operación

> Especificación implementable del bloque O de `plan-post-revamp.md`. El
> objetivo económico: que una tarea de operación estándar (consultar
> cartera, cargar un riesgo, generar un reporte) le cueste a un agente
> <10k tokens de contexto y corra en Haiku. El mecanismo: **el modelo
> decide y redacta; el CLI navega, autentica, pagina, valida y formatea.**

## O1 — CLI `pmo` (`tools/pmo/`)

### Arquitectura

- Paquete Python en `tools/pmo/` (fuera de `apps/` — no se despliega),
  entrada `python -m pmo` o script `tools/pmo/pmo`. Cliente HTTP `httpx`
  contra el API público (`PMO_API_URL`, default producción; **nunca** toca
  la DB directo — así respeta permisos, scoping y auditoría como cualquier
  usuario).
- Estado en `~/.pmo/ctx.json`: `{api_url, token, refresh_token, tenant_id,
  organization_id}` con permisos 0600. Refresh automático transparente; si
  el refresh muere, error `AUTH_EXPIRED` accionable.
- **Salida**: JSON compacto a stdout, SIEMPRE de la forma
  `{"ok": true, "data": …}` o `{"ok": false, "error": {"code", "mensaje",
  "arregla": "<comando o acción concreta>"}}`. Campos mínimos por defecto;
  `--full` para el objeto completo del API. `--tabla` para humanos (no es
  la ruta del agente).
- **Exit codes**: 0 ok · 1 error de negocio (validación, 404) · 2 error de
  auth · 3 error de red/API caída. El agente decide por exit code sin
  parsear.
- Toda escritura acepta `--dry-run` (imprime el payload que enviaría y las
  validaciones locales) y es idempotente donde el API lo permita.

### Comandos v1 (el mínimo que cubre la operación diaria)

| Comando | Qué devuelve / hace | API que usa |
|---|---|---|
| `pmo login --email … [--api URL]` | pide password (stdin oculto o `PMO_PASSWORD`), maneja el 2º paso OTP interactivo, guarda ctx | `auth/login` |
| `pmo ctx [--tenant ID] [--org ID]` | muestra o fija tenant/org activos | `auth/switch-tenant`, `/me` |
| `pmo cartera` | resumen ejecutivo: KPIs + semáforo consolidado + tops, plano | `dashboard/kpis`, `charts`, `tops` |
| `pmo proyectos [--salud red\|yellow] [--fase X] [--q texto]` | lista compacta: folio, nombre, fase, salud, avance | `projects` |
| `pmo proyecto <folio>` | detalle: hoja de datos + conteos RAID + próximo hito | `projects/{id}` (resuelve folio→id con un lookup) |
| `pmo raid <folio> [--tipo riesgo\|accion\|issue\|decision] [--abiertos]` | items RAID compactos | `modules` |
| `pmo riesgo nuevo <folio> --json archivo.json` | alta de riesgo (schema local validado antes de enviar) | `modules` POST |
| `pmo tarea avanzar <task_id> <pct>` | actualiza avance | `tasks` PATCH |
| `pmo capacidad [--semanas N]` | sobreasignados + conflictos, compacto | `capacity/summary`, `conflicts` |
| `pmo importar <archivo.xlsx> --clase proyectos\|recursos [--confirmar]` | preview (default) o confirm del flujo US-216; imprime el resumen de 3 estados por fila | `imports/*` |
| `pmo minuta generar <folio> --transcript archivo.txt [--guardar]` | pipeline G3: extrae → valida → renderiza → (opcional) persiste | `ai/*`, `modules` (ver doc `-generacion`) |
| `pmo reporte generar --spec spec.yaml [--out reporte.html]` | pipeline G2 | ver doc `-generacion` |

Fuera de v1 a propósito (YAGNI hasta que la operación lo pida): CRUD de
organizaciones/usuarios, cambios/lecciones, admin. Se agregan cuando una
sesión real los eche en falta — cada comando nuevo copia el patrón.

### Reglas de implementación

1. Un módulo por dominio (`pmo/cartera.py`, `pmo/proyectos.py`, …), un
   `client.py` (auth+retry+errores) y un `salida.py` (formato único).
2. Los shapes de salida se declaran como TypedDicts en `pmo/shapes.py` —
   son EL contrato que la skill `operar` documenta; cambiar un shape obliga
   a tocar la skill (trinquete O4).
3. Errores del API se traducen a `arregla`: 401→`pmo login`, 403→«pide el
   permiso X al admin», 404 folio→«verifica con pmo proyectos --q»,
   red→«API caída, reintenta o revisa PMO_API_URL».
4. Tests en `tools/pmo/tests/` con respx/httpx-mock: por comando, el happy
   path + el mapeo de errores. No requieren API viva.

## O2 — Skills de operación (`.claude/skills/`)

Formato: el de las skills existentes (`SKILL.md` con frontmatter
name/description). Regla de oro: **autocontenidas** — la skill trae todo;
si para operar hace falta abrir el repo, la skill está incompleta y se
corrige la skill.

### `operar` (la principal)

Contenido: (1) tabla completa de comandos ↔ shapes de salida (copiada de
`shapes.py`, con el trinquete de abajo velando que no diverja); (2) los 4
códigos de salida y el campo `arregla`; (3) recetas de las 6 tareas más
comunes, cada una en 2–4 comandos («estado de la cartera», «por qué este
proyecto está rojo», «alta de riesgo desde un correo», «avance semanal de
tareas», «carga masiva», «conflictos de capacidad»); (4) presupuesto: si la
tarea no sale con los comandos listados, PARAR y reportar el hueco — no
explorar el repo.

### `sembrar-datos`

Orden de alta (org → portafolio → programa → proyecto → plan → recursos →
asignaciones), plantillas XLSX de US-216 (columnas exactas que declara
`imports/columns`), los tres estados por fila y qué hacer con cada uno, y
un juego de datos demo mínimo (1 org, 2 proyectos, 6 tareas, 3 personas)
inline en la skill.

### `reporte-html` y `minuta`

Delgadas: el contrato vive en `plan-post-revamp-generacion.md` y en los
JSON Schema; la skill trae el flujo (comandos `pmo reporte generar` /
`pmo minuta generar`), el checklist de validación previa y los 3 errores
típicos de schema con su corrección. La redacción de narrativa/bullets
sigue las reglas del schema (longitudes, tono factual) que la skill cita
verbatim.

## O3 — Enrutamiento de modelos (extensión de la skill `delegar`)

| Tarea | Modelo | Por qué |
|---|---|---|
| Ejecutar comandos `pmo` y reportar | Haiku | decisión trivial, contrato cerrado |
| Extracción transcript→JSON minuta | Haiku (retry con Sonnet si el schema rechaza 2×) | schema estricto contiene al modelo chico |
| Llenar `report-spec` desde una petición del owner | Haiku–Sonnet según ambigüedad | catálogo cerrado de secciones |
| Narrativa ejecutiva de un reporte | Sonnet | juicio de síntesis |
| Triage/diseño/decisiones de scope | sesión principal | necesita contexto vivo |

Regla de presupuesto (va en `delegar`): tarea de operación >10k tokens de
contexto ⇒ falta un tool o una receta en la skill; se registra el hueco en
`LESSONS.md` y se corrige el tool, no se sube de modelo.

## O4 — Trinquetes

- `tools/pmo/tests/test_contrato_skill.py`: parsea la tabla de comandos de
  `.claude/skills/operar/SKILL.md` y la compara contra los subcomandos
  registrados en el CLI — divergencia = rojo (misma familia que el
  trinquete de vocabulario US-202).
- Los JSON de minuta/reporte inválidos que lleguen a un usuario entran al
  conjunto `evaluacion-ia` antes del fix (MCS IA-07/08/09, regla existente).
- CI: job liviano `pmo-cli` (ruff + pytest de `tools/pmo`) — solo con
  cambios en `tools/**` (filtro de paths).

## Orden dentro del bloque

O1 núcleo (`login/ctx/cartera/proyectos/proyecto/raid`) → skill `operar`
v1 → resto de comandos → `sembrar-datos` → O3 (editar `delegar`) → O4.
G se monta encima cuando O1 esté.
