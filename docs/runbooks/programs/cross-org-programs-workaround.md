---
tipo: runbook
responsable: propietario
estado: vigente
revisado: 2026-08-12
revisar_cada: 180d
---

# Workaround: programas cross-empresa

**ID:** `RUN-PROG-001`
**Estado:** Vigente — 2026-04-29
**Relacionado:** [ADR-016](../../adr/README.md#adr-016--programas-cross-empresa-diferir-hasta-criterio-de-demanda) · ENH-043 (#180)

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

#### Opción A — usar el campo `business_unit` del Charter

Captura la empresa real ahí (ej. `business_unit = "Empresa A"`). Es
texto libre y permite filtrar luego en reportes.

#### Opción B — usar Áreas del proyecto (US-062)

Crea un Área por empresa (`Área: Empresa A`, `Área: Empresa B`) y
asigna los miembros correspondientes. Esto te permite reportar
participación por empresa.

#### Opción C — convención en el nombre del proyecto

Prefijo `[Empresa A] Proyecto X`. Útil para listados rápidos pero
limitante para reportes estructurados.

**Recomendación owner:** usa la Opción A por simplicidad. Complementa con
la Opción B cuando el proyecto necesita stakeholders o áreas dedicadas
por empresa.

### 4. Reporte cross-empresa

El reporte ejecutivo del programa (US-038) muestra todos los proyectos
del programa. Para desglosar por empresa:

- En el listado de proyectos del programa, filtra por
  `business_unit = "Empresa A"` (header de columna).
- En reportes PDF, el bloque "Información general" del proyecto incluye
  `business_unit`. Quedan agrupables manualmente.

---

## Limitaciones del workaround

1. **Navegación por org sigue siendo 1:1.** El sidebar muestra los
   proyectos bajo la org umbrella, no bajo "Empresa A" / "Empresa B"
   reales.
2. **Permisos por org no se propagan**: si el PM de "Empresa A" no
   tiene permisos sobre la org umbrella, no verá el proyecto. Solución:
   asigna membership directa al proyecto (US-074 user management).
3. **Reportes cross-empresa requieren filtro manual** por `business_unit`
   o Áreas; no hay un dashboard nativo "ver proyectos por empresa
   subordinada".
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
3. Crea los 2 proyectos bajo `Grupo XYZ`:
   - `ERP modernización` — `business_unit = "Empresa A"`.
   - `CRM upgrade` — `business_unit = "Empresa B"`.
4. Asigna PMs y membership directa al proyecto.
5. Para el reporte cross-empresa: exporta el listado del programa y agrupa
   por `business_unit` en Excel/Sheets.

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
