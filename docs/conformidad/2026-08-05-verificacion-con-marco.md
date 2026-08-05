# Verificación de las Olas 0 y 1 contra `MCS-CORE`

| Campo | Valor |
|---|---|
| Fecha | 2026-08-05 |
| Motivo | El marco llegó al repositorio; las dos olas se habían cerrado sin él |
| Antes | 41 bloquean N1 |
| Después | **44 bloquean N1** |

---

## Qué pasó

Las Olas 0 y 1 se cerraron leyendo la **evidencia** que los informes anotaban
—«ningún ADR en `docs/adr/`», «rama no protegida»— y no el **texto del
requisito**, que no estaba disponible. Con el marco en la mano, **tres de los
seis cierres no se sostienen**.

No es que la evidencia fuera falsa: los 24 ADR existen y la rama está protegida.
Es que el requisito pedía más de lo que la evidencia medía.

---

## Los tres que se revierten

### `CFG-03` e `INT-03` — el residual no era residual

`CFG-03` exige la rama principal protegida **«sin escritura directa»**.
`INT-03` exige que la integración **no se permita** con verificaciones en fallo.

Con `enforce_admins: false`, un administrador puede hacer las dos cosas. El
marco no deja margen interpretativo: §6.1 define **Parcial** como «se cumple en
parte del alcance», y §6.2 dice que **un requisito en estado Parcial impide
alcanzar su nivel**. Los dos son N1.

**Esto cambia el precio de una decisión ya tomada.** El owner dejó
`enforce_admins` en `false` el 2026-08-05 entendiendo —porque así se lo
presenté— que era un residual sobre requisitos cerrados. No lo es: mantiene dos
requisitos N1 abiertos, y N1 es el objetivo intermedio del plan.

La decisión sigue siendo suya y sigue siendo defendible —con un solo
desarrollador, la salida de emergencia tiene valor real—. Lo que cambia es que
ahora se sabe qué cuesta: **N1 no se alcanza con `enforce_admins` en `false`.**

### `ARQ-02` — el salto fue grande y no llega

Exige que **toda** decisión irreversible esté en un ADR. Pasar de cero a 24 es
el salto grande, pero `DECISIONS.md` conserva 25 entradas `DEC-` y algunas son
irreversibles de manual: `DEC-003` (jerarquía en tablas separadas en vez de
JSONB) y `DEC-008` (charter como tabla propia) son forma de esquema.

Queda **PARCIAL**. Cerrarlo es trabajo de una tarde: revisar las 25, decidir
cuáles son irreversibles y promoverlas a ADR.

---

## Los tres que sí se sostienen

| ID | Texto del requisito | Por qué cumple |
|---|---|---|
| `GOB-02` | Toda exclusión de un requisito aplicable en un ADR con justificación, riesgo aceptado y fecha de revisión | La única exclusión —`ARQ-03`— está en **ADR-018** con las tres cosas y fecha de revisión 2027-02-04 |
| `LEN-01` | Glosario canónico versionado con término en español, término en inglés, definición y términos prohibidos | `02-GLOSARIO.md` tiene «Preferente / En código / Vetado» más definición, aprobado y completo |
| `DAT-05` | Un concepto derivado NO DEBE formularse más de una vez | Una sola paleta de salud y un solo vocabulario de fase. **Salvedad:** el requisito es más amplio que la evidencia que lo midió; una reauditoría con el marco podría mirar más conceptos derivados |

---

## Lo que el marco desbloqueó

`DAT-08` y `DAT-16` figuraban **sin medir** porque llegaban del informe base sin
evidencia escrita y no se sabía qué exigían. Ya se sabe:

| ID | Requisito | Medido | Nivel |
|---|---|---|---|
| `DAT-08` | Las constantes numéricas de conversión NO DEBEN aparecer dispersas | **26 sitios** con conversiones inline en `app/` | N2 |
| `DAT-16` | Los datos incompletos o de periodo en curso DEBEN señalarse | Sin señalización en analíticas ni gráficos | N2 |

Los dos son N2: no bloquean N1, pero dejan de ser un agujero en el registro.

---

## Un defecto del propio marco

**El Anexo A de `MCS-CORE` contradice sus tablas normativas.** La fila `DAT`
declara 6 requisitos N1 y 8 N2; contando §5.7.1 y §5.7.2 salen **10 N1 y 6 N2**.
La fila suma 18 y su propia columna de total dice 19.

El arrastre llega a los totales del anexo: **N1 son 68 y no 64; N2 son 58 y no
60.** Y aquí está lo interesante — la suma N1+N2 da **126**, que es exactamente
el alcance que las tres auditorías midieron.

**O sea que el alcance de la auditoría era correcto y el resumen del marco es el
que está mal.** Queda anotado como errata al pie del anexo, sin tocar el texto:
un documento normativo se reemplaza, no se edita en silencio (`DOC-08`,
`CFG-18`). Corregirlo corresponde a una versión 2.0.1 emitida por el propietario
del marco.

---

## Estado corregido

**44 bloquean N1**, no 41. Las Olas 0 y 1 cerraron **tres** requisitos, no seis:
`GOB-02`, `LEN-01` y `DAT-05`.

La lección es la misma que el expediente lleva repitiendo: **medir contra la
evidencia anotada, y no contra el requisito, produce cierres que no aguantan.**
Es el sexto error de recuento de este expediente, y el primero que se detecta
antes de construir sobre él en vez de después.
