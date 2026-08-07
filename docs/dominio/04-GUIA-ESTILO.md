---
tipo: guia
responsable: propietario
estado: vigente
revisado: 2026-08-06
revisar_cada: 90d
---

# Guía de estilo — lengua, números y fechas

Cierra **MCS LEN-03**: «DEBE existir una guía de estilo que fije el tratamiento
personal, la política de anglicismos y el formato de números y fechas».

Aplica a **todo texto que ve una persona usuaria**: interfaz, mensajes de error,
correos, informes generados y documentos exportados. No aplica a nombres de
variables, columnas ni claves de API, que se rigen por el glosario
([`02-GLOSARIO.md`](02-GLOSARIO.md)).

> **Decisiones del owner, 2026-08-06.** Cada regla de abajo responde a una
> pregunta concreta. Donde la plataforma hoy hace otra cosa, se dice.

---

## 1. Tratamiento personal

**Informal, en tercera persona.** Ni «usted» ni «tú»: se le habla a la persona
sin dirigirse a ella gramaticalmente.

| Se escribe | No se escribe |
|---|---|
| «No se pudo guardar el proyecto» | «No pudiste guardar el proyecto» |
| «El informe está listo» | «Tu informe está listo» |
| «Faltan tres campos obligatorios» | «Te faltan tres campos» |
| «Se requiere permiso de administrador» | «Necesitas permiso de administrador» |

**Por qué tercera persona y no tuteo.** El producto es multiinquilino y su texto
lo leen perfiles muy distintos —desde dirección hasta quien captura tareas—.
La tercera persona no se equivoca de registro con ninguno.

**El imperativo sí se permite** cuando es una instrucción de acción, porque la
alternativa es artificiosa: «Seleccioná un archivo» → **«Seleccionar archivo»**.
En botones y etiquetas, infinitivo.

---

## 2. Anglicismos

**Se permiten los que el dominio ya usa como término propio.** Traducirlos
produce textos que quien trabaja en PMO no reconoce.

**Admitidos** —medidos sobre la interfaz actual, no elegidos a dedo—:

`gap` · `status` · `tracking` · `issue` · `scope` · `owner` · `dashboard` ·
`baseline` · `milestone` · `sprint` · `backlog` · `stakeholder` · `kickoff` ·
`feedback`

**Se traducen siempre**, porque tienen equivalente asentado y no son término
técnico:

| Se escribe | No se escribe |
|---|---|
| guardar | *save* |
| eliminar | *delete* |
| cargar / subir | *upload* |
| descargar | *download* |
| ajustes | *settings* |
| buscar | *search* |
| cancelar | *cancel* |
| filtro | *filter* |

**Regla para lo no listado:** si el término aparece en
[`02-GLOSARIO.md`](02-GLOSARIO.md), manda el glosario. Si no aparece y existe
equivalente en español que un profesional de PMO reconocería, se traduce.

**Sin cursivas ni comillas** para los admitidos: son parte del vocabulario, no
citas de otro idioma. Se escriben en minúscula y se pluralizan en español
(«los gaps», «tres milestones»).

---

## 3. Números

| Regla | Valor | Ejemplo |
|---|---|---|
| Separador de miles | coma | `1,234` · `1,250,000` |
| Separador decimal | punto | `1,234.56` |
| Decimales en cantidades | **2** | `1,234.50` |
| Decimales en porcentajes | **0** | `87%` |
| Moneda | símbolo antes, 2 decimales | `$1,234.50` |

**Es lo que la plataforma ya hace**, y no por casualidad: la interfaz usa
`es-MX`, cuya convención es exactamente miles con coma y decimal con punto.

**El porcentaje no lleva decimales nunca.** Un `87.3%` de avance sugiere una
precisión que el dato no tiene: sale de contar tareas hechas sobre tareas
totales, y la tercera cifra es ruido. Redondeo al entero más cercano.

**Cero no es lo mismo que sin dato** (MCS DAT-12). Un valor ausente se escribe
`—`, nunca `0`. Está implementado en [`lib/sin-dato.ts`](../../apps/web/lib/sin-dato.ts).

---

## 4. Fechas y horas

| Regla | Formato | Ejemplo |
|---|---|---|
| Fecha | `dd-mm-aaaa` | `06-08-2026` |
| Hora | **24 h**, `HH:mm` | `14:30` |
| Fecha y hora | `dd-mm-aaaa HH:mm` | `06-08-2026 14:30` |

**Sin meses en letra.** `06-08-2026`, no «6 ago 2026»: la forma numérica es
inequívoca una vez fijado el orden, y no cambia de ancho.

**Guion, no barra.** `06-08-2026`, no `06/08/2026`.

### Lo que hoy diverge

Medido el 2026-08-06: la interfaz llama a `toLocaleString("es-MX", { dateStyle:
"medium", timeStyle: "short" })`, que produce **«6 ago 2026, 2:30 p.m.»** — mes
abreviado en letra y hora en 12 horas.

**Los números ya cumplen; las fechas y horas no.** Es trabajo pendiente, no una
excepción declarada: hace falta un formateador único que aplique esta guía y un
control que impida volver a llamar a `toLocaleString` con formato de fecha
suelto por la aplicación.

---

## 5. Mayúsculas y puntuación

- **Títulos y botones en mayúscula solo inicial:** «Nuevo proyecto», no «Nuevo
  Proyecto» ni «NUEVO PROYECTO».
- **Los nombres de estado van en minúscula** dentro de una frase: «el proyecto
  está en riesgo», no «en Riesgo».
- **Sin punto final** en etiquetas, títulos, botones y celdas de tabla. **Con
  punto** en mensajes de error y textos de ayuda, que son oraciones.
- **Comillas angulares** («») para citas en documentos; las rectas se reservan
  para código.

---

## 6. Mensajes de error

Los rige **MCS LEN-02**, y esta guía no lo repite: todo mensaje dice **qué
ocurrió, por qué y qué hacer**. El mecanismo está en
[`core/errors.py`](../../apps/api/app/core/errors.py) —`mensaje(que=, porque=,
accion=)`, con las tres partes obligatorias— y el control en
`scripts/check_mensajes.py`.

Lo que esta guía añade es el registro: tercera persona, sin culpar a quien lee.

| Se escribe | No se escribe |
|---|---|
| «No se pudo guardar el proyecto porque falta el nombre. Completar el campo y reintentar.» | «Error al guardar. Ingresaste mal los datos.» |
