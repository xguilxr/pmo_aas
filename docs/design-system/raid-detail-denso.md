---
responsable: propietario
estado: vigente
revisado: 2026-05-08
revisar_cada: 90d
---

# RAID — Vista detalle item (layout "Denso")

> **Origen:** spec del owner 2026-05-06, mock en
> `docs/design-system/Denso _ todo arriba_ comentarios al final.html`
> (artefacto exportado del Claude Design Canvas — se archiva en
> `docs/archive/` tras esta documentación, ver al final).
>
> **Issue de implementación:** [US-100 #246](https://github.com/xguilxr/pmo_aas/issues/246).
> Sub-issues: ENH-069 #247 (banner edición), ENH-070 #248 (card
> Comentarios + Historial), BUG-052 #249 (breadcrumb + ← Volver).
>
> **Restricciones:** sin cambios de modelo, sin cambios de paleta, sin
> cambios de tipografía. Solo reorganización visual.

---

## 1. Objetivo

Reemplazar la vista actual del detail RAID — que tiene la metadata
clave (estado, severidad, área, responsable, fechas) enterrada en un
sidebar vertical largo y el título separado de sus metadatos — por un
layout **denso vertical** donde lo crítico vive en una sola card de
header escaneable de un vistazo.

Aplica a los 4 tipos de items RAID:

| Tipo | Icono | Identificador |
|---|---|---|
| Riesgo | `warning` | `RIS-AAAA-NNN` |
| Acción | `check` | `ACT-AAAA-NNN` |
| Issue | `alert` | `ISS-AAAA-NNN` |
| Decisión | `scale` | `DEC-AAAA-NNN` |

Los 4 comparten el mismo layout — solo varían los campos del strip de
metadatos y el icono del header.

---

## 2. Estructura (de arriba a abajo)

