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

Ocho requisitos, **un commit cada uno**, todos con verificación por mutación:

| Qué | Estado |
|---|---|
| **SUM-02** | El contenedor deja de correr como root |
| **DES-03** | `/health` hace `SELECT 1` acotado y devuelve 503 |
| **LEN-02** | Catálogo con qué/por qué/qué hacer **como datos, no prosa**. Sigue PARCIAL |
| **DIS-02** | 34/34 pares AA en los dos temas + job `contraste-wcag` |
| **D-7** | Una sola paleta de salud (eran cuatro, no dos) |
| **AM-09** | Límite por IP en el login, contando fallos |
| **AM-08 / SEG-07** | `audit_log` de solo anexado |
| **D-9** | `is_milestone ⟹ duration_days = 0` |
| **SEG-01** | `python-jose` fuera, PyJWT dentro. 5 CVE menos |

Informe: `docs/conformidad/2026-08-05-mcs-remediacion.md`.

**Tres hallazgos que la medición no podía ver:**

1. **El `REVOKE` que AM-08 proponía no habría funcionado.** La aplicación se
   conecta con el rol **dueño** de las tablas y en PostgreSQL el dueño conserva
   sus privilegios. Habría sido un control declarado que no actúa. Comprobado
   contra Postgres 16; van disparadores.
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
- **El presupuesto de contexto va justo.** Correr `python scripts/check_contexto.py`
  antes de engordar `CLAUDE.md`, `SPRINT.md` o este archivo: el CI lo frena.
- **El guard bloquea comandos que *mencionan* uno denegado**, aunque sea en una
  ruta (`git stash push -- app/main.py` cayó por «push … main»). La salida es
  reformular, no relajar el patrón.
- **La suite tarda ~2m45s** con `-n auto`. Correrla en segundo plano.
- Sin tests de frontend. Python 3.12 no es negociable.

## 📚 Estado de las epics docs

Ninguna epic cambió de comportamiento. Sí cambiaron, y están al día:
`api-conventions.md`, `modelo-amenazas.md`, `amenazas.yaml`, `DB-CHANGES.md`,
`02-GLOSARIO.md`, `03-REVISION-GLOSARIO.md`, `design-system/tokens.md`.

## ✅ Decisiones del owner — 2026-08-05

| # | Decisión | Estado |
|---|---|---|
| Rumbo | **Volver al producto.** Las Tandas C/D/E no se abren; se retoman con motivo de negocio | Registrada |
| LEN-02 | **Norma para lo nuevo.** Convención en `api-conventions.md` §7; los 152 se arreglan al tocar cada endpoint | **Hecha** |
| SEG-01 | **Migrar a PyJWT.** Cierra 5 CVE | **Hecha** |
| D-2 | **Renombrar `support` → `hypercare`** | **Hecha** (ADR-019, mig 0098) |

## 🛠️ Producto — hecho después de las decisiones

- **ENH-202** — Helvetica en los cuatro caminos de export. Cerró **AM-12** de
  paso: ya no hay tipografías remotas al renderizar un PDF. Y destapó que los
  informes **llevaban meses saliendo en DejaVu Sans**: el CSS pedía DM Sans y la
  imagen no instalaba ninguna de las fuentes declaradas.
- **D-2** — `support` → `hypercare`, con ventana de compatibilidad: el API sigue
  aceptando el nombre viejo y devuelve siempre el canónico.
- **D-3** — **ADR-020**, con la medición: 259 ocurrencias en 22 archivos. No es
  un `sed`: los tres importadores usan «WBS» como etiqueta que el usuario ve en
  su propio Excel, y esa no se renombra. Ronda propia.
- **D-8** — **bloqueada.** Falta decidir el nombre destino: el glosario deja
  «Preferente» en «—» y el campo es un parámetro público de consulta.

**Sigue abierta:** D-4, el umbral del semáforo. No se preguntó porque no tiene
respuesta útil sin un proyecto real con desviación medible contra el que
calibrar. También si hacen falta las fases `initiation` y `cancelled`.

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
