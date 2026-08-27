---
tipo: gestion
responsable: propietario
estado: borrador
revisado: 2026-08-27
revisar_cada: 30d
---

# Post-revamp · Bloque G — Reportes HTML y minutas por especificación

> Especificación implementable del bloque G. Principio: **el layout se
> escribe una vez** (plantillas Jinja2 con los tokens del revamp); cada
> generación solo aporta un JSON validado por schema. El modelo nunca
> escribe HTML; escribe la spec y los textos narrativos.

## G1 — `report-spec` (el formato que el owner o un agente escriben)

YAML (o JSON equivalente) validado contra JSON Schema. Versión en el
propio documento (`version: 1`). Draft del schema — la implementación lo
materializa en `apps/api/app/schemas_json/report_spec.schema.json` y es la
fuente de verdad desde entonces:

```yaml
version: 1
titulo: "Reporte ejecutivo — Dirección de TI"      # 1..120 chars
audiencia: comite | sponsor | equipo                # afecta densidad de nota al pie
alcance:                                            # exactamente uno
  tipo: tenant | organization | portfolio | program | project
  id: "<uuid>"                                      # omitible si tipo=tenant
ventana:
  corte: "2026-08-24"          # fecha de corte; null = vivo (y se rotula así)
  semanas_tendencia: 12        # para secciones de tendencia
branding: true                 # logo/nombre del tenant en el encabezado
secciones:                     # 1..12, del catálogo cerrado; orden = orden de render
  - tipo: kpi_band             # sin params
  - tipo: semaforo_consolidado
  - tipo: tabla_proyectos
    params: {salud: [red, yellow], max_filas: 15}   # filtros opcionales
  - tipo: matriz_riesgos
  - tipo: tendencia            # requiere ventana.semanas_tendencia
  - tipo: capacidad_resumen
  - tipo: gantt_resumen        # solo alcance project
  - tipo: raid_abiertos
    params: {tipos: [riesgo, issue], max_filas: 10}
  - tipo: narrativa            # el ÚNICO texto libre
    params: {titulo: "Lectura del PM", cuerpo_md: "…"}   # markdown restringido: p, strong, em, ul/li — nada más; se sanitiza al render
```

Reglas duras del schema: `secciones` no vacío; `gantt_resumen` solo con
`alcance.tipo=project`; `narrativa.cuerpo_md` ≤ 2.000 chars; propiedades
adicionales prohibidas (`additionalProperties: false` en todos los
niveles) — un typo de un modelo chico debe fallar el schema, no colarse.

### Contrato de datos por sección (todas son endpoints existentes)

| Sección | Fuente (router `dashboard` salvo nota) |
|---|---|
| kpi_band | `kpis` (con scope del alcance) |
| semaforo_consolidado | `health-matrix` |
| tabla_proyectos | `plan-vs-actual` (las 16 columnas; la sección elige 7) |
| matriz_riesgos | `risk-matrix` |
| tendencia | `trends` (+`cadencia_dias`) |
| capacidad_resumen | `capacity/summary` + `conflicts` |
| gantt_resumen | `tasks` del proyecto (nivel 1 del WBS) |
| raid_abiertos | `tenant_cross` o `modules` según alcance |
| narrativa | el propio spec |

`ventana.corte` no nulo ⇒ los datos salen de `metric_snapshots` del corte
más cercano ≤ corte (y el reporte rotula la fecha real usada); nulo ⇒
lectura viva rotulada «vivo» (mismo criterio DAT-11 de la UI).

## G2 — Renderer determinista

- **Dónde**: `apps/api/app/services/reportes_html/` — `render(spec, datos)
  -> str` + plantillas `plantillas/*.html.j2` (una por sección + `base`).
  Server-side junto al PDF renderer existente; el HTML resultante es
  autocontenido (CSS inline, SVG estático para gráficos, cero JS) y entra
  tal cual al pipeline PDF vigente (`html_to_pdf`).
- **Tokens**: `check_tokens.py` solo barre `apps/web` — las plantillas
  necesitan su propia fuente. Crear `core/tokens_html.py` con el
  subconjunto usado (superficie, texto, bordes, semáforo, profundidad) y
  un trinquete `test_tokens_html_espejo.py` que lo compare contra
  `globals.css` (mismo patrón que `test_adr023_paleta_graficos.py` con
  `core/paleta.py` — esa infraestructura ya existe, copiarla).
- **Gráficos**: SVG generado en Python (barras, dona de salud, línea de
  tendencia) con `core/paleta.py` — prohibido introducir una librería de
  charts; los SVG de la web sirven de referencia visual.
