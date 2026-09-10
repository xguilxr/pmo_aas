---
tipo: gestion
responsable: propietario
estado: vigente
revisado: 2026-09-10
revisar_cada: 30d
---

# REVAMP-V2-FEEDBACK.md — bitácora de la ronda de limpieza visual

> Registro puntual de comentarios del owner, con screenshot de referencia
> cuando aplica, **antes** de tocar código. De aquí sale el plan de
> implementación de la ronda. No es un documento de producto (eso son las
> epics) ni el plan en sí — es la materia prima del plan.

## Cómo se usa

1. El owner comenta un punto (con o sin screenshot).
2. Se anota aquí tal cual, con estado `pendiente`.
3. Cuando hay suficientes puntos para una pasada, se arma el plan de
   implementación (sección al final) y se pasa cada punto a `en plan`.
4. Al implementar y verificar, pasa a `hecho` con el commit que lo cerró.

---

## Puntos registrados

### 1. Dashboard — el rediseño visual completo sigue sin aplicar

**Estado:** pendiente
**Origen:** spec `PMO-aaS Dashboard Redesign.dc.html` (owner, sesión 2026-09-10),
gramática editorial Lieflat Charts sobre tokens ADR-023.

Lo único que se implementó de toda la ronda anterior fue: sidebar
(Admin → Configuraciones, botón de colapsar al pie), la celda de la matriz
RAID (contorno + punto en vez de bloque sólido) y el roadmap trimestral en
Portafolio. El resto del spec —que es la parte que más se ve— no se tocó:

- [ ] **KPI band**: sigue con el layout viejo. El spec pide 5 columnas,
  paneles centrados con label pequeño en mayúsculas, cifra en JetBrains Mono,
  sparkline mínima y nota de contexto debajo.
- [ ] **Cards de tendencia** (avance promedio, riesgos abiertos, proyectos
  activos): formato label → valor → gráfica → delta. Sin cambios.
- [ ] **Distribuciones** (por fase, por programa, por sponsor): barras finas
  con hairlines, sin cambios respecto al diseño anterior.
- [ ] **Fusión "Salud" (KPI) + "Por salud" (distribución)** en una sola card
  de anillo + leyenda. Explícitamente pendiente, señalado al cerrar la ronda
  anterior y sin resolver.
- [ ] **Semáforo consolidado**: sin cambios.

**Screenshot de referencia:** pendiente de que el owner lo adjunte.

---

### 2. Barra de navegación (sidebar) — reestructuración completa

**Estado:** pendiente
**Origen:** owner, sesión 2026-09-10 (dictado, sin screenshot todavía).

#### 2.1 Estructura actual

```
Organizaciones
  Dashboard
  Portafolio
  Proyectos
  Importar
  Solicitudes
  Recursos
  Reportes
Transversal
  RAID
  Cambios
  Minutas
  Notificaciones
Configuraciones
  Configuraciones
    Tenant
    IA
    Organizaciones
    Usuarios
    Permisos
    Plan
    Auditoría
```

#### 2.2 Estructura pedida

```
Organización
  Dashboard
  PMO
    — fusiona Portafolio + Board en una sola página
    — el import masivo de proyectos se mueve aquí
    — botón que lleva a la config de portafolios y programas
    — siempre existe un portafolio-programa base de la organización, donde
      caen los proyectos sin programa ni portafolio asignado
    — para cada portafolio hay su propio panel, que agrupa sus programas y,
      adentro, sus proyectos ya asignados (estilo carpetas)
    — debe quedar muy simple de navegar
  Recursos
    — el import masivo de recursos se mueve aquí
  Solicitudes
  Reportes
    — clic lleva a /pmo/reports
    — incluye RAID y Cambios
    — Minutas y Notificaciones NO van aquí (no se consideran relevantes)
  Proyectos
    — lista de proyectos, solo para navegar a la página propia de cada uno

Configuraciones
  Cuenta
    — todos los usuarios ven su propia página: datos personales y todo lo
      que pueden hacer
  Admin
    Tenant
      Branding
      Usuarios (creación, gestión y asignación de roles)
      Organizaciones, Portafolios, Programas y Proyectos
        (agregar, configurar, eliminar, reasignar)
      Plan e IA
      Auditoría
```

