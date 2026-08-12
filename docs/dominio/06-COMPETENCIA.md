---
tipo: referencia
responsable: propietario
estado: vigente
revisado: 2026-08-12
revisar_cada: 90d
---

# Alcance de materia y frontera de competencia

Cierra **MCS CON-01** —«el producto DEBE declarar en documento versionado el
alcance de su materia, las jurisdicciones cubiertas y su frontera de
competencia»—. Da la base a `CON-03` y `CON-05`.

---

## 1. Materia

**Gestión de proyectos, programas y cartera**, en organizaciones que operan una
PMO.

El producto **no adopta un marco único**. Combina, por decisión del owner
(2026-08-06):

| Fuente | Qué aporta | Versión de referencia |
|---|---|---|
| **PMBOK** (PMI) | Vocabulario de áreas de conocimiento, grupos de procesos, acta de constitución, matriz de interesados, EDT | Guía PMBOK 7.ª edición |
| **PRINCE2** | Gobierno por etapas, roles de dirección, justificación continua de negocio, gestión por excepción | PRINCE2 7.ª edición |
| **Agile** | Iteración, backlog, avance por incremento entregado | Manifiesto Ágil y prácticas Scrum/Kanban de uso corriente |

**Por qué combinado y no puro.** Las PMO reales no operan un marco de manual.
Llevan gobierno tipo PRINCE2 hacia dirección, vocabulario PMBOK en la
documentación formal, y ejecución ágil en los equipos. Un producto que
impusiera uno solo obligaría a traducir en las otras dos direcciones.

**Consecuencia declarada:** cuando los marcos discrepan, **manda el glosario**
([`02-GLOSARIO.md`](02-GLOSARIO.md)), que fija un término por concepto. No se
sostienen dos vocabularios en paralelo.

---

## 2. Jurisdicciones

**Ninguna declarada, y es deliberado.**

El producto **no emite afirmaciones sujetas a jurisdicción**: no calcula
impuestos, no interpreta legislación laboral, no certifica cumplimiento
normativo ni produce documentos con valor legal. Un acta de constitución
generada aquí es un documento de gestión interna, no un instrumento jurídico.

Lo único con dimensión jurisdiccional es el **tratamiento de datos personales**,
y vive en [`05-DATOS-PERSONALES.md`](05-DATOS-PERSONALES.md). Ahí la
responsabilidad es del inquilino, que es el responsable del tratamiento.

**Si en el futuro el producto emite afirmaciones normativas** —plazos legales,
obligaciones de reporte, requisitos sectoriales—, esta sección deja de ser
válida. Hay que declarar jurisdicción por afirmación (`CON-03`).

---

## 3. Frontera de competencia

Lo que el producto **hace**:

- Estructura, registra y muestra información de proyectos según los marcos de §1.
- Calcula indicadores derivados de esa información: avance, carga, desviación,
  riesgos abiertos.
- Genera documentos e informes a partir de datos que el inquilino introdujo.
- Señala condiciones según umbrales **que el inquilino configura**.

Lo que el producto **no hace**, y donde está la frontera:

| Fuera de competencia | Por qué |
|---|---|
| **Consejo jurídico o fiscal** | No es su materia y no hay jurisdicción declarada |
| **Decidir cancelar, aprobar o continuar un proyecto** | Es una decisión de gobierno. El producto informa; decide la persona |
| **Certificar cumplimiento** de PMBOK, PRINCE2, ISO 21500 o similares | Usar su vocabulario no es certificar conformidad |
| **Valorar el desempeño de personas** | Los datos de carga miden asignación, no rendimiento. Usarlos para evaluar personas es un uso que el producto no respalda |
| **Predecir resultados** | Lo que se muestra es cálculo sobre lo introducido, no pronóstico |
| **Sustituir criterio profesional** de dirección de proyectos | Es herramienta, no asesor |

---

## 4. Qué pasa al cruzar la frontera (`CON-05`)

El requisito pide **derivar a persona profesional cualificada** toda consulta que
exceda la frontera declarada.

**El punto donde esto se aplica es el asistente de IA**, que es lo único capaz
de recibir una pregunta abierta. El resto de la plataforma son formularios e
informes: no hay dónde preguntar algo fuera de alcance.

**Estado: implementado el 2026-08-06.** Antes de esa fecha nada impedía que
alguien le preguntara al asistente si puede despedir a un colaborador por bajo
desempeño. Nada garantizaba que la respuesta derivara en vez de opinar. Ese
caso literal es hoy una prueba (`test_el_ejemplo_del_documento`).

Los tres pasos que este apartado pedía, y dónde están:

