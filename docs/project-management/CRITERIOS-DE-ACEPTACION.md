---
tipo: gestion
responsable: propietario
estado: vigente
revisado: 2026-08-07
revisar_cada: 180d
---

# Criterio de aceptación: qué cuenta y dónde vive

Cierra **MCS REQ-01** («todo requisito funcional DEBE tener criterio de
aceptación verificable»).

---

## El hueco que había

La plantilla de issue exige «Criterios de aceptación», así que el trabajo que
pasa por un issue lo tiene. El problema lo dejó escrito la auditoría del
2026-08-03: **varios lotes se ejecutaron por chat sin crear issues** —es el
principio 0.1 de `CLAUDE.md`, «solucionar > documentar»— y para ese trabajo no
había criterio verificable en ninguna parte.

Dos salidas malas y una buena. La mala rápida: exigir issue para todo, que es
retroceder sobre una decisión del owner tomada a conciencia. La mala lenta:
escribir criterios a posteriori en un documento, que envejece el día que se
guarda. La buena es la que el repositorio ya venía practicando sin llamarla por
su nombre.

---

## La regla

> **El criterio de aceptación de un cambio es la prueba que lo nombra.**

No un párrafo que lo describa: una prueba ejecutable que cite su identificador
—`US-196`, `BUG-082`, `DAT-09`— y que falle si el comportamiento se pierde.

Tres consecuencias, y son el motivo de escribirlo así:

1. **Es verificable por definición.** «El sidebar no muestra items de admin a
   usuarios plain» es una frase que dos personas leen distinto. `pytest -k
   BUG-006` no.
2. **No envejece en silencio.** Un criterio escrito en un documento sigue
   diciendo lo mismo cuando el código deja de hacerlo. Una prueba se pone roja.
3. **Sirve igual con issue y sin él.** Es lo que hace compatible REQ-01 con el
   principio 0.1: el lote por chat entrega su criterio en el mismo commit, no
   en un formulario aparte.

### Qué cuenta como prueba

Cualquiera de estas, siempre que **nombre el identificador** y **falle si el
comportamiento se pierde**:

| Forma | Ejemplo |
|---|---|
| Caso de `pytest` | `apps/api/tests/test_dat09_indicadores.py` |
| Barrido con trinquete | `scripts/check_frescura.py` (DAT-11) |
| Caso del conjunto de evaluación de IA | `EV-S-13` (CON-05) |

Lo que **no** cuenta: un comentario en el código, una entrada en `SPRINT.md`,
una captura de pantalla en el comment de cierre. Documentan; no verifican.

### Cómo se comprueba que la regla se cumple

`scripts/check_criterios.py` recorre los requisitos que el registro declara
**CONFORME** y comprueba que exista una prueba o un barrido que los nombre. Al
2026-08-07 son **55 con prueba y 4 verificables solo fuera del repositorio**
—protección de rama en GitHub, almacén de secretos y canalización en Railway—,
cada uno con el sitio donde sí se comprueba escrito al lado.

No es una lista escrita a mano: los identificadores salen del registro y los
nombres se buscan en el árbol de pruebas. Un cierre nuevo sin prueba hace
fallar el control el mismo día.

> **La primera versión de este barrido decía «59 de 59» y era mentira.**
> Incluía `registro_conformidad.py` en el corpus donde buscaba, así que cada
> requisito se encontraba a sí mismo en la línea que lo declaraba conforme.
> Al quitarlo aparecieron **doce** cierres sin prueba: ocho se cubrieron con
> `test_req01_criterios.py` y cuatro quedaron declarados. Lo destapó la
> verificación por mutación —un cierre inventado y sin prueba pasaba en
> verde—, que es exactamente el argumento de la sección siguiente.

---

## Lo que este control NO comprueba

**Que la prueba sea buena.** Un caso que nombre `DAT-09` y no compruebe nada
pasaría. Lo que impide eso es otra práctica, y también está escrita: **la
verificación por mutación** —aplicar el fallo que la prueba dice cazar y
confirmar que se pone roja— es parte del cierre de cada item, y su resultado va
en el mensaje del commit.

Las dos juntas dan lo que REQ-01 pide. Por separado, ninguna: un control de
existencia sin mutación cuenta archivos, y una mutación sin control de
existencia solo cubre lo que alguien se acordó de verificar.

---

## Para el trabajo de producto que no toca conformidad

Una `US`, un `BUG` o un `ENH` sigue el mismo criterio y lo declara donde le
toca: la plantilla de issue pide los criterios de aceptación **antes** de
empezar, y el comment de cierre demuestra que se cumplen ejecutando la prueba.
Eso ya está en `CLAUDE.md` §3 y en la skill `cerrar-item`; este documento no lo
cambia, solo dice qué cuenta como criterio cuando no hay issue.
