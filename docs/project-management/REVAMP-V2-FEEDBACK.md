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

<!-- Los siguientes puntos se agregan según los vaya dictando el owner. -->

---

## Plan de implementación

*(vacío — se arma cuando el owner da por cerrada la ronda de comentarios)*
