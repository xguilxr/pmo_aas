# HANDOFF.md — Estado para la próxima sesión

**Última actualización:** 2026-08-04
**Branch activa:** `claude/auditoria-conformidad-mca-mcs` · **PR #573** (abierto)
**Generado por:** sesión de conformidad — Tanda B, contexto y **reauditoría**

---

## 🎯 Dónde estamos parados

Sesión **de conformidad, no de producto**: se auditó el repo contra MCA (entorno
agéntico) y MCS (software), y se remedió la Tanda A (4 de 5) y **la B entera**.

**Reauditado el 2026-08-04** ([MCA](../conformidad/2026-08-04-mca.md) ·
[MCS](../conformidad/2026-08-04-mcs.md)). Ya no hay estados sin medir.

| Marco | Objetivo | Alcanzado | Conformes | Bloquean |
|---|---|---|---|---|
| MCA | N2 | **N0** | 9 / 11 | AUT-01 (owner, 2 min) · CAP-01 (10 min) |
| MCS | N2 | **N0** | 21 / 126 | 54 para N1 |

**MCA está a dos requisitos de N2**, y uno es tuyo. **MCS sigue lejos**, y hay
que corregir una expectativa: la distancia a N1 **nunca fue 43, era 60** — el
informe anterior omitió los 14 requisitos en NO VERIFICABLE, que bloquean igual.
Hoy son 54. Las Tandas A y B cerraron 6 bloqueantes de N1 y 6 de N2 porque
apuntaban a **riesgo activo, no a nivel**.

## 📍 Dónde retomar

**Lo más barato son dos acciones del owner**, no de Claude:

1. Abrir Claude Code con el repo como directorio de trabajo y comprobar que el
   guard intercepta (`echo "prueba: git push --force"`). Cierra AUT-01 → **N2**.
2. Proteger `main`. Es **AM-14** del modelo de amenazas.

Después, **evaluar los 13 requisitos NO VERIFICABLE** (1-2 días). Es medición,
no construcción: puede cerrar varios sin código y destapar riesgo. Precedente:
IA-05 estaba NO VERIFICABLE, se verificó, y el modelo **sí** calculaba cifras que
iban a informes ejecutivos. Hacerlo **antes** de comprometer las 6-9 semanas de
las Tandas C/D/E.

## ✅ Hecho en esta sesión

Detalle en `docs/conformidad/plan.md` §B3 y §B5.

**B3 — conjunto de evaluación de IA** (IA-07/08/09), en `apps/api/evaluacion/`.
B2 cerró que el contenido ajeno no llegue al modelo como instrucción; nadie
comprobaba la otra mitad: si el modelo desobedece igualmente, **qué sale**. Por
eso puede ser un gate — mide el sistema, no el modelo: sin clave de API, sin red,
job `evaluacion-ia` con umbral eliminatorio. Los fallos de IA que ya llegaron a
un usuario (BUG-063/068/069/070/073, ENH-102, ENH-147) son casos permanentes.

**Contexto permanente: −39 %**, y por primera vez bajo el objetivo de 40.000. La
partida grande no era un archivo sino una regla: §1.4 obligaba a cargar «el epic
relevante» entero antes de saber si se iba a abrir. Ahora se carga `docs/epics/README.md` —que ya era el índice—
y el epic se abre **al tocarlo**; §0.3 se fue a la skill
`verificar`; Deferred/DONE/backlog, a `SPRINT-BACKLOG.md`. El techo bajó con él
—si no, la ganancia se erosiona sola— y `medir_contexto()` se actualizó en el
mismo cambio: el medidor y la política van juntos o la cifra miente.

**B5 — modelo de amenazas** (SEG-06), en `docs/architecture/modelo-amenazas.md`:
ocho fronteras de confianza y catorce amenazas con control, evidencia, residual y
estado. La mitad de «revisado ante cambios significativos» la hace cumplir
`tests/test_seg06_modelo_amenazas.py`, que falla si aparece una ruta sin
autenticación o un destino externo que `amenazas.yaml` no declara.

**Tres defectos encontrados y corregidos**, ninguno reportado por usuarios, todos
verificados por mutación:

- El copiloto ofrecía navegaciones **fuera del sitio**: el parser de URL trata
  `\` como `/` y borra TAB/LF/CR, así que `/\evil.example` pasaba el filtro de
  «empieza por `/` y no por `//`», y el frontend hace `router.push` sin más.
