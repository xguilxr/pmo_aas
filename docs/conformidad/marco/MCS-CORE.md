---
tipo: marco
id: MCS-CORE
titulo: Marco de Calidad de Software — Documento normativo
marco: MCS
capa: normativa
version: 2.0.0
estado: vigente
reemplazado_por: null
idioma: es
responsable: propietario
revisado: 2026-08-02
revisar_cada: 90d
uso: recurrente
depende_de: [INDICE, CONVENCIONES, glosario]
---

> **Nota de incorporación al repositorio — 2026-08-05.** Este documento se
> auditó tres veces (`2026-08-03-mcs.md`, `2026-08-04-mcs.md`,
> `2026-08-04-mcs-r1.md`) **sin estar versionado aquí**: vivía en el entorno de
> quien corría `MCS-P01`. Su ausencia obligó a reconstruir el registro desde los
> informes y dejó dos requisitos —`DAT-08` y `DAT-16`— sin poder medirse, porque
> no se sabía qué exigían.
>
> Se incorpora sin modificar una coma. El propio §5.2.2 lo pedía: «Documentación
> — todos los documentos» son elementos de configuración, y `CFG-01` exige que
> residan en el repositorio.
>
> **Se detectó una inconsistencia aritmética en el Anexo A**, anotada al pie del
> propio anexo. No se corrige el texto: un documento normativo se reemplaza, no
> se edita en silencio (`DOC-08`, `CFG-18`).

# MCS — Marco de Calidad de Software

**Documento normativo**

---

# 0. Control del documento

## 0.1 Identificación

| Campo | Valor |
|---|---|
| Identificador | MCS-CORE |
| Título | Marco de Calidad de Software — Documento normativo |
| Versión | 2.0.0 |
| Estado | Vigente |
| Fecha de emisión | 2026-08-02 |
| Fecha de próxima revisión | 2026-11-02 |
| Periodicidad de revisión | Trimestral |
| Responsable del documento | Propietario del marco |
| Clasificación | Interno |
| Idioma original | Español (es-ES) |
| Reemplaza a | — |
| Reemplazado por | — |

## 0.2 Historial de versiones

| Versión | Fecha | Autor | Naturaleza del cambio |
|---|---|---|---|
| 0.1.0 | 2026-08-02 | Propietario | Borrador inicial: ciclo de vida en 12 fases |
| 0.2.0 | 2026-08-02 | Propietario | Incorporación de los tracks de diseño (D) e IA (A) |
| 0.3.0 | 2026-08-02 | Propietario | Incorporación de disciplinas transversales (L, M, E, K) |
| 1.0.0 | 2026-08-02 | Propietario | Conversión a documento normativo. Requisitos numerados, modelo de conformidad de cinco niveles, incorporación del dominio CFG (gestión de configuración) |
| 2.0.0 | 2026-08-02 | Propietario | Incorporación del dominio CON (conocimiento del dominio): competencia experta como artefacto versionado, jerarquía de autoridad, jurisdicción y vigencia, frontera de competencia y validación por experto. Incremento mayor conforme a 0.2 por adición de requisitos |

**Regla de versionado de este documento:** se aplica SemVer.
- **MAYOR** — se añade, elimina o endurece un requisito, o cambia la asignación de nivel de un requisito existente
- **MENOR** — se añade una guía, ejemplo o anexo sin alterar requisitos
- **PARCHE** — corrección de redacción, erratas o enlaces

## 0.3 Documentos relacionados

Este documento es **normativo**: establece qué se exige. Los siguientes documentos son **guías de aplicación**: explican cómo cumplirlo. En caso de conflicto, prevalece este documento.

| ID | Documento | Naturaleza |
|---|---|---|
| MCS-CORE | Este documento | Normativo |
| MCS-G01 | Framework de Calidad de Software — Ciclo de vida completo | Guía |
| MCS-G02 | Track de Diseño — UI/UX | Guía |
| MCS-G03 | Track de IA — Agentes | Guía |
| MCS-G04 | Disciplinas transversales — L, M, E, K | Guía |

## 0.4 Convenciones de lenguaje normativo

Este documento sigue las convenciones de RFC 2119 y de las Directivas ISO/IEC Parte 2:

| Término | Significado |
|---|---|
| **DEBE** | Requisito obligatorio en el nivel indicado. Su incumplimiento constituye no conformidad |
| **NO DEBE** | Prohibición absoluta en el nivel indicado |
| **DEBERÍA** | Recomendación. Puede omitirse si existe justificación documentada en un ADR |
| **PUEDE** | Permiso. Su presencia o ausencia no afecta la conformidad |

## 0.5 Estructura de los identificadores de requisito

```
CFG-04
 │   └── Número secuencial dentro del dominio
 └────── Código de dominio (tres letras)
```

Los identificadores son **inmutables**. Un requisito retirado conserva su número, marcado como *Retirado*, y su número no se reutiliza.

---

# 1. Objeto y campo de aplicación

## 1.1 Objeto

Este documento establece los requisitos de calidad aplicables al ciclo de vida completo de productos de software desarrollados bajo el marco MCS, desde la concepción hasta la operación y retirada.

## 1.2 Campo de aplicación

Aplica a todo producto de software desarrollado o mantenido bajo este marco, incluyendo aplicaciones web, interfaces de programación, componentes de inteligencia artificial e infraestructura asociada.

## 1.3 Exclusiones

Toda exclusión de un requisito aplicable al nivel declarado DEBE registrarse en un ADR que documente el requisito excluido, la justificación, el riesgo aceptado y la fecha de revisión de la exclusión.

---

# 2. Referencias normativas

