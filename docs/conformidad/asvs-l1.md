---
tipo: informe
responsable: propietario
estado: vigente
revisado: 2026-08-07
revisar_cada: 90d
---

# ASVS 4.0.3 nivel 1 — mapeo completo del producto

Trabaja **MCS SEG-01**: «el producto DEBE cumplir los controles de OWASP ASVS
nivel 1 aplicables».

| | |
|---|---|
| **Catálogo** | OWASP ASVS 4.0.3, nivel 1 — **127 controles**, en [`marco/asvs-4.0.3-L1.csv`](marco/asvs-4.0.3-L1.csv) |
| **Mapeo** | [`asvs-l1.yaml`](asvs-l1.yaml), uno por control |
| **Barrido** | `scripts/check_asvs.py` — falla si falta uno, si un estado no tiene evidencia o si los huecos crecen |
| **Medición** | 2026-08-07 · **109 CUMPLE · 13 NO APLICA · 2 ACEPTADO · 3 HUECO** |
| **Estado del requisito** | **PARCIAL**, y honestamente parcial |

> El catálogo se incorpora del proyecto OWASP ASVS, bajo licencia
> [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Se versiona
> aquí para que el mapeo se pueda comprobar sin red y para que un cambio de
> catálogo sea un cambio visible en `git log`.

---

## Por qué esto no cierra SEG-01, y por qué aun así es el avance

La auditoría del 2026-08-03 lo dejó **NO VERIFICABLE** («sin evaluación ASVS»).
La R1 lo bajó a **PARCIAL** con un muestreo declarado y tres huecos nombrados —y
los tres se cerraron después: límite por IP en el inicio de sesión, `audit_log`
de solo anexado, y `python-jose` sustituido por PyJWT—. Pero el propio informe
avisaba de que «con los tres cerrados seguiría haciendo falta el mapeo completo».

El mapeo completo llegó el 2026-08-07 y sacó **quince huecos**. Ese mismo día se
cerraron **doce**. Quedan tres, y los tres son producto que hay que construir,
no configuración que ajustar: segundo factor para administración, derechos de
exportación y supresión, y consentimiento explícito.

Declararlo CONFORME con tres huecos abiertos seguiría siendo la conformidad de
papel que este expediente lleva seis recuentos evitando. Se declara PARCIAL, con
la lista delante — que ahora cabe en tres líneas.

---

## Los tres que quedan

| Control | Qué pide | Por qué sigue abierto |
|---|---|---|
| `4.3.1` | Segundo factor para las interfaces de administración. | No hay nada de MFA. `cryptography` ya trae TOTP, así que no hace falta dependencia nueva, pero es producto: enrolamiento, códigos de recuperación, migración y pantalla. **Necesita postura del owner**: obligatorio para administración cambia cómo entra él mismo. |
| `8.3.2` | Que la persona pueda exportar o borrar sus datos a petición. | Ya estaba anotado como la carencia más seria de `05-DATOS-PERSONALES.md` §5. El borrado choca de frente con `audit_log`, que es de solo anexado por diseño, así que la forma viable es exportar + anonimizar. **Necesita decidir eso primero.** |
| `8.3.3` | Texto claro sobre qué se recoge y para qué, con aceptación explícita. | No hay alta por autoservicio: las cuentas las crea un administrador, así que el consentimiento no cabe en un registro que no existe. El sitio natural es el primer inicio de sesión, junto al cambio de contraseña forzado. |

Los tres comparten una propiedad que los separa de los doce cerrados: **ninguno
se arregla dentro del código que ya hay**. Los doce eran defectos o piezas que
faltaban en flujos existentes; estos tres son funcionalidad nueva con decisiones
de producto detrás.

---

## Los doce que se cerraron, y qué enseñó cerrarlos

Tres de ellos no eran lo que la evidencia decía, y eso es lo que más vale de
haber medido contra el texto del control:

- **`10.3.2` decía «hoy no se cargan recursos externos».** Cargaba tres: la hoja
  de estilo de Google Fonts, sin `integrity`, con permiso para decidir de dónde
  bajar los tipos. No se arregla con `integrity` —Google devuelve un CSS
  distinto según el navegador— sino sirviéndolos desde nuestro origen.
- **`2.1.7` no se puede cerrar con «las 10.000 más usadas».** De las 59.186 de
  `rockyou-75`, las que pasan la política del producto son **ocho**: las demás
  ya las rechazan las reglas de composición. Lo que amenaza a este producto es
  lo que su propia política produce —la familia de `Password1!`—, que es
  exactamente el residual que ADR-032 aceptó, ahora medido.
- **`12.4.2` tenía dos mitades y solo una necesita antivirus.** El tipo del
  archivo salía de la cabecera del navegador y de la extensión del nombre, las
  dos escritas por quien sube: un ejecutable renombrado a `.pdf` se guardaba
  como `.pdf` y se servía con ese `Content-Type`. Eso se cierra mirando los
  bytes, sin motor.

Y dos más donde el control existía pero no donde hacía falta:

- **`2.2.3` / `2.5.5`** avisaban en **uno** de los seis sitios que tocan una
  credencial — el cambio hecho por el propio usuario. Faltaban justo los cinco
  donde el cambio **no** lo hace el dueño de la cuenta, que es el único caso en
  que el aviso sirve para algo.
- **`2.1.12`** estaba copiado a mano en dos pantallas y faltaba en las nueve
  donde se **elige** contraseña nueva.

El resto —`8.2.1`, `3.4.4`, `5.2.7`, `11.1.4`, `3.2.3`, `8.2.2`— eran piezas
que faltaban, sin sorpresa. `3.2.3` y `8.2.2` son los de mayor impacto: el token
de acceso salió de `localStorage` a una cookie `HttpOnly`, y eso **cierra todas
las sesiones vivas al desplegar**.

---

## Cómo se agrupan, y qué decisión pide cada grupo

**Política de contraseñas — resuelta el 2026-08-07 (ADR-032).** Era el grupo
más grande de la primera medición: seis controles, y no todos eran lo mismo.

*La postura,* `2.1.1` y `2.1.9`: ASVS pide mínimo de 12 caracteres y **ninguna
regla de composición**, y los pide juntos porque para NIST 800-63b son la misma
medida —las reglas producen contraseñas predecibles y la longitud es lo que
encarece adivinarlas—. **El owner decidió quedarse en 8 con reglas**, con el
contraste delante. Figuran **ACEPTADO**, no CUMPLE: el producto no los cumple, y
hay una decisión escrita detrás. Un auditor tiene derecho a ver esa diferencia
sin preguntar.

*El defecto,* `2.1.2` y `2.1.3`: **cerrados**. bcrypt truncaba a 72 bytes en
silencio, y estaba comprobado —una contraseña de 103 caracteres y otra de 108
con los mismos 72 primeros abrían la misma cuenta—. El esquema pasa a
`bcrypt_sha256`, que resume antes de hashear; `bcrypt` queda deprecado y no
retirado, así que los hashes existentes verifican y se reescriben en el
siguiente inicio de sesión. Y el máximo pasa a ser 128 **declarado**: «sin
máximo» sonaba generoso mientras por detrás había uno de 72 sin avisar.

*También cerrados* `2.1.7` (contraseñas filtradas) y `2.1.12` (revelar
temporalmente lo escrito), que no dependían de esa decisión. El primero, con un
conjunto derivado de la familia predecible que **estas mismas reglas de
composición producen**: es el residual de ADR-032, medido en vez de supuesto.

**Token en el navegador (`3.2.3`, `8.2.2`) — cerrado el 2026-08-07 (ADR-033).**
El token de acceso pasó de `localStorage` a una cookie `HttpOnly` con prefijo
`__Host-`; el perfil dejó de persistirse y se repone desde `/auth/me`.
`Authorization` se sigue aceptando para el SDK y las integraciones de servidor a
servidor. **Cierra todas las sesiones vivas al desplegar**, y no hay forma de
evitarlo: migrarlas en caliente exigiría que el servidor leyera el token del
sitio inseguro para reemitirlo, que es justo lo que se quita.

**Derechos de las personas (`8.3.2`, `8.3.3`) — siguen abiertos.** Exportación y
borrado a petición, y consentimiento explícito. Ya estaban anotados como carencia
abierta en `05-DATOS-PERSONALES.md` cuando se cerró REQ-03; aquí aparecen otra
vez, desde otro marco, que es lo que pasa cuando una carencia es real. El
borrado choca con `audit_log`, de solo anexado por diseño: la forma viable es
exportar y anonimizar, y esa es la decisión que falta.

**Notificación de cambios de credencial (`2.2.3`, `2.5.5`) — cerrado.** El aviso
existía en uno de los seis sitios que tocan una credencial. Ahora está en los
seis, incluido el correo a la **dirección que se abandona** cuando alguien
cambia el correo de una cuenta — sin eso, quien se apodera de una cuenta
consigue que su dueño no se entere nunca.

**El resto — cerrado.** `3.4.4` (prefijo `__Host-`), `5.2.7` (saneado de SVG),
`8.2.1` (cabeceras anti-caché), `10.3.2` (integridad de subrecursos), `11.1.4`
(límite sobre los listados) y `12.4.2` (análisis de las subidas). Sigue abierto
`4.3.1`, el segundo factor para administración, que es el único de este grupo
que era producto y no una pieza.

---

## Lo que este mapeo no demuestra

**Que la evidencia sea cierta.** «CUMPLE — SQLAlchemy con parámetros ligados»
lo escribe una persona, y el barrido lo lee sin comprobarlo. Lo que sí lo
comprueba son las suites de los controles que tienen una —`SEG-04` con sus 18
casos de autorización sobre el objeto, `IA-11` con los suyos de inyección— y el
hecho de que cada evidencia cite archivo o función, para que se pueda ir a
mirar.

Es el mismo límite que tiene cualquier autoevaluación, y por eso se escribe en
vez de dejarlo implícito.
