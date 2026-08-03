# Auditoría MCA — seguimiento tras las acciones 1-8

| Campo | Valor |
|---|---|
| Repositorio | `xguilxr/pmo_aas` · árbol de trabajo, **sin commitear** |
| Marco | MCA-CORE v1.0.0 · procedimiento MCA-P02 v1.0.0 |
| Fecha | 2026-08-03 (misma jornada que la auditoría inicial) |
| Nivel objetivo | **N2** |
| Nivel alcanzado | **N0** |
| Anterior | [2026-08-03-mca.md](2026-08-03-mca.md) — también N0, pero por corte duro en Etapa 1 |

---

## 1. Contexto permanente y nivel alcanzado

Ya **no hay corte duro**: `conformidad.yaml` declara el presupuesto, así que esta
vez se evaluaron los once requisitos de N1 y N2 uno a uno.

**El nivel alcanzado sigue siendo N0.** Dos requisitos de N1 lo bloquean:

- **AUT-01 PARCIAL** — el guard de acciones irreversibles existe y está probado,
  pero se comprobó que **no se ejecuta** en esta sesión.
- **CTX-03 NO CONFORME** — quedan dos cifras vivas en `CLAUDE.md`, y **las
  introduje yo** durante las acciones 3 y 3b.

Un PARCIAL impide alcanzar su nivel (MCA-CORE §6.2). Dicho sin suavizarlo: el
entorno mejoró mucho y sigue sin ser conforme a N1.

**Contexto permanente: 50.217 caracteres (~12.554 tokens)**, contra 87.623 al
abrir la auditoría. **−43 %**, con nueve de once requisitos cerrados.

---

## 2. Etapa 2 — ejecución de los comandos declarados

Los cinco de `CLAUDE.md` §0.3. Ejecutados hoy, no citados.

| Comando declarado | ¿Corre? | ¿Resultado inequívoco? |
|---|---|---|
| `ruff check .` | Sí | Sí — `All checks passed!`, exit 0 |
| `pytest -q -n auto -m "not heavy"` | Sí | Sí — **778 passed · 1 skipped · exit 0** · 13 m 12 s |
| `tsc --noEmit` | Sí | Sí — sin salida, exit 0 |
| `pnpm --filter @pmoaas/web build` | **No ejecutado** | Declarado como tal en §0.3 |
| `alembic upgrade/downgrade/upgrade` | **No ejecutado** | Exige Postgres levantado; declarado como tal |
| `scripts/check_contexto.py` | Sí | Sí — exit 0 |
| `scripts/proximo_id.py` | Sí | Sí — US-194 / BUG-092 / ENH-203 |

Ningún comando declarado falla. Es la diferencia con la auditoría anterior, donde
la Etapa 2 **no pudo correrse** porque no había comandos declarados.

---

## 3. Etapa 3 — evaluación requisito a requisito

### N1 — seis requisitos

| ID | Requisito | Estado | Evidencia | Gravedad |
|---|---|---|---|---|
| CTX-01 | Stack, comandos de verificación y rutas que no se tocan | **CONFORME** | `CLAUDE.md` §0.3: stack, preparación del entorno, 5 comandos con salida registrada, 3 rutas protegidas | — |
| CTX-02 | Presupuesto de contexto permanente declarado | **CONFORME** | `conformidad.yaml` `presupuesto_contexto.permanente_max_chars: 40000`. Ver salvedad en §4 H-3 | — |
| CTX-03 | Sin cifras vivas ni inventarios en el contexto permanente | **NO CONFORME** | Dos en `CLAUDE.md`: línea 106 `778 passed · 1 skipped`, línea 145 `alembic/versions/ (97 archivos)` | **MEDIA** |
| CAP-01 | Procedimiento repetible en artefacto invocable | **CONFORME** | `.claude/skills/`: `triage`, `cerrar-item`, `delegar`, `resumen-ronda`, `handoff`. 25.684 caracteres bajo demanda | — |
| AUT-01 | Acción irreversible exige confirmación humana | **PARCIAL** | `.claude/settings.json` + hook `PreToolUse` → `scripts/guard_irreversible.py`. Lógica probada en 15 casos; **activación comprobada y fallida** | **MEDIA** |
| HER-01 | Credenciales fuera del repositorio | **CONFORME** | `.gitignore` cubre `.env*`; solo `.env.example` versionado. Barrido de `AKIA…`, `sk-…`, `ghp_…`, claves privadas y URIs `postgres://` con credenciales: cero | — |

