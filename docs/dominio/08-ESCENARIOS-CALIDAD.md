---
tipo: referencia
responsable: propietario
estado: vigente
revisado: 2026-08-12
revisar_cada: 90d
---

# Escenarios de calidad

Cierra **MCS REQ-02**: «DEBEN definirse al menos **cuatro** escenarios de
calidad con medida de respuesta numérica».

> **Estado: cuatro declarados, con medida numérica y comprobable.**

---

## Cómo se salió del atasco

La primera versión de este documento declaraba uno y dejaba tres pendientes «a
falta de dato de producción». Los tres candidatos eran percentiles de latencia,
y un P95 necesita una muestra que todavía no existe. La postura era correcta
—declarar cuatro con números inventados cierra el requisito y no mejora el
producto— y el atasco también era real.

Lo que lo desatascó fue mirar el requisito otra vez. **Pide una medida de
respuesta numérica, no un percentil de latencia.** El producto ya hace
cumplir tres números que nadie había escrito como escenario. Son el tope de
tiempo del análisis de un plan, la ventana de pérdida máxima de datos que fija
la copia diaria, y el retardo creciente del inicio de sesión.

Son mejores que un P95 improvisado por dos motivos. **Ya se cumplen** —el
código los impone, no los aspira— y **se comprueban sin esperar tráfico**: hay
una prueba por escenario.

---

## Formato

Cada escenario declara: **estímulo**, **entorno**, **respuesta** y **medida
numérica**. Sin la medida no es un escenario, es un deseo.

---

## E-1 — Disponibilidad del servicio

| Campo | Valor |
|---|---|
| **Atributo** | Disponibilidad |
| **Estímulo** | Una persona usuaria abre la plataforma |
| **Entorno** | Operación normal, sin ventana de mantenimiento anunciada |
| **Respuesta** | El servicio atiende la petición |
| **Medida** | **99.9 % de disponibilidad mensual** (≤ 43 min de caída al mes) |
| **Origen** | Decisión del owner 2026-08-06: alinearse a lo que ofrece Railway |
| **Cómo se comprueba** | Panel de Railway. `/health` publica `status`, `database` y `error_capture` para vigilancia externa |

**Único que no se comprueba desde el repositorio**, y es inevitable: la
disponibilidad la mide quien observa el servicio desde fuera. Lo que sí está
aquí es la ruta que un supervisor externo puede consultar.

---

## E-2 — Análisis de un plan importado

| Campo | Valor |
|---|---|
| **Atributo** | Rendimiento acotado |
| **Estímulo** | Alguien sube un `.mpp` o un `.xlsx` con el plan de un proyecto |
| **Entorno** | Producción, el worker con su carga normal |
| **Respuesta** | El análisis termina, o falla con un mensaje — **nunca se queda colgado** |
| **Medida** | **≤ 60 s** (`MPP_PARSE_TIMEOUT_SECONDS`), impuesto por el propio proceso |
| **Cómo se comprueba** | `test_req02_escenarios.py`; el ajuste existe y el análisis lo aplica |

**Por qué un tope y no un percentil.** Lo que le importa a quien sube un plan no
es que tarde 4 s o 9 s. Es que no se quede esperando sin fin. Un tope es una
promesa que se puede incumplir de forma observable; un promedio, no.

El percentil sigue siendo interesante y queda como trabajo abierto: la
instrumentación (`core/observabilidad.py`, `medir`/`medido`) ya emite
`duracion_ms` en los cuatro puntos de generación. Cuando haya muestra, se añade
un escenario **más**, sin quitar este.

---

## E-3 — Pérdida máxima de datos ante una restauración

| Campo | Valor |
|---|---|
| **Atributo** | Recuperabilidad |
| **Estímulo** | La base de datos se pierde o se corrompe y hay que restaurar |
| **Entorno** | Producción |
| **Respuesta** | El servicio vuelve con los datos de la última copia |
| **Medida** | **RPO ≤ 24 h** (copia diaria a las 03:30 UTC) · **retención 30 días** · el volcado se aborta a los **1800 s** |
| **Cómo se comprueba** | `test_inf03_respaldo.py` restaura de verdad contra Postgres y comprueba que los datos vuelven; `test_req02_escenarios.py` fija los tres números |

**Los tres números importan y dicen cosas distintas.** El RPO acota lo que se
pierde. La retención acota hasta cuándo se puede volver —un borrado que se
descubre a los 40 días ya no tiene copia—. El tope del volcado impide que un
proceso colgado retenga el worker y deje el día sin copia.

---

## E-4 — Resistencia a la adivinación de contraseñas

| Campo | Valor |
|---|---|
| **Atributo** | Seguridad |
| **Estímulo** | Alguien prueba contraseñas contra una cuenta, o contra muchas desde una IP |
| **Entorno** | Producción, punto de acceso de inicio de sesión |
| **Respuesta** | Los intentos se frenan **sin dejar a nadie fuera** |
| **Medida** | Retardo creciente desde el intento **5**, base **2 s**, tope **300 s** · máximo **30 fallos/hora por IP** |
| **Cómo se comprueba** | `test_req02_escenarios.py` fija los cuatro números; `test_auth_*` ejercita el flujo |

**El «sin dejar a nadie fuera» es la parte medida.** Antes eran 15 minutos de
bloqueo fijo. Quien conociera un nombre de usuario dejaba esa cuenta
fuera un cuarto de hora, y con una lista, al inquilino entero. El retardo
creciente frena igual la adivinación (unos 12 intentos por hora con el tope
puesto) y quien tecleó mal espera segundos, no minutos.

---

## Lo que queda abierto, y no bloquea

| Qué | Por qué no está aquí |
|---|---|
| **P95 de generación de informes** | Necesita muestra de producción. La instrumentación está puesta; se añadirá como escenario adicional, no en lugar de ninguno |
| **Latencia del tablero** | Lo mismo |
| **Capacidad por inquilino** | Hoy los proyectos son ilimitados. El escenario se escribe cuando entren los planes de suscripción, con sus niveles — no antes |

---

## La regla que se aplicó al elegirlos

Un escenario declarado **tiene que cumplirse el día que se escribe**. Un umbral
que ya se está incumpliendo no es un objetivo. Es una alarma encendida a la que
todo el mundo se acostumbra, y a las dos semanas nadie la mira.

Por eso los cuatro salen de números que el código ya impone. Cuando haya dato
de producción, los percentiles se añadirán con margen por encima del real.
