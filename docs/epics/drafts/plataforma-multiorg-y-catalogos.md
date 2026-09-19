---
tipo: gestion
responsable: propietario
estado: borrador
revisado: 2026-09-19
revisar_cada: 30d
---

# Plataforma multi-organización y catálogos de proyecto — plan de desarrollo

**Origen:** batch del owner del 2026-09-19, refinado en dos rondas.
**Estado:** Fase B cerrada. Issues #623-#641 creados con `status:triage`.
**IDs:** BUG-103 #623, BUG-104 #624 · US-273 #625 … US-289 #641 ·
DEC-040 … DEC-045
(derivados con `proximo_id.py` + GitHub el 2026-09-19).

---

## Qué pide el owner

1. Poder vaciar, desactivar y borrar un inquilino desde el superadmin.
2. Arreglar el bloqueo por recursos asignados a proyectos de otra
   organización.
3. Navegación que guíe a un inquilino nuevo a crear y configurar su
   organización.
4. Módulo de creación de portafolio, programa y proyecto.
5. Tablero general de todas las organizaciones asignadas, con sus
   portafolios, programas y proyectos segmentados.
6. Landing general; el resto de la plataforma vive dentro de una
   organización.
7. En admin de organizaciones: paneles de portafolios y programas con
   agregar, listar, editar y retirar. Retirar desasigna proyectos, no los
   borra.
8. Configuración por inquilino de los atributos del proyecto: tipo y fase.
   El RAID **no** se configura (decisión del owner, segunda ronda).

---

## Qué existe hoy

| Pieza | Dónde | Estado |
|---|---|---|
| Desactivar inquilino | `DELETE /superadmin/tenants/{id}` | Existe, con botón en la ficha |
| Borrar inquilino | `DELETE /superadmin/tenants/{id}/permanent` | Existe, con confirmación por slug |
| Vaciar datos del inquilino | — | **No existe** |
| CRUD de portafolios y programas | `endpoints/organizations.py` | Completo, con papelera de dos pasos |
| Tarjetas de organización con conteos | `GET /organizations/panels` | Cuenta portafolios, programas, proyectos activos y salud |
| Jerarquía en admin | `components/org-hierarchy-section.tsx` | Árbol con crear, editar y eliminar |
| Contexto de organización activa | `components/organizacion-activa.tsx` | Proveedor + switcher en el header (US-205) |
| Vocabulario del proyecto | `dominio/proyecto.py` | Enum cerrado: 5 fases, 4 tipos |
| Landing | `apps/web/app/page.tsx` | Solo redirige a `/dashboard` |
| Onboarding | — | No existe |
| Catálogos por inquilino | — | No existen |

---

## El bloqueo por recursos cruzados

El owner no puede borrar un recurso de una organización porque tiene
participaciones en proyectos de otra. Es un defecto, y tiene tres capas.

**La capa del modelo está bien.** `actors.organization_id` es nullable a
propósito: `NULL` significa recurso global del inquilino, el mismo patrón
que `areas.organization_id` (BUG-061). Un actor global en un proyecto de
cualquier organización es legítimo.

**La capa de la API no valida.** `project_directory.py::create_participation`
comprueba que el actor sea del inquilino y nada más. Un actor de la
organización A se asigna hoy a un proyecto de la organización B sin que
nada lo impida.

**La capa de la UI tampoco filtra.** `directory/DirectoryView.tsx` llama a
`listActors()` sin parámetros, así que el selector ofrece todos los actores
del inquilino.

**Y el borrado cuenta lo que no debe.** `areas.py::delete_actor` ya se acotó
el 2026-09-11 a proyectos vivos y en fase no terminal, pero sigue sin
filtrar por organización: una participación cruzada —que nunca debió
existir— bloquea el borrado.

Hay datos viejos que arrastran esto. `scripts/diagnostico_participaciones_actor.py`
ya lista las participaciones de un actor con su organización y su fase; el
diagnóstico cruzado de todo el inquilino todavía no existe.

---

## Bloques de trabajo

Siete bloques. El 0 desbloquea al owner hoy. E precede a F; B precede a C;
A y D son independientes.

### Bloque 0 — Recursos cruzados entre organizaciones