1. **La instrucción declara la frontera.** Se genera desde
   [`app/services/ai/frontera.py`](../../apps/api/app/services/ai/frontera.py),
   que refleja la tabla del §3; escribirla a mano permitiría que el prompt
   dijera algo que este documento no dice.
2. **El sistema deriva, y no le pide permiso al modelo.** `aplicar_frontera`
   corre **después** de la respuesta, sobre la consulta de quien pregunta. Si
   el modelo se saltó la instrucción y opinó igualmente, el aviso va delante de
   su opinión. Un prompt es una petición, no una garantía.
3. **La derivación está en el conjunto de evaluación**: `EV-S-10` a `EV-S-15`,
   una por exclusión, con el modelo opinando alegremente en las seis. Y
   `EV-C-37` mide la otra mitad — que una consulta de dentro de alcance **no**
   se derive, porque derivar siempre cumpliría el requisito por vacuidad.

El paso 3 no es adorno. Una frontera que solo vive en el texto de un prompt se
erosiona con cada cambio de modelo y nadie se entera.

### El residual, escrito

La detección es **por señales léxicas**, así que tiene falsos negativos: una
consulta jurídica formulada sin ninguna de las palabras declaradas pasa de
largo. No se afirma «detecta todas las consultas fuera de alcance».

Lo que sí se afirma es lo que el requisito pide de un sistema. Cuando la
consulta cruza la frontera de forma reconocible, la derivación **ocurre por
construcción**. Misma postura que `ruta_interna_segura` con las rutas de
navegación: lista blanca de forma y el residual por escrito.

Que las señales cubran lo que deben es lo que se revisa cuando alguien reporta
una consulta que se coló. Ese reporte entra al conjunto de evaluación antes
de arreglarse, como cualquier otro fallo de IA.

---

## 5. El conocimiento de dominio, y dónde vive (`CON-02`)

El requisito exige que el conocimiento del dominio **resida en artefactos
versionados**. Prohíbe que se implemente **únicamente** mediante instrucciones
de rol dirigidas a un modelo.

Parte está bien: el vocabulario está en [`02-GLOSARIO.md`](02-GLOSARIO.md), la
semántica de estados y umbrales está en código y configuración, y las decisiones
están en `docs/adr/`. Este documento añade la materia y la frontera.

### El contraste, hecho el 2026-08-06

Se revisaron las cuatro instrucciones de sistema (`MINUTE_SYSTEM`,
`MINUTE_NORMALIZE_SYSTEM`, `REPORT_SYSTEM`, `ASSISTANT_SYSTEM`) contra el
glosario, los modelos y los ADR. La mayor parte de su texto es **contrato de
salida** —qué claves devolver, en qué orden, sin bloques de código—. Eso no es
conocimiento de dominio: es formato. Salieron dos cosas que sí lo eran.

**1. La taxonomía RAID estaba versionada, y el glosario no la cubría.** Las
cuatro categorías viven en `validator.ALLOWED_RAID_TYPES` y en
`minutes_formatter.RAID_TYPE_ORDER`, así que en código estaban. Pero el §3 del
glosario definía riesgo, incidencia, acción y lección aprendida — y **no
mencionaba la decisión**. Es una de las cuatro que el producto implementa, y
que el modelo recibe en su instrucción. Dos artefactos versionados diciendo
cosas distintas es la misma enfermedad con otra cara. Corregido: el glosario
§3.4 la define, y una prueba mantiene unidos glosario, corpus y validador.

**2. El mapa de señales existía solo en el prompt.** «se acordó» → Decisión,
«preocupación» → Riesgo. Eso es criterio de dominio puro —la parte que un
director de proyecto discutiría— y vivía únicamente dentro de una cadena de 180
líneas. Es el caso exacto que el requisito nombra.

Ahora vive en [`app/services/ai/corpus.py`](../../apps/api/app/services/ai/corpus.py),
declarado en el glosario §3, y **la instrucción se genera desde ahí**. La
diferencia práctica: cambiar una señal es cambiar un dato versionado con su
historia en `git log`, no editar prosa dentro de un prompt. Un trinquete impide
que la correspondencia vuelva a teclearse en `prompts.py`.

### Lo que este contraste NO cubre

No cubre el conocimiento que el modelo trae **de su propio entrenamiento**. Un
modelo que sabe qué es un diagrama de Gantt lo sabe sin que este producto se lo
diga. Eso no es implementable ni auditable desde aquí. Lo que CON-02 exige y
lo que se cumple es que **el producto** no ponga reglas de dominio propias
solo en el prompt. Lo que el modelo aporte por su cuenta lo acota la frontera
del §3, y lo mide el conjunto de evaluación.
