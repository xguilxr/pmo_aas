---
responsable: propietario
estado: archivado
revisado: 2026-05-08
revisar_cada: nunca
---

# EP-008: Inteligencia Artificial - Minutas y Reportes

**Prioridad:** Alta
**Módulo:** IA / Automatización
**Dependencias:** EP-005 (Proyectos), EP-006 (Módulos - Minutas)

> Objetivo: Automatizar la generación de minutas desde transcripciones y generar reportes de avance
> por correo con un click. Soporte para modelo local ligero (costo reducido) con fallback a Claude API.

---

## Decisión técnica: Modelo local vs API

### Modelo local recomendado
| Modelo               | Tamaño   | VRAM     | Capacidad para minutas | Español  |
|----------------------|----------|----------|------------------------|----------|
| **Mistral 7B**       | ~4GB Q4  | 6GB      | Buena                  | Bueno    |
| **Llama 3.1 8B**     | ~4.5GB Q4| 6GB      | Muy buena              | Bueno    |
| **Phi-3 Mini 3.8B**  | ~2.2GB Q4| 4GB      | Aceptable              | Aceptable|
| **Qwen 2.5 7B**      | ~4GB Q4  | 6GB      | Muy buena              | Muy bueno|

**Recomendación:** Qwen 2.5 7B o Llama 3.1 8B cuantizado (Q4_K_M) corriendo con **Ollama** o **llama.cpp**.
Ambos manejan bien español y tienen capacidad suficiente para resumir transcripciones de 1-2 horas.

### Estrategia híbrida
1. **Modelo local** (Ollama): Para generación de minutas y resúmenes de avance (uso frecuente, costo $0)
2. **Claude API** (fallback): Para análisis complejos, síntesis cross-proyecto, o cuando el modelo local no está disponible
3. **Configurable por .env**: El admin elige qué backend usar

### Stack de IA
- **Ollama** como runtime para modelo local (API REST compatible)
- **LangChain** o llamadas directas a la API de Ollama (`POST /api/generate`)
- **Anthropic SDK** para fallback a Claude API
- **Chunking**: Transcripciones largas se dividen en segmentos de ~3000 tokens con overlap

---

## US-027: Generación de minutas desde transcripción con IA

**Épica:** EP-008
**Prioridad:** Alta
**Estimación:** XL

**Como** Project Manager
**Quiero** subir una transcripción de reunión (texto o archivo) y que la IA genere una minuta estructurada automáticamente
**Para** ahorrar tiempo en la documentación de reuniones y no perder información clave

### Flujo del usuario
1. En el módulo de Minutas → Click "+ Nueva Minuta con IA"
2. Seleccionar proyecto asociado
3. Subir transcripción: pegar texto, subir archivo .txt/.docx/.srt, o subir audio (futuro)
4. Click "Generar Minuta"
5. La IA procesa y genera: resumen, temas tratados, acuerdos, compromisos, participantes detectados, próximos pasos
6. El usuario **revisa y edita** la minuta generada antes de guardar
7. Guardar como minuta del proyecto

### Formato de salida de la IA
```
## Minuta de Reunión - [Título detectado]
**Fecha:** [detectada o ingresada]
**Participantes:** [detectados del transcript]

### Resumen ejecutivo
[2-3 párrafos]

### Temas tratados
1. [Tema 1] - [Resumen]
2. [Tema 2] - [Resumen]

### Acuerdos y compromisos
| # | Acuerdo/Compromiso | Responsable | Fecha compromiso |
|---|-------------------|-------------|------------------|
| 1 | ...               | ...         | ...              |

### Decisiones tomadas
- [Decisión 1]

### Próximos pasos
- [Paso 1] - [Responsable]

### Riesgos o bloqueos mencionados
- [Riesgo 1]
```

### Criterios de aceptación
- [ ] Acepta transcripción como texto pegado, archivo .txt, .docx o .srt (subtítulos)
- [ ] Procesa transcripciones de hasta 2 horas (~15,000 palabras) con chunking automático
- [ ] Genera minuta en el formato estructurado definido arriba
- [ ] La minuta generada es **completamente editable** antes de guardar
- [ ] Detecta automáticamente: participantes, temas, acuerdos, fechas mencionadas
- [ ] Genera la minuta en español por defecto (configurable a inglés)
- [ ] Usa modelo local (Ollama) por defecto, con fallback configurable a Claude API
- [ ] Indicador de progreso mientras la IA procesa
- [ ] Tiempo de generación < 60 segundos para transcripción de 1 hora (modelo local)
- [ ] La minuta generada se vincula al proyecto seleccionado
- [ ] Se registra en log: modelo usado, tokens procesados, tiempo de generación