| ID | Epic | Qué entrega |
|---|---|---|
| BUG-103 #623 | EP017 | `create_participation` rechaza un actor cuya organización no es la del proyecto; el actor global (`organization_id IS NULL`) sigue siendo asignable. El selector de personas filtra por la organización del proyecto |
| BUG-104 #624 | EP017 | `delete_actor` cuenta como bloqueantes solo los proyectos de la organización del actor. Las participaciones cruzadas se nombran aparte, como dato a limpiar, y no impiden el borrado |
| US-273 #625 | EP017 | `scripts/diagnostico_participaciones_cruzadas.py` (solo lectura) + acción de limpieza que desactiva las participaciones cruzadas con reporte por organización y auditoría |

### Bloque A — Ciclo de vida del inquilino

Desactivar y borrar ya funcionan desde `/superadmin/tenants/[id]`. Falta
vaciar. Todo lo corre el owner desde la interfaz, no por script (D8).

| ID | Epic | Qué entrega |
|---|---|---|
| US-274 #626 | EP010 | `GET /superadmin/tenants/{id}/wipe/preview` (conteo por tabla, sin borrar) y `POST /superadmin/tenants/{id}/wipe?confirm_slug=` con inventario de tablas declarado y trinquete que falla si aparece una tabla con `tenant_id` fuera del inventario |
| US-275 #627 | EP010 | Botón «Vaciar datos» en la ficha del inquilino, con el preview de conteos y la confirmación por slug, junto a «Desactivar» y «Borrar permanente» |

El inventario declarado es el punto del diseño. Son 32 modelos con
`tenant_id`: un vaciado que recorra las tablas por reflexión se salta la
siguiente que se agregue, y un vaciado incompleto deja un inquilino que
parece limpio y no lo está. El trinquete vive en los tests de API.

### Bloque B — Landing general y navegación por organización

| ID | Epic | Qué entrega |
|---|---|---|
| US-276 #628 | EP002, EP004 | `GET /inicio/organizaciones`: árbol organización → portafolios → programas con conteos de proyectos y salud, filtrado por `user_scope_assignments` |
| US-277 #629 | EP004 | Pantalla `/organizaciones`: tarjeta por organización con su jerarquía segmentada y su semáforo |
| US-278 #630 | EP004, EP007 | Entrar y salir de una organización: fija la organización activa, migas de pan, «ver todas» y redirección post-login |

`/dashboard` sigue siendo el tablero de una organización. La landing es una
pantalla nueva, no un reemplazo.

### Bloque C — Onboarding del inquilino nuevo

Epic nueva: `EP022-onboarding.md`.

| ID | Epic | Qué entrega |
|---|---|---|
| US-279 #631 | EP022 | Estado de onboarding en `tenants.settings.onboarding` + `GET/POST /onboarding/estado` con la lista de pasos y su avance |
| US-280 #632 | EP022 | Wizard `/bienvenida`: organización → portafolio → programa → tipos y fases → invitaciones, con avance guardado y salida en cualquier paso |
| US-281 #633 | EP002, EP005 | Creación de portafolio, programa y proyecto como formularios reutilizables, alcanzables desde el wizard, la landing y el admin |

### Bloque D — Paneles de portafolios y programas

| ID | Epic | Qué entrega |
|---|---|---|
| US-282 #634 | EP002, EP007 | Panel de portafolios en tabla: nombre, código, responsable, programas, proyectos, estado; botón «Agregar» y acción «Editar» |
| US-283 #635 | EP002, EP007 | Panel de programas en tabla: nombre, portafolio, responsable, proyectos, estado; mismos botones |
| US-284 #636 | EP002 | «Retirar»: desactiva el portafolio o el programa y **desasigna** sus proyectos, sin borrarlos. Auditoría con el conteo de proyectos movidos |

Editar toca solo campos descriptivos. El árbol actual se sustituye por dos
paneles; la papelera de dos pasos se conserva y queda separada de
«Retirar».

### Bloque E — Catálogos del proyecto: infraestructura

| ID | Epic | Qué entrega |
|---|---|---|
| US-285 #637 | EP007 | Tabla `tenant_catalog_values` + migración + siembra de los valores actuales por inquilino + servicio `services/catalogos.py` |
| US-286 #638 | EP007 | API `/admin/catalogos/{catalogo}` (listar, crear, editar, reordenar, desactivar) y validación de proyectos contra el catálogo del inquilino |
| US-287 #639 | EP007 | Pantalla `/admin/catalogos` con dos pestañas: Tipos de proyecto · Fases |

Dos catálogos, no más: `tipo_proyecto` y `fase_proyecto`. La tabla nace
genérica (`catalogo` como columna) para no rehacerla si mañana entra un
tercero, y eso es todo lo que se generaliza.

