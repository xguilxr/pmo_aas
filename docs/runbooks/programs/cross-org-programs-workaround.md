---
tipo: runbook
responsable: propietario
estado: vigente
revisado: 2026-08-19
revisar_cada: 180d
---

# Workaround: programas cross-empresa

**ID:** `RUN-PROG-001`
**Estado:** Vigente — reescrito el 2026-08-19 (ADR-037 dejó sin campo la Opción A)
**Relacionado:** [ADR-016](../../adr/README.md#adr-016--programas-cross-empresa-diferir-hasta-criterio-de-demanda) · ENH-043 (#180) · ADR-037

> **La solución estructural cambió de forma, no de estado.** ADR-016 difirió el
> programa N:M por falta de demanda. ADR-037 anota que el agrupador cross ya no
> tendría que ser un programa N:M: con el portafolio existiendo, sería **un
> portafolio por encima de la organización**. Sigue diferido —hoy
> `portfolios.organization_id` es obligatorio, así que un portafolio tampoco
> cruza empresas— pero cuando se retome, se retoma por ahí.

---

## Limitación actual

El modelo `programs` tiene **FK 1:1 a `organizations`**:

```text
programs (id, organization_id, name, ...)
```

Un programa vive en una sola organización. No hay soporte nativo para
programas que agrupen proyectos de **varias empresas** del grupo (ej.
un Programa Corporativo que cruce "Empresa A" y "Empresa B" del mismo
holding).

Ampliar a N:M (tabla `program_organizations`) está **diferido** según
ADR-016 hasta que se cumpla alguno de los triggers de demanda.

---

## Workaround: programa en la org "umbrella"

### 1. Identificar la org "umbrella"

Elige (o crea) una organización del tenant que represente el grupo
corporativo:

- **Si ya existe** una org "principal" (la matriz, la holding, etc.):
  úsala.
- **Si no existe**: créala desde `/admin/organizations` con un nombre
  representativo (ej. `Grupo XYZ`, `Holding Corporativo`).

### 2. Crear el programa cross-empresa en la org umbrella

Desde la pantalla de la org umbrella:

```
/pmo/organizations/{umbrella_id} → "Nuevo Programa"
```

Nombre sugerido: `Corporativo Q3 2026`, `Cross-empresa Innovación`, etc.

### 3. Etiquetar los proyectos por empresa real

Cada proyecto que entra al programa, aunque viva administrativamente
bajo la org umbrella, **se etiqueta con la empresa real**. Usa uno
de estos mecanismos:

#### ~~Opción A — usar el campo `business_unit` del Charter~~ ⛔ nunca existió

Esta opción era falsa desde que se escribió, y hay que decirlo porque es la que
el runbook recomendaba: el acta **no tiene** ningún `business_unit` de texto
libre. Tuvo un FK `business_unit_id` —que la migración 0109 soltó (US-199)— y ese
apuntaba a una tabla de unidades de negocio, no a un nombre de empresa que se
pudiera escribir. El único `business_unit` de texto libre del producto está en
`project_requests`, es la **solicitud** y no el proyecto, y desde US-200 se
llama «Área que solicita»: describe de dónde salió la petición, no a qué empresa
pertenece el trabajo.

#### Opción A (era la B) — usar Áreas del proyecto (US-062) ← **la recomendada**

Crea un Área por empresa (`Empresa A`, `Empresa B`) y asigna los miembros
correspondientes. Es la única de las tres que deja el dato en una entidad con la
que después se puede consultar y reportar participación por empresa.

#### Opción B (era la C) — convención en el nombre del proyecto

Prefijo `[Empresa A] Proyecto X`. Sirve para encontrarlos con el buscador
(`GET /projects?q=`), y para nada más: no hay forma de agrupar ni de sumar por
un prefijo de texto.

**Recomendación:** Áreas. Antes este runbook recomendaba la Opción A por
simplicidad, y esa simplicidad era que el campo no existía.

### 4. Reporte cross-empresa

El reporte ejecutivo del programa (US-038) muestra todos los proyectos
del programa. Para desglosar por empresa:

- **Por Área.** Es la vía que funciona: el organigrama del programa
  (`GET /programs/{id}/organigrama/export`) sale por área, así que el desglose
  por empresa cae solo si cada empresa es un Área.
- **Por nombre**, si se usó el prefijo: `GET /projects?program_id=…&q=[Empresa A]`.
- Lo que **no** existe: filtrar el listado por empresa. Los filtros de
  `GET /projects` son `organization_id`, `portfolio_id`, `program_id`, `phase`,
  `type`, `health`, prioridad y `q` — ninguno es «empresa subordinada», porque el
  modelo no tiene ese concepto. El bloque «Información general» del acta en PDF
  lista organización, portafolio y programa; `business_unit` no aparece ahí y
  nunca apareció.

---

## Limitaciones del workaround

1. **Navegación por org sigue siendo 1:1.** El sidebar muestra los
   proyectos bajo la org umbrella, no bajo "Empresa A" / "Empresa B"
   reales.
2. **Permisos por org no se propagan**: si el PM de "Empresa A" no
   tiene permisos sobre la org umbrella, no verá el proyecto. Solución:
   asigna membership directa al proyecto (US-074 user management).
3. **Reportes cross-empresa requieren Áreas.** No hay un dashboard nativo
   «ver proyectos por empresa subordinada», y tampoco un campo de empresa en el
   proyecto por el que filtrar.
4. **Cuentas analíticas (presupuesto consolidado por empresa)**: no
   soportadas; cada proyecto reporta su presupuesto al programa
   umbrella sin atribución por empresa.

---

## Cuándo migrar a soporte nativo

Ver [ADR-016](../../adr/README.md#adr-016--programas-cross-empresa-diferir-hasta-criterio-de-demanda).
Trigger para retomar:

- ≥3 grupos de clientes lo solicitan formalmente, **o**
- El cliente más grande (>50 proyectos) lo necesita estructuralmente, **o**
- La tasa de "programas con un solo proyecto cuyo PM es de otra
  empresa" supera el 20% del total (proxy de uso forzado).

Cuando se active el trigger, abre una US nueva con este scope:

1. Tabla `program_organizations` (m2m) + migración data.
2. Redesign de listados que filtran por `organization_id` único.
3. Reporting cross-empresa nativo (drill-down por empresa
   subordinada).
4. Permisos sobre programas cross-org.

ETA estimado: 3-4 días + tests.

---

## Caso de ejemplo

**Cliente:** Grupo XYZ (holding con Empresa A y Empresa B).

**Programa:** "Transformación Digital Q3 2026" — quiere agrupar:
- "ERP modernización" — Empresa A — PM: Daniel.
- "CRM upgrade" — Empresa B — PM: Mariana.

**Ejecución:**

1. Crea (si no existe) la org `Grupo XYZ` desde `/admin/organizations`.
2. Crea el programa `Transformación Digital Q3 2026` en `Grupo XYZ`.
3. Crea un Área por empresa en el catálogo del inquilino: `Empresa A` y
   `Empresa B`.
4. Crea los 2 proyectos bajo `Grupo XYZ` y asígnale a cada uno su Área:
   - `ERP modernización` → Área `Empresa A`.
   - `CRM upgrade` → Área `Empresa B`.
5. Asigna PMs y membership directa al proyecto.
6. Para el reporte cross-empresa: exporta el organigrama del programa
   (`GET /programs/{id}/organigrama/export`), que ya sale por área.

**Limitación que el workaround NO resuelve:** si Daniel y Mariana no
tienen rol global, no podrán navegar a `/pmo/organizations/Grupo XYZ`
salvo que reciban acceso explícito a esa org. El acceso al proyecto
se da vía membership.

---

## Referencias

- [ADR-016](../../adr/README.md#adr-016--programas-cross-empresa-diferir-hasta-criterio-de-demanda)
- ENH-043 (#180) — issue de origen.
- US-062 — Áreas/Recursos.
- US-007 — Charter MVP.
