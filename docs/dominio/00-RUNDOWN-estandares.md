---
tipo: referencia
responsable: propietario
estado: vigente
revisado: 2026-08-12
revisar_cada: 90d
---

# Rundown — estándares y certificaciones de Project Management y PMO

| Campo | Valor |
|---|---|
| Propósito | Mapa del terreno para decidir **después**, con criterio, a qué normas apegarse |
| Estado | **Borrador para revisión.** No compromete a nada |
| Fecha | 2026-08-03 |
| Advertencia | Las ediciones y numeraciones cambian. Verificar la vigente antes de citar en material de cliente |

---

## 0. Lo primero, porque ahorra tiempo

**No existe una norma certificable de gestión de proyectos equivalente a ISO 9001.** Las
familias ISO 21500 son *guías*, no requisitos. No se auditan ni se certifican a nivel
organización. Sí se certifican **personas** (PMP, PRINCE2 Practitioner, IPMA). Por otra vía
se certifica la **madurez** de la organización, con modelos como P3M3.

Consecuencia práctica para el producto: no puedes decir «cumple ISO 21502». Sí puedes decir
algo más defendible: **«el modelo de datos y los indicadores siguen la terminología y las
fórmulas de X, y aquí está el mapeo»**. Es lo que pide un cliente con PMO madura.

---

## 1. Las cuatro familias

### 1.1 PMI — la más difundida en LatAm y EE. UU.

| Documento | Qué aporta |
|---|---|
| **PMBOK Guide 7ª ed.** (2021) | Reescritura completa: pasó de 10 Áreas de Conocimiento y 49 procesos a **12 principios + 8 dominios de desempeño**. Menos prescriptivo, más orientado a resultados |
| **PMBOK Guide 6ª ed.** (2017) | La estructura de procesos que todavía usa la mayoría de las PMO reales. Sigue siendo la referencia operativa de facto |
| *Process Groups: A Practice Guide* (2022) | PMI recuperó el contenido por procesos que la 7ª quitó |
| *Standard for Program Management* | Capa de programa |
| *Standard for Portfolio Management* | Capa de portafolio |
| *Practice Standard for WBS* · *for Scheduling* · *for EVM* | Los tres que más le tocan a un producto de PMO |

**Certificaciones:** CAPM (entrada), **PMP** (la que importa comercialmente), PgMP
(programa), PfMP (portafolio), PMI-RMP (riesgos), PMI-SP (cronograma), PMI-PBA (análisis de
negocio).

> **Nota sobre la 7ª edición.** El giro a principios la volvió más elegante y menos útil
> como fuente de definiciones. Si el objetivo es homogeneizar vocabulario y fórmulas, la
> 6ª edición y los *Practice Standards* dan más material concreto que la 7ª.

### 1.2 ISO — la más neutral, y la que mejor encaja con tu familia de marcos

| Norma | Objeto |
|---|---|
| **ISO 21500:2021** | Contexto y conceptos de proyecto, programa y portafolio |
| **ISO 21502:2020** | Guía de dirección de proyectos. **La operativa** |
| ISO 21503 | Programas |
| ISO 21504 | Portafolios |
| ISO 21505 | Gobernanza |
| **ISO 21506** | **Vocabulario.** Insumo directo del glosario |
| ISO 21508 | EVM en proyectos y programas |
| ISO 21511 | WBS para proyectos y programas |
| ISO 31000:2018 | Gestión del riesgo (transversal, no solo proyectos) |

**Por qué encaja con lo tuyo.** Tus marcos MCA/MCC/MCS ya son normativa por niveles con
requisitos verificables. ISO es la familia que habla ese mismo idioma —cláusulas,
vocabulario controlado, trazabilidad— y **ISO 21506 te regala media base del glosario**.

### 1.3 AXELOS / PeopleCert — la única con estándar dedicado a PMO

| Documento | Objeto |
|---|---|
| **P3O** | **Portfolio, Programme and Project Offices.** El único estándar dedicado a *la oficina*, que es exactamente lo que vendés. Modelos de oficina, funciones, servicios, dimensionamiento |
| **PRINCE2** (7ª ed., 2023) | Principios, prácticas y procesos. Muy fuerte en Europa y sector público |
| MSP | Programas, con foco en **beneficios** |
| MoP | Portafolios |
| M_o_R | Riesgo |
| **P3M3** | **Modelo de madurez**, 7 perspectivas × 5 niveles. Lo más cercano a «certificar» una PMO |

> **P3O y P3M3 son los dos que más deberías leer**, aunque no adoptes PRINCE2. P3O define
> qué *es* una PMO y qué servicios presta; P3M3 define cómo se mide su madurez. Tu producto
> vende ambas cosas.

### 1.4 IPMA — competencias, no procesos

**ICB 4.0** define 29 elementos de competencia en tres áreas: Perspectiva (5), Personas
(10), Práctica (14). Certifica personas por niveles A–D según responsabilidad, no por
examen de memoria. Relevante si algún día el producto evalúa **capacidad del equipo**;
poco relevante para el modelo de datos.