```
┌──────────────────────────────────────────────────────────────┐
│ Topbar + tabs del proyecto (sin cambios)                     │
├──────────────────────────────────────────────────────────────┤
│ ← Volver   RAID / Riesgos / RIS-2026-003          [Editar]   │
├──────────────────────────────────────────────────────────────┤
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ ⚠  f7b1b949 · RIESGO              [Identificado] [Sev 9]│ │
│ │    Implementación EDP                                    │ │
│ ├──────────────────────────────────────────────────────────┤ │
│ │ ÁREA      RESPONSABLE   P×I       CATEGORÍA   F. CREAC. │ │
│ │ Comercial Juan Pérez    3×3 (=9)  Comercial   2026-05-02│ │
│ └──────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌──────────────── (solo si editing) ───────────────────────┐ │
│ │ Modo edición activo.            [Cancelar] [Guardar]    │ │
│ └──────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌────── Descripción ───────────────────────────────────────┐ │
│ │ Las dependencias abiertas relacionadas con los derechos…│ │
│ └──────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌────── Proyecto ──────────────────────────────────────────┐ │
│ │ f7e5a3bc...  Implementación EDP                          │ │
│ └──────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌────── Comentarios & Historial ───────────────────────────┐ │
│ │ Comentarios:                                             │ │
│ │   Sin comentarios todavía.                               │ │
│ │   [textarea + botón Agregar →]                           │ │
│ │ ──────                                                   │ │
│ │ Historial de cambios:                                    │ │
│ │   02/05/26 5:25 p.m. · risk.create · f7b1b949            │ │
│ └──────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

### 2.1. Fila de navegación
- Padding `10px 24px 0`.
- Izquierda: botón `← Volver` (ghost, 28px alto) + breadcrumb
  `RAID / [Tipo] / [ID]` separados por `/` gris (BUG-052).
- Derecha: botón `Editar` (toggle global). Cuando `editing === true`:
  cambia a estado "Editando…" con fondo azul suave.

### 2.2. Card de header
Padding interno `14px 18px`. Una sola card que contiene **dos
bloques internos** separados por `border-top` suave:

**Bloque superior (cabecera):**
- Icono del tipo a la izquierda.
- A la derecha:
  - Línea 1: `[ID mono gris] · [TIPO pill mayúsculas]` — empujados a la
    derecha los badges Estado y Severidad (Severidad solo en
    Riesgos/Issues).
  - Línea 2: Título (17px, weight 600, line-height 1.4).

**Bloque inferior (strip de metadatos):**
- Fondo `chrome-soft-bg` (azul muy claro, `oklch(97% 0.012 240)`).
- Grid de 6 columnas, gap 16px, padding `12px 18px`.
- Cada celda: label uppercase 10px gris arriba + valor 13px abajo.
- Celdas vacías: `—` en gris claro.

#### Campos del strip por tipo

| Pos | Riesgo | Acción | Issue | Decisión |
|---|---|---|---|---|
| 1 | Área | Área | Área | Área |
| 2 | Responsable | Responsable | Responsable | Decisor |
| 3 | P×I | Prioridad | Severidad | Tipo de decisión |
| 4 | Categoría | Categoría | Categoría | Estado de aprobación |
| 5 | F. Creación | F. Creación | F. Creación | F. Creación |
| 6 | F. Compromiso | F. Compromiso | F. Resolución | F. Vigencia |

**P×I (solo Riesgo):** dos cuadritos pequeños (Probabilidad y Impacto)
con `×` entre ellos y resultado calculado al lado en gris pequeño
(`= 9`).

### 2.3. Banner de modo edición
Visible **solo** cuando `editing === true`. Aparece debajo del header,
fondo azul suave, mensaje "Modo edición activo." + botones
`Cancelar` y `Guardar` a la derecha. (Ver ENH-069.)

### 2.4. Card "Descripción"
- Lectura: texto plano.
- Edición: `<textarea>` con el valor actual.

### 2.5. Card "Proyecto"
Una fila con ID del proyecto (mono, link azul subrayado) + nombre del
proyecto.

### 2.6. Card "Comentarios & Historial"
Una sola card con dos secciones internas separadas por gap (ENH-070):

- **Comentarios:** lista (vacía → "Sin comentarios todavía."),
  textarea para escribir, botón `Agregar` alineado a la derecha.
- **Historial de cambios:** lista de filas con timestamp (mono) +
  acción + ID corto (mono). Ej.:
  `02/05/26 5:25 p.m. · risk.create · f7b1b949`.

---

## 3. Modo edición (toggle global)

- Estado: `editing: boolean` controla todo el form.
- `editing === false` (default): vista de lectura.
- `editing === true`: el strip de metadatos + textarea descripción se
  vuelven editables:
  - Texto plano → `<input>`
  - Selects (Área, Categoría, Tipo, Estado de aprobación) → `<select>`
    con las opciones del modelo.
  - Fechas → `<input type="date">`
  - P×I → dos selects 1–5 con `×` entre ellos.
  - Descripción → `<textarea>`.
- Banner aparece arriba con `Cancelar` (descarta cambios sin llamar
  backend) y `Guardar` (1 sola PATCH con todos los campos editados).
- **No** hay edición inline campo-por-campo. Solo el toggle global.

---

## 4. Estilo visual (mantener exactamente igual al actual)

### Tipografía
- UI: **DM Sans**.
- IDs y timestamps: **JetBrains Mono**.

### Colores
- Topbar: azul oscuro `oklch(42% 0.13 255)`, texto claro.
- Cards: blanco, border `1px solid oklch(92.5% 0.005 80)`, radio 12px.
- Header de card: padding `14px 16px`, border-bottom suave, font-size
  13px weight 600.

### Badges de estado
| Estado | Color |
|---|---|
| Identificado / En progreso | info (azul) |
| Mitigado / Resuelto / Aprobada | success (verde) |
| Materializado | danger (rojo) |
| Cerrado / Rechazada | neutral (gris) |

### Badge de severidad (Riesgos / Issues)
| Valor | Color |
|---|---|
| ≤ 5 | success |
| 6 – 11 | warning (amarillo suave) |
| ≥ 12 | danger |

### Pill de tipo
- 10px mono uppercase.
- Fondo `oklch(97% 0.012 240)`.
- Border `oklch(90% 0.018 240)`.
- Color `oklch(36% 0.025 240)`.

### Inputs
- Height 32px, border `1px solid oklch(87% 0.006 80)`, radio 6px,
  focus con halo azul.

### Botones
- Primario: gris muy oscuro / texto blanco.
- Secundario: blanco con border.
- Ghost: transparente.

---

## 5. Comportamiento

- **`← Volver`** → listado RAID con el filtro del tipo activo
  preservado (ver BUG-052).
- **Click en breadcrumb** (`RAID` o `[Tipo]`) → navega al nivel
  correspondiente.
- **Click en link del proyecto** → detalle del proyecto.
- **Guardar** → POST/PATCH al endpoint del item con todos los campos
  del form, refresca la vista, agrega entrada al historial.
- **Cancelar** → descarta cambios locales sin llamar backend.
- **Comentarios:** botón `Agregar` postea un comentario nuevo y lo
  agrega a la lista sin recargar.

---

## 6. Restricciones explícitas

- ❌ No agregar campos nuevos. Solo reorganizar los existentes en el
  modelo actual.
- ❌ No cambiar el sistema de colores ni la tipografía.
- ✅ Reutilizar el mismo layout para los 4 tipos — solo cambian los
  campos del strip y el icono del header.

---

## 7. Mock visual de referencia

Mock exportado por el owner desde Claude Design Canvas:
**`docs/archive/raid-detail-denso-mock-2026-05-06.html`** (artefacto
estático, ~1.8MB con fuentes/CSS embebido — se archiva por
referencia histórica; este `.md` es la fuente canónica del spec).