- **AM-01:** el BYO dejaba a un administrador de inquilino fijar `base_url`, y
  `POST /admin/ai/provider/test` la usaba para pedir **desde dentro de la red
  privada de Railway** devolviendo estado, cuerpo y latencia. Un escáner de red
  para cualquier administrador de cliente.
- Un `field: null` del modelo con confianza alta borraba el mapeo que la
  heurística había acertado, en el importador.

## ⚠️ Gotchas

- **`main` no está protegida** (AM-14). Al hacerlo, añadir `evaluacion-ia` a los
  checks requeridos.
- **Cuatro amenazas quedan SIN CONTROL**, escritas en vez de ignoradas: AM-08 (el
  registro de auditoría es una tabla ordinaria, y AM-06 se apoya en él como único
  control), AM-09 (`/auth/login` sin límite por IP), AM-10 (el bloqueo por
  usuario es a su vez una denegación de servicio) y AM-14.
- **`MCS-CORE §5.14` enuncia SEG-06 y no trae procedimiento**, así que el método
  del modelo de amenazas lo eligió Claude y el documento lo declara (`plan.md`
  §B5). Es un defecto del kit.
- **El informe del 2026-08-03 tiene tres errores comprobados:** la distancia a
  N1, la evidencia de ARQ-01 y IA-12 atribuido a B2. Sus estados no remedidos se
  leen como indicativos, no como medidos.
- **Los gates de CI son trinquetes:** fallan ante crecimiento nuevo, no por el
  pasivo heredado. El de contexto frenó tres veces esta sesión, incluida la
  redacción de este archivo. Recortar es la respuesta; subir el techo exige
  razón escrita en `conformidad.yaml`.
- **No hay tests de frontend**, y **Python 3.12 no es negociable**
  (`psycopg[binary]` no publica wheel para 3.13+).

## 🔄 PRs en flight

| PR / branch | Acción pendiente |
|---|---|
| **#573** · `claude/auditoria-conformidad-mca-mcs` | Revisar y mergear |
| #570 · `claude/pmo-portfolio-architecture-6hbuen` | Verificar + mergear · `alembic upgrade head` (0091-0094) |
| `claude/plan-import-wbs-fixes-nwotng` | Falta abrir PR · migs 0095-0096 |
| `claude/gantt-areas-fixes` | Falta abrir PR (ENH-149/BUG-075/ENH-154/ENH-152) |

## 📋 Lo que sigue

- **Conformidad:** R1 — evaluar los 13 NO VERIFICABLE. Luego Tandas C, D y E.
- **Amenazas:** AM-08 es la más barata — un `REVOKE UPDATE, DELETE` al rol de la
  aplicación, sin código. AM-09 es aplicar el limitador que ya existe.
- **Evaluación de IA:** falta superficie para el informe ejecutivo; antes hay que
  sacar el ensamblado del contexto fuera de `_run_report`.
- **Producto:** ENH-202 (Helvetica en exports) es el siguiente batch y se cruza
  con AM-12. US-168 sigue `in-progress`.

## 🧹 Acciones del owner

- [ ] Verificar el guard desde una sesión dentro del repo (cierra AUT-01 → N2).
- [ ] Proteger `main` tras cerrar los PR, con `evaluacion-ia` incluido (AM-14).
- [ ] Revisar y mergear **PR #573**.
- [ ] Revisar `docs/dominio/02-GLOSARIO.md` término por término.
- [ ] Smoke manual de la web tras el salto de Next 15.0 → 15.5.
- [ ] `SENTRY_DSN` en Railway — **es el requisito más barato del marco** (OPS-02).
- [ ] Los tres PR pendientes de las ramas anteriores.

## 🔮 Sin issue todavía

- **Calidad de cronograma DCMA 14-point** (`docs/dominio/01-DIAGNOSTICO.md` §4) y
  **línea base**, sin la cual no existe «desviación».
- **Migrar de `python-jose` a PyJWT** — cerraría 5 CVE que bloquea `pyasn1<0.5.0`.

---

El orden de lectura al abrir sesión lo fija `CLAUDE.md` §1; no se repite aquí.
Continúa desde «Dónde retomar».