| Referencia | Título abreviado | Dominios |
|---|---|---|
| ISO/IEC 25010 | Modelo de calidad de producto | REQ, ARQ, DIS |
| ISO/IEC 25012 | Modelo de calidad de datos | DAT |
| ISO/IEC/IEEE 12207 | Procesos del ciclo de vida del software | GOB |
| ISO/IEC/IEEE 29148 | Ingeniería de requisitos | REQ |
| ISO/IEC/IEEE 42010 | Descripción de arquitectura | ARQ |
| ISO/IEC/IEEE 29119 | Pruebas de software | DEV |
| **ISO 10007** | **Gestión de la configuración** | **CFG** |
| **ISO/IEC/IEEE 828** | **Gestión de configuración en ingeniería de software** | **CFG** |
| ISO 24495-1 | Lenguaje claro | LEN |
| ISO 704 / 1087 / 30042 | Terminología | LEN |
| ISO 9241-210 / 9241-110 | Diseño centrado en el humano | DIS |
| WCAG 2.2 nivel AA | Accesibilidad | DIS |
| ISO/IEC 27001 | Gestión de seguridad de la información | SEG |
| ISO/IEC 42001 | Gestión de sistemas de inteligencia artificial | IA |
| NIST SP 800-218 (SSDF) | Desarrollo seguro | SEG |
| NIST AI RMF | Gestión de riesgos de IA | IA |
| OWASP ASVS | Verificación de seguridad de aplicaciones | SEG |
| OWASP Top 10 for LLM | Riesgos en aplicaciones de LLM | IA |
| SLSA | Integridad de la cadena de suministro | SUM |
| SemVer 2.0.0 | Versionado semántico | CFG |
| Conventional Commits 1.0.0 | Convención de mensajes de commit | CFG |
| ASD-STE100 | Inglés técnico simplificado | LEN |
| Diátaxis | Estructura de documentación técnica | DOC |

---

# 3. Términos y definiciones

**3.1 elemento de configuración.** Artefacto sujeto a control de versiones e identificación única, cuya modificación afecta al comportamiento o a la comprensión del producto.

**3.2 línea base.** Conjunto de elementos de configuración en un estado formalmente revisado, que sirve de referencia para el desarrollo posterior y que solo se altera mediante un procedimiento de control de cambios.

**3.3 escenario de calidad.** Especificación verificable de un atributo de calidad, expresada como estímulo, contexto, respuesta y medida de respuesta.

**3.4 deriva conceptual.** Situación en la que un mismo concepto de dominio recibe nombres, unidades o definiciones distintas en partes diferentes del sistema, sin que ello produzca un fallo detectable.

**3.5 nivel de conformidad.** Grado de cumplimiento del marco, expresado en la escala N1 a N5 definida en el capítulo 4.

**3.6 puerta de calidad.** Conjunto de verificaciones automáticas cuyo resultado condiciona la progresión de un cambio hacia producción.

**3.7 flujo de trabajo (workflow).** Secuencia de pasos predefinida en código, en la que un modelo de lenguaje ejecuta pasos concretos sin decidir el orden.

**3.8 agente.** Sistema en el que un modelo de lenguaje determina dinámicamente qué acciones ejecutar y en qué orden, mediante un bucle con herramientas.

**3.9 requisito aplicable.** Requisito cuyo nivel mínimo es igual o inferior al nivel de conformidad declarado por el producto.

**3.10 corpus de dominio.** Conjunto versionado de elementos de conocimiento especializado que sustentan la competencia del sistema en una materia, cada uno con fuente, nivel de autoridad, jurisdicción y periodo de vigencia declarados.

**3.11 frontera de competencia.** Límite declarado más allá del cual el sistema no emite juicio propio y deriva a una persona profesional cualificada, por tratarse de actividad regulada o de consecuencia jurídica, fiscal, financiera o sanitaria.

**3.12 cifra viva.** Valor numérico cuya vigencia depende del momento de consulta, tal como un tipo de referencia, un precio de mercado o un índice. Una cifra viva no constituye conocimiento estable y no forma parte del corpus.

---

# 4. Modelo de niveles de conformidad

## 4.1 Escala

| Nivel | Denominación | Perfil de aplicación |
|---|---|---|
| **N1** | Fundacional (MVP) | Producto en validación. Un solo desarrollador. Objetivo: que sea sólido, no que sea completo |
| **N2** | Profesional | Producto comercial en operación. Clientes de pequeña y mediana empresa. Ingresos dependientes del servicio |
| **N3** | Escalable | Múltiples clientes con expectativas contractuales. Equipo reducido. Compromisos de disponibilidad explícitos |
| **N4** | Auditable | Clientes que exigen evidencia formal. Preparación o mantenimiento de certificaciones. Datos sensibles o regulados |
| **N5** | Corporativo | Gobernanza formal, segregación de funciones, control de cambios con aprobación, certificación acreditada |

## 4.2 Reglas de conformidad

**4.2.1** Un producto es conforme al nivel N cuando cumple **todos** los requisitos marcados como DEBE en el nivel N y en todos los niveles inferiores.

**4.2.2** Los niveles son acumulativos. No existe conformidad parcial: un producto que cumple el 90% de N2 es conforme a N1, no a N2.

**4.2.3** El nivel se declara por producto, no por organización. Productos distintos de un mismo propietario pueden declarar niveles distintos.

**4.2.4** El nivel declarado DEBE registrarse en el repositorio del producto y revisarse al menos trimestralmente.

**4.2.5** Un requisito con nivel mínimo N2 es DEBERÍA en N1, salvo indicación expresa en contrario.

## 4.3 Advertencia sobre la selección de nivel

Un nivel superior no es mejor: es más caro. **N5 aplicado a un producto en validación destruye la capacidad de iterar** y consume recursos que el producto necesita para encontrar su mercado. Del mismo modo, N1 aplicado a un producto que gestiona datos regulados constituye una exposición inaceptable.

La selección del nivel DEBE justificarse en función de: consecuencia del fallo, sensibilidad de los datos tratados, exigencias contractuales de los clientes, tamaño del equipo y expectativa de vida del producto.

---

# 5. Requisitos

## 5.1 GOB — Gobierno del ciclo de vida

| ID | Requisito | Nivel |
|---|---|---|
| GOB-01 | El producto DEBE declarar su nivel de conformidad MCS en un archivo versionado en la raíz del repositorio | N1 |
| GOB-02 | Toda exclusión de un requisito aplicable DEBE registrarse en un ADR con justificación, riesgo aceptado y fecha de revisión | N1 |
| GOB-03 | El nivel de conformidad DEBE revisarse trimestralmente y el resultado registrarse | N2 |
| GOB-04 | El producto DEBE identificar un responsable único por cada dominio de requisitos | N3 |
| GOB-05 | DEBE existir un procedimiento documentado de revisión y aprobación de cambios al propio marco | N4 |
| GOB-06 | Las funciones de desarrollo, aprobación de cambio y despliegue a producción DEBEN estar segregadas | N5 |
| GOB-07 | DEBE conservarse evidencia auditable de cada revisión de conformidad durante al menos tres años | N5 |

