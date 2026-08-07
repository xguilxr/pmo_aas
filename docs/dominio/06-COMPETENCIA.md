---
tipo: referencia
responsable: propietario
estado: vigente
revisado: 2026-08-06
revisar_cada: 90d
---

# Alcance de materia y frontera de competencia

Cierra **MCS CON-01** —«el producto DEBE declarar en documento versionado el
alcance de su materia, las jurisdicciones cubiertas y su frontera de
competencia»— y da la base a `CON-03` y `CON-05`.

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

**Por qué combinado y no puro.** Las PMO reales no operan un marco de manual:
llevan gobierno tipo PRINCE2 hacia dirección, vocabulario PMBOK en la
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
válida y hay que declarar jurisdicción por afirmación (`CON-03`).

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

**Estado hoy: no implementado.** Nada impide que alguien le pregunte al
asistente si puede despedir a un colaborador por bajo desempeño, y nada
garantiza que la respuesta derive en vez de opinar.

Lo que hace falta, declarado como trabajo pendiente y no como excepción:

1. Que la instrucción del asistente **declare la frontera de este documento**.
2. Que ante una consulta fuera de alcance **derive explícitamente** —«esto
   excede lo que esta herramienta cubre; conviene consultarlo con …»— en vez de
   responder.
3. Que la derivación esté **en el conjunto de evaluación** (MCS IA-07/08/09), o
   no hay forma de saber si sigue funcionando tras cambiar el modelo.

El paso 3 no es adorno: una frontera que solo vive en el texto de un prompt se
erosiona con cada cambio de modelo y nadie se entera.

---

## 5. El conocimiento de dominio, y dónde vive (`CON-02`)

El requisito exige que el conocimiento del dominio **resida en artefactos
versionados**, y prohíbe que se implemente **únicamente** mediante instrucciones
de rol dirigidas a un modelo.

Parte está bien: el vocabulario está en [`02-GLOSARIO.md`](02-GLOSARIO.md), la
semántica de estados y umbrales está en código y configuración, y las decisiones
están en `docs/adr/`. Este documento añade la materia y la frontera.

Lo que falta es el **contraste**: comprobar que lo que se le dice al modelo no
contiene reglas de dominio que no existan en ningún otro sitio. Es una revisión
de las instrucciones del asistente contra estos artefactos, y está pendiente.
