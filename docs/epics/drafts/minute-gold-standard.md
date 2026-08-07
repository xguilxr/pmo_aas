---
tipo: epica
responsable: propietario
estado: vigente
revisado: 2026-05-22
revisar_cada: 90d
---

# Minuta — Gold Standard de referencia (Sprint 26 Bloque 0)

> **Propósito:** caso real proporcionado por el owner como referencia
> normativa para el parser IA y los TC de ENH-102 y ENH-105.
> Define el nivel de detalle, el formato y la estructura esperada.
> **NO modificar el contenido del ejemplo** — solo es de lectura.

---

## 0. Conclusiones del ejemplo (revisión owner 2026-05-22)

Comparando el transcript real vs la minuta escrita a mano que le gustó al
owner, queda fijado lo siguiente para la implementación:

### Estructura final (6 secciones, owner OK)

1. **Encabezado** — proyecto + código, fecha, hora, duración, tipo de
   sesión, facilitador, modalidad, sede. Título auto desde nombre de
   archivo si import (ENH-104).
2. **Participantes** — Asistentes + Ausentes (justificados / no
   justificados). Cada uno con rol y área. Matcheados a actores del
   proyecto (ENH-103).
3. **Resumen / Objetivo** — 1 párrafo (2-3 oraciones) que sintetiza
   el objetivo de la sesión. Equivalente al "Objetivo de la sesión"
   del ejemplo.
4. **Temas tratados** — segmentación por tema. Para cada tema:
   - Título del tema (corto, accionable)
   - Bullets factuales del nivel del ejemplo (nombres concretos,
     fechas, decisiones, dependencias). NO prosa narrativa.
5. **RAID — A/R/D/I unificado** — tabla con todos los items
   accionables del proyecto detectados en la minuta:
   - **A (Acciones)** — incluye TODAS las "actividades a hacer", las
     "actividades del backlog" del ejemplo y todo lo accionable con
     responsable + fecha compromiso. **No hay sección separada de
     "actividades del backlog"** — owner aclaró que esto debería ser
     RAID Acciones desde siempre.
   - **R (Riesgos)** — preocupaciones, "podría", "no alineado".
   - **D (Decisiones)** — "se acordó", "se decidió", "se confirma".
   - **I (Issues)** — "problema", "falta", "no resuelto".
   - Cada item con checkbox individual "crear como item del proyecto"
     (default sí). Solo se persisten los marcados al guardar (BUG-061).
   - **NO admite Lecciones ni Cambios** (ENH-102 — el IA aluciaba estos
     tipos; descartar silenciosamente).
6. **Notas libres** (opcional) — bloque rich text del PM para todo lo
   que no encaja arriba (incluye "próximos pasos calendarizados" del
   ejemplo si el PM quiere mantenerlos como lista; alternativa: que el
   IA los suba como Acciones con fecha compromiso explícita).

### Mapeo de fuente → sección esperada del parser

| Fuente en transcript | Sección destino |
|---|---|
| Speaker list + metadata header | 1. Encabezado |
| Nombres en speakers + "hoy no vino X" | 2. Participantes |
| Primeras oraciones del facilitador ("el objetivo de hoy es…") | 3. Resumen |
| Cambios de tema en el flujo de conversación | 4. Temas tratados (uno por tema) |
| "X va a hacer Y" / "se contactará" / "se agendará" | 5. RAID — Acción |
| "preocupación" / "podría" / "riesgo" / "no alineado" | 5. RAID — Riesgo |
| "se acordó" / "se decidió" / "se confirma" | 5. RAID — Decisión |
| "problema" / "falta claridad" / "no resuelto" | 5. RAID — Issue |
| "lección aprendida" / "solicitud de cambio" | DESCARTAR (no admitido en minuta) |

---

## 1. Transcript de entrada (input al parser IA)