---

## 5.2 CFG — Gestión de configuración y control de versiones

> **Referencias:** ISO 10007, ISO/IEC/IEEE 828, SemVer 2.0.0, Conventional Commits 1.0.0

### 5.2.1 Principio

Todo lo que determina el comportamiento o la comprensión del producto es un elemento de configuración y DEBE estar bajo control de versiones. La distinción entre "código" y "todo lo demás" es artificial y es el origen de la mayoría de las divergencias entre entornos.

### 5.2.2 Elementos de configuración

Los siguientes artefactos DEBEN estar bajo control de versiones desde N1:

| Categoría | Elementos |
|---|---|
| Código | Fuente, pruebas, scripts |
| Configuración | Plantillas de entorno, parámetros, definiciones de servicio |
| Infraestructura | Definiciones de infraestructura como código, manifiestos de despliegue |
| Datos | Migraciones de esquema, fichas de métrica, datos semilla |
| Diseño | Tokens de diseño, definiciones de componente |
| Lenguaje | Glosario canónico, reglas de estilo, cadenas de internacionalización |
| Inteligencia artificial | Prompts, definiciones de herramientas, skills, conjuntos de evaluación |
| Documentación | Todos los documentos, incluidos los generados y sus generadores |
| Dependencias | Archivo de bloqueo con versiones exactas |

**NO DEBEN estar bajo control de versiones:** secretos, credenciales, certificados privados ni datos personales reales.

### 5.2.3 Requisitos

| ID | Requisito | Nivel |
|---|---|---|
| CFG-01 | Todo elemento de configuración enumerado en 5.2.2 DEBE residir en el repositorio | N1 |
| CFG-02 | El repositorio NO DEBE contener secretos. La ausencia DEBE verificarse automáticamente sobre el historial completo | N1 |
| CFG-03 | La rama principal DEBE estar protegida: sin escritura directa, con integración mediante solicitud de cambio y verificación automática superada | N1 |
| CFG-04 | Los mensajes de commit DEBEN seguir Conventional Commits | N1 |
| CFG-05 | Las dependencias DEBEN fijarse mediante archivo de bloqueo determinista, versionado y usado en modo estricto durante la construcción | N1 |
| CFG-06 | El producto DEBE aplicar SemVer 2.0.0 a su versión pública | N1 |
| CFG-07 | Toda entrega a producción DEBE corresponder a una etiqueta inmutable, trazable a un identificador de commit único | N2 |
| CFG-08 | DEBE mantenerse un registro de cambios generado a partir de los mensajes de commit | N2 |
| CFG-09 | Las ramas de trabajo DEBERÍAN tener una vida inferior a dos días. La funcionalidad incompleta DEBE ocultarse mediante indicadores de funcionalidad, no mediante ramas de larga duración | N2 |
| CFG-10 | El contrato público de la interfaz de programación DEBE estar versionado explícitamente, con política documentada de compatibilidad y de retirada | N2 |
| CFG-11 | Las migraciones de esquema DEBEN ser reversibles y compatibles hacia atrás, aplicando el patrón de expansión y contracción en despliegues separados | N2 |
| CFG-12 | Los prompts, definiciones de herramientas y skills DEBEN versionarse en el repositorio y desplegarse con la aplicación. NO DEBEN editarse en consolas externas sin control de versiones | N2 |
| CFG-13 | Las fichas de métrica DEBEN llevar número de versión y referencia explícita a la versión que reemplazan | N2 |
| CFG-14 | Los tokens de diseño DEBEN versionarse y su cambio DEBE seguir el mismo procedimiento que un cambio de código | N2 |
| CFG-15 | DEBE existir trazabilidad completa y consultable en la cadena: incidencia → solicitud de cambio → commit → artefacto → despliegue | N3 |
| CFG-16 | Los artefactos de construcción DEBEN identificarse por resumen criptográfico, no por etiqueta mutable | N3 |
| CFG-17 | DEBE definirse una línea base en cada entrega, con inventario de las versiones exactas de todos los elementos de configuración que la componen | N3 |
| CFG-18 | Los documentos normativos y los ADR DEBEN versionarse mediante reemplazo bidireccional, nunca mediante edición silenciosa | N3 |
| CFG-19 | Todo cambio en producción DEBE contar con aprobación registrada de una persona distinta de su autor | N4 |
| CFG-20 | DEBE mantenerse una política documentada de soporte de versiones, con ramas de mantenimiento para las versiones vigentes | N4 |
| CFG-21 | DEBE realizarse una auditoría de configuración periódica que verifique la correspondencia entre la línea base declarada y el contenido real de producción | N4 |
| CFG-22 | DEBE existir un comité o procedimiento formal de control de cambios para modificaciones que afecten a interfaces públicas, esquemas de datos o controles de seguridad | N5 |
| CFG-23 | Los registros de configuración DEBEN conservarse durante el periodo exigido por las obligaciones contractuales o regulatorias aplicables | N5 |

### 5.2.4 Política de versionado por tipo de artefacto

| Artefacto | Esquema | Regla de incremento mayor |
|---|---|---|
| Producto | SemVer | Cambio incompatible en la interfaz pública |
| Interfaz de programación | Versión en la ruta o en la cabecera | Retirada o cambio incompatible de un campo |
| Esquema de datos | Migración secuencial numerada | Migración no reversible |
| Ficha de métrica | Entero incremental | Cambio en fórmula, inclusiones o exclusiones |
| Prompt | SemVer | Cambio que altera el resultado de la evaluación |
| Skill | SemVer | Cambio en el procedimiento o en las herramientas invocadas |
| Tokens de diseño | SemVer | Retirada o cambio semántico de un token |
| Glosario | Entero incremental por término | Cambio de definición o de término preferente |
| Documento | SemVer | Cambio de requisitos o de conclusiones |