### N2 — cinco requisitos

| ID | Requisito | Estado | Evidencia | Gravedad |
|---|---|---|---|---|
| CTX-04 | Instrucciones temáticas solo cuando la tarea las toca | **CONFORME** | Del contenido de las skills, se carga siempre el **7,2 %** (1.861 de 25.684 caracteres): solo las `description` | — |
| CTX-05 | El presupuesto se verifica de forma automática | **CONFORME** | `scripts/check_contexto.py` + job `contexto-permanente` en `ci.yml`, sin filtro de paths. Probado en ambos sentidos. Salvedad en §4 H-2 | — |
| FLU-01 | Comandos sin intervención y con resultado inequívoco | **CONFORME** | Los tres ejecutables salen exit 0 en Windows limpio, sin GTK/Pango. Antes de la acción 3b: 4 fallos y exit 1 | — |
| FLU-02 | Definición de terminado comprobable por el entorno | **CONFORME** | `CLAUDE.md:125` la declara; CI la comprueba entera — un PR no pasa sin `lint` + `api-tests-smoke` + `web-typecheck` en verde | — |
| FLU-03 | Lo que debe ocurrir siempre está automatizado | **CONFORME** | El límite de 250 líneas de `SPRINT.md`, antes confiado a que alguien invocara `/handoff`, lo ejecuta CI. Estaba en 521; hoy 223 | — |

**Nueve CONFORME · uno PARCIAL · uno NO CONFORME.**

---

## 4. Etapa 4 — hallazgos transversales

### H-1 · Cifras vivas reintroducidas por la propia remediación — **MEDIA**

**Patrón 9 del catálogo.** `CLAUDE.md` §0.3 declara «778 passed · 1 skipped» y
«`alembic/versions/` (97 archivos)». Ambas derivan del contenido real y quedan
obsoletas con el próximo test o la próxima migración.

**Consecuencia.** Es el mismo fallo que CTX-03 previene y que este repositorio ya
pagó con los IDs duplicados de 2026-06-06 — salvo que aquí el daño es menor: un
número que envejece y confunde, no una colisión.

**Lo señalo contra mi propio trabajo.** Las escribí yo en las acciones 3 y 3b,
como evidencia de ejecución. Eran correctas el día que las medí y dejan de serlo
sin que nadie lo note.

**Corrección.** El criterio estable es `exit 0`, no el conteo. Dejar en
`CLAUDE.md` solo el criterio, y que las cifras medidas vivan en
`conformidad.yaml`, que es el registro de auditoría y **no** contexto permanente.
Cierra CTX-03 y respeta CTX-06.

### H-2 · Controles configurados que CI todavía no ha ejercido — **BAJA**

Los jobs `contexto-permanente` y los tres de verificación están declarados en
`ci.yml`, pero **CI no ha corrido nunca con esta configuración**: no hay push. La
lógica de `check_contexto.py` sí se probó localmente en ambos sentidos.

Se declaran CONFORME y no PARCIAL por una distinción deliberada: aquí el control
**no se ha ejercido todavía**, mientras que en AUT-01 se ejerció y se confirmó
**inactivo**. No es lo mismo «pendiente de estrenar» que «probado y no funciona».
Aun así, el primer PR es el que convierte esto en evidencia.

### H-3 · El presupuesto declarado está excedido y no lo ratificó el owner — **BAJA**

