---
tipo: gestion
responsable: propietario
estado: vigente
revisado: 2026-08-07
revisar_cada: 30d
---

# HANDOFF.md — Estado para la próxima sesión

**Última actualización:** 2026-08-07
**Branch activa:** `claude/cierre-auditoria-asvs` — solo docs
**Generado por:** `/handoff`

---

## 🎯 Dónde estamos parados

**La conformidad está cerrada. Vuelta al producto.**

El programa de remediación terminó el 2026-08-07: los quince huecos ASVS L1 se
cerraron y el owner **aceptó los tres residuales** que quedaban (ADR-036). No
hay auditoría externa — el trabajo se hizo para subir la calidad de la
plataforma, no para pasar una revisión.

`SEG-01` se queda **PARCIAL** y no se toca. MCS se queda en **N0 con un solo
requisito en contra**, a sabiendas. MCA sigue en **N2**, su objetivo.

## 📍 Dónde retomar

**Producto.** No queda nada de conformidad que retomar: `SPRINT.md` → INBOX ya
solo tiene trabajo de producto, y lo primero es **desplegar lo mergeado**
(migraciones `0105`-`0107`, con los dos efectos que se notan).

## ✅ Hecho en esta sesión

Dos tandas, las dos mergeadas a `main` (**#584** y **#585**).

- **Los quince controles ASVS**, uno por commit, con suite propia y verificación
  por mutación. Medición final: **116 CUMPLE · 8 NO APLICA · 3 ACEPTADO · 0
  HUECO**; tope de `check_asvs.py` en **0**. Tabla control → commit en
  `SPRINT-DONE-HISTORY.md` § *Ronda 2026-08-07*.
- **Cuatro ADR:** `033` (tokens de sesión en cookies `__Host-`), `034`
  (supresión por anonimización), `035` (segundo factor por correo + ventana de
  equipo de confianza), **`036` (cierre del programa y aceptación de los tres
  residuales)**.
- **Expediente de conformidad ordenado:** `plan-remediacion.md` y
  `runbook-cierre-n1.md` pasan a `historico`; el índice de `docs/conformidad/`
  dice qué sigue vivo (solo el mapeo ASVS y su barrido).

## 🔄 PRs abiertos o en flight

| # | Branch | Estado CI | Acción pendiente |
|---|---|---|---|
| — | `claude/cierre-auditoria-asvs` | pendiente | abrir PR de cierre documental |

## ⚠️ Gotchas y decisiones recientes

- **Cerrar el programa NO apaga los trinquetes**, y es lo que más importa de
  ADR-036. Sin nadie mirando desde fuera, el CI es lo único que impide que la
  calidad se degrade. Esta ronda lo demostró: **tres de los quince controles
  tenían evidencia escrita a mano que no era cierta** — `10.3.2` decía que no se
  cargaban recursos externos y cargaba tres.
- **`registro_conformidad.py` seguirá diciendo `BLOQUEAN N1: 1 ['SEG-01']`.**
  Es correcto y se deja así: el derivador mide, no opina sobre si el nivel se
  persigue. No es una tarea pendiente.
- **`SEG-01` no se marca CONFORME.** El producto no cumple tres controles L1
  aplicables; que la decisión sea deliberada no lo convierte en cumplimiento, y
  el barrido rechaza un `ACEPTADO` sin ADR.
- **Un fallo propio lo cazó una prueba ajena:** al partir el inicio de sesión en
  dos caminos para el segundo factor, el camino directo perdió su registro
  `login_success`; lo detectó la suite de exportación de datos personales.

## 📋 Lo que sigue

Detalle en `SPRINT.md` → INBOX. **Todo es producto.**

- **Desplegar `0105`-`0107`** con sus dos efectos visibles.
- **Cerrar las ventanas de compatibilidad** cuando el contador lo permita.
- **Contrastar los umbrales de D-4** contra cartera real.
- **`design-system/tokens.md`** describe una paleta anterior a D-7.
- **Línea base (D-6) y DCMA 14-point.** Épica propia, sin abrir.

## 📚 Estado de las epics docs

Ninguna epic quedó desactualizada. El trabajo de esta sesión fue seguridad
transversal y documentación de conformidad, no funcionalidad descrita en una
`EP0XX-*.md`.

| Documento | Sincronizado | Notas |
|---|---|---|
| `docs/conformidad/asvs-l1.md` | sí | El único vivo del expediente; declara el programa cerrado |
| `plan-remediacion.md`, `runbook-cierre-n1.md` | sí | Pasados a `historico` |
| `05-DATOS-PERSONALES.md` | sí | §5 cerrado: hay procedimiento de acceso y supresión |
| `DB-CHANGES.md`, `amenazas.yaml`, `er-generado.md` | sí | Al día tras las tres migraciones |

## 🧹 Cleanup técnico pendiente

- [ ] **Mergear el PR de cierre documental** de esta branch.
- [ ] **Desplegar y correr `0105`, `0106`, `0107`.** Ten acceso a tu correo:
      se cierran todas las sesiones vivas y entrar al panel pasa a ser dos pasos.
- [ ] **Tres variables opcionales en Railway**, todas con defecto seguro:
      `CLAMAV_URL` (vacía), `ADMIN_MFA_REQUIRED` (`true`),
      `DISPOSITIVO_CONFIABLE_DIAS` (`30`).
- [ ] Pendientes de antes: añadir `tipos-python` y `commits` a las
      verificaciones exigidas de `main`; activar el hook local
      (`git config core.hooksPath .githooks`); confirmar Sentry en Railway.

## 🔮 Para sesiones futuras (sin issue todavía)

- **TOTP como segundo factor primario.** Cerraría `2.7.1` y quitaría el «si
  Resend se cae nadie entra». Descartado por alcance, no por postura.
- **`CLAMAV_URL` + `POLITICA_SIN_MOTOR = rechazar`.** Despliegue, no código.
- **Más evidencia del expediente que nadie vuelve a mirar.** Los dos trinquetes
  nuevos cubren dos casos; probablemente haya más.
- **`DOC-07`** (el gate solo informa) y **`DAT-07`** (tipos propios de magnitud).

---

## Cómo retomar

1. Lee este `HANDOFF.md` primero.
2. Luego `CLAUDE.md` + `SPRINT.md`.
3. **No abras el expediente de conformidad** salvo que algo del CI falle: está
   cerrado y sus barridos se defienden solos.
