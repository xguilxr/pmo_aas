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
| **Medición** | 2026-08-07 · **97 CUMPLE · 13 NO APLICA · 2 ACEPTADO · 15 HUECO** |
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

El mapeo completo ya está. Y lo que enseña es que **quedan quince
controles L1 sin cumplir y dos aceptados por decisión**, la mayoría concentrados en dos sitios: la política
de contraseñas y el almacenamiento del token en el navegador.

Declararlo CONFORME con quince huecos abiertos sería la conformidad de papel
que este expediente lleva seis recuentos evitando. Se declara PARCIAL, con la
lista delante.

---

## Los quince huecos

| Control | Qué pide | Qué pasa hoy |
|---|---|---|
| `2.1.7` | Verify that passwords submitted during account registration, login, and password change are checked again… | No se contrasta contra ningún conjunto de contraseñas filtradas. |
| `2.1.12` | Verify that the user can choose to either temporarily view the entire masked password, or temporarily vie… | No hay control para revelar temporalmente la contraseña escrita. |
| `2.2.3` | Verify that secure notifications are sent to users after updates to authentication details, such as crede… | No se notifica al usuario un cambio de credenciales ni un inicio de sesión desde equipo nuevo. |
| `2.5.5` | Verify that if an authentication factor is changed or replaced, that the user is notified of this event. | Mismo hueco que 2.2.3: no hay notificación al cambiar el factor. |
| `3.2.3` | Verify the application only stores session tokens in the browser using secure methods such as appropriate… | El token de acceso se guarda en `localStorage` (`apps/web/lib/auth- storage.ts`). El de refresco sí va en cookie `HttpOnly`. |
| `3.4.4` | Verify that cookie-based session tokens use the "__Host-" prefix so cookies are only sent to the host tha… | La cookie de refresco no usa el prefijo `__Host-`. |
| `4.3.1` | Verify administrative interfaces use appropriate multi-factor authentication to prevent unauthorized use. | No hay segundo factor para las interfaces de administración. |
| `5.2.7` | Verify that the application sanitizes, disables, or sandboxes user-supplied Scalable Vector Graphics (SVG… | Se admite SVG como logotipo de marca y no se sanea su contenido activo. |
| `8.2.1` | Verify the application sets sufficient anti-caching headers so that sensitive data is not cached in moder… | No se emiten cabeceras anti-caché en las respuestas con datos de inquilino. |
| `8.2.2` | Verify that data stored in browser storage (such as localStorage, sessionStorage, IndexedDB, or cookies) … | El token de acceso y el perfil del usuario viven en `localStorage`. |
| `8.3.2` | Verify that users have a method to remove or export their data on demand. | No hay exportación ni borrado de datos personales a petición; queda anotado en 05-DATOS-PERSONALES.md §carencias. |
| `8.3.3` | Verify that users are provided clear language regarding collection and use of supplied personal informati… | No hay texto de consentimiento ni aceptación explícita en el alta. |
| `10.3.2` | Verify that the application employs integrity protections, such as code signing or subresource integrity.… | No se declara integridad de subrecursos; hoy no se cargan recursos externos, pero nada lo impide. |
| `11.1.4` | Verify that the application has anti-automation controls to protect against excessive calls such as mass … | No hay límite de peticiones sobre los listados: una cuenta válida puede paginar la cartera entera sin freno. |
| `12.4.2` | Verify that files obtained from untrusted sources are scanned by antivirus scanners to prevent upload and… | No hay análisis antivirus de lo que se sube. |
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

*Siguen abiertos* `2.1.7` (contraseñas filtradas) y `2.1.12` (revelar
temporalmente lo escrito), que no dependían de esa decisión.

**Token en el navegador (`3.2.3`, `8.2.2`).** El token de acceso vive en
`localStorage`, que es legible por cualquier script inyectado. El de refresco sí
va en cookie `HttpOnly`, que es la mitad buena. Moverlo entero a cookies es un
cambio del flujo de autenticación con impacto en las sesiones vivas: se hace con
ventana, no al final de una ronda.

**Derechos de las personas (`8.3.2`, `8.3.3`).** Exportación y borrado a
petición, y consentimiento explícito en el alta. Ya estaban anotados como
carencia abierta en `05-DATOS-PERSONALES.md` cuando se cerró REQ-03; aquí
aparecen otra vez, desde otro marco, que es lo que pasa cuando una carencia es
real.

**Notificación de cambios de credencial (`2.2.3`, `2.5.5`).** Un correo al
cambiar contraseña o dirección. Barato, y necesita decidir el texto y el canal.

**El resto** (`3.4.4` prefijo `__Host-`, `4.3.1` segundo factor para
administración, `5.2.7` saneado de SVG, `8.2.1` cabeceras anti-caché, `10.3.2`
integridad de subrecursos, `11.1.4` límite sobre los listados, `12.4.2` antivirus
en las subidas) son piezas independientes. `8.2.1` y `10.3.2` son las dos más
baratas y no tocan comportamiento visible.

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
