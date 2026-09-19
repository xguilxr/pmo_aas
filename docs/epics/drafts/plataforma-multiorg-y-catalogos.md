---
tipo: gestion
responsable: propietario
estado: borrador
revisado: 2026-09-19
revisar_cada: 30d
---

# Plataforma multi-organización y catálogos por inquilino — plan de desarrollo

**Origen:** batch del owner del 2026-09-19.
**Estado:** Fase A (diseño). Sin issues creados. Espera el OK del owner.
**IDs reservados:** US-273 … US-289 · DEC-040 … DEC-043
(derivados con `proximo_id.py` + GitHub el 2026-09-19).

---

## Qué pide el owner

Siete frentes, en las palabras del batch:

1. Wipe de la base de datos y borrado de un inquilino.
2. Navegación que guíe a un inquilino nuevo a crear y configurar su
   organización.
3. Módulo de creación de portafolio, programa y proyecto.
4. Tablero general de todas las organizaciones asignadas, con sus
   portafolios, programas y proyectos segmentados.
5. Landing general; el resto de la plataforma vive dentro de una
   organización.
6. En admin de organizaciones: paneles de portafolios y programas con
   agregar, listar, editar y retirar. Retirar desasigna proyectos, no los
   borra.
7. Configuración por inquilino de los catálogos del proyecto: tipo, fase y
   RAID (modo de riesgo y estados de los ítems).

---

## Qué existe hoy

Lo relevante, para no rediseñar lo que ya está.

| Pieza | Dónde | Estado |
|---|---|---|
| CRUD de portafolios y programas | `endpoints/organizations.py` | Completo, con papelera de dos pasos |
| Tarjetas de organización con conteos | `GET /organizations/panels` | Cuenta portafolios, programas, proyectos activos y salud |
| Jerarquía en admin | `components/org-hierarchy-section.tsx` | Árbol con «Nuevo portafolio», «Nuevo programa», editar y eliminar |
| Contexto de organización activa | `components/organizacion-activa.tsx` | Proveedor + switcher en el header (US-205) |
| Vocabulario del proyecto | `dominio/proyecto.py` | Enum cerrado: 5 fases, 4 tipos |
| Estados RAID | `lib/api/modules.ts` | Cuatro fijos: abierto, en progreso, on hold, resuelto |
| Riesgo | `models/modules.py` | Probabilidad × impacto → severidad. Sin modo alterno |
| Borrado de inquilino | `DELETE /superadmin/tenants/{id}/permanent` | Existe, con cascada |
| Landing | `apps/web/app/page.tsx` | Solo redirige a `/dashboard` |
| Onboarding | — | No existe |
| Catálogos por inquilino | — | No existen |

Huecos reales contra lo pedido: onboarding, landing general, tablero
multi-organización, paneles en tabla, semántica de «retirar» y todo el
módulo de catálogos.

---

## Bloques de trabajo

Siete bloques. E precede a F y G; B precede a C; A y D son independientes.

### Bloque A — Reseteo de datos y borrado de inquilino

Lo ejecuta el owner. Claude entrega el runbook y el script, nunca el
comando (CLAUDE.md §0.3; `guard_irreversible.py` deniega `alembic`,
`DROP` y `TRUNCATE`).

| ID | Epic | Qué entrega |
|---|---|---|
| US-273 | EP010 | Runbook `docs/ops/reseteo-de-datos.md` + `scripts/ops/resetear_datos.py` con `--dry-run` por default, conteo por tabla antes y después, y confirmación por slug |

El borrado del inquilino usa el endpoint que ya existe; no se escribe
código nuevo para eso.

### Bloque B — Landing general y navegación por organización

| ID | Epic | Qué entrega |
|---|---|---|
| US-274 | EP002, EP004 | `GET /inicio/organizaciones`: árbol organización → portafolios → programas con conteos de proyectos y salud, filtrado por `user_scope_assignments` |
| US-275 | EP004 | Pantalla `/organizaciones`: tarjeta por organización con su jerarquía segmentada y su semáforo |
| US-276 | EP004, EP007 | Entrar y salir de una organización: fija la organización activa, migas de pan, «ver todas» y redirección post-login |

`/dashboard` sigue siendo el tablero de una organización. La landing es una
pantalla nueva, no un reemplazo.

### Bloque C — Onboarding del inquilino nuevo

Epic nueva: `EP022-onboarding.md`.

| ID | Epic | Qué entrega |
|---|---|---|
| US-277 | EP022 | Estado de onboarding en `tenants.settings.onboarding` + `GET/POST /onboarding/estado` con la lista de pasos y su avance |
| US-278 | EP022 | Wizard `/bienvenida`: organización → portafolio → programa → catálogos → invitaciones, con avance guardado y salida en cualquier paso |
| US-279 | EP002, EP005 | Creación de portafolio, programa y proyecto como formularios reutilizables, alcanzables desde el wizard, la landing y el admin |

### Bloque D — Paneles de portafolios y programas

