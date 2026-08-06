---
tipo: referencia
responsable: propietario
estado: vigente
revisado: 2026-08-06
revisar_cada: 90d
---

# Conformidad — índice del expediente

Trece documentos y ninguna forma de saber cuál está vivo. Este índice existe
para eso, y para una regla que se aplica a todo el directorio:

> **Los informes fechados no se editan.** Son el expediente: lo que se midió, el
> día que se midió y con qué marco. Corregirlos a posteriori destruye la única
> propiedad que los hace útiles —poder reconstruir qué se sabía y cuándo—. Lo
> que se mueve es el **plan**; los informes se acumulan.

Por eso todos llevan `estado: historico` y `revisar_cada: nunca` en el
encabezado, y no es descuido.

---

## Lo que está vivo

| Documento | Para qué |
|---|---|
| [`plan-remediacion.md`](plan-remediacion.md) | **El plan activo.** Olas, qué falta y qué necesita decisión del owner |
| [`marco/MCS-CORE.md`](marco/MCS-CORE.md) | El catálogo normativo: 126 requisitos, y §6.2 con la regla de nivel |
| [`marco/`](marco/) | Los marcos tal como se recibieron. No se editan aquí |

**El estado real no está en ningún documento**, y es a propósito:

```bash
python scripts/registro_conformidad.py
```

Une el registro y lo deriva. Cualquier cifra escrita en prosa es una foto del
día que se escribió, y el expediente ya acumula cinco errores de recuento por
transcribir a mano. **Si un documento y el script discrepan, gana el script.**

---

## El expediente, en orden

Se lee de arriba abajo como la historia de qué se supo y cuándo.

### 2026-08-03 — la primera pasada

| Documento | Qué aporta |
|---|---|
| [`2026-08-03-mca.md`](2026-08-03-mca.md) | Auditoría MCA inicial del entorno agéntico (commit `d79c31d`) |
| [`2026-08-03-mca-seguimiento.md`](2026-08-03-mca-seguimiento.md) | Reauditoría tras las acciones 1-8 de esa misma jornada |
| [`2026-08-03-mca-cierre.md`](2026-08-03-mca-cierre.md) | Cierre de la Tanda 1 |
| [`2026-08-03-mcs.md`](2026-08-03-mcs.md) | Auditoría MCS inicial. **La tabla de 117 filas de la que sale el registro** |

### 2026-08-04 — seguimiento y lo no verificable

| Documento | Qué aporta |
|---|---|
| [`2026-08-04-mca.md`](2026-08-04-mca.md) | Reauditoría MCA |
| [`2026-08-04-mcs.md`](2026-08-04-mcs.md) | Reauditoría MCS de seguimiento |
| [`2026-08-04-mcs-r1.md`](2026-08-04-mcs-r1.md) | **R1** — los 13 requisitos que la auditoría dejó en NO VERIFICABLE |

### 2026-08-05 — llega el marco y desmiente tres cierres

| Documento | Qué aporta |
|---|---|
| [`2026-08-05-mcs-remediacion.md`](2026-08-05-mcs-remediacion.md) | Lo que R1 etiquetó como barato, más dos amenazas del modelo |
| [`2026-08-05-ola0-recuento.md`](2026-08-05-ola0-recuento.md) | Ola 0: remedir antes de construir |
| [`2026-08-05-verificacion-con-marco.md`](2026-08-05-verificacion-con-marco.md) | **El más importante de leer.** Con `MCS-CORE` en mano, **tres de seis cierres no se sostuvieron** |
| [`plan.md`](plan.md) | El plan del 08-03. **Superado** por `plan-remediacion.md`; se conserva fechado |

---

## Lo que este expediente enseñó

Tres lecciones que se ganaron caro y que conviene tener presentes antes de
declarar cualquier cosa cerrada:

1. **Medir contra el texto del requisito, no contra la evidencia anotada.** La
   Ola 2 destapó seis defectos reales que ninguna de las cinco auditorías
   previas había visto, y en todos los casos porque la evidencia decía «hecho» y
   el requisito pedía otra cosa.
2. **Una lista escrita a mano no puede probar «uno solo».** Prueba «uno solo
   entre los que me acordé de listar». `DAT-05` estuvo CONFORME con una quinta
   paleta suelta en el acta que se firma. Los controles nuevos recorren el árbol
   y declaran sus excepciones con motivo escrito.
3. **Un control que no se puede ver fallar no es un control.** Antes de dar algo
   por cerrado se muta el código y se comprueba que la prueba se pone roja. Así
   salieron seis pruebas que no podían fallar —y, el 2026-08-06, una
   justificación falsa en el encabezado de la migración 0101.

---

## Los otros dos marcos

`MCA` (entorno agéntico) y `MCC` viven fuera de este directorio en lo que hace a
su cumplimiento diario: los umbrales y las mediciones fechadas están en
[`conformidad.yaml`](../../conformidad.yaml), en la raíz, porque son los que el
CI hace cumplir en cada PR.
