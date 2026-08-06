---
tipo: runbook
responsable: propietario
estado: vigente
revisado: 2026-08-06
revisar_cada: 30d
---

# Runbook — cerrar N1

Qué falta para que MCS pase de **N0 a N1**, en orden de ejecución, separando lo
que depende de una decisión tuya de lo que es solo trabajo.

**La cifra viva no está aquí.** Sale de `python scripts/registro_conformidad.py`.
Al escribir esto: **29 bloqueantes**. Si el script y este documento discrepan,
gana el script.

> **Regla de nivel (MCS-CORE §6.2):** el nivel alcanzado es el mayor N donde
> **todos** los requisitos DEBE están Conforme o No aplicable. **Un solo PARCIAL
> bloquea el nivel entero.** No hay crédito parcial: cerrar 28 de 29 deja el
> producto en N0 igual que cerrar 0.

---

## Fase 0 — desbloquear la integración

Nada de lo de abajo llega a `main` mientras esto no se resuelva.

1. **Mergear el PR #582.** Lleva `SEG-04` —la única CRÍTICA del expediente— y
   `DAT-06`. GitHub lo bloquea porque las verificaciones exigidas **no
   reportaron**: Actions estuvo caído, no falló nada.
   - Primero: «Re-run all jobs». Si Actions volvió, se acabó.
   - Si sigue caído: quitar temporalmente de las exigidas **solo las que no
     reportan** (Settings → Branches → `main`), mergear, y reponerlas. Mantené
     `enforce_admins`; es lo que sostiene `CFG-03` e `INT-03`. Anotalo con ADR
     (GOB-02).
   - Evidencia para justificarlo: [`2026-08-06-verificacion-local.md`](2026-08-06-verificacion-local.md).
2. **Tras el merge**, añadir `tipos-python` y `commits` a las exigidas. Antes no
   se puede: GitHub no deja exigir un check que nunca ha reportado.
3. `git config core.hooksPath .githooks` en cada clon.
4. Correr las migraciones `0097`-`0101`.

---

## Fase 1 — lo que cierra con una confirmación tuya

**`OPS-02`** es el único requisito a un paso de cerrar, y el paso no es código:
confirmar en Railway que salen **dos** líneas de Sentry, `proceso=api` y
`proceso=worker`. Con las dos, cierra. Con una, no.

---

## Fase 2 — los que necesitan tu postura

**No son caros por volumen. Son caros porque fijan una posición del producto**, y
esa no la puede tomar quien implementa. Cada uno está en las preguntas de abajo.
Respondida la pregunta, la implementación es trabajo normal.

| ID | Qué se decide |
|---|---|
| `CON-01`, `CON-03`, `CON-05` | Frontera de competencia, fuente normativa, derivación a profesional |
| `REQ-02` | Cuatro escenarios de calidad **con número** (hoy: cero) |
| `REQ-03` | Inventario de datos personales y su base |
| `DAT-01`, `DAT-10` | Unidades canónicas y fichas de indicador: qué métricas y quién firma |
| `LEN-03` | Guía de estilo: tratamiento personal, anglicismos, formato de números y fechas |
| `CFG-06` | Si el producto tiene versión pública, y qué la avanza |
| `SEG-02` | Almacén de secretos, o se queda en variables de Railway |
| `DEV-02`, `DEV-03` | Estrategia de pruebas: hoy hay **cero** pruebas de frontend |
| `SUM-01` | Si la canalización produce artefacto, o Railway sigue construyendo desde la rama |
| `INF-02`, `INF-03`, `DES-02` | Paridad de entornos, copias probadas, reversión |
| `CON-02` | Si el conocimiento de dominio vive en artefactos o en instrucciones al modelo |

---

## Fase 3 — trabajo sin decisión

Estos los puedo hacer sin preguntarte nada. Están ordenados por relación
resultado/esfuerzo.

| ID | Medido hoy | Nota |
|---|---|---|
| `LEN-02` | **166** mensajes con texto suelto | El mecanismo ya obliga a las tres partes; es barrido |
| `IA-02` | `AuditLog` **no tiene** campo que distinga IA de humano | Columna + migración + cableado |
| `DIS-04` | 17 archivos con borrado; **no hay** componente único de confirmación | Confirmar y nombrar el objeto |
| `DAT-09` | `report_kpis.py` existe; `progress` aparece en 20 archivos | Hay que medir cuántas son reimplementación real |
| `CFG-01` | Sin medir contra la lista de §5.2.2 | Medición primero |
| `ARQ-04` | Registros a stdout ✅ (OPS-01), configuración por entorno ✅ | Falta comprobar procesos sin estado |
| `REQ-01` | Sin medir | Criterio de aceptación por requisito funcional |
| `SEG-01` | Sin medir | OWASP ASVS L1 aplicable: es auditoría, no barrido |

**Frentes de producto, con épica propia** — medidos y deliberadamente no
mecanizados: `DIS-03` (3 de 75 pantallas con los cuatro estados), `DAT-11` (10
de 87 superficies con marca de actualización), `DAT-02` (8 campos, ~100 sitios,
ADR + migración + ventana por cada uno).

---

## Deuda descubierta el 2026-08-06, sin issue todavía

**29 de 30 migraciones de datos no están ejercidas por ninguna prueba**, y 27 de
ellas **transforman datos existentes** (`UPDATE`/`DELETE`). El job
`api-migrations-postgres` corre sobre base limpia, así que su bucle recorre cero
filas y no las ejerce.

No es hipotético: el encabezado de la `0098` dice que escribía en una tabla
inexistente y pasaba «porque la verificación se fabricaba su propio sujeto».

El molde ya existe y es reutilizable: `apps/api/tests/test_dat06_migracion_0101.py`.

---

## Cómo se cierra un requisito aquí

1. **Medir contra el texto de `MCS-CORE`**, no contra la evidencia anotada. Seis
   defectos reales salieron así en la Ola 2.
2. Implementar con **gate que barre el árbol**, no lista escrita a mano.
3. **Mutar y ver el rojo.** Si la prueba no falla al romper el código, no es
   prueba. Aquí murieron seis pruebas y una justificación falsa.
4. Un requisito, un commit.
5. Registrar el cierre en `CIERRES` de `scripts/registro_conformidad.py`, con
   fuente.