### Casos de prueba
| ID      | Escenario                                | Pasos                                                                  | Resultado esperado                                       |
|---------|------------------------------------------|------------------------------------------------------------------------|----------------------------------------------------------|
| TC-124  | Generar minuta desde texto pegado        | 1. "+ Nueva Minuta con IA" 2. Pegar transcripción 3. "Generar"         | Minuta estructurada generada, editable                   |
| TC-125  | Generar minuta desde archivo .txt        | 1. Subir archivo .txt con transcripción 2. "Generar"                   | Archivo procesado, minuta generada                       |
| TC-126  | Generar minuta desde .srt                | 1. Subir archivo de subtítulos .srt 2. "Generar"                       | Timestamps limpiados, minuta generada                    |
| TC-127  | Editar minuta antes de guardar           | 1. Generar minuta 2. Modificar acuerdos 3. Guardar                     | Minuta guardada con ediciones del usuario                |
| TC-128  | Transcripción muy larga (>15k palabras)  | 1. Pegar transcripción de 2+ horas 2. "Generar"                        | Chunking automático, minuta coherente                    |
| TC-129  | Modelo local no disponible               | 1. Ollama apagado 2. Intentar generar minuta                           | Fallback a Claude API (si configurado) o mensaje de error|
| TC-130  | Vinculación a proyecto                   | 1. Seleccionar proyecto 2. Generar y guardar minuta                    | Minuta aparece en módulo de minutas del proyecto         |
| TC-131  | Transcripción en inglés                  | 1. Pegar transcripción en inglés 2. Generar                            | Minuta generada en español (o idioma configurado)        |

### Defectos/Bugs
| ID      | Descripción | Severidad | Estado  | Relacionado a |
|---------|-------------|-----------|---------|---------------|
| —       | —           | —         | —       | —             |

---

## US-028: Reportes de avance automatizados por correo

**Épica:** EP-008
**Prioridad:** Alta
**Estimación:** XL

**Como** Project Manager
**Quiero** generar un reporte de avance del proyecto con un click, poder editarlo y enviarlo por correo
**Para** comunicar el estado del proyecto a stakeholders de forma rápida y consistente

### Flujo del usuario
1. En detalle de proyecto → Click "Generar Reporte de Avance"
2. La IA recopila datos del proyecto (avance, riesgos, incidencias, cambios, últimas minutas) y genera un borrador
3. El reporte se muestra en un **editor editable** (rich text)
4. El usuario revisa, modifica lo que necesite
5. Click "Enviar por correo"
6. Seleccionar destinatarios (de la lista de stakeholders del proyecto o escribir correos)
7. Se envía el correo con el reporte (HTML embebido + opción PDF adjunto)
8. El reporte se guarda en el historial del proyecto

### Formato del reporte
```
═══════════════════════════════════════════
REPORTE DE AVANCE - [Nombre del Proyecto]
Periodo: [Fecha desde] - [Fecha hasta]
Generado: [Fecha] | PM: [Nombre]
═══════════════════════════════════════════

■ RESUMEN EJECUTIVO
[Generado por IA: 2-3 párrafos con lo más relevante del periodo]

■ INDICADORES CLAVE
  Avance: [XX%] (Plan: [XX%]) [▲/▼]
  Presupuesto: $[X] de $[X] MXN
  Salud: [🟢/🟡/🔴]
  Riesgos abiertos: [X]
  Incidencias abiertas: [X]

■ LOGROS DEL PERIODO
  - [Generado desde tareas completadas y minutas]

■ PRÓXIMAS ACTIVIDADES
  - [Generado desde tareas planificadas]

■ RIESGOS PRINCIPALES
  | Riesgo | Severidad | Estrategia |
  [Datos del módulo de riesgos]

■ BLOQUEOS / ESCALACIONES
  - [Generado desde incidencias críticas]

■ OBSERVACIONES
  [Espacio para comentarios manuales del PM]
```

