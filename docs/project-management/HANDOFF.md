# HANDOFF.md — Estado para la próxima sesión

**Última actualización:** 2026-08-05
**Branch activa:** `claude/cap01-y-recuento` — **PR #576 abierto, CI verde**
**Generado por:** `/handoff`

---

## 🎯 Dónde estamos parados

**La medición terminó; la remediación no.** Ya no queda un solo requisito sin
estado en ninguno de los dos marcos. Con el merge de #576, **MCA alcanza su
objetivo N2**. **MCS sigue en N0**: 22 de 126 conformes y **51 requisitos
bloquean N1**.

| Marco | Objetivo | Hoy | Falta |
|---|---|---|---|
| MCA (entorno) | N2 | **N2** al mergear #576 | Nada del objetivo. N3 no lo es |
| MCS (producto) | N2 | **N0** | 51 para N1 · Tandas C/D/E, 6-9 semanas |

## 📍 Dónde retomar

> **Modo de trabajo pedido por el owner (2026-08-05):** recorrer **todo lo
> pendiente de una corrida**, sin parar a preguntar. Las decisiones que necesiten
> su confirmación se **acumulan y se preguntan al final**, juntas. No fragmentar
> la sesión en idas y vueltas.

Orden sugerido, de menor a mayor coste — todo esto **no necesita confirmación**:

1. **SUM-02** — `USER` sin privilegios en `apps/api/Dockerfile`. 3 líneas. Cuidar
   que el `CMD` corre migraciones y que MPXJ quede legible para ese usuario.
2. **DES-03** — `SELECT 1` con tiempo límite en `/health`. 10 líneas.
3. **LEN-02** — los seis textos por defecto de `app/core/errors.py`. Es la palanca:
   los malos viven todos ahí.
4. **DIS-02 + D-7** — cinco tokens de `globals.css` y unificar las dos paletas de
   salud. **Son el mismo trabajo**: el verde que falla AA (`#1F8A5B`, 4.33:1) es
   el del semáforo. Después enganchar `scripts/check_contraste.py` al CI.
5. **AM-09** — límite por IP en `/auth/login`. El limitador ya existe
   (`services/rate_limit.py`) y se aplica en recuperación y reseteo; falta ahí.
6. **AM-08** — `REVOKE UPDATE, DELETE` al rol de la aplicación sobre `audit_log`.
   Sin código.
7. **D-9** — validar `is_milestone ⟹ duration_days = 0`.

**Al final, preguntar en bloque** (§ «Confirmaciones pendientes»).

## ✅ Hecho en esta sesión

**PR #575, mergeado** (`98fa3a2`) — 9 commits:

- **R1 completa**: los 13 requisitos MCS en NO VERIFICABLE, medidos. Resultado:
  1 no aplicable, 1 conforme, 1 excluido, 4 parciales, 6 no conformes.
  `docs/conformidad/2026-08-04-mcs-r1.md`.
- **AUT-01**: lo irreversible pasó de `ask` a `deny` + 24 casos de prueba.
- **ADR-018**: ARQ-03 excluido con riesgo aceptado y revisión el 2027-02-04.
- **IA-04 conforme** y **CON-04 mitigado** (código).
- **Glosario aprobado**: 8 decisiones del owner, 1 abierta.

**PR #576, abierto** (`852c19e`, `d8892b9`) — CAP-01 (skill `rebasear`) y la
corrección del recuento de R1.

**Acciones del owner cerradas:** `SENTRY_DSN` puesto, `main` protegida con los 8
checks, migraciones verificadas en 0096.

## 🔄 PRs en flight

| # | Branch | CI | Acción |
|---|---|---|---|
| #576 | `claude/cap01-y-recuento` | **verde** (`MERGEABLE`/`CLEAN`) | **Mergear** |

## ⚠️ Gotchas

- **Las migraciones las corre el owner.** El guard las deniega desde #575. Es el
  precio acordado de que `deny` sobreviva a cualquier modo de permisos.
- **El guard bloquea mensajes de commit que *mencionan* un comando denegado.**
  Pasó dos veces. La salida es `git commit -F <archivo>`, no relajar el patrón.
- **Un check requerido que se salta NO bloquea el merge** — verificado con #576,
  que es de solo-docs: `MERGEABLE`/`CLEAN` con cinco jobs en *skipping*.
- **`api-tests-heavy` nunca debe ser requerido:** solo corre en push a `main`.
- **La suite de API tarda ~26 min en local** (3m21s en CI). Correrla en segundo
  plano y seguir trabajando.
- **Publiqué mal el recuento de R1** («3 parciales, 7 no conformes»). Son 4 y 6.
  Corregido **con la corrección anotada** en el informe, no en silencio.
- Sin tests de frontend. Python 3.12 no es negociable.

## 📋 Lo que sigue

- **Conformidad:** la lista de «Dónde retomar». Después, Tandas C/D/E — pero eso
  merece decisión de negocio, no inercia.
- **Glosario:** D-3 (`wbs_code`) y D-8 (`portfolio_function`) tocan contrato: ADR
  + US propia, una por una.
- **Producto:** ENH-202 (Helvetica en todos los exports) es el batch que espera.
- **Amenazas:** AM-14 cerrada al proteger `main`. Quedan AM-08, AM-09 y AM-10.

## 📚 Estado de las epics docs

| Epic | Sincronizada | Notas |
|---|---|---|
| EP008 (IA) | **sí** | Actualizada esta sesión: contexto fechado (CON-04), aviso y escalada (IA-04), y por qué IA-01 es NO APLICABLE **hoy** |

Ninguna otra epic cambió de comportamiento.

## ❓ Confirmaciones pendientes — preguntar AL FINAL de la próxima sesión

1. **¿Seguimos con las Tandas C/D/E de MCS o cortamos?** Son 6-9 semanas y 51
   requisitos. Mi recomendación: cerrar lo barato y volver al producto; retomar
   las tandas cuando haya motivo de negocio.
2. **D-4, umbral del semáforo.** Sigue abierto y es lo único que deja el glosario
   en borrador. ¿Uno o varios? Se calibra contra un proyecto real.
3. **D-2, nombre de la fase de hypercare.** ¿`support` se queda o se renombra a
   `hypercare`? ¿Hacen falta `initiation` y `cancelled`?
4. **DAT-11 y DIS-03** son transversales y caros. ¿Norma para lo nuevo y arrastre
   por tandas, o campaña dedicada?
5. **Migrar `python-jose` a PyJWT** — cerraría 5 CVE que bloquea `pyasn1<0.5.0`.

## 🧹 Acciones del owner

- [ ] **Mergear #576** — con eso MCA queda en N2.
- [ ] Smoke manual de la web tras el salto de Next 15.0 → 15.5.
- [ ] Correr las migraciones locales cuando una branch traiga alguna.

## 🔮 Sin issue todavía

- **DCMA 14-point** (`docs/dominio/01-DIAGNOSTICO.md` §4) y **línea base** (D-6),
  sin la cual «desviación» no tiene referente.
- **MCA N3**: CAP-02 y APR-01 no existen. No es objetivo.
- **`MCS-CORE §5.14` enuncia SEG-06 sin traer procedimiento** — defecto del kit,
  merece issue.

---

El orden de lectura al abrir sesión lo fija `CLAUDE.md` §1; no se repite aquí.
