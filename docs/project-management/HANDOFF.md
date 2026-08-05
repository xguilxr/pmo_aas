# HANDOFF.md — Estado para la próxima sesión

**Última actualización:** 2026-08-05
**Branch activa:** `claude/audit-continuation-fzrtko` — **16 commits, sin PR**
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
  **AM-08/SEG-07** `audit_log` de solo anexado · **SEG-01** PyJWT, 5 CVE menos ·
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

1. **Abrir el PR** de esta branch y mergear.
2. **Correr las migraciones `0097` y `0098`** (las deniega el guard; son del owner).
3. Después: **D-3** (`wbs_code`) si el owner da luz verde a la ronda — ADR-020 la
   mide en 259 ocurrencias y 22 archivos. **D-8** está bloqueada por el nombre.

## ⚠️ Gotchas

- **La migración 0097 no se ejecutó por Alembic.** Su SQL sí se ejercitó contra
  un Postgres 16 real, `downgrade` incluido.
- **`RATE_LIMITED` pasó de 422 a 429.** Cambio de contrato pequeño, ya en
  `api-conventions.md`. Afecta también a reseteo de contraseña.
- **El presupuesto de contexto va al límite.** Correr `check_contexto.py` antes
  de engordar `CLAUDE.md`, `SPRINT.md` o este archivo.
- **El guard bloquea comandos que *mencionan* uno denegado**, aunque el patrón
  aparezca en una ruta de archivo. Se reformula, no se relaja el patrón.
- **La suite tarda ~2m45s** con `-n auto`. Correrla en segundo plano.
- Sin tests de frontend. Python 3.12 no es negociable.
- **El clon local se revirtió dos commits a mitad de sesión** y hubo que
  rebasar sobre el remoto. Si el árbol no cuadra con lo que recordás, mirá
  `git log origin/<branch>` antes de rehacer nada.

## 📚 Epics docs

Solo EP014 cambió (tipografía de los entregables). Al día también:
`api-conventions.md`, `modelo-amenazas.md`, `amenazas.yaml`, `DB-CHANGES.md`,
glosario, ADR y `design-system/tokens.md`.

## ✅ Decisiones del owner — 2026-08-05

| # | Decisión | Estado |
|---|---|---|
| Rumbo | **Volver al producto.** Las Tandas C/D/E no se abren; se retoman con motivo de negocio | Registrada |
| LEN-02 | **Norma para lo nuevo.** Convención en `api-conventions.md` §7; los 152 se arreglan al tocar cada endpoint | **Hecha** |
| SEG-01 | **Migrar a PyJWT.** Cierra 5 CVE | **Hecha** |
| D-2 | **Renombrar `support` → `hypercare`** | **Hecha** (ADR-019, mig 0098) |

## 🛠️ Producto — después de las decisiones

- **ENH-202** — Helvetica en los cuatro caminos de export. Cerró **AM-12** y
  destapó que los informes **llevaban meses saliendo en DejaVu Sans**: el CSS
  pedía DM Sans y la imagen no instalaba ninguna de las fuentes declaradas.
- **D-2** — con ventana: el API acepta `support` y devuelve `hypercare`.

## 🗳️ Segunda tanda de decisiones — 2026-08-05

| Decisión | Siguiente paso |
|---|---|
| **D-3: ejecutar en la próxima ronda** | Es lo primero al retomar |
| **D-8: `portfolio_function` → `discipline`** | ADR-021 escrita. 18 ocurrencias, 9 archivos. Falta la US |
| **Fase `cancelled`: sí. `initiation`: no** | ADR + US propias, sin abrir |
| **Paleta de gráficos: propia** | Ni marca ni Tailwind: categórica y distinta del semáforo a propósito |

`discipline` se eligió porque «función» y «rol» ya significan otras cosas aquí
—`by_function` es agregación de capacidad, «rol» es el de permisos—.

**Sigue abierta solo D-4**, el umbral del semáforo: no tiene respuesta útil sin
un proyecto real con desviación medible contra el que calibrar.

## 🧹 Acciones del owner

- [ ] **Abrir el PR de `claude/audit-continuation-fzrtko` y mergear.**
- [ ] **Correr las migraciones `0097` y `0098`** cuando el PR entre.
- [ ] Smoke manual de la web: cambiaron seis tokens de color y la fase
      `support` pasó a `hypercare` en filtros y etiquetas.
- [ ] Decidir el nombre destino de `portfolio_function` (D-8, bloqueada).

## 🔮 Sin issue todavía

- **La paleta de gráficos** (tendencias, Gantt, curva-S) arrastra los colores de
  Tailwind que D-7 retiró del semáforo.
- **`design-system/tokens.md`** describe una paleta anterior; queda declarado
  obsoleto, no corregido.
- **AM-10** —bloqueo por cuenta como denegación de servicio— sigue sin control.
- **DCMA 14-point** y **línea base** (D-6), sin la cual «desviación» no tiene
  referente.
- **`MCS-CORE §5.14` enuncia SEG-06 sin traer procedimiento** — defecto del kit.

---

El orden de lectura al abrir sesión lo fija `CLAUDE.md` §1; no se repite aquí.