---

## 5.3 REQ — Requisitos y calidad de producto

| ID | Requisito | Nivel |
|---|---|---|
| REQ-01 | Todo requisito funcional DEBE tener criterio de aceptación verificable | N1 |
| REQ-02 | DEBEN definirse al menos cuatro escenarios de calidad con medida de respuesta numérica | N1 |
| REQ-03 | DEBE identificarse el inventario de datos personales tratados por el sistema | N1 |
| REQ-04 | Los criterios de aceptación DEBEN estar trazados a las pruebas que los verifican | N2 |
| REQ-05 | Los escenarios de calidad DEBEN revisarse en cada entrega mayor | N3 |
| REQ-06 | DEBE existir trazabilidad bidireccional entre requisito, diseño, código y prueba | N4 |
| REQ-07 | Los requisitos DEBEN someterse a aprobación formal y registrada antes de su implementación | N5 |

---

## 5.4 ARQ — Arquitectura

| ID | Requisito | Nivel |
|---|---|---|
| ARQ-01 | DEBEN existir diagramas de contexto y de contenedores versionados | N1 |
| ARQ-02 | Toda decisión irreversible DEBE registrarse en un ADR | N1 |
| ARQ-03 | La lógica de dominio NO DEBE depender del framework web ni del mecanismo de persistencia | N1 |
| ARQ-04 | El producto DEBE cumplir los doce factores: configuración en el entorno, procesos sin estado, registros a la salida estándar | N1 |
| ARQ-05 | Cada escenario de calidad DEBE estar respaldado por una decisión arquitectónica documentada | N2 |
| ARQ-06 | Los ADR DEBEN registrar las opciones consideradas y descartadas, no solo la decisión adoptada | N2 |
| ARQ-07 | La arquitectura DEBE revisarse formalmente contra los escenarios de calidad al menos anualmente | N4 |
| ARQ-08 | Los cambios arquitectónicos DEBEN someterse a revisión por una persona distinta de su autor | N4 |

---

## 5.5 DIS — Diseño e interacción

| ID | Requisito | Nivel |
|---|---|---|
| DIS-01 | Los valores visuales DEBEN expresarse como tokens. NO DEBEN existir valores literales de color ni de espaciado en el código de componentes | N1 |
| DIS-02 | Toda combinación semántica de texto y fondo DEBE alcanzar la relación de contraste exigida por WCAG 2.2 nivel AA | N1 |
| DIS-03 | Toda pantalla DEBE definir sus estados: vacío, en carga, con datos, error y sin permiso | N1 |
| DIS-04 | Toda acción destructiva DEBE nombrar el objeto afectado y su consecuencia, y ofrecer confirmación o reversión | N1 |
| DIS-05 | La aplicación DEBE ser operable en su totalidad mediante teclado, con indicador de foco visible | N2 |
| DIS-06 | Los componentes interactivos DEBEN seguir el patrón correspondiente de las guías de autoría WAI-ARIA. NO DEBEN reimplementarse primitivas de accesibilidad desde cero | N2 |
| DIS-07 | La verificación automática de accesibilidad DEBE ejecutarse en la integración continua sin violaciones críticas ni serias | N2 |
| DIS-08 | Los flujos críticos DEBEN verificarse manualmente con lector de pantalla | N3 |
| DIS-09 | DEBE aplicarse verificación de regresión visual sobre los componentes del sistema de diseño | N3 |
| DIS-10 | DEBE publicarse una declaración de accesibilidad | N4 |
| DIS-11 | DEBE realizarse una auditoría de accesibilidad por tercero independiente | N5 |

---

## 5.6 LEN — Lenguaje y terminología

| ID | Requisito | Nivel |
|---|---|---|
| LEN-01 | DEBE existir un glosario canónico versionado, con término en español, término en inglés, definición y términos prohibidos, cubriendo los conceptos centrales del dominio | N1 |
| LEN-02 | Todo mensaje de error DEBE indicar qué ocurrió, por qué y qué acción tomar | N1 |
| LEN-03 | DEBE existir una guía de estilo que fije el tratamiento personal, la política de anglicismos y el formato de números y fechas | N1 |
| LEN-04 | La verificación de terminología DEBE ejecutarse automáticamente sobre documentación, textos de interfaz y descripciones de herramientas de IA | N2 |
| LEN-05 | DEBE existir paridad completa de claves entre los idiomas soportados | N2 |
| LEN-06 | Los textos dirigidos a usuarios finales DEBERÍAN cumplir el umbral de legibilidad definido para cada idioma | N3 |
| LEN-07 | El glosario DEBE ser la fuente de la que se derivan los diccionarios de verificación, la ayuda de interfaz y la terminología del agente | N3 |
| LEN-08 | Los cambios terminológicos DEBEN seguir un procedimiento de aprobación y propagarse a todos los artefactos dependientes | N4 |

---

## 5.7 DAT — Datos, métricas y exactitud

### 5.7.1 Formulación en el código

| ID | Requisito | Nivel |
|---|---|---|
| DAT-01 | Cada magnitud del dominio DEBE tener una unidad canónica declarada en el glosario | N1 |
| DAT-02 | Todo identificador numérico DEBE expresar su unidad en el nombre o en su tipo | N1 |
| DAT-03 | Los importes monetarios NO DEBEN representarse en coma flotante | N1 |
| DAT-04 | La conversión de unidades DEBE ocurrir únicamente en fronteras explícitas y nombradas, nunca en la lógica de dominio | N1 |
| DAT-05 | Un concepto derivado del dominio NO DEBE formularse más de una vez. Su definición DEBE residir en el dominio y ser invocada por todos los consumidores | N1 |
| DAT-06 | NO DEBEN emplearse sinónimos ni adjetivos acumulados para designar un mismo concepto | N1 |
| DAT-07 | Los valores con unidad, rango o regla de combinación DEBERÍAN representarse como tipos propios, verificados estáticamente | N2 |
| DAT-08 | Las constantes numéricas de conversión NO DEBEN aparecer dispersas en el código | N2 |

### 5.7.2 Métricas y presentación