#### 2.3 Filtro por organización activa (nota aparte, no es de navegación)

Con una organización seleccionada, **todo** el contenido de **todas** las
páginas debe filtrar solo esa organización. El owner marca que ahora mismo
los Recursos se ven mezclados entre organizaciones por las migraciones —lo
deja anotado, lo retoma después, no es parte de este punto de navegación.

#### 2.4 Encabezado (barra superior)

- La barra (y el primer rótulo del sidebar) debe arrancar justo debajo de la
  línea que separa el header del resto — actualmente hay un espacio/salto ahí.
- El logo del tenant deja el lugar donde hoy dice "PMO-aaS": ese lugar pasa a
  decir **"Organización:"** seguido del dropdown de organizaciones que ya
  existe.
- El logo del tenant se mueve a la derecha, entre el buscador y las
  notificaciones.
- El buscador pasa a ocupar el espacio central: centrado y más extendido
  (más ancho que el actual de 260px).

**Screenshot de referencia:** pendiente de que el owner lo adjunte.

---

### 3. Dashboard — corrección de alcance: el roadmap trimestral NO va aquí

**Estado:** pendiente
**Origen:** owner, sesión 2026-09-10 (dictado, sin screenshot todavía).
Corrige el punto 1: ahí se había dicho que el roadmap trimestral (estilo
Gantt por trimestre) iba en el Dashboard — el owner rectifica: **no va ahí**.

- [ ] **Mover** el roadmap trimestral (US-247, ya implementado en `/pmo`) de
  donde esté hoy hacia la página de **PMO** (la que resulta de fusionar
  Portafolio + Board, punto 2.2). Si ya vive en `/pmo`, este punto queda en
  standby hasta que exista la página PMO fusionada — no hay que moverlo dos
  veces.

