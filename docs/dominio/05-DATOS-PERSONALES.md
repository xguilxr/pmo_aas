---
tipo: referencia
responsable: propietario
estado: vigente
revisado: 2026-08-06
revisar_cada: 90d
---

# Inventario de datos personales

Cierra **MCS REQ-03**: «DEBE identificarse el inventario de datos personales
tratados por el sistema».

**Se derivó del esquema real** (`apps/api/app/models/`), no de lo que se
recordaba guardar. Es la diferencia entre un inventario y una lista de buenas
intenciones: los dos campos de `audit_log` y el de `password_reset_tokens` no
los habría escrito nadie de memoria, y son los más sensibles del conjunto.

> **Alcance declarado.** Este documento identifica **qué** dato personal se
> trata, dónde vive y para qué. **No** es una política de privacidad ni un
> registro de actividades de tratamiento del RGPD: eso requiere asesoría legal
> y excede la competencia declarada del producto
> ([`06-COMPETENCIA.md`](06-COMPETENCIA.md)). Es el insumo para redactarlos.

---

## 1. Lo que se trata hoy

### Personas usuarias de la plataforma

| Tabla | Campo | Tipo | Para qué |
|---|---|---|---|
| `users` | `email` | obligatorio | Identificador de acceso y destino de notificaciones |
| `users` | `full_name` | obligatorio | Atribución de acciones en la interfaz y en informes |
| `users` | *hash* de contraseña | obligatorio | Autenticación. **No es la contraseña**: es un derivado irreversible |
| `users` | `privacy_accepted_at`, `privacy_version` | opcional | Consentimiento del aviso de privacidad y a qué versión (ASVS 8.3.3). Nulos = no ha aceptado |
| `admin_otp_codes` | *resumen* del código, `user_id` | efímero | Segundo factor de administración (ASVS 4.3.1). Caduca a los diez minutos; solo se guarda el resumen, nunca el código |

### Personas registradas *sobre* las que se guarda información

Son terceros que **no necesariamente usan la plataforma**. Quien los da de alta
es la organización cliente, no la persona. Esto importa para la base legal.

| Tabla | Campos | Para qué |
|---|---|---|
| `stakeholders` | `full_name`, `email`, `phone` | Matriz de interesados del proyecto |
| `actors` | `name`, `email`, `phone` | Asignación de tareas y cálculo de carga |

### Datos técnicos que identifican indirectamente

| Tabla | Campos | Para qué | Nota |
|---|---|---|---|
| `audit_log` | `ip_address`, `user_agent`, `user_id` | Trazabilidad de acciones | **De solo anexado**: no se puede borrar ni modificar (migración 0097, AM-08) |
| `password_reset_tokens` | `ip_address` | Detección de abuso en recuperación de contraseña | |

**La IP es dato personal** en la mayoría de marcos, aunque no lo parezca. Está
aquí por eso.

### Contenido libre — el riesgo que no está en ninguna columna

`meeting_minutes`, `assistant_messages`, descripciones de tareas, actas y
documentos subidos son **campos de texto libre**. Quien los escribe puede meter
ahí cualquier dato personal, y el esquema no lo puede impedir ni enumerar.

Se declara explícitamente porque un inventario que solo lista columnas tipadas
da una falsa sensación de completitud.

---

## 2. Lo que **no** se trata

Declarado con la misma seriedad que lo anterior, porque acota el riesgo:

- **Ningún dato de pago.** No existe modelo de suscripción ni de cobro en el
  esquema — se verificó el 2026-08-06. Cuando entren los planes por niveles, el
  medio de pago **debe delegarse a la pasarela** y no guardarse aquí; este
  documento se actualiza en ese momento.
- **Ninguna categoría especial:** salud, biometría, origen étnico, afiliación
  sindical, orientación, convicciones. El producto no tiene campo para nada de
  eso y no debería adquirirlo sin decisión expresa.
- **Sin documento de identidad, dirección postal ni fecha de nacimiento.**

---

## 3. Quién es quién

| Papel | Quién |
|---|---|
| Responsable del tratamiento | **La organización cliente** (el inquilino). Decide a quién da de alta y para qué |
| Encargado del tratamiento | **La plataforma**. Trata los datos por cuenta del inquilino |
| Persona interesada | Quien usa la plataforma, y los interesados y actores registrados por el inquilino |

Esta distinción no es formalismo: **la plataforma no elige qué datos entran**.
Un inquilino que registra el teléfono de un interesado lo hace bajo su propia
base legal, y quien debe poder responder a esa persona es él.

---

## 4. Dónde viven y por cuánto tiempo

| Dónde | Qué |
|---|---|
| Postgres (Railway) | Todo lo tabular de arriba |
| Almacenamiento de objetos | Documentos subidos y sus adjuntos |
| Sentry | Trazas de error. **Pueden arrastrar identificadores** si aparecen en el contexto del fallo |
| Proveedor de correo (Resend) | Dirección de correo de cada destinatario, para poder entregar |
| Proveedor de IA | Lo que se le envía al generar informes. Ver [`06-COMPETENCIA.md`](06-COMPETENCIA.md) |

**No hay política de retención declarada, y es una carencia real.** Hoy nada
borra nada: el borrado es lógico (`deleted_at`) y `audit_log` es de solo
anexado por diseño. Definir plazos exige decidir qué se conserva por
trazabilidad frente a qué se elimina a petición — y esas dos cosas chocan
justamente en `audit_log`.

Queda anotado como pendiente, no resuelto.

---

## 5. Derechos de la persona interesada

**Resuelto el 2026-08-07** (ASVS 8.3.2, ADR-034). Era la carencia más seria de
este inventario y ya no lo es.

- **Acceso:** `GET /api/v1/users/me/datos-personales` devuelve en JSON la cuenta,
  las preferencias, el registro de actividad propio y las notificaciones.
- **Supresión:** `POST /api/v1/users/me/datos-personales/suprimir` **anonimiza**
  —no borra—. Las filas se quedan y dejan de apuntar a nadie, porque el borrado
  físico choca con `audit_log`, que es de solo anexado por diseño, y con el
  historial del proyecto, que es dato del inquilino. Exige re-teclear el correo
  y cierra la sesión.

**El límite de §1 sigue en pie y ahora va declarado en el propio archivo
exportado:** el texto libre que menciona a alguien por su nombre no se barre.
Buscarlo exigiría recorrer todo el contenido con coincidencia difusa y decidir a
mano cada acierto. Se dice, en vez de fingir que la copia es completa.

Las dos acciones quedan en la auditoría: una exportación de datos personales es
una lectura masiva de datos personales, y tiene que dejar rastro.

---

## 6. Qué hacer al cambiar el esquema

**Añadir un campo personal obliga a actualizar este documento en el mismo
bloque de trabajo** (CLAUDE.md §0.2). En particular al tocar `users`,
`stakeholders`, `actors`, `audit_log` o al introducir pagos.

El ER generado ([`er-generado.md`](../architecture/er-generado.md)) se deriva del
modelo y sirve para contrastar que este inventario no se quedó atrás.