| ID | Requisito | Nivel |
|---|---|---|
| DAT-09 | Cada indicador DEBE definirse una sola vez en el código. NO DEBE reimplementarse por consumidor | N1 |
| DAT-10 | Cada indicador DEBE disponer de ficha versionada con fórmula, grano, inclusiones, exclusiones, zona horaria, tratamiento de nulos y responsable | N1 |
| DAT-11 | Todo número presentado DEBE indicar su periodo y su marca de actualización | N1 |
| DAT-12 | La ausencia de dato DEBE distinguirse visualmente del valor cero | N1 |
| DAT-13 | Cada indicador crítico DEBE contar con una prueba de reconciliación contra un cálculo independiente, ejecutada de forma programada sobre datos reales | N2 |
| DAT-14 | DEBEN ejecutarse pruebas de datos de estructura, frescura y volumen de forma programada | N2 |
| DAT-15 | Todo número presentado DEBE ofrecer acceso a su definición y camino al detalle que lo compone | N2 |
| DAT-16 | Los datos incompletos o de periodo en curso DEBEN señalarse explícitamente | N2 |
| DAT-17 | DEBE detectarse y notificarse la variación anómala de indicadores respecto a su comportamiento esperado | N3 |
| DAT-18 | DEBE documentarse el linaje de cada indicador desde su origen hasta su presentación | N4 |
| DAT-19 | Los cambios en la definición de un indicador DEBEN aprobarse formalmente y comunicarse a los consumidores afectados | N4 |

---

## 5.8 DEV — Desarrollo y verificación

| ID | Requisito | Nivel |
|---|---|---|
| DEV-01 | DEBE existir una definición de terminado documentada y aplicada | N1 |
| DEV-02 | La lógica de dominio DEBE ser verificable sin acceso a base de datos | N1 |
| DEV-03 | DEBEN existir pruebas automatizadas separadas por nivel: unitarias, de integración y de extremo a extremo | N1 |
| DEV-04 | El análisis estático y la verificación de tipos DEBEN ejecutarse en modo estricto | N1 |
| DEV-05 | La cobertura de la lógica de dominio DEBE alcanzar el umbral declarado y no disminuir entre entregas | N2 |
| DEV-06 | Los criterios de aceptación DEBEN estar cubiertos por pruebas automatizadas | N2 |
| DEV-07 | Los contratos de interfaz de programación DEBEN verificarse automáticamente contra su especificación | N3 |
| DEV-08 | Toda solicitud de cambio DEBE ser revisada por una persona distinta de su autor | N3 |
| DEV-09 | DEBE mantenerse evidencia de la ejecución de pruebas asociada a cada entrega | N4 |
| DEV-10 | Las pruebas DEBEN estar trazadas a los requisitos que verifican | N4 |

---

## 5.9 INT — Integración continua

| ID | Requisito | Nivel |
|---|---|---|
| INT-01 | DEBE existir una canalización automática que ejecute verificación de estilo, tipos y pruebas en cada solicitud de cambio | N1 |
| INT-02 | DEBEN ejecutarse análisis estático de seguridad, análisis de dependencias vulnerables y detección de secretos | N1 |
| INT-03 | La integración NO DEBE permitirse con verificaciones en estado de fallo | N1 |
| INT-04 | La canalización DEBERÍA completarse en menos de diez minutos | N2 |
| INT-05 | Los hallazgos de severidad alta DEBEN impedir la integración | N2 |
| INT-06 | DEBE existir actualización automatizada de dependencias con verificación previa | N2 |
| INT-07 | DEBE ejecutarse análisis dinámico de seguridad contra un entorno desplegado | N3 |
| INT-08 | Los resultados de las verificaciones DEBEN conservarse como evidencia asociada a la línea base | N4 |

---

## 5.10 SUM — Cadena de suministro

| ID | Requisito | Nivel |
|---|---|---|
| SUM-01 | Los artefactos desplegados DEBEN construirse exclusivamente en la canalización automática, nunca en equipos locales | N1 |
| SUM-02 | Las imágenes de contenedor DEBEN ejecutarse con usuario sin privilegios | N1 |
| SUM-03 | DEBE generarse un inventario de componentes de software en cada construcción y conservarse como artefacto | N2 |
| SUM-04 | Las imágenes DEBEN analizarse en busca de vulnerabilidades conocidas antes de su publicación. Los hallazgos críticos DEBEN impedir la publicación | N2 |
| SUM-05 | Los artefactos DEBEN acompañarse de una declaración de procedencia firmada | N3 |
| SUM-06 | Los artefactos DEBEN firmarse criptográficamente y su firma DEBE verificarse antes del despliegue | N4 |
| SUM-07 | La construcción DEBE ejecutarse en entornos efímeros y aislados, sin credenciales de larga duración | N4 |
| SUM-08 | El inventario de componentes DEBE ponerse a disposición de los clientes que lo requieran | N5 |

---

## 5.11 INF — Infraestructura y entornos

| ID | Requisito | Nivel |
|---|---|---|
| INF-01 | La configuración del entorno DEBE residir en el repositorio | N1 |
| INF-02 | DEBEN existir entornos separados para desarrollo y producción, con paridad en las versiones de los servicios de datos | N1 |
| INF-03 | DEBEN existir copias de seguridad automáticas | N1 |
| INF-04 | DEBE existir un entorno de preproducción donde se ensayen los cambios y las migraciones | N2 |
| INF-05 | La restauración de copias de seguridad DEBE probarse y cronometrarse periódicamente | N2 |
| INF-06 | Los objetivos de punto y de tiempo de recuperación DEBEN declararse explícitamente | N2 |
| INF-07 | Los recursos de infraestructura ajenos a la plataforma de despliegue DEBEN definirse como código | N3 |
| INF-08 | Todo recurso configurado manualmente DEBE documentarse en un ADR | N3 |
| INF-09 | Los datos en entornos distintos de producción DEBEN estar anonimizados | N3 |
| INF-10 | El plan de continuidad DEBE documentarse y ejercitarse anualmente | N4 |
| INF-11 | El acceso a producción DEBE ser nominal, temporal y registrado | N4 |
| INF-12 | La infraestructura DEBE ser reconstruible en su totalidad desde el repositorio, sin intervención manual | N5 |

