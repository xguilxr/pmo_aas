---
tipo: gestion
responsable: propietario
estado: vigente
revisado: 2026-08-07
revisar_cada: 30d
---

# HANDOFF.md — Estado para la próxima sesión

**Última actualización:** 2026-08-07
**Branch activa:** `claude/asvs-l1-quince-huecos-kgk2qz` · **PR #584 abierto, CI verde**
**Generado por:** `/handoff`

---

## 🎯 Dónde estamos parados

**Los quince huecos ASVS L1 de `SEG-01` están cerrados**, uno por commit, cada
uno con suite propia y verificación por mutación. El mapeo pasa de 15 huecos a
**0** y el tope de `check_asvs.py` de 15 a 0.

**Y aun así `SEG-01` sigue bloqueando N1.** No es un descuido: queda **PARCIAL**
por tres residuales **ACEPTADO** —decisiones tuyas, con ADR— y MCS-CORE §6.2 no
da crédito parcial. Cerrar los quince huecos redujo el problema de quince cosas
por construir a **una decisión por tomar**.

MCA sigue en **N2**, su objetivo. MCS sigue en **N0**, con un solo requisito en
contra.

## 📍 Dónde retomar

**Mergear #584.** El CI está verde; `api-tests-heavy` figura saltado a
propósito, porque solo corre en push a `main`. Lleva tres migraciones y dos
cambios que se notan al desplegar — están en «Cleanup técnico».

Después, la decisión de N1: ver el primer bullet de `SPRINT.md` → INBOX.

## ✅ Hecho en esta sesión

Dieciocho commits en `claude/asvs-l1-quince-huecos-kgk2qz`. Detalle completo, con
la tabla control → commit, en `SPRINT-DONE-HISTORY.md` § *Ronda 2026-08-07*.

- **Los quince controles**, de `7f0c63b` a `ec965ca`. Medición final: **116
  CUMPLE · 8 NO APLICA · 3 ACEPTADO · 0 HUECO**.
- **Tres ADR nuevos:** `ADR-033` (tokens de sesión en cookies `__Host-`),
  `ADR-034` (supresión por anonimización), `ADR-035` (segundo factor por correo
  + ventana de equipo de confianza).
- **Tres migraciones:** `0105` consentimiento, `0106` códigos OTP, `0107`
  equipos de confianza.
- **Dos trinquetes nuevos** en el job `contexto-permanente`:
  `check_subrecursos.py` y `check_password_input.py`.
- `docs/dominio/05-DATOS-PERSONALES.md` §5 deja de declarar «la carencia más
  seria de este inventario»: ya hay procedimiento de acceso y de supresión.

## 🔄 PRs abiertos o en flight

| # | Branch | Estado CI | Acción pendiente |
|---|---|---|---|
| #584 | `claude/asvs-l1-quince-huecos-kgk2qz` | verde | **merge** |

## ⚠️ Gotchas y decisiones recientes

- **Medir contra el texto del control destapó tres evidencias que no eran
  ciertas.** `10.3.2` decía «hoy no se cargan recursos externos» y cargaba tres
  (Google Fonts, sin `integrity`). `2.1.7` no se puede cerrar con una lista
  estándar: de las 59.186 de `rockyou-75`, las que pasan la política del
  producto son **ocho** — una lista así habría sido un archivo grande, un
  control marcado y cero contraseñas detenidas. `12.4.2` tenía dos mitades y
  solo una necesitaba antivirus: el tipo del archivo salía de la cabecera del
  navegador y del nombre, las dos escritas por quien sube.
- **Dos controles existían pero no donde hacían falta.** `2.2.3`/`2.5.5`
  avisaban en uno de los seis sitios que tocan una credencial — justo el único
  donde el cambio lo hace el dueño de la cuenta, o sea donde el aviso no sirve.
- **Cerrar un control abre otros.** El segundo factor hizo que cuatro `NO
  APLICA` dejaran de no aplicar, y convirtió `2.7.1` en residual aceptado. Un
  mapeo no es una lista que solo encoge; al cerrar hay que remedir los vecinos.
