# HANDOFF.md — Estado para la próxima sesión

**Última actualización:** 2026-08-05
**Branch activa:** `claude/audit-continuation-fzrtko` — #577 **mergeado**; reiniciada desde `main`
**Generado por:** `/handoff`

---

## 🎯 Dónde estamos parados

**MCA está en N2**, su objetivo, desde el merge de #576. La lista de «lo barato
de R1» que dejó la sesión anterior **está hecha entera**, más dos amenazas.

| Marco | Objetivo | Hoy | Falta |
|---|---|---|---|
| MCA (entorno) | N2 | **N2** | Nada del objetivo |
| MCS (producto) | N2 | **N0** · 25/126 | 50 para N1 (eran 54) |

## ✅ Hecho en esta sesión

Nueve requisitos, **un commit cada uno**, todos verificados por mutación:

- **SUM-02** el contenedor no corre como root · **DES-03** `/health` hace
  `SELECT 1` acotado y devuelve 503 · **DIS-02** 34/34 pares AA en los dos temas
  + job `contraste-wcag` · **AM-09** límite por IP en el login, contando fallos ·
  **AM-08/SEG-07** `audit_log` de solo anexado · **SEG-01** PyJWT 2.13.0, 5 CVE
  menos (2.10.1 traía 7 propias; lo cazó el CI) ·
  **D-7** una sola paleta de salud · **D-9** `is_milestone ⟹ duración 0`.
- **LEN-02** mejora pero **sigue PARCIAL**: el catálogo guarda qué/por qué/qué
  hacer como datos, no como prosa.

Informe: `docs/conformidad/2026-08-05-mcs-remediacion.md`.

**Tres hallazgos que la medición no podía ver:**

1. **El `REVOKE` que AM-08 proponía no habría funcionado.** La aplicación se
   conecta con el rol **dueño** y en PostgreSQL el dueño conserva sus
   privilegios. Comprobado contra Postgres 16; van disparadores.
2. **`check_contraste.py` llevaba los valores copiados a mano** y el tema oscuro
   nunca se había medido. Dos agujeros del propio instrumento.
3. **El caso que incumplía D-9 era el corriente:** días inclusivos hacían que un
   hito de un día durara 1.

## 📍 Dónde retomar

**D-3 cerrada** (US-194, mig 0100): con ella **el glosario no tiene ninguna
decisión abierta**. Lo siguiente sin dueño es la **fase `cancelled`** y la
**paleta de gráficos**, las dos con ADR por escribir. Lo que espera al owner está
en su checklist, más abajo, y no se repite aquí.

## ⚠️ Gotchas

- **Las migraciones 0097-0100 no las corre Alembic aquí** (guard). Su SQL se
  ejercita contra el esquema de `Base.metadata`, **no contra tablas a mano**:
  así se coló `UPDATE lessons_learned` en 0098 (la tabla es `lessons`).
- **`RATE_LIMITED` pasó de 422 a 429.** Cambio de contrato pequeño, ya en
  `api-conventions.md`. Afecta también a reseteo de contraseña.
- **El presupuesto de contexto va al límite.** Correr `check_contexto.py` antes
  de engordar `CLAUDE.md`, `SPRINT.md` o este archivo.
- **El guard bloquea comandos que *mencionan* uno denegado**, aunque el patrón
  aparezca en una ruta de archivo. Se reformula, no se relaja el patrón.
- **La suite tarda ~2m45s** con `-n auto`. Correrla en segundo plano.
- Sin tests de frontend. Python 3.12 no es negociable.

## 📚 Epics docs

Solo EP014 cambió (tipografía de los entregables). Al día también:
`api-conventions.md`, `modelo-amenazas.md`, `amenazas.yaml`, `DB-CHANGES.md`,
glosario, ADR y `design-system/tokens.md`.

## ✅ Decisiones del owner — 2026-08-05, primera tanda

| Decisión | Estado |
|---|---|
| **Volver al producto**; las Tandas C/D/E no se abren | Registrada |
| **LEN-02 como norma**, no como tanda (`api-conventions.md` §7) | ✅ |
| **Migrar a PyJWT** — 5 CVE | ✅ en `2.13.0` |
| **`support` → `hypercare`** | ✅ ADR-019, mig 0098 |

## 🛠️ Producto — después de las decisiones

- **ENH-202** — Helvetica en los cuatro caminos de export. Cerró **AM-12** y
  destapó que los informes **llevaban meses saliendo en DejaVu Sans**: el CSS
  pedía DM Sans y la imagen no instalaba ninguna de las fuentes declaradas.
- **D-2** y **D-8** — con ventana: el API acepta el nombre viejo y devuelve el
  canónico. La de D-8 tiene **dos puertas**, cuerpo y parámetro de consulta.
- **AM-10** — el bloqueo de cuenta pasó a retardo creciente. Con AM-14 reflejada
  —llevaba un día cerrada y la ficha decía lo contrario—, **el modelo de
  amenazas no tiene ninguna sin control**.

## 🗳️ Segunda tanda de decisiones — 2026-08-05

| Decisión | Siguiente paso |
|---|---|
| **D-3: ejecutar en la próxima ronda** | ✅ **hecha** (US-194, mig 0100) |
| **D-8: `portfolio_function` → `discipline`** | ✅ **hecha** (ADR-021, mig 0099) |
| **Ventanas: cerrar con dato** | ✅ **hecha** — se cuentan por `compat.nombre_viejo` |
| **AM-10: retardo creciente** | ✅ **hecha** — ninguna amenaza queda sin control |
| **D-4: uno por dimensión** | ✅ forma decidida. Faltan los **cinco valores** |
| **Fase `cancelled`: sí. `initiation`: no** | ADR + US propias, sin abrir |
| **Paleta de gráficos: propia** | Ni marca ni Tailwind: categórica y distinta del semáforo |

`discipline` se eligió porque «función» y «rol» ya significan otras cosas aquí
—`by_function` era agregación de capacidad, «rol» es el de permisos—.

## 🧹 Acciones del owner

- [ ] **Correr las migraciones `0097`-`0100`.** Ninguna las corrió Alembic aún.
- [ ] Smoke manual de la web: seis tokens de color, `support` → `hypercare` en
      filtros, y el plan (`wbs_code`) en alta, edición e importación.
- [ ] Calibrar los cinco valores del umbral (D-4) contra un proyecto real.

## 🔮 Sin issue todavía

- **`design-system/tokens.md`** describe una paleta anterior; queda declarado
  obsoleto, no corregido.
- **DCMA 14-point** y **línea base** (D-6), sin la cual «desviación» no tiene
  referente.
- **`MCS-CORE §5.14` enuncia SEG-06 sin traer procedimiento** — defecto del kit.

---

El orden de lectura al abrir sesión lo fija `CLAUDE.md` §1; no se repite aquí.