- **Seguridad**: autoescape de Jinja ON; `narrativa.cuerpo_md` pasa por el
  render de markdown restringido + sanitización (lista blanca de tags del
  schema). Declarar en `modelo-amenazas.md`: entrada de usuario/modelo →
  HTML compartible.
- **Endpoints**: `POST /api/v1/reports/html` (body = spec JSON; responde
  HTML) y el guardado como artefacto: `?guardar=true` crea
  `project_artifacts`/`reports` según alcance (reusar el flujo de reports
  existente). El CLI `pmo reporte generar` llama a esto.
- **AC**: TC-1 spec válido de 3 secciones → HTML con las 3 en orden; TC-2
  spec con sección desconocida → 422 con el error del schema; TC-3
  narrativa con `<script>` → sanitizado; TC-4 corte sin snapshot → usa el
  anterior y lo rotula; TC-5 el HTML pasa por `html_to_pdf` sin error.

## G3 — Minutas: JSON Schema + pipeline

Estructura = gold standard (`minute-gold-standard.md`, 6 secciones, owner
OK 2026-05-22). Draft del schema
(`apps/api/app/schemas_json/minuta.schema.json`):

```jsonc
{
  "encabezado": {
    "proyecto_folio": "PRJ-…", "titulo": "str ≤120",
    "fecha": "date", "hora": "str|null", "duracion_min": "int|null",
    "tipo_sesion": "str", "facilitador": "str", "modalidad": "virtual|presencial|mixta",
    "sede": "str|null"
  },
  "participantes": {
    "asistentes":  [{"nombre": "str", "rol": "str|null", "area": "str|null", "actor_id": "uuid|null"}],
    "ausentes":    [{"nombre": "str", "justificado": "bool"}]
  },
  "resumen": "str 100..600",                        // 2-3 oraciones, objetivo de la sesión
  "temas": [                                        // 1..12
    {"titulo": "str ≤80",                           // corto, accionable
     "bullets": ["str ≤240", "…"]}                  // 1..10, factuales: nombres, fechas, decisiones — NO prosa
  ],
  "raid": [                                         // 0..30
    {"tipo": "accion|riesgo|decision|issue",        // NUNCA leccion/cambio (ENH-102: descartar silencioso)
     "descripcion": "str ≤300",
     "responsable": "str|null", "fecha_compromiso": "date|null",   // acciones: responsable obligatorio
     "crear_item": true}                            // checkbox BUG-061, default true
  ],
  "notas_libres": "str|null ≤2000"
}
```

Reglas del schema: `additionalProperties: false`; acción sin responsable →
inválido; los mapeos fuente→sección del gold standard (§«Mapeo») van en el
prompt de extracción, verbatim.

**Pipeline** (`pmo minuta generar` / endpoint):

1. Transcript → **modelo pequeño** con el schema y el mapeo; salida JSON.
2. Validación estricta; si falla, un retry con los errores del validador
   como feedback (retry sobre el error de schema, no sobre prosa); segundo
   fallo → escalar modelo una vez; tercero → reportar, nunca «arreglar» a
   mano el JSON.
3. Matcheo `actor_id` contra el directorio del proyecto (ENH-103 ya
   define la lógica; reusar).
4. Render HTML con plantilla de minuta del mismo sistema G2 → persistir
   por el flujo existente de `meeting_minutes` (con `raid_suggestions` =
   los items `crear_item:true`, que ya alimentan el flujo minuta→RAID).
- **AC**: TC-1 el transcript gold standard produce las 6 secciones y ≥ los
  items RAID que la minuta de referencia lista (fixture
  `tests/fixtures/minutes/highlander-…`); TC-2 «lección aprendida» en el
  transcript NO aparece en `raid`; TC-3 acción sin responsable rechazada
  por el validador con mensaje accionable; TC-4 JSON válido → render →
  guardado visible en la UI de minutas del proyecto.

## G4 — Evaluación y cierre

- Casos nuevos en `apps/api/evaluacion/casos.yaml`: spec inválida (typo de
  sección), transcript pobre (2 líneas → minuta mínima honesta, no
  inventada), datos vacíos (secciones renderizan el patrón `SIN_DATO`,
  nunca ceros — DAT-12 aplica a documentos generados), narrativa con HTML
  malicioso.
- Los reportes generados de alcance project quedan en Artefactos (EP018);
  los de alcance superior en `reports` con su history.
- Epic destino: G crece dentro de **EP020** (report builder — mismas
  secciones, nueva cara) y las minutas en **EP008/EP006** según el tramo;
  actualizar epics en los commits que entreguen.

## Orden dentro del bloque

G3-schema + G1-schema primero (son documentos: desbloquean prompts y
evaluación) → G2 base+3 plantillas (kpi_band, tabla_proyectos, narrativa)
→ G3 pipeline completo → resto de secciones → G4.