---

## 2. Estándares técnicos que le pegan directo a un producto de PMO

Estos importan más que la discusión PMI-vs-ISO, porque son **fórmulas verificables**, no
filosofía.

| Estándar | Qué te da | Aplicabilidad hoy |
|---|---|---|
| **ANSI/EIA-748** | 32 guías de un sistema EVM. Es el estándar de contratos públicos en EE. UU. | Alta, si algún día hacés EVM |
| **ISO 21508** | EVM, versión ISO | Alta |
| **DCMA 14-point** | 14 chequeos de **calidad de cronograma**: lógica faltante, holguras negativas, adelantos, restricciones duras, tareas huérfanas | **Muy alta. Ver §4** |
| **GAO Schedule Assessment Guide** | 10 buenas prácticas de cronograma confiable | Alta |
| **AACE 17R-97** | Clasificación de estimaciones en 5 clases por madurez y rango de exactitud | Media |
| **ISO 31000** | Vocabulario y proceso de riesgo | Alta: ya tenés `risks` |
| **PMI Practice Standard for WBS** / **ISO 21511** | Reglas de descomposición: regla del 100 %, paquetes de trabajo | Alta: ya tenés `wbs` y `outline_level` |

---

## 3. El núcleo homogeneizable — lo que conviene fijar aunque no elijas familia

Estos conceptos significan **lo mismo en las cuatro familias**. Fijarlos no te compromete
con ninguna y elimina la mayor parte de la ambigüedad actual.

| # | Concepto | Por qué es el que más duele si queda ambiguo |
|---|---|---|
| 1 | **Línea base** (*baseline*) | Sin ella no existe «desviación», «retraso» ni «sobrecosto». Todas las demás métricas cuelgan de esta |
| 2 | **Fases del ciclo de vida** | Hoy conviven dos vocabularios distintos. Ver `01-DIAGNOSTICO.md` |
| 3 | **Estado de salud (RAG)** | Un semáforo sin regla de derivación es una opinión con color |
| 4 | **Avance (% completado)** | ¿Por duración, por esfuerzo, por entregables, o declarado? Cuatro números distintos con el mismo nombre |
| 5 | **Hito** | ¿Duración cero obligatoria? ¿Es entregable o fecha? |
| 6 | **RAID** | Riesgo vs Incidencia es la confusión más común: **riesgo es futuro y probable; incidencia ya ocurrió** |
| 7 | **Interesado** (*stakeholder*) | Clasificación poder/interés e influencia |
| 8 | **Acta de constitución** (*charter*) | Qué la hace válida y quién la autoriza |
| 9 | **Solicitud de cambio** | Umbral que obliga a control formal |
| 10 | **Beneficio** | Diferencia entre entregable, resultado y beneficio. Es el eje de MSP |

---

## 4. La oportunidad que veo, y no es la obvia

Ya importás MS Project (`EP009`, campos `predecessors`, `successors`, `is_critical`,
`outline_level`, `wbs`). **Tenés el insumo exacto que necesita un chequeo DCMA 14-point.**

Ningún competidor de gama media evalúa calidad de cronograma. Un informe así es defendible y
automático: *«tu cronograma tiene 34 tareas sin sucesor, 12 con restricción dura y holgura
negativa de −18 días»*. Es justo lo que compra una PMO seria.
Sale de datos que **ya tenés en la base**, sin necesidad de costos ni de EVM.

Lo digo aquí y no en el diagnóstico porque es una decisión de producto, no una brecha.

---

## 5. Ruta sugerida, si me preguntás

No hay que elegir familia todavía. El orden que menos trabajo desperdicia:

1. **Fijar el vocabulario del núcleo (§3)** con ISO 21506 como árbitro. Barato, no
   compromete, y desbloquea todo lo demás.
2. **Definir la regla de derivación de la salud RAG.** Es el número que más se mira y hoy
   no tiene fórmula.
3. **Introducir línea base.** Es la pieza que falta para que exista cualquier métrica de
   desviación seria.
4. **Recién ahí** decidir entre EVM completo (exige costos por tarea) o calidad de
   cronograma tipo DCMA (no los exige). La segunda es mucho más barata y casi igual de
   vendible.
5. Elegir familia cuando haya un cliente que lo pida, y mapear, no reescribir.

---

## 6. Qué falta verificar antes de usar esto con un cliente

Marcado por honestidad: mi conocimiento tiene corte y **las ediciones se mueven**.

- Edición vigente de PRINCE2, MSP, MoP y P3O bajo PeopleCert
- Si PMBOK va por la 7ª o ya salió la 8ª
- Estado actual de las revisiones ISO 21502 y 21504
- Panorama de certificaciones específicas de PMO (PMO Global Alliance, AIPMO): es el
  segmento que más se ha movido y del que menos seguro estoy

Puedo verificarlo contra fuentes en línea cuando quieras cerrar la decisión.