---

## 5.12 DES — Despliegue

| ID | Requisito | Nivel |
|---|---|---|
| DES-01 | El despliegue DEBE ser automatizado y reproducible | N1 |
| DES-02 | DEBE existir un procedimiento de reversión documentado y ejecutable | N1 |
| DES-03 | Las verificaciones de salud DEBEN condicionar la aceptación de un despliegue | N1 |
| DES-04 | La reversión DEBE completarse en menos de cinco minutos | N2 |
| DES-05 | Las migraciones de datos DEBEN desplegarse de forma separada del código | N2 |
| DES-06 | Las métricas de rendimiento de entrega DEBEN registrarse y revisarse | N2 |
| DES-07 | La funcionalidad DEBE poder desactivarse sin redespliegue mediante indicadores de funcionalidad | N3 |
| DES-08 | El despliegue DEBERÍA ser progresivo, con observación de la tasa de error antes de completarse | N3 |
| DES-09 | Los despliegues a producción DEBEN contar con aprobación registrada | N4 |
| DES-10 | DEBE existir una ventana de cambio definida y un procedimiento de cambio de emergencia | N5 |

---

## 5.13 OPS — Operación y fiabilidad

| ID | Requisito | Nivel |
|---|---|---|
| OPS-01 | Los registros DEBEN ser estructurados y emitirse a la salida estándar | N1 |
| OPS-02 | DEBE existir captura y notificación automática de errores en producción | N1 |
| OPS-03 | DEBE existir un runbook con los procedimientos de respuesta a los fallos más probables | N1 |
| OPS-04 | La instrumentación DEBE emplear un estándar abierto y neutral respecto al proveedor | N2 |
| OPS-05 | DEBEN definirse al menos dos objetivos de nivel de servicio con indicador, umbral y ventana | N2 |
| OPS-06 | Las alertas DEBEN basarse en síntomas percibidos por el usuario, no en causas técnicas | N2 |
| OPS-07 | Los registros DEBEN correlacionarse mediante un identificador de petición propagado entre servicios | N2 |
| OPS-08 | DEBE existir trazado distribuido de extremo a extremo | N3 |
| OPS-09 | Todo incidente con impacto en usuarios DEBE producir un análisis posterior sin atribución de culpa, cuyas acciones correctivas se conviertan en controles automáticos | N3 |
| OPS-10 | El consumo del presupuesto de error DEBE gobernar la priorización entre funcionalidad y fiabilidad | N3 |
| OPS-11 | DEBE existir un procedimiento de guardia con tiempos de respuesta definidos | N4 |
| OPS-12 | Los objetivos de nivel de servicio DEBEN reflejarse en compromisos contractuales | N4 |
| OPS-13 | DEBEN ejercitarse periódicamente escenarios de fallo controlado | N5 |

---

## 5.14 SEG — Seguridad

| ID | Requisito | Nivel |
|---|---|---|
| SEG-01 | El producto DEBE cumplir los controles de OWASP ASVS nivel 1 aplicables | N1 |
| SEG-02 | Los secretos DEBEN gestionarse mediante un almacén dedicado, nunca en el repositorio | N1 |
| SEG-03 | El transporte DEBE estar cifrado y DEBEN aplicarse las cabeceras de seguridad correspondientes | N1 |
| SEG-04 | La autorización DEBE verificarse a nivel de objeto, no únicamente de punto de acceso | N1 |
| SEG-05 | DEBE publicarse una política de divulgación responsable | N1 |
| SEG-06 | DEBE existir un modelo de amenazas derivado de la arquitectura, revisado ante cambios significativos | N2 |
| SEG-07 | Las acciones sensibles DEBEN registrarse en un registro de auditoría no modificable | N2 |
| SEG-08 | En sistemas multiinquilino, el aislamiento entre inquilinos DEBE verificarse mediante pruebas automatizadas | N2 |
| SEG-09 | El producto DEBE cumplir los controles de OWASP ASVS nivel 2 aplicables | N3 |
| SEG-10 | Los datos en reposo DEBEN cifrarse | N3 |
| SEG-11 | DEBE existir un procedimiento documentado de respuesta a incidentes de seguridad | N3 |
| SEG-12 | DEBE realizarse una prueba de intrusión por tercero independiente con periodicidad definida | N4 |
| SEG-13 | Los accesos DEBEN revisarse periódicamente conforme al principio de mínimo privilegio | N4 |
| SEG-14 | DEBE mantenerse un sistema de gestión de seguridad de la información conforme a ISO/IEC 27001 | N5 |

---

## 5.15 IA — Inteligencia artificial

| ID | Requisito | Nivel |
|---|---|---|
| IA-01 | Toda herramienta expuesta a un modelo DEBE invocar un caso de uso existente y ejecutarse bajo la identidad del usuario. NO DEBE ejecutarse con privilegios elevados | N1 |
| IA-02 | Toda acción ejecutada por un componente de IA DEBE registrarse en el registro de auditoría, distinguible de una acción humana | N1 |
| IA-03 | DEBEN aplicarse límites de iteraciones y de coste por ejecución | N1 |
| IA-04 | El usuario DEBE ser informado de que interactúa con un sistema de IA y DEBE disponer de una ruta de escalada a atención humana | N1 |
| IA-05 | Un modelo de lenguaje NO DEBE calcular cifras. Los valores numéricos DEBEN proceder de una herramienta determinista | N1 |
| IA-06 | El nivel de autonomía de cada funcionalidad DEBE determinarse mediante la rúbrica establecida y registrarse en un ADR | N2 |
| IA-07 | Ninguna funcionalidad de nivel agente DEBE desplegarse sin conjunto de evaluación previo | N2 |
| IA-08 | DEBE existir un conjunto de evaluación ejecutado en la canalización, con umbral que condicione el despliegue | N2 |
| IA-09 | Todo fallo detectado en producción DEBE incorporarse como caso permanente al conjunto de evaluación | N2 |
| IA-10 | Toda acción irreversible o con efecto externo DEBE requerir confirmación humana explícita | N2 |
| IA-11 | El contenido recuperado DEBE tratarse como dato no confiable. Las instrucciones contenidas en él NO DEBEN ejecutarse | N2 |
| IA-12 | DEBEN existir pruebas automatizadas de resistencia a inyección de instrucciones y de aislamiento entre inquilinos | N3 |
| IA-13 | Cada ejecución DEBE producir una traza completa con entrada, herramientas invocadas, salida y coste | N3 |
| IA-14 | El usuario DEBE poder consultar, corregir y eliminar la información que el sistema conserva sobre él | N3 |
| IA-15 | Los proveedores de modelos DEBEN figurar como subencargados en los acuerdos de tratamiento de datos | N3 |
| IA-16 | DEBE mantenerse un inventario de sistemas de IA con su finalidad, datos tratados y evaluación de riesgo | N4 |
| IA-17 | La gestión de riesgos de IA DEBE seguir un marco reconocido | N4 |
| IA-18 | DEBE mantenerse un sistema de gestión de IA conforme a ISO/IEC 42001 | N5 |