```
Sesión Highlander EAM-BNF – Operacional-20260323_120200-Grabación de la reunión
March 23, 2026, 6:02PM
46m 25s

NAVARRO Mario (EXT) started transcription

Martin Scalia   0:03
Gracias Mario.

David Aguilar   0:04
Gracias.
O.
Siempre empezamos sesiones cuando viene Juan Carlos, pero hoy no vamos a esperar un par de minutos.
[…]

David Aguilar   2:15
Ok, lo primero es.
La sesión para la revisión del business área hoy a las 5:00 de la tarde ya se tiene agendada la sesión.
Con la nueva, digamos, el nuevo avance y la nueva propuesta o propuesta actualizada de cómo se va a trabajar […]
[transcript completo de 46 minutos — guardado por separado en
 tests/fixtures/minutes/highlander-eam-bnf-20260323.txt]
```

## 2. Minuta esperada (output gold standard del parser)

```
MINUTA DE SESIÓN
EAM-BNF Fase 1 — Sesión Operacional
Proyecto Highlander — OBELIT PMO

1. Encabezado
   Fecha:        23 de marzo de 2026
   Hora:         12:02 PM (MX)
   Duración:     46 minutos
   Tipo:         Operacional — Seguimiento semanal
   Facilitador:  David Aguilar (PM / OBELIT)
   Modalidad:    virtual

2. Participantes
   ASISTENTES:
   - David Aguilar      — PM / OBELIT          — PMO
   - Martin Scalia      — Sponsor / Director   — PMO
   - NAVARRO Mario (EXT)— Consultor SAP        — IT / SAP
   - DIAZ ORDAZ Alfonso — Finanzas / DBS       — DBS / Finanzas
   - GOMORA Elizabeth   — DBS / Controlling    — DBS / Finanzas
   - PABLO Aline        — Comercial / Business — Comercial
   - GONZALEZ Diego     — Operaciones          — Operaciones
   - VIANA Francisco    — Comercial / Reporting— Comercial
   - YAÑEZ Juan         — Participante         — N/D
   - MARTINEZ Ivan      — Participante         — N/D

3. Resumen / Objetivo
   Revisar el estatus de avance de la migración de legal entity de EAM
   a Bonafont, con foco en el backlog de actividades abiertas, planes
   por área funcional, y próximos pasos para las definiciones críticas
   (Business Area, cuentas abiertas en SAP Themis, balance sheet).

4. Temas tratados

   4.1 Business Area
   - Sesión programada hoy a las 5:00 PM con propuesta actualizada.
   - Poncho tuvo sesión con Global: para Beck alineado, pero IPP no.
   - Otra sesión el lunes para definir Business Areas definitivamente.
   - Aline solicita socializar resultados de Global en la sesión de 5 PM.
   - Eli: asegurar continuidad post-definición; no detener en Business
     Area, avanzar con balance sheet y workarounds.

   4.2 Cuentas abiertas / SAP Themis para BEC
   - Sesión mañana AM para definir manejo de temas abiertos al 31 de enero.
   - Dos compañías en SAP: Themis BEC (saldos anteriores) y Themis BNF
     (nuevos movimientos desde 1 de enero).
   - Eli ya entregó actividades de DBS para BNF (counting, P2P,
     tesorería, finanzas).
   - Plan SAP Themis BEC se completa una vez resuelta la sesión de mañana.

   [… 9 temas adicionales con el mismo nivel de bullets factuales …]

5. RAID

   ID     | Tipo | Descripción                                              | Responsable           | Fecha compromiso | Status
   -------+------+----------------------------------------------------------+-----------------------+------------------+--------
   A-001  | A    | Contactar a Paola Canchola esta semana para etiquetas    | Diego González        | Sem 24-28 mar    | Open
   A-002  | A    | Agregar definición de balances al backlog                | Martin / David        | Inmediato        | Open
   A-003  | A    | Socializar resultados Global en sesión 5 PM hoy          | Poncho / Aline        | Hoy 5 PM         | Open
   A-004  | A    | Mapear Víctor Rodríguez / D&A en plan integración Themis | David / Mario         | Sem 25 mar       | Open
   A-005  | A    | Inducción Highlander para product owners IT legacy       | David / Aline / Martin| Esta semana      | Open
   A-006  | A    | Aline: mapear fuentes de reportes (One Source/Frog/SAP)  | Aline / Janine        | Post 5 PM        | Open
   A-007  | A    | Invitar Amado Lim a sesiones comerciales (BigBeck)       | David                 | Sem 24-28 mar    | Open
   R-001  | R    | Workarounds de balance pueden ser más costosos que actual| Eli / Poncho          | —                | Open
   R-002  | R    | IPP Business Area no alineado con Global                 | Poncho                | —                | Open
   R-003  | R    | Reporting D&A (Víctor Rodríguez) no mapeado en Themis    | David / Mario         | —                | Open
   R-004  | R    | Permisos de pozos de extracción podrían retrasarse       | Luis / CMP            | abr-may          | Open
   D-001  | D    | Mantenimiento de vehículos/flota: SÍ se implementa       | Mario                 | (resuelta)       | Closed
   D-002  | D    | Reclasificar pozos/arrendamiento a tema transversal      | David                 | (resuelta)       | Closed
   D-003  | D    | Business Area: definición final en sesión lunes c/ Global| Poncho / Aline        | Lunes            | Pending
   D-004  | D    | eComercio vs Estela: decisión integral 27 marzo          | Aline / Felipe / Sandy| 27 mar           | Pending
   I-001  | I    | Falta claridad sobre quién valida etiquetas              | Diego González        | En curso         | In Progress

   (Sin lecciones ni cambios — owner confirmó que no aplican a minuta.)

6. Notas libres
   Próximos pasos calendarizados:
   - Hoy 5:00 PM — Sesión Business Area (socializar Global)
   - Mañana AM — Sesión cuentas abiertas SAP Themis BEC
   - Mañana — Sesión líderes (escenarios extracción de agua con Poncho)
   - 25 marzo — Sesión con PINI (condiciones comerciales EAM en BNF)
   - Viernes 27 marzo — Sesión eComercio/Estela
   - Lunes — Segunda sesión Business Area con Global
   - Miércoles 12:00 — Sesión de seguimiento de backlog
```

