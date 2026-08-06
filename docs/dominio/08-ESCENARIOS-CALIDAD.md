---
tipo: referencia
responsable: propietario
estado: borrador
revisado: 2026-08-06
revisar_cada: 90d
---

# Escenarios de calidad

Trabaja **MCS REQ-02**: «DEBEN definirse al menos **cuatro** escenarios de
calidad con medida de respuesta numérica».

> **Estado: uno de cuatro declarado.** El resto necesita dato de producción, no
> una decisión. La instrumentación ya está puesta (`core/observabilidad.py`,
> `medir`/`medido`); faltan los días de tráfico que den el percentil.
>
> Declarar los cuatro con números inventados cerraría el requisito y no
> mejoraría el producto — que es la definición de conformidad de papel, y este
> expediente existe justamente por haberla sufrido cinco veces.

---

## Formato

Cada escenario declara: **estímulo**, **entorno**, **respuesta** y **medida
numérica**. Sin la medida no es un escenario, es un deseo.

---

## E-1 — Disponibilidad del servicio ✅ declarado

| Campo | Valor |
|---|---|
| **Atributo** | Disponibilidad |
| **Estímulo** | Una persona usuaria abre la plataforma |
| **Entorno** | Operación normal, sin ventana de mantenimiento anunciada |
| **Respuesta** | El servicio atiende la petición |
| **Medida** | **99.9 % de disponibilidad mensual** |
| **Origen** | Decisión del owner 2026-08-06: alinearse a lo que ofrece Railway |
| **Cómo se comprueba** | Panel de Railway |

**99.9 % son ~43 minutos de caída al mes.** Conviene tenerlo escrito en minutos
y no en nueves: es lo que hace que la cifra se pueda contrastar contra un
incidente real en vez de discutirse en abstracto.

**Este número lo pone la plataforma de despliegue, no el producto.** Prometer
más que Railway sería prometer algo que no se controla; el compromiso propio no
puede superar al de la infraestructura sobre la que corre.

---

## E-2 — Generación de informes ⏳ instrumentado, sin medida

| Campo | Valor |
|---|---|
| **Atributo** | Rendimiento |
| **Estímulo** | Se solicita la generación de un informe de proyecto |
| **Entorno** | Producción, carga normal |
| **Respuesta** | El informe queda disponible |
| **Medida** | **Pendiente** — percentil 95, con dato real |
| **Cómo se medirá** | `duracion_ms` de la operación `informe.html` |

**La instrumentación ya está.** Los cuatro puntos de generación —informe de
proyecto, minuta, acta `.docx` y plantilla del constructor— emiten
`operacion`, `duracion_ms` y `exito` en cada ejecución, con Sentry y sin él.

**Falta el dato, y por eso el número no está aquí.** Un P95 necesita una muestra
que hoy no existe. El procedimiento es: dejar correr, mirar el percentil real, y
declarar el umbral **por encima** de él con margen — un umbral que ya se está
incumpliendo el día que se escribe no es un objetivo, es una alarma encendida a
la que todo el mundo se acostumbra.

---

## E-3 y E-4 — sin declarar

Faltan dos, y las candidatas naturales son **latencia del tablero** y
**capacidad por inquilino**. Las dos dependen de lo mismo que E-2: medir antes.

La de capacidad tiene además una decisión detrás que hoy no aplica: los
proyectos por inquilino son **ilimitados** y dejarán de serlo cuando entren los
planes de suscripción. El escenario se escribe con los niveles, no antes.

---

## Por qué esto no cierra `REQ-02` todavía

Porque el requisito pide cuatro **con medida numérica**, y hay una. Se deja
declarado en vez de rellenado: el expediente ya arrastra cinco errores de
recuento por escribir cifras que nadie midió, y un escenario de calidad
inventado es peor que ninguno — lo que hace es dar por resuelto el análisis de
rendimiento que nunca se hizo.

**Qué falta, en orden:** dejar correr la instrumentación, leer el percentil,
declarar E-2 con margen, y repetir para tablero y capacidad.