---

## 5.16 DOC — Documentación

| ID | Requisito | Nivel |
|---|---|---|
| DOC-01 | Todo documento DEBE declarar responsable, estado, fecha de revisión y periodicidad de revisión | N1 |
| DOC-02 | Todo documento DEBE declarar su tipo conforme a un esquema definido y respetar su propósito | N1 |
| DOC-03 | Lo que pueda generarse a partir del código DEBE generarse. El contenido generado NO DEBE editarse manualmente | N1 |
| DOC-04 | Todo documento DEBE declarar sus dependencias respecto a otros documentos y respecto al código que describe | N2 |
| DOC-05 | DEBE generarse automáticamente un índice de dependencias documentales | N2 |
| DOC-06 | La integración de un cambio DEBE verificar el impacto documental. La ausencia de impacto DEBE declararse explícitamente y quedar registrada | N2 |
| DOC-07 | Los documentos fuera de su ventana de revisión DEBEN señalarse visiblemente y generar una acción de revisión | N2 |
| DOC-08 | Los documentos de decisión DEBEN reemplazarse, nunca editarse silenciosamente. La relación de reemplazo DEBE ser bidireccional | N3 |
| DOC-09 | Los indicadores de salud documental DEBEN registrarse y revisarse | N3 |
| DOC-10 | La documentación DEBE estar disponible en los idiomas exigidos por los destinatarios, con paridad de contenido | N4 |
| DOC-11 | Los documentos normativos DEBEN someterse a aprobación formal registrada antes de su entrada en vigor | N5 |

---

## 5.17 CON — Conocimiento del dominio

> **Aplicabilidad:** este dominio aplica a todo producto que emita afirmaciones, recomendaciones o análisis sobre una materia especializada, tanto si lo hace mediante componentes de inteligencia artificial como si lo hace mediante lógica determinista.

### 5.17.1 Principio

La competencia en una materia es un artefacto versionado con fuente, autoridad, jurisdicción, vigencia y responsable. NO DEBE implementarse mediante afirmaciones de rol en instrucciones de un modelo, que producen fluidez sin competencia y son indistinguibles de la competencia real para el usuario.

### 5.17.2 Requisitos

| ID | Requisito | Nivel |
|---|---|---|
| CON-01 | El producto DEBE declarar en documento versionado el alcance de su materia, las jurisdicciones cubiertas y su frontera de competencia | N1 |
| CON-02 | El conocimiento del dominio DEBE residir en artefactos versionados. NO DEBE implementarse únicamente mediante instrucciones de rol dirigidas a un modelo | N1 |
| CON-03 | Toda afirmación normativa DEBE declarar fuente, jurisdicción y periodo de vigencia | N1 |
| CON-04 | Las cifras vivas NO DEBEN residir en el corpus. DEBEN obtenerse en el momento de la consulta mediante una herramienta determinista | N1 |
| CON-05 | El sistema DEBE derivar a persona profesional cualificada toda consulta que exceda la frontera de competencia declarada | N1 |
| CON-06 | Cada elemento del corpus DEBE tener responsable identificado y periodicidad de revisión declarada | N2 |
| CON-07 | Cada afirmación del corpus DEBE clasificarse conforme a una jerarquía de autoridad, y el sistema DEBE reflejar ese nivel en su respuesta | N2 |
| CON-08 | El conjunto de evaluación del dominio DEBE ser construido o certificado por una persona experta en la materia, distinta de quien desarrolla | N2 |
| CON-09 | El conocimiento fuera de su periodo de vigencia DEBE bloquearse o señalarse. NO DEBE presentarse como vigente | N2 |
| CON-10 | La selección entre marcos, metodologías o instrumentos alternativos DEBE regirse por una rúbrica declarada y versionada, no por criterio no explicitado del modelo | N2 |
| CON-11 | El corpus DEBE incluir casos trabajados representativos, con razonamiento explícito, revisados por persona experta | N3 |
| CON-12 | Las respuestas fundamentadas en el corpus DEBEN citar la fuente y su fecha de vigencia | N3 |
| CON-13 | DEBE registrarse qué persona validó cada elemento del corpus y en qué fecha | N3 |
| CON-14 | Ante conflicto entre elementos de distinto nivel de autoridad, DEBE prevalecer el superior y el conflicto DEBE señalarse al usuario | N3 |
| CON-15 | El corpus DEBE someterse a revisión experta periódica, documentada y trazable | N4 |
| CON-16 | Los cambios normativos aplicables DEBEN vigilarse mediante un procedimiento definido, con actualización trazable del corpus y notificación a los usuarios afectados | N4 |
| CON-17 | La competencia del sistema en la materia DEBE evaluarse por tercero independiente cualificado | N5 |

### 5.17.3 Asignación del conocimiento por naturaleza

| Naturaleza | Ubicación exigida |
|---|---|
| Terminología del dominio | Glosario canónico (LEN-01) |
| Regla estable, compacta y siempre aplicable | Instrucciones base |
| Cuerpo extenso consultable por partes | Corpus recuperable |
| Procedimiento de varios pasos | Skill versionada (CFG-12) |
| Cifra viva | Herramienta determinista (CON-04, IA-05) |
| Criterio de elección entre alternativas | Rúbrica declarada (CON-10) |