CTX-02 exige **declarar** el presupuesto, y está declarado: CONFORME por el texto
del requisito. Pero conviene no leerlo como que el entorno cabe en su presupuesto:

- Declarado **40.000**, real **50.217**: excedido en un 25 %.
- El 40.000 **lo propuso la auditoría**, no el owner.
- Ninguna acción pendiente cierra esa brecha. El epic mediano son 16.006
  caracteres y `CLAUDE.md` §1.4 obliga a cargar uno entero por sesión.

Un presupuesto permanentemente incumplido deja de informar decisiones. O se
cambia el método de carga de epics, o se fija el objetivo en lo que el entorno
cuesta de verdad (~50.000). Es decisión del owner.

### H-4 · Sin caso de no-activación para las skills nuevas — **BAJA, informativa**

EVA-01 y EVA-02 son N3, fuera del objetivo. Se anota porque las cuatro skills
nuevas se escribieron con «cuándo NO usarla» en la `description` —un anticipo
barato de EVA-02— y conviene no perder ese hábito al crear la siguiente.

---

## 5. Etapa 5 — nivel alcanzado

**N0.**

| Bloquea | Estado | Qué falta exactamente |
|---|---|---|
| AUT-01 (N1) | PARCIAL | Que el hook se active: abrir `/hooks` o reiniciar, y reconfirmar |
| CTX-03 (N1) | NO CONFORME | Quitar dos cifras vivas de `CLAUDE.md` §0.3 |

**Distancia a N1: dos requisitos.** **Distancia a N2: los mismos dos** — los cinco
de N2 ya están CONFORME, así que N1 y N2 caen juntos.

| Dominio | Conformes / aplicables | Gravedad máxima |
|---|---|---|
| CTX | 4 / 5 | MEDIA |
| CAP | 1 / 1 | — |
| FLU | 3 / 3 | — |
| AUT | 0 / 1 | MEDIA |
| HER | 1 / 1 | — |

---

## 6. Etapa 6 — plan

Una sola tanda, corta. No hay nada que diseñar: son dos correcciones puntuales.

| # | Acción | Cierra | Esfuerzo | Quién |
|---|---|---|---|---|
| 1 | Sacar de `CLAUDE.md` §0.3 el conteo de tests y el de migraciones; dejar `exit 0` como criterio y mover las cifras a `conformidad.yaml` | **CTX-03** | 10 min | Claude |
| 2 | Abrir `/hooks` o reiniciar la sesión, y reconfirmar que el guard intercepta | **AUT-01** | 2 min | **Owner** — no puedo abrir `/hooks` |
| 3 | Reejecutar `MCA-P02`. Con 1 y 2 hechas, el entorno alcanza **N2** | — | 20 min | Claude |

**Después de eso, y solo después, MCS.** `AUDITORIA.md` §1.1: los hallazgos de MCA
cambian los otros dos marcos, y ahora los comandos de verificación existen y
corren, así que lo que MCS reporte sobre cobertura por fin significará algo.

**Lo que baja el contexto permanente** ya no está en este plan: se agotó lo barato.
Lo que queda exige decidir si `CLAUDE.md` §1.4 sigue obligando a cargar el epic
entero (16.006 caracteres, el mayor consumidor que queda).

---

## 7. Anexo — no verificable / no evaluado

| Elemento | Motivo |
|---|---|
| `pnpm build` y migraciones Alembic | No ejecutados: el primero por tiempo, el segundo exige Postgres. Declarados como tal en `CLAUDE.md` §0.3 |
| Jobs de CI | Nunca ejecutados en GitHub Actions: no hay push. Ver H-2 |
| Los 2 tests heavy de `html_to_pdf` | Exigen GTK/Pango, ausentes en Windows. Colectan (6 tests, exit 0); corren en `api-tests-heavy` |
| Requisitos N3-N5 | Fuera del nivel objetivo N2 |
| MCC | `no_aplica` declarado: producto propio, sin encargo |
| MCS | No auditado. Correcto mientras MCA no llegue a N2 |
