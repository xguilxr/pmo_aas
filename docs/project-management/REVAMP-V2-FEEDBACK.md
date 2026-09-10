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

<!-- Los siguientes puntos se agregan según los vaya dictando el owner. -->

---

## Plan de implementación

*(vacío — se arma cuando el owner da por cerrada la ronda de comentarios)*