### Criterios de aceptación
- [ ] El reporte se genera con datos reales del proyecto (avance, presupuesto, riesgos, incidencias, minutas recientes)
- [ ] La IA sintetiza y redacta el resumen ejecutivo, logros y próximas actividades
- [ ] El reporte se muestra en un editor rich text completamente editable
- [ ] El usuario puede modificar cualquier sección antes de enviar
- [ ] Selección de destinatarios: desde equipo del proyecto, stakeholders, o correos manuales
- [ ] Envío por correo en formato HTML con diseño profesional
- [ ] Opción de adjuntar el reporte como PDF
- [ ] El reporte enviado se guarda en el historial del proyecto (con fecha y destinatarios)
- [ ] Se puede re-enviar o duplicar un reporte anterior como base
- [ ] Disponible en español e inglés

### Casos de prueba
| ID      | Escenario                                | Pasos                                                                     | Resultado esperado                                       |
|---------|------------------------------------------|---------------------------------------------------------------------------|----------------------------------------------------------|
| TC-132  | Generar reporte con datos completos      | 1. En proyecto con datos 2. "Generar Reporte" 3. Revisar                  | Reporte con datos reales del proyecto, resumen coherente |
| TC-133  | Editar reporte antes de enviar           | 1. Generar reporte 2. Modificar resumen ejecutivo 3. Guardar cambios      | Cambios reflejados en el reporte                         |
| TC-134  | Enviar reporte por correo                | 1. Generar reporte 2. Seleccionar destinatarios 3. "Enviar"              | Correo enviado, reporte guardado en historial            |
| TC-135  | Enviar con PDF adjunto                   | 1. Generar reporte 2. Activar "Adjuntar PDF" 3. Enviar                   | Correo con HTML + PDF adjunto                            |
| TC-136  | Proyecto sin datos suficientes           | 1. Proyecto nuevo sin riesgos ni minutas 2. "Generar Reporte"            | Reporte con secciones vacías marcadas como "Sin datos"   |
| TC-137  | Duplicar reporte anterior                | 1. Ir a historial 2. "Duplicar" un reporte pasado                        | Nuevo borrador con datos del reporte anterior            |
| TC-138  | Destinatarios múltiples                  | 1. Agregar 5 destinatarios 2. Enviar                                     | Correo enviado a todos los destinatarios                 |

### Defectos/Bugs
| ID      | Descripción | Severidad | Estado  | Relacionado a |
|---------|-------------|-----------|---------|---------------|
| —       | —           | —         | —       | —             |

---

## US-029: Configuración del motor de IA

**Épica:** EP-008
**Prioridad:** Media
**Estimación:** M

**Como** administrador del sistema
**Quiero** configurar qué motor de IA se usa (modelo local u API) y sus parámetros
**Para** controlar costos y rendimiento según la infraestructura disponible

### Criterios de aceptación
- [ ] Panel de configuración de IA en Administración
- [ ] Opciones: Ollama (local), Claude API, Deshabilitado
- [ ] Para Ollama: URL del servidor, modelo seleccionado, timeout
- [ ] Para Claude API: API key (enmascarada), modelo, max tokens
- [ ] Test de conexión: botón para verificar que el motor está accesible
- [ ] Indicador de estado del motor en el dashboard (online/offline)
- [ ] Parámetros: temperatura, max tokens de respuesta, idioma de salida

### Casos de prueba
| ID      | Escenario                        | Pasos                                                          | Resultado esperado                                    |
|---------|----------------------------------|----------------------------------------------------------------|-------------------------------------------------------|
| TC-139  | Configurar Ollama                | 1. Admin > IA 2. Seleccionar "Ollama" 3. URL + modelo 4. Test | Conexión exitosa, modelo disponible                   |
| TC-140  | Configurar Claude API            | 1. Seleccionar "Claude API" 2. Ingresar API key 3. Test       | Conexión exitosa                                      |
| TC-141  | Motor offline                    | 1. Configurar Ollama con URL incorrecta 2. Test               | Error: "No se puede conectar al motor de IA"          |
| TC-142  | Cambiar de motor                 | 1. Cambiar de Ollama a Claude API 2. Generar minuta            | Minuta generada con Claude API                        |

### Defectos/Bugs
| ID      | Descripción | Severidad | Estado  | Relacionado a |
|---------|-------------|-----------|---------|---------------|
| —       | —           | —         | —       | —             |
