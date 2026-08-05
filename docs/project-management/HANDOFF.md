# HANDOFF.md — Estado para la próxima sesión

**Última actualización:** 2026-08-05
**Branch activa:** `claude/audit-continuation-fzrtko` — **10 commits, sin PR**
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

Nueve requisitos, **un commit cada uno**, todos con verificación por mutación:

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
2. **Correr la migración `0097`** (la deniega el guard; es del owner).
3. Después: las cinco confirmaciones de abajo mandan sobre qué sigue.

## ⚠️ Gotchas

- **La migración 0097 no se ejecutó por Alembic.** Su SQL sí se ejercitó contra
  un Postgres 16 real, `downgrade` incluido.
- **`RATE_LIMITED` pasó de 422 a 429.** Cambio de contrato pequeño, ya en
  `api-conventions.md`. Afecta también a reseteo de contraseña.
- **El presupuesto de contexto va al 98 %** (33.917 de 34.500). Cualquier cosa
  que engorde `CLAUDE.md`, `SPRINT.md` o este archivo rompe el CI.
- **El guard bloquea comandos que *mencionan* uno denegado**, aunque sea en una
  ruta (`git stash push -- app/main.py` cayó por «push … main»). La salida es
  reformular, no relajar el patrón.
- **La suite tarda ~2m45s** con `-n auto`. Correrla en segundo plano.
- Sin tests de frontend. Python 3.12 no es negociable.

## 📚 Estado de las epics docs

Ninguna epic cambió de comportamiento. Sí cambiaron, y están al día:
`api-conventions.md`, `modelo-amenazas.md`, `amenazas.yaml`, `DB-CHANGES.md`,
`02-GLOSARIO.md`, `03-REVISION-GLOSARIO.md`, `design-system/tokens.md`.

## ❓ Confirmaciones pendientes

Se le preguntaron al owner al cierre de la sesión. **Si no hay respuesta
registrada abajo, siguen abiertas:**

1. **¿Tandas C/D/E de MCS, o cortar?** 50 requisitos, 6-9 semanas.
   Recomendación: volver al producto y retomarlas con motivo de negocio.
2. **D-4, umbral del semáforo.** Lo único que deja el glosario en borrador.
3. **D-2, nombre de la fase de hypercare.** ¿`support` o renombrar?
4. **LEN-02, los 152 mensajes restantes.** ¿Norma para lo nuevo, o tanda?
5. **Migrar `python-jose` a PyJWT** — cerraría 5 CVE que bloquea `pyasn1<0.5.0`.

## 🧹 Acciones del owner

- [ ] **Abrir el PR de `claude/audit-continuation-fzrtko` y mergear.**
- [ ] **Correr la migración `0097`** cuando el PR entre.
- [ ] Smoke manual de la web: cambiaron seis tokens de color.
- [ ] Responder las cinco confirmaciones.

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
