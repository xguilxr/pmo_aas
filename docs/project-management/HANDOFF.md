# HANDOFF.md — Estado para la próxima sesión

**Última actualización:** 2026-08-04
**Branch activa:** ninguna. **PR #573 mergeado** (`a725d10`)
**Generado por:** `/handoff` — cierre de la sesión de conformidad

---

## 🎯 Dónde estamos parados

La sesión de conformidad **cerró y está en `main`**: auditoría MCA/MCS, Tanda A
(4 de 5), **Tanda B entera**, presupuesto de contexto y **reauditoría de los dos
marcos**. Ya no hay estados sin medir.

| Marco | Objetivo | Alcanzado | Conformes | Bloquean |
|---|---|---|---|---|
| MCA | N2 | **N0** | 9 / 11 | AUT-01 (owner, 2 min) · CAP-01 (10 min) |
| MCS | N2 | **N0** | 21 / 126 | 54 para N1 |

Informes: [MCA](../conformidad/2026-08-04-mca.md) ·
[MCS](../conformidad/2026-08-04-mcs.md) · plan: [plan.md](../conformidad/plan.md).

**Una expectativa que hay que corregir:** la distancia de MCS a N1 **nunca fue
43, era 60**. El informe del 2026-08-03 omitió los 14 requisitos de N1 en
NO VERIFICABLE, que bloquean igual (`MCS-CORE` §6.2 exige CONFORME **o** NO
APLICABLE). Hoy son 54. Las Tandas A y B cerraron 6 bloqueantes de N1 y 6 de N2
porque apuntaban a **riesgo activo, no a nivel**.

## 📍 Dónde retomar

**Rama nueva desde `main`.** La anterior está mergeada.

**R1 — evaluar los 13 requisitos MCS en NO VERIFICABLE** (1-2 días):
`ARQ-03`, `CON-04`, `DAT-04`, `DAT-11`, `DAT-12`, `DES-03`, `DIS-02`, `DIS-03`,
`IA-01`, `IA-04`, `LEN-02`, `SEG-01`, `SUM-02`.

Es **medición, no construcción**: puede cerrar varios sin escribir código. Y el
precedente pesa — IA-05 estaba NO VERIFICABLE, se verificó, y el modelo **sí**
calculaba cifras que iban a informes ejecutivos. Hacerlo **antes** de comprometer
las 6-9 semanas de las Tandas C/D/E, que hoy se planificarían contra un
inventario que ya demostró dos veces estar mal contado.

Después: **CAP-01** (10 min — sacar «Rebase + force-push» de `CLAUDE.md` §8 a un
artefacto bajo demanda) y luego Tandas C, D y E.

## ✅ Qué dejó la sesión

Seis commits en `main`. Detalle en `plan.md` §B3 y §B5 y en los informes.

- **B3** — conjunto de evaluación de IA (`apps/api/evaluacion/`), job
  `evaluacion-ia` con umbral eliminatorio. Mide el sistema, no el modelo: sin
  clave de API y sin red, así que puede ser gate.
- **B5** — modelo de amenazas (`docs/architecture/modelo-amenazas.md`): ocho
  fronteras, catorce amenazas. Su trinquete falla si aparece una ruta sin
  autenticación o un destino externo sin declarar.
- **Contexto permanente −61 %** (87.623 → 34.080). La partida grande no era un
  archivo sino una regla: §1.4 cargaba el epic entero antes de saber si se iba a
  abrir.
- **Tres defectos de seguridad**, ninguno reportado por usuarios, los tres
  verificados por mutación: navegación fuera del sitio desde el copiloto; **AM-01**
  (la `base_url` del BYO permitía pedir desde dentro de la red privada de Railway
  y leer la respuesta); y un `field: null` del modelo borrando el acierto de la
  heurística en el importador.

## ⚠️ Gotchas

- **`main` no está protegida** (AM-14). Al hacerlo, añadir `evaluacion-ia`.
- **Cuatro amenazas SIN CONTROL**, escritas en vez de ignoradas: AM-08 (registro
  de auditoría modificable, y AM-06 se apoya en él como único control), AM-09
  (`/auth/login` sin límite por IP), AM-10 (bloqueo de cuenta como DoS), AM-14.
- **El informe del 2026-08-03 tiene tres errores comprobados** (distancia a N1,
  evidencia de ARQ-01, IA-12 atribuido a B2). Sus estados no remedidos se leen
  como indicativos, no como medidos.
- **`MCS-CORE §5.14` enuncia SEG-06 sin traer procedimiento**, así que el método
  del modelo de amenazas lo eligió Claude y el documento lo declara. Defecto del
  kit, merece issue.
- **Las skills del proyecto no cargan** si la sesión se enraíza fuera del repo —
  `/handoff` falló por eso en esta misma sesión. Es la misma causa que AUT-01.
- **Los gates de CI son trinquetes:** el de contexto frenó cuatro veces esta
  sesión. Recortar es la respuesta; subir el techo exige razón escrita.
- **No hay tests de frontend**, y **Python 3.12 no es negociable**.

## 🔄 PRs en flight

| PR / branch | Acción pendiente |
|---|---|
| #570 · `claude/pmo-portfolio-architecture-6hbuen` | Verificar + mergear · `alembic upgrade head` (0091-0094) |
| `claude/plan-import-wbs-fixes-nwotng` | Falta abrir PR · migs 0095-0096 |
| `claude/gantt-areas-fixes` | Falta abrir PR (ENH-149/BUG-075/ENH-154/ENH-152) |

## 📋 Lo que sigue

- **Conformidad:** R1 (los 13 NO VERIFICABLE) → CAP-01 → Tandas C, D, E.
- **Amenazas:** AM-08 es la más barata — `REVOKE UPDATE, DELETE` al rol de la
  aplicación, sin código. AM-09 es aplicar el limitador que ya existe.
- **Evaluación de IA:** falta superficie para el informe ejecutivo; antes hay que
  sacar el ensamblado del contexto fuera de `_run_report`.
- **Producto:** ENH-202 (Helvetica en exports) es el siguiente batch y se cruza
  con AM-12. US-168 sigue `in-progress`.

## 🧹 Acciones del owner

- [ ] Verificar el guard desde una sesión **dentro** del repo (AUT-01 → N2).
- [ ] `SENTRY_DSN` en Railway — el requisito más barato del marco (OPS-02).
- [ ] Proteger `main` tras cerrar los PR, con `evaluacion-ia` incluido (AM-14).
- [ ] Los tres PR pendientes de las ramas anteriores.
- [ ] Revisar `docs/dominio/02-GLOSARIO.md` término por término.
- [ ] Smoke manual de la web tras el salto de Next 15.0 → 15.5.

## 🔮 Sin issue todavía

- **DCMA 14-point** (`docs/dominio/01-DIAGNOSTICO.md` §4) y **línea base**, sin la
  cual no existe «desviación».
- **Migrar `python-jose` a PyJWT** — cerraría 5 CVE que bloquea `pyasn1<0.5.0`.

---

El orden de lectura al abrir sesión lo fija `CLAUDE.md` §1; no se repite aquí.