Forma de la tabla: `tenant_id`, `catalogo`, `clave`, `etiqueta`, `orden`,
`activo`, `metadata` JSON, `deleted_at`. Único por (`tenant_id`,
`catalogo`, `clave`).

La siembra usa las claves canónicas actuales, así que ningún registro
existente queda apuntando a un valor que desapareció y no hay migración de
datos. Ninguna fila queda marcada como intocable (D9).

### Bloque F — Tipo y fase configurables

| ID | Epic | Qué entrega |
|---|---|---|
| US-288 #640 | EP005 | Tipos de proyecto del inquilino: alta, edición y baja, sin valores de sistema. Un tipo en uso se desactiva, no se borra. Uso en formularios, filtros y gráficos |
| US-289 #641 | EP005 | Fases del inquilino: alta, edición y reordenamiento, **máximo 8**, con banderas `activa` y `terminal`; las transiciones se derivan del orden |

La fase no es una etiqueta suelta: `FASES_ACTIVAS`, `FASES_TERMINALES` y
`TRANSICIONES` gobiernan KPIs, capacidad y cortes. Por eso cada fase declara
si cuenta como activa y si es terminal, en vez de dejar que el nombre lo
insinúe. Validación mínima: al menos una fase activa, al menos una terminal
y no más de ocho en total.

---

## Decisiones a registrar

| ID | Decisión | Resolución |
|---|---|---|
| DEC-040 | Dónde viven los catálogos | Tabla propia, no `tenants.settings`. Se consultan por fila, se ordenan y se auditan; un JSON no hace nada de eso |
| DEC-041 | Qué pasa con los proyectos al retirar un portafolio | Van a «Portafolio General» del mismo inquilino, que `services/jerarquia.py` ya crea. Dejarlos en `NULL` rompe el invariante `program_id ⇒ portfolio_id` |
| DEC-042 | Hasta dónde llega una fase configurable | Se agregan, se renombran y se reordenan, con tope de 8. El grafo de transiciones se deriva del orden; no se edita a mano (D10) |
| DEC-043 | Relación entre landing general y `/dashboard` | Conviven. La landing es multi-organización; `/dashboard` es de una |
| DEC-044 | Recursos entre organizaciones | Un actor con organización solo participa en proyectos de esa organización. El actor global (`organization_id IS NULL`) participa en cualquiera. No se crea una figura de «préstamo» |
| DEC-045 | Qué sobrevive al vaciado | El inquilino, su `settings`, su marca, sus usuarios y sus membresías. Todo lo demás se borra, y el inquilino queda como recién aprovisionado — que es justo donde arranca el onboarding del Bloque C |

Cerradas por el owner en la segunda ronda: el vaciado se corre desde el
superadmin y no por script (D8); los cuatro tipos actuales se siembran como
valores editables y borrables, sin figura de «tipo de sistema» (D9); las
fases se agregan y se modifican con tope de ocho (D10); el RAID **no** se
vuelve configurable — ni el modo de riesgo ni los estados de los ítems
(D11). El kanban de RAID y la matriz de severidad se quedan como están.

---

## Qué va a morder

1. **`test_us202_vocabulario.py`** ata `lib/api/projects.ts` al enum del
   backend. Con catálogo abierto, el trinquete tiene que atar la siembra
   inicial, no la lista viva.
2. **Colores de gráficos** (ADR-023) son cuatro, en orden fijo. Ocho fases y
   un número libre de tipos necesitan asignación por índice con repetición
   declarada.
3. **RLS** (W3, US-240–242) sigue en curso. La tabla nueva nace con su
   política, no después.
4. **`check_impacto_documental.py`** exigirá tocar EP002, EP005, EP007,
   EP010 y EP017 en los mismos bloques.
5. **Ventanas de compatibilidad** (`core/compatibilidad.py`): el vocabulario
   de US-202 tiene una abierta. El catálogo se siembra con las claves
   canónicas para no abrir una segunda.
6. **La auditoría del vaciado** se borra a sí misma si se escribe antes. Se
   escribe después del borrado, o no queda rastro de quién vació qué.
7. **Sin valores de sistema** (D9), un inquilino puede quedarse sin ningún
   tipo de proyecto. El alta de proyecto necesita decir qué falta y llevar a
   `/admin/catalogos`, no romperse con un desplegable vacío.