- **Un fallo propio lo cazó una prueba ajena.** Al partir el inicio de sesión en
  dos caminos para el segundo factor, el camino directo perdió su registro
  `login_success`; lo detectó la suite de exportación de datos personales.
- **`ACEPTADO` no es `CUMPLE`, y el barrido lo hace cumplir**: rechaza un
  `ACEPTADO` que no cite su ADR. Es lo que impide que un residual se disfrace.

## 📋 Lo que sigue

Detalle en `SPRINT.md` → INBOX.

- **La decisión de N1** (única): revertir `ADR-032` (contraseñas de 12 sin
  reglas) y/o `ADR-035` (TOTP antes que correo) cierra `SEG-01` y lleva MCS a
  N1. **No es código, es postura.**
- **Ola 4 — de N1 a N2.** Se replanifica al alcanzar N1.
- **Cuatro ventanas de compatibilidad abiertas** (`phase=support`,
  `portfolio_function`, `wbs`, `amber_max`) más la nueva
  `cookie:refresh_token`, que se cierra sola al caducar las cookies viejas.
- **`design-system/tokens.md`** sigue describiendo una paleta anterior a D-7.
- **Línea base (D-6) y DCMA 14-point.** Épica propia, sin abrir.

## 📚 Estado de las epics docs

Ninguna epic quedó desactualizada. Los quince controles son **seguridad
transversal**, no funcionalidad descrita en una `EP0XX-*.md`: el documento vivo
de este trabajo es `docs/conformidad/asvs-l1.md`, reescrito en `cd5f9cc`.

| Epic | Sincronizada | Notas |
|---|---|---|
| — | N/A | Ninguna epic describe autenticación, cookies ni el mapeo ASVS |
| `05-DATOS-PERSONALES.md` | sí | §5 actualizado: la carencia de supresión queda cerrada |
| `DB-CHANGES.md` | sí | 0105, 0106 y 0107 documentadas con el porqué de cada forma |
| `amenazas.yaml` | sí | Dos rutas abiertas nuevas declaradas con su motivo |
| `er-generado.md` | sí | Regenerado tras las tres migraciones |

## 🧹 Cleanup técnico pendiente

- [ ] **Mergear #584.**
- [ ] **Correr las migraciones `0105`, `0106` y `0107`.**
- [ ] **Antes de desplegar, ten acceso a tu correo.** Se cierran **todas las
      sesiones vivas** (ADR-033) y entrar al panel pasa a ser dos pasos
      (ADR-035).
- [ ] **Tres variables nuevas en Railway**, las tres opcionales y con valor por
      defecto seguro: `CLAMAV_URL` (vacía), `ADMIN_MFA_REQUIRED` (`true`),
      `DISPOSITIVO_CONFIABLE_DIAS` (`30`).
- [ ] **Decidir sobre `SEG-01`** — es lo único que separa de N1.
- [ ] Pendientes de antes: añadir `tipos-python` y `commits` a las
      verificaciones exigidas de `main`; activar el hook local
      (`git config core.hooksPath .githooks`); confirmar Sentry en Railway;
      contrastar los umbrales de D-4 contra cartera real.

## 🔮 Para sesiones futuras (sin issue todavía)

- **TOTP como segundo factor primario.** Cierra `2.7.1`, quita la dependencia de
  que el correo llegue, y elimina el «si Resend se cae nadie entra». Descartado
  por alcance en ADR-035, no por postura.
- **Poner `CLAMAV_URL` y cambiar `POLITICA_SIN_MOTOR` a `rechazar`.** Trabajo de
  despliegue, no de código.
- **Más evidencia del expediente que nadie vuelve a mirar.** `10.3.2` enseñó que
  la evidencia escrita a mano se queda atrás; los dos trinquetes nuevos cubren
  dos casos, y probablemente haya más.
- **`DOC-07`** — el gate solo informa y hoy hay cero vencidos.
- **`DAT-07`** — tipos propios de magnitud.

---

## Cómo retomar

1. Lee este `HANDOFF.md` primero.
2. Luego `CLAUDE.md` + `SPRINT.md` + `docs/conformidad/plan-remediacion.md`.
3. `python scripts/registro_conformidad.py` da el estado real.
