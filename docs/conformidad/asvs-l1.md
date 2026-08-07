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
| **Medición** | 2026-08-07 · **116 CUMPLE · 8 NO APLICA · 3 ACEPTADO · 0 HUECO** |
| **Estado del requisito** | **PARCIAL** — cero huecos, tres residuales aceptados |

> El catálogo se incorpora del proyecto OWASP ASVS, bajo licencia
> [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Se versiona
> aquí para que el mapeo se pueda comprobar sin red y para que un cambio de
> catálogo sea un cambio visible en `git log`.

---

## Cero huecos, y aun así PARCIAL

La auditoría del 2026-08-03 lo dejó **NO VERIFICABLE** («sin evaluación ASVS»).
La R1 lo bajó a **PARCIAL** con un muestreo declarado y tres huecos nombrados.
El mapeo completo llegó el 2026-08-07 y sacó **quince**. Ese mismo día se
cerraron los quince.

**No se declara CONFORME**, y el motivo cabe en una frase: quedan **tres
controles ACEPTADO**, y un residual aceptado no es un control cumplido.

| Control | Qué pide | Qué se aceptó, y quién lo decidió |
|---|---|---|
| `2.1.1` | Mínimo de 12 caracteres | 8 con reglas de composición. Owner, ADR-032 |
| `2.1.9` | Ninguna regla de composición | Se conservan. Va en el mismo paquete que 2.1.1: para NIST son la misma medida |
| `2.7.1` | Que un autenticador débil no se ofrezca por defecto, y que haya una alternativa más fuerte primero | El segundo factor es un código por **correo**, que NIST 800-63B §5.1.3.1 desaconseja para fuera de banda. No hay TOTP que ofrecer antes. Owner, ADR-035 |

Los tres tienen una decisión escrita detrás y ninguno está escondido: el barrido
`check_asvs.py` **rechaza** un `ACEPTADO` que no cite su ADR. Es la misma
distinción que este expediente lleva seis recuentos defendiendo — un auditor
tiene derecho a ver la diferencia entre «lo hacemos» y «decidimos no hacerlo»
sin preguntar.

El tope de huecos del barrido queda en **cero**: a partir de aquí, cualquier
control que se degrade rompe el CI.

---

## Lo que enseñó cerrar los quince

Tres controles no eran lo que su evidencia decía, y eso es lo que más vale de
haber medido contra el texto en vez de contra el recuerdo:

- **`10.3.2` decía «hoy no se cargan recursos externos».** Cargaba tres: la hoja
  de estilo de Google Fonts, sin `integrity`, con permiso para decidir de dónde
  bajar los tipos. No se arregla con `integrity` —Google devuelve un CSS distinto
  según el navegador— sino sirviéndolos desde nuestro origen.
- **`2.1.7` no se puede cerrar con «las 10.000 más usadas».** De las 59.186 de
  `rockyou-75`, las que pasan la política del producto son **ocho**: las demás
  ya las rechazan las reglas de composición. Lo que amenaza a este producto es lo
  que su propia política produce —la familia de `Password1!`—, que es
  exactamente el residual que ADR-032 aceptó, ahora medido.
- **`12.4.2` tenía dos mitades y solo una necesita antivirus.** El tipo del
  archivo salía de la cabecera del navegador y de la extensión del nombre, las
  dos escritas por quien sube: un ejecutable renombrado a `.pdf` se guardaba como
  `.pdf` y se servía con ese `Content-Type`. Eso se cierra mirando los bytes.

Y dos donde el control existía, pero no donde hacía falta:

- **`2.2.3` / `2.5.5`** avisaban en **uno** de los seis sitios que tocan una
  credencial — el cambio hecho por el propio usuario. Faltaban justo los cinco
  donde el cambio **no** lo hace el dueño de la cuenta, que es el único caso en
  que el aviso sirve para algo.
- **`2.1.12`** estaba copiado a mano en dos pantallas y faltaba en las nueve
  donde se **elige** contraseña nueva.

**Cerrar un control abre otros.** El segundo factor de `4.3.1` hizo que cuatro
NO APLICA dejaran de no aplicar (`2.2.2`, `2.7.2`, `2.7.3`, `2.7.4` — los tres
últimos con requisitos concretos: diez minutos, un solo uso atado a su desafío,
canal independiente) y convirtió `2.7.1` en el tercer residual aceptado. Un
mapeo no es una lista que solo encoge.

**Dos cambios se notan al desplegar.** El token de sesión pasó a cookie
`HttpOnly` (`3.2.3`/`8.2.2`), así que **se cierran todas las sesiones vivas**; y
entrar al panel de administración pasa a ser dos pasos.

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

**Derechos de las personas (`8.3.2`, `8.3.3`) — cerrados (ADR-034).** Exportación
en JSON y supresión por **anonimización**: las filas se quedan y dejan de apuntar
a nadie, porque el borrado físico choca con `audit_log` —de solo anexado— y con
el historial del proyecto, que es dato del inquilino y no de la persona. El
consentimiento va en el primer inicio de sesión, versionado, y vuelve a pedirse
si el aviso cambia. Cierra lo que `05-DATOS-PERSONALES.md` §5 llamaba «la
carencia más seria de este inventario».

**Notificación de cambios de credencial (`2.2.3`, `2.5.5`) — cerrado.** El aviso
existía en uno de los seis sitios que tocan una credencial. Ahora está en los
seis, incluido el correo a la **dirección que se abandona** cuando alguien
cambia el correo de una cuenta — sin eso, quien se apodera de una cuenta
consigue que su dueño no se entere nunca.

**El resto — cerrado.** `3.4.4` (prefijo `__Host-`), `5.2.7` (saneado de SVG),
`8.2.1` (cabeceras anti-caché), `10.3.2` (integridad de subrecursos), `11.1.4`
(límite sobre los listados), `12.4.2` (análisis de las subidas) y `4.3.1`
(segundo factor de administración), que era el único de este grupo que no era
una pieza sino producto.

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