| ID | Epic | Qué entrega |
|---|---|---|
| US-280 | EP002, EP007 | Panel de portafolios en tabla: nombre, código, responsable, programas, proyectos, estado; botón «Agregar» y acción «Editar» |
| US-281 | EP002, EP007 | Panel de programas en tabla: nombre, portafolio, responsable, proyectos, estado; mismos botones |
| US-282 | EP002 | «Retirar»: desactiva el portafolio o el programa y **desasigna** sus proyectos, sin borrarlos. Auditoría con el conteo de proyectos movidos |

Editar toca solo campos descriptivos. El árbol actual se sustituye por dos
paneles; la papelera de dos pasos se conserva y queda separada de
«Retirar».

### Bloque E — Catálogos por inquilino: infraestructura

| ID | Epic | Qué entrega |
|---|---|---|
| US-283 | EP007 | Tabla `tenant_catalog_values` + migración + siembra de los valores de sistema por inquilino + servicio `services/catalogos.py` |
| US-284 | EP007 | API `/admin/catalogos/{catalogo}` (listar, crear, editar, reordenar, desactivar) y validación de proyectos y RAID contra el catálogo del inquilino |
| US-285 | EP007 | Pantalla `/admin/catalogos` con pestañas: Tipos de proyecto · Fases · RAID |

Forma de la tabla: `tenant_id`, `catalogo`, `clave`, `etiqueta`, `orden`,
`activo`, `es_sistema`, `metadata` JSON, `deleted_at`. Único por
(`tenant_id`, `catalogo`, `clave`).

Los valores actuales se siembran con `es_sistema = true`: se renombran y se
reordenan, no se borran. Así ningún registro existente queda apuntando a
una clave que desapareció y no hay migración de datos.

### Bloque F — Tipo y fase configurables

| ID | Epic | Qué entrega |
|---|---|---|
| US-286 | EP005 | Tipos de proyecto del inquilino: alta, edición, desactivación y uso en formularios, filtros y gráficos |
| US-287 | EP005 | Fases del inquilino: etiqueta, orden y banderas `activa` / `terminal`; las transiciones se derivan del orden |

La fase no es una etiqueta suelta: `FASES_ACTIVAS`, `FASES_TERMINALES` y
`TRANSICIONES` gobiernan KPIs, capacidad y cortes. Por eso cada fase
declara si cuenta como activa y si es terminal, en vez de dejar que el
nombre lo insinúe.

### Bloque G — RAID configurable

| ID | Epic | Qué entrega |
|---|---|---|
| US-288 | EP006 | Modo de riesgo por inquilino: `prioridad` (escala simple) o `matriz` (probabilidad × impacto, lo actual). Formularios, columnas y matriz de riesgo siguen el modo |
| US-289 | EP006 | Estados RAID del inquilino: catálogo propio con orden y bandera `final`; el kanban dibuja una columna por estado activo |

Los campos de detención (`on_hold_*`) se atan a una bandera
`requiere_detencion` del estado, no al literal `on_hold`. Si no, renombrar
el estado apaga la captura de la razón y la dependencia.

---

## Decisiones a registrar

| ID | Decisión | Propuesta |
|---|---|---|
| DEC-040 | Dónde viven los catálogos | Tabla propia, no `tenants.settings`. Se consultan por fila, se ordenan y se auditan; un JSON no hace nada de eso |
| DEC-041 | Qué pasa con los proyectos al retirar un portafolio | Van a «Portafolio General» del mismo inquilino, que `services/jerarquia.py` ya crea. Dejarlos en `NULL` rompe el invariante `program_id ⇒ portfolio_id` |
| DEC-042 | Hasta dónde llega una fase configurable | Etiqueta, orden y banderas. El grafo de transiciones se deriva; no se edita a mano |
| DEC-043 | Relación entre landing general y `/dashboard` | Conviven. La landing es multi-organización; `/dashboard` es de una |

---

## Qué va a morder

1. **`test_us202_vocabulario.py`** ata `lib/api/projects.ts` al enum del
   backend. Con catálogo abierto, el trinquete debe atar los valores de
   sistema, no la lista completa.
2. **Colores de gráficos** (ADR-023) son cuatro, en orden fijo. Un catálogo
   abierto necesita asignación por índice con repetición declarada.
3. **RLS** (W3, US-240–242) sigue en curso. La tabla nueva nace con su
   política, no después.
4. **`check_impacto_documental.py`** exigirá tocar EP002, EP005, EP006 y
   EP007 en los mismos bloques.
5. **Ventanas de compatibilidad** (`core/compatibilidad.py`): el vocabulario
   de US-202 tiene una abierta. El catálogo se siembra con las claves
   canónicas para no abrir una segunda.

---

## Qué falta decidir antes de arrancar

| # | Pregunta | Bloquea |
|---|---|---|
| D8 | ¿El wipe es contra producción en Railway, o solo local y QA? ¿Qué inquilino se borra? | Bloque A |
| D9 | ¿Los cuatro tipos de sistema se conservan como base, o el inquilino parte de cero? | US-286 |
| D10 | ¿Las fases se agregan de verdad, o solo se renombran y reordenan? | US-287 |
| D11 | ¿El modo de riesgo se elige una vez, o se puede cambiar con datos ya cargados? | US-288 |

D8 es irreversible y no tiene supuesto seguro. Las otras tres tienen
propuesta en este documento y se pueden cerrar al aprobar el plan.
