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

**Se cerró todo lo aprobado**: D-3 (US-194), fase `cancelled` (US-195), umbrales
D-4 (US-196) y paleta de gráficos (US-197). **El glosario no tiene ninguna
decisión abierta.** Lo que espera al owner está en su checklist, más abajo.

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

## ✅ Decisiones del owner — 2026-08-05

**Las once, decididas y ejecutadas.** Primera tanda: volver al producto ·
LEN-02 como norma · PyJWT · `support` → `hypercare`. Segunda: D-3 `wbs_code` ·
D-8 `discipline` · ventanas que se cierran con dato · AM-10 retardo creciente ·
D-4 calibrada · fase `cancelled` (`initiation` no) · paleta de gráficos propia.

El detalle de cada una vive donde corresponde —ADR-019 a ADR-023,
`03-REVISION-GLOSARIO.md`— y no se repite aquí.

**Lo que dejaron de camino, que no estaba en ninguna decisión:**

- Los informes **llevaban meses saliendo en DejaVu Sans**: el CSS pedía DM Sans y
  la imagen no instalaba ninguna de las fuentes declaradas (ENH-202).
- El presupuesto del semáforo **no miraba el tiempo**: 85 % gastado con 10 % de
  avance salía verde (US-196).
- `#dc2626` marcaba «ruta crítica» y el semáforo «en problemas» **en la misma
  página** (US-197).
- Con AM-14 reflejada, **el modelo de amenazas no tiene ninguna sin control**.

## 🧹 Acciones del owner

- [ ] **Correr las migraciones `0097`-`0100`.** Ninguna las corrió Alembic aún.
- [ ] Smoke manual de la web: seis tokens de color, `support` → `hypercare` en
      filtros, y el plan (`wbs_code`) en alta, edición e importación.
- [ ] **Contrastar los umbrales de D-4 contra tu cartera real.** Los valores son
      razonados, no medidos; se ajustan en `settings`, sin tocar código.

## 🔮 Sin issue todavía

- **`design-system/tokens.md`** describe una paleta anterior; queda declarado
  obsoleto, no corregido.
- **DCMA 14-point** y **línea base** (D-6), sin la cual «desviación» no tiene
  referente.
- **`MCS-CORE §5.14` enuncia SEG-06 sin traer procedimiento** — defecto del kit.

---

El orden de lectura al abrir sesión lo fija `CLAUDE.md` §1; no se repite aquí.
