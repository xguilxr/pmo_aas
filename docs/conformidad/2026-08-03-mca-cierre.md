# Auditoría MCA — cierre de la Tanda 1

| Campo | Valor |
|---|---|
| Repositorio | `xguilxr/pmo_aas` · árbol de trabajo, **sin commitear** |
| Marco | MCA-CORE v1.0.0 · procedimiento MCA-P02 v1.0.0 |
| Fecha | 2026-08-03 · tercera ejecución de la jornada |
| Nivel objetivo | **N2** |
| Nivel alcanzado | **N0** |
| Anteriores | [inicial](2026-08-03-mca.md) (N0, corte duro) · [seguimiento](2026-08-03-mca-seguimiento.md) (N0, 9/11) |

---

## 1. Resultado

**Diez de once requisitos CONFORME.** El nivel sigue siendo **N0** porque el
undécimo, `AUT-01`, está PARCIAL — y un PARCIAL impide alcanzar su nivel
(MCA-CORE §6.2). AUT-01 es de N1, así que bloquea los dos.

**No es que falte trabajo: falta una verificación que no puedo hacer desde aquí.**
El guard de acciones irreversibles está escrito, versionado y probado en 15 casos
de lógica. Lo que no se ha podido observar es su **activación**, porque
`.claude/settings.json` es configuración *del proyecto* y esta sesión está
enraizada en `C:/Users/David Aguilar`, no en el repositorio.

Contexto permanente: **50.380 caracteres**, contra 87.623 al abrir. **−43 %**.

---

## 2. Etapa 1 — contexto permanente

| Artefacto que se carga sin pedirlo | Caracteres |
|---|---:|
| `CLAUDE.md` | 17.080 |
| `docs/project-management/SPRINT.md` | 10.866 |
| Epic relevante (mediana de 18) | 16.006 |
| `docs/project-management/HANDOFF.md` | 4.567 |
| Catálogo de skills (solo `description`) | 1.861 |
| **Total** | **50.380** (~12.595 tokens) |

Techo que CI hace cumplir: 50.400. Objetivo declarado: 40.000.

### Serie

| Hito | Caracteres | vs. inicio |
|---|---:|---:|
| Inicio de la auditoría | 87.623 | — |
| Acción 4 — check en CI | 87.623 | +0 % |
| Acción 5 — `SPRINT.md` 521→219 líneas | 68.055 | −22 % |
| Acción 6 — `CLAUDE.md` a skills | 50.036 | −43 % |
| Acciones 7-10 | 50.380 | −43 % |

El grueso lo dieron dos acciones. Las tres últimas cerraron requisitos sin bajar
volumen, y eso es correcto: CTX-03 y AUT-01 son de corrección, no de tamaño.

---

## 3. Etapa 2 — ejecución de los comandos declarados

| Comando declarado | ¿Corre? | Resultado |
|---|---|---|
| `ruff check .` | Sí | `All checks passed!` · exit 0 |
| `pytest -q -n auto -m "not heavy"` | Sí | 778 passed · 1 skipped · exit 0 · 13 m 05 s |
| `tsc --noEmit` | Sí | exit 0 |
| `scripts/check_contexto.py` | Sí | exit 0 |
| `scripts/proximo_id.py` | Sí | exit 0 · US-194 / BUG-092 / ENH-203 |
| `pnpm build` | **No ejecutado** | Declarado como tal |
| Migraciones Alembic | **No ejecutado** | Exige Postgres; declarado como tal |

---

## 4. Etapa 3 — los once requisitos

### N1

| ID | Estado | Evidencia |
|---|---|---|
| CTX-01 | **CONFORME** | `CLAUDE.md` §0.3: stack, entorno, comandos, rutas protegidas |
| CTX-02 | **CONFORME** | `conformidad.yaml` → `permanente_max_chars: 40000`. Salvedad en H-4 |
| CTX-03 | **CONFORME** | Cero cifras vivas. Verificado por `check_contexto.py::cifras_vivas`, probado en 4 escenarios |
| CAP-01 | **CONFORME** | 5 skills en `.claude/skills/`; 25.684 caracteres bajo demanda |
| AUT-01 | **PARCIAL** | Guard escrito, versionado y probado en 15 casos. **Activación no observada** — ver H-5 |
| HER-01 | **CONFORME** | `.env*` ignorados; barrido de secretos sobre archivos versionados: cero |

### N2