---

## 3. Spec del parser IA (cierra ENH-102 y ENH-105)

### Pipeline

```
[Transcript / archivo / paste]
    │
    ▼
1. PREPROCESAMIENTO
   - Detectar speakers (líneas "Nombre  HH:MM" o "Nombre (EXT)  HH:MM")
   - Detectar metadata header (título de archivo, fecha, duración)
   - Limpiar líneas de transcripción ("X started transcription", etc.)
   - Chunking si > 3000 tokens (con overlap de 200 tokens — reusa EP008)
    │
    ▼
2. LLAMADA IA — UN SOLO PROMPT con schema JSON estricto
   Modelo: cascada EP008 (Groq plataforma o BYO tenant)
   Schema output:
   {
     "header": { title, date, time, duration, modality, location, facilitator },
     "participants": { attendees: [...], absent_justified: [...], absent_unjustified: [...] },
     "summary": "string (2-3 oraciones)",
     "topics": [
       { title: "string", bullets: ["string", ...] },
       ...
     ],
     "raid": [
       {
         type: "A"|"R"|"D"|"I",     // ENUM estricto — RECHAZAR otros valores
         description: "string",
         responsible: "string",       // nombre tal como aparece en transcript
         due_date: "string|null",    // ISO o "Sem N", "Inmediato", etc.
         status: "Open"|"In Progress"|"Pending"|"Closed"
       },
       ...
     ],
     "free_notes": "string|null"   // bullets de próximos pasos calendarizados
                                    // u otras notas que no encajan en RAID
   }

3. VALIDADOR POST-IA (services/ai/validator.py — nuevo)
   - Descarta items RAID con type ∉ {A, R, D, I} silenciosamente
     (no error — anota en log para métricas; el IA alucina lecciones/cambios)
   - Valida shape del JSON; fallback a chunk re-prompt si malformado
   - Normaliza fechas relativas ("mañana", "lunes") usando fecha de la
     reunión como ancla
    │
    ▼
4. MATCHING DE PARTICIPANTES (services/minutes/participant_matcher.py)
   - Para cada nombre en `participants`, buscar match en
     project_participations del proyecto (fuzzy match nombre completo,
     case-insensitive, tolerancia 2 chars)
   - Match → asignar actor_id
   - Sin match → crear actor con auto_created=true, verified=false,
     rol "guest" en project_participations
    │
    ▼
5. PREVIEW UI
   - Mostrar minuta renderizada con la estructura de 6 secciones
   - Cada participante: chip verde (matched) o amarillo (auto-creado)
   - Cada item RAID: checkbox individual "crear como item" (default sí)
   - Bug a evitar: en ACCEPT, los items con checkbox marcado DEBEN
     persistirse (BUG-061)
    │
    ▼
6. ACCEPT / GUARDAR
   - Pedir título si está vacío (modal — ENH-104)
   - Crear meeting_minute con origin = transcript_ai|import_file|import_paste
   - Crear registros RAID por cada item confirmado, linkeados a la minuta
   - Generar export en plantillas (PDF/DOCX/MD/TXT) con la nueva estructura
```

