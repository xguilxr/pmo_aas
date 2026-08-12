---
tipo: gestion
responsable: propietario
estado: vigente
revisado: 2026-08-12
revisar_cada: 30d
---

# HANDOFF.md — Estado para la próxima sesión

**Última actualización:** 2026-08-12
**Branch activa:** `claude/docs-context-debloat-1j4o3b` — debloat de docs y contexto
**Generado por:** sesión de debloat 2026-08-12

## 🎯 Dónde estamos parados

La conformidad está cerrada (ADR-036, 2026-08-07) y los trinquetes de CI siguen
activos. Vuelta al producto. Esta sesión ejecutó el debloat documental:
CLAUDE.md compacto, HANDOFF/SPRINT solo con lo abierto, links vivos reparados y
techo de contexto más bajo en `conformidad.yaml`.

## 📍 Dónde retomar

**Producto.** Lo primero es desplegar lo mergeado: migraciones `0105`-`0107`.
Al desplegar: ten acceso a tu correo (se cierran todas las sesiones vivas y el
panel pasa a dos pasos) y define en Railway las variables opcionales
`CLAMAV_URL` (vacía), `ADMIN_MFA_REQUIRED` (`true`) y
`DISPOSITIVO_CONFIABLE_DIAS` (`30`).

El resto de lo abierto vive en `SPRINT.md` → INBOX. No se repite aquí.

## ⚠️ Gotchas vigentes

- 2026-08-07 — Cerrar el programa no apaga los trinquetes (ADR-036): sin
  auditoría externa, el CI es lo único que impide que la calidad se degrade.
- 2026-08-07 — `registro_conformidad.py` dice `BLOQUEAN N1: 1 ['SEG-01']`. Es
  correcto y se deja así. `SEG-01` queda PARCIAL a sabiendas y no se marca
  CONFORME; el barrido rechaza un `ACEPTADO` sin ADR.

## 🧹 Cleanup técnico pendiente

- [ ] Abrir y mergear el PR de esta branch (debloat documental).
- [ ] Añadir `tipos-python` y `commits` a las verificaciones exigidas de `main`.
- [ ] Activar el hook local: `git config core.hooksPath .githooks`.
- [ ] Confirmar Sentry en Railway.

## 🔮 Para sesiones futuras (sin issue todavía)

- TOTP como segundo factor primario: cerraría `2.7.1`. Descartado por alcance,
  no por postura.
- `CLAMAV_URL` + `POLITICA_SIN_MOTOR = rechazar`: despliegue, no código.
- Más trinquetes sobre evidencia del expediente que nadie vuelve a mirar.
- `DOC-07` (el gate solo informa) y `DAT-07` (tipos propios de magnitud).

## Cómo retomar

1. Lee este `HANDOFF.md` primero; luego `CLAUDE.md`, `SPRINT.md` y `LESSONS.md`.
2. No abras el expediente de conformidad salvo que el CI falle: está cerrado y
   sus barridos se defienden solos.