| ID | Estado | Evidencia |
|---|---|---|
| CTX-04 | **CONFORME** | Se carga siempre el **7,2 %** del contenido de las skills |
| CTX-05 | **CONFORME** | `check_contexto.py` + job `contexto-permanente`, sin filtro de paths |
| FLU-01 | **CONFORME** | Los tres comandos ejecutables dan exit 0 en Windows limpio |
| FLU-02 | **CONFORME** | Declarada en `CLAUDE.md`; CI la comprueba entera (3 jobs) |
| FLU-03 | **CONFORME** | El límite de `SPRINT.md`, antes en prosa, lo ejecuta CI |

> **Nota de método.** La reverificación automatizada marcó FLU-01 como REVISAR.
> Era el arnés, no el requisito: `shell=True` en Windows usa `cmd.exe`, que no
> resuelve `.venv/Scripts/python.exe` con barras normales. Comprobado con la
> invocación real: exit 0. Se deja escrito porque un falso negativo silenciado
> es tan malo como un falso positivo.

---

## 5. Etapa 4 — hallazgos transversales

| # | Hallazgo | Gravedad |
|---|---|---|
| H-1 | La skill `handoff` no declara cuándo **no** usarla (patrón 7). Las cuatro nuevas sí. EVA-02 es N3: no bloquea N2 | BAJA |
| H-2 | Dos de siete comandos declarados nunca se han ejecutado (`pnpm build`, migraciones). Declarados como tal, no ocultos | BAJA |
| H-3 | Los jobs de CI **nunca han corrido** en GitHub Actions: no hay push. La lógica se probó localmente en ambos sentidos | BAJA |
| H-4 | El presupuesto declarado (40.000) está excedido un 25 % y **lo propuso la auditoría**, no el owner | BAJA |
| H-5 | **AUT-01 no es verificable desde esta sesión.** Ver §6 | MEDIA |

Patrones **no** encontrados: permiso global por omisión (P5, `allow` vacío y sin
`defaultMode` permisivo) · memoria persistente contradictoria (P6, ninguna
versionada) · configuración copiada de otro repositorio (P10).

---

## 6. El único bloqueo, y por qué

`.claude/settings.json` es configuración **del proyecto**. Solo se carga cuando
Claude Code se abre con ese repositorio como directorio de trabajo. La auditoría
corrió desde `C:/Users/David Aguilar`.

Se probó **dos veces** con un comando inofensivo que coincide con un patrón de
bloqueo. Las dos veces se ejecutó sin ser interceptado. La primera hipótesis
—«el vigilante no toma un settings creado a mitad de sesión»— **quedó descartada**
cuando el owner abrió `/hooks` y el comportamiento no cambió.

**Prueba de aceptación:**

```bash
cd "C:/Users/David Aguilar/claude/pmo_aas"
claude
# y dentro de esa sesión:
echo "prueba: git push --force"
```

Si queda interceptado, AUT-01 pasa a CONFORME y **el entorno alcanza N2** sin
tocar una línea de código.

Esto no es solo un tecnicismo de conformidad: **el guard tampoco protege hoy** a
quien trabaje desde fuera del repositorio. Empieza a hacerlo al abrir la sesión
dentro.

---

## 7. Etapa 6 — plan

| # | Acción | Cierra | Quién |
|---|---|---|---|
| 13 | Prueba de aceptación del guard desde una sesión dentro del repo | **AUT-01** → N2 | **Owner** |
| 14 | Decidir `permanente_max_chars`: o se cambia cómo se cargan los epics, o se fija en ~50.000 | H-4 | **Owner** |
| 15 | Commitear el trabajo en branch (`main` es productiva) y abrir PR: es lo que estrena los jobs de CI | H-3 | Owner + Claude |
| 16 | Añadir a `handoff` cuándo no usarla | H-1 | Claude · 5 min |
| 17 | **MCS-P01 contra N2** | Tanda 2 | Claude · 2-4 h |

**MCS ya no está bloqueada por falta de comandos verificables**: existen, corren y
dan exit 0. Arranca cuando AUT-01 cierre.

---

## 8. Anexo — no verificado

| Elemento | Motivo |
|---|---|
| Activación del guard | Requiere sesión enraizada en el repositorio |
| `pnpm build`, migraciones Alembic | No ejecutados; declarados como tal en §0.3 |
| Jobs de CI | Nunca ejecutados en GitHub Actions: no hay push |
| 2 tests heavy de `html_to_pdf` | Exigen GTK/Pango; colectan, corren en `api-tests-heavy` |
| Requisitos N3-N5 | Fuera del objetivo N2 |
| MCC · MCS | `no_aplica` declarado · no auditado hasta que MCA llegue a N2 |