---

# 6. Evaluación de conformidad

## 6.1 Estados de evaluación

| Estado | Definición |
|---|---|
| **Conforme** | Existe evidencia verificable del cumplimiento |
| **Parcial** | El requisito se cumple en parte del alcance, o sin control automático que lo sostenga |
| **No conforme** | No existe evidencia de cumplimiento |
| **No aplicable** | El requisito no aplica al producto, con justificación registrada |

## 6.2 Determinación del nivel alcanzado

El nivel alcanzado es el mayor nivel N tal que **todos** los requisitos DEBE de N y de los niveles inferiores se encuentran en estado Conforme o No aplicable.

Un requisito en estado Parcial impide alcanzar su nivel.

## 6.3 Periodicidad

| Nivel declarado | Periodicidad mínima de evaluación |
|---|---|
| N1 | Semestral |
| N2 | Trimestral |
| N3 | Trimestral |
| N4 | Trimestral, con evidencia conservada |
| N5 | Continua, con auditoría interna anual y externa según certificación |

## 6.4 Registro de conformidad

El resultado de cada evaluación DEBE registrarse en el repositorio del producto, con: fecha, versión del marco aplicada, nivel declarado, nivel alcanzado, relación de requisitos no conformes, plan de remediación y responsable.

---

# Anexo A — Distribución de requisitos por nivel

| Dominio | N1 | N2 | N3 | N4 | N5 | Total |
|---|---|---|---|---|---|---|
| GOB | 2 | 1 | 1 | 1 | 2 | 7 |
| CFG | 6 | 8 | 4 | 3 | 2 | 23 |
| REQ | 3 | 1 | 1 | 1 | 1 | 7 |
| ARQ | 4 | 2 | — | 2 | — | 8 |
| DIS | 4 | 3 | 2 | 1 | 1 | 11 |
| LEN | 3 | 2 | 2 | 1 | — | 8 |
| DAT | 6 | 8 | 2 | 2 | — | 19* |
| DEV | 4 | 2 | 2 | 2 | — | 10 |
| INT | 3 | 3 | 1 | 1 | — | 8 |
| SUM | 2 | 2 | 1 | 2 | 1 | 8 |
| INF | 3 | 3 | 3 | 2 | 1 | 12 |
| DES | 3 | 3 | 2 | 1 | 1 | 10 |
| OPS | 3 | 4 | 3 | 2 | 1 | 13 |
| SEG | 5 | 3 | 3 | 2 | 1 | 14 |
| IA | 5 | 6 | 4 | 2 | 1 | 18 |
| DOC | 3 | 4 | 2 | 1 | 1 | 11 |
| CON | 5 | 5 | 4 | 2 | 1 | 17 |
| **Total** | **64** | **60** | **37** | **28** | **14** | **203** |

\* DAT incluye los subgrupos 5.7.1 y 5.7.2.

**Lectura práctica:** alcanzar N1 exige 64 requisitos; alcanzar N2 exige 124 acumulados. El 61% del marco se concentra en los dos primeros niveles, que es donde reside también la mayor parte del valor. Los niveles N4 y N5 añaden 42 requisitos que son en su mayoría de evidencia, aprobación y conservación: necesarios para certificar, irrelevantes para construir bien.

> **Errata detectada al incorporar el documento — 2026-08-05.** La fila **DAT**
> de este anexo no concuerda con las tablas normativas de §5.7, que son las que
> mandan (§0.3: en caso de conflicto prevalece este documento, y el anexo es
> resumen del cuerpo, no al revés).
>
> Contando §5.7.1 y §5.7.2: DAT-01 a DAT-06 y DAT-09 a DAT-12 son N1 (**10**);
> DAT-07, DAT-08 y DAT-13 a DAT-16 son N2 (**6**); DAT-17 es N3 (**1**);
> DAT-18 y DAT-19 son N4 (**2**). Total 19, que sí cuadra con la columna. La
> fila dice 6 / 8 / 2 / 2, que suma 18 y contradice tanto el total como las
> tablas.
>
> El arrastre a los totales: **N1 son 68 y no 64; N2 son 58 y no 60.** La suma
> acumulada N1+N2 da **126**, que es exactamente el alcance que las tres
> auditorías midieron. La cifra de «124 acumulados» de la lectura práctica
> hereda el mismo error.
>
> No se corrige el texto del anexo: un documento normativo se reemplaza, no se
> edita en silencio (`DOC-08`, `CFG-18`). La corrección corresponde a una
> versión 2.0.1 emitida por el propietario del marco.

---

# Anexo B — Plantilla de declaración de conformidad

```yaml
# mcs.yaml — en la raíz del repositorio
marco:
  version: 1.0.0
producto:
  nombre: ""
  responsable: ""
conformidad:
  nivel_declarado: N2
  nivel_alcanzado: N1
  fecha_evaluacion: 2026-08-02
  proxima_evaluacion: 2026-11-02
no_conformidades:
  - requisito: DAT-13
    estado: no_conforme
    plan: "Prueba de reconciliación para MRR y ARPU"
    responsable: ""
    fecha_objetivo: 2026-09-15
exclusiones:
  - requisito: DIS-11
    justificacion: "Auditoría externa no exigible en N2"
    adr: adr-0021
    revisar: 2027-02-01
```

---

# Anexo C — Plantilla de ADR

```markdown
# ADR-NNNN: <Título en forma de decisión>

Fecha: AAAA-MM-DD
Estado: Propuesto | Aceptado | Reemplazado por ADR-NNNN
Reemplaza: ADR-NNNN | —
Requisitos MCS afectados: ARQ-02, CFG-10

## Contexto
<Situación, restricciones y escenarios de calidad implicados>

## Opciones consideradas
1. <Opción> — <ventajas> / <inconvenientes>
2. <Opción> — <ventajas> / <inconvenientes>

## Decisión
<Opción adoptada y razón determinante>

## Consecuencias
Positivas: <…>
Negativas: <…>
Requisitos que pasan a ser exigibles: <…>
```

---

**Fin del documento MCS-CORE v2.0.0**