Para el resto del Dashboard (lo que sí queda aquí, "lo que estuvimos
reconstruyendo"):

- [ ] **Rueda de salud + número de proyectos activos**: solidificar en una
  sola pieza — la dona de "por salud" con el total de proyectos activos al
  centro (ya es parecido al spec original; falta fusionarlo con el KPI
  "Proyectos activos" en vez de tenerlos como dos elementos separados).
- [ ] **Hero de avance**: juntar el KPI "Avance plan vs real" (el que da el
  % puntual) con la card de tendencia "Avance promedio" (la que trae la
  gráfica de tendencia) en **una sola pieza hero principal** — no dos cards
  separadas mostrando cosas relacionadas.
- [ ] El resto de las piezas (distribuciones por fase/programa/sponsor, top
  en riesgo/atraso/sobrecarga, matriz RAID, semáforo consolidado) **sin
  cambio de alcance**: se implementan como ya estaba diseñado en el spec
  original (`PMO-aaS Dashboard Redesign.dc.html`, punto 1).

**Nota:** este punto reemplaza, para el Dashboard, la lista de pendientes
del punto 1 en lo referente al roadmap — el resto de la lista del punto 1
(KPI band, distribuciones, semáforo) sigue vigente tal cual.

**Screenshot de referencia:** pendiente de que el owner lo adjunte.

---

### 4. Página PMO — el Gantt trimestral navegable + lista de proyectos debajo

**Estado:** pendiente
**Origen:** owner, sesión 2026-09-10 (dictado, sin screenshot todavía).

- [ ] El Gantt trimestral (roadmap del punto 3, US-247) es donde se ve
  **todos** los proyectos a nivel trimestral.
- [ ] Tiene que poder **navegar entre años**: años previos y siguientes.
  Ejemplo dado: 2025, 2026, 2027. Todo lo de **2026 en adelante** debe estar
  cubierto (no es solo el año en curso, como está implementado hoy).
- [ ] **Debajo** del Gantt: la lista de proyectos, **ordenada** por
  organización → portafolio → programa (no "agrupados", el owner corrige a
  media frase: es orden, no agrupación por separado).
  - Todos los proyectos de esa lista van a tener la misma organización,
    porque solo un rol específico puede ver a nivel de varias
    organizaciones a la vez — la idea general de la página es que todo viva
    a nivel de **una** organización (ver también punto 2.3, filtro por
    organización activa).

**Screenshot de referencia:** pendiente de que el owner lo adjunte.

---

### 5. Recursos — unicidad por organización, borrado, % asignado, import masivo

**Estado:** pendiente
**Origen:** owner, sesión 2026-09-10 (dictado, sin screenshot todavía).

**Lo que ya funciona y le gusta al owner (no tocar):** la información que
se ve hoy — quién es el recurso, su organización/empresa (contempla
proveedores externos, no solo empleados). Confirma que esto está bien.

- [ ] **Porcentaje asignado**: dice que "creo que ya está" — verificar que el
  dato exista y **se refleje** en la UI (puede ser un problema de visualización,
  no de datos).
- [ ] **Borrar / quitar recurso**: no existe la opción hoy. Falta poder
  quitar o poner usuarios como recurso.
- [ ] **Unicidad por organización** (la pieza central del punto): un recurso
  es **estrictamente de una organización**. Hoy hay recursos duplicados
  porque dos organizaciones se juntaron (mismo problema de datos que ya
  había anotado en el punto 2.3) y aparecen en ambas — hay que limpiar eso.
  - Un recurso solo puede asignarse a proyectos **dentro de su propia
    organización**.
  - Si la misma persona participa en otra organización, se tiene que volver
    a dar de alta ahí — es un registro nuevo e independiente, no el mismo
    recurso compartido entre organizaciones.
  - La unicidad **no es por nombre** (puede haber personas con el mismo
    nombre dentro de una organización) — el candidato es **correo
    electrónico**, a validar cómo se implementa exactamente.
- [ ] **Import masivo de recursos** (ya apuntado en el punto 2.2, ahora con
  el detalle):
  - Necesita una plantilla con los campos obligatorios para poder subir
    correctamente.
  - El sistema debe **crear** los usuarios que no existen todavía.
  - El sistema debe **validar** (por el criterio de unicidad de arriba) los
    que ya existen y **no volver a crearlos** — evitar duplicados en la
    importación.

**Screenshot de referencia:** pendiente de que el owner lo adjunte.

---

### 6. Solicitudes — conforme, sin cambios

**Estado:** conforme (nada que implementar)
**Origen:** owner, sesión 2026-09-10 (dictado, sin screenshot).

La página tal cual está hoy: lista de solicitudes con opción de crear una
nueva, y el flujo completo hasta generar el charter y el registro del
proyecto en estado "pendiente por aprobación" (el flujo normal). El owner
confirma que esta página está bien — no hay nada que registrar aquí.

---

### 7. Reportes — pestañas RAID / Cambios / Organización, HTML one-page + descargas

**Estado:** pendiente
**Origen:** owner, sesión 2026-09-10 (dictado, sin screenshot todavía).

La página en sí está bien (confirma). El contenido: incluye una pestaña de
**RAID** y una de **Cambios**. Cada reporte de esta página es un **HTML
ya definido**, con ciertas especificaciones, que se puede generar en
cualquier momento, con opción de descargar algunos archivos.

- [ ] **Pestaña RAID**:
  - Reporte "one-page" en HTML (a diseñar — el owner lo marca explícitamente
    como pendiente de diseño, no de implementación todavía).
  - Debajo del reporte: tabla agrupada con **todos** los riesgos, todas las
    acciones, todos los issues, todas las decisiones (con su información),
    de los proyectos que estén filtrados.
  - Opción de **descargar el Excel** del RAID — mismo formato que ya existe
    a nivel de proyecto individual, pero agregando **todos los proyectos
    filtrados** en ese momento (no uno solo).
- [ ] **Pestaña Cambios**: mismo patrón que RAID (reporte HTML + descarga),
  sin más detalle todavía — pendiente de que el owner lo precise.
- [ ] **Pestaña / vista a nivel organización**: un "snapshot" del Dashboard,
  más una lista de portafolios → programas → proyectos, mostrando cómo
  están agrupados, con sus líneas (relación jerárquica visible).

**Nota del owner:** el diseño puntual de estos reportes ("ahorita lo vamos a
diseñar") queda para después — este punto registra el alcance funcional
(qué pestañas, qué contenido, qué se descarga), no el layout final.

**Screenshot de referencia:** pendiente de que el owner lo adjunte.

---

### 8. Proyectos — orden de columnas y filtros como dropdown con checkmarks

**Estado:** pendiente
**Origen:** owner, sesión 2026-09-10 (dictado, sin screenshot todavía).

La página en general está bien (confirma), con dos ajustes:

- [ ] **Orden de columnas**: portafolio, programa, nombre del proyecto —
  en ese orden. (La organización es siempre la misma para todos los
  proyectos listados, ver punto 2.3/4 — no hace falta como columna
  separada.) Más algunas columnas de detalle adicionales para dar contexto
  (el owner no precisa cuáles todavía).
- [ ] **Filtros como dropdown con checkmarks**: que se puedan marcar/
  desmarcar valores dentro del dropdown (selección múltiple), no como están
  hoy.
  - Nota de contexto del owner: los PMs, por su rol, normalmente solo ven
    un subconjunto de proyectos (a los que están asignados), así que no
    espera que usen mucho los filtros — pero deben quedar disponibles
    igual.

**Screenshot de referencia:** pendiente de que el owner lo adjunte.

---

### 9. Configuraciones → Cuenta — las acciones del dropdown del usuario

**Estado:** pendiente (bajo detalle — confirma alcance, falta precisar contenido)
**Origen:** owner, sesión 2026-09-10 (dictado, sin screenshot todavía).

"Cuenta" (punto 2.2) es la página a la que hoy se llega por el dropdown del
avatar del usuario, arriba a la derecha ("administrar cuenta"). El owner
confirma que el contenido de esa página son, básicamente, esas mismas
acciones — no agrega detalle nuevo sobre qué campos o funciones debe tener
más allá de lo que ya existe en ese dropdown.

- [ ] Verificar qué opciones tiene hoy el dropdown de "administrar cuenta" y
  confirmarlas/trasladarlas como el contenido de la página Cuenta del nuevo
  sidebar.

**Screenshot de referencia:** pendiente de que el owner lo adjunte.

---

### 10. Configuraciones → Admin — acceso, branding, usuarios (borrado real), jerarquía

**Estado:** pendiente
**Origen:** owner, sesión 2026-09-10 (dictado, sin screenshot todavía).

**Acceso:** esta sección completa (Admin, punto 2.2) es **solo para el
administrador del tenant**. No es a nivel de organización — es a nivel de
tenant.

- [ ] **Branding**: lo que ya existe hoy — sin cambios de alcance.
- [ ] **Usuarios**: lo que ya existe hoy, con un cambio:
  - [ ] Poder **eliminar** usuarios de verdad. Hoy solo se pueden
    **desactivar** — el owner marca que necesita el borrado real, no solo
    desactivación.
- [ ] **Organizaciones, Portafolios, Programas y Proyectos** (gestión
  jerárquica): desde acá el admin del tenant puede:
  - Reasignar: por ejemplo, mover un proyecto de un programa a otro.
  - Crear/borrar programas, proyectos, portafolios (todo el árbol).
  - Esto es **exclusivo del administrador**, para todo lo que es a nivel
    de organización hacia abajo (organización, portafolio, programa,
    proyecto).
  - Y a nivel de **tenant**: el admin puede configurar y **dar de baja
    organizaciones completas** — también exclusivo del admin.

**Nota:** no tocó en este punto Plan e IA ni Auditoría — quedan pendientes
de que el owner los dicte por separado.

**Screenshot de referencia:** pendiente de que el owner lo adjunte.

---

<!-- Los siguientes puntos se agregan según los vaya dictando el owner. -->

---

## Plan de implementación

*(vacío — se arma cuando el owner da por cerrada la ronda de comentarios)*