### Prompt few-shot

El prompt incluye COMO EJEMPLO el caso de este documento (Highlander
EAM-BNF). Esto asegura que el IA emule el nivel de detalle del bullet
que le gusta al owner.

```
SYSTEM:
Eres un asistente experto en estructurar minutas operativas de proyectos.
Devuelves SIEMPRE JSON estrictamente válido con el schema proporcionado.
Reglas críticas:
- Cada item RAID es tipo A, R, D o I exclusivamente.
- Lecciones aprendidas y solicitudes de cambio NO van en la minuta;
  descártalos silenciosamente.
- Los bullets de "temas tratados" deben ser factuales, concretos, con
  nombres propios y fechas cuando aparezcan. NO uses prosa narrativa.
- Las "actividades a hacer" del flujo de la reunión son RAID Acciones.
- "Próximos pasos calendarizados" (fechas concretas de eventos) van en
  free_notes si no tienen responsable claro; si tienen responsable y
  fecha, van como Acción del RAID.

USER (few-shot example 1):
<transcript completo de Highlander EAM-BNF>

ASSISTANT (few-shot example 1):
<JSON del gold standard arriba>

USER (real query):
<nuevo transcript a procesar>

ASSISTANT:
<JSON del nuevo transcript>
```

### Test cases derivados (TC para ENH-102, ENH-105 y BUG-061)

- TC-300 — parser ingiere transcript Highlander y devuelve JSON con
  ≥ 11 temas detectados.
- TC-301 — parser extrae ≥ 7 Acciones, ≥ 4 Riesgos, ≥ 4 Decisiones,
  ≥ 1 Issue del transcript Highlander.
- TC-302 — parser DESCARTA cualquier item con type "Lección" o "Cambio"
  silenciosamente (transcript con menciones explícitas).
- TC-303 — preview muestra N items RAID; al aceptar con todos los
  checkboxes marcados, se crean exactamente N registros (BUG-061).
- TC-304 — preview muestra N items; al desmarcar 3 antes de aceptar,
  se crean N-3 registros.
- TC-305 — participantes "Aline", "Aline Pablo", "PABLO Aline" hacen
  match al mismo actor del proyecto (fuzzy matcher tolerante).
- TC-306 — participante sin match en proyecto se crea con
  auto_created=true y se agrega como rol "guest".
- TC-307 — minuta exportada a PDF tiene exactamente 6 secciones en
  el orden definido.
- TC-308 — origin queda registrado en BD (transcript_ai / import_file /
  import_paste / manual) y NO aparece en la minuta exportada.
- TC-309 — título auto desde nombre de archivo si import; modal de
  título obligatorio al guardar si vacío y origen != import.

---

## 4. Fixture para tests

El transcript completo del ejemplo Highlander debe guardarse en:
`apps/api/tests/fixtures/minutes/highlander-eam-bnf-20260323.txt`

La minuta esperada (gold standard JSON) en:
`apps/api/tests/fixtures/minutes/highlander-eam-bnf-20260323.expected.json`

Estos archivos serán los TC verde de ENH-102 y ENH-105.
