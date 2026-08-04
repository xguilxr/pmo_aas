---
name: resumen-ronda
description: Formato del resumen que se entrega al owner al terminar cada turno — qué se hizo, qué archivos cambiaron y qué acciones le quedan a él (crear PR, correr migración, cerrar issue). Úsala al cerrar cualquier ronda de trabajo, incluidas las que fueron solo discusión. NO la uses para el cierre de sesión completo, que es handoff.
---

# Resumen de ronda

Una **ronda** = un prompt del owner + la acción que Claude ejecuta en respuesta.
Al terminar cada ronda se entrega este resumen antes de quedar a la espera.

---

## Plantilla

```markdown
## Resumen de la ronda

**Hecho:**
- <bullet 1: qué decisión se tomó / qué se implementó>
- <bullet 2: qué se movió en SPRINT.md / qué label cambió>
- <bullet 3: commits nuevos con SHA corto>

**Archivos modificados:**
- `path/a/archivo.ext` — <razón 1 línea>
- `path/a/otro.ext` — <razón 1 línea>
(o referencia a `git diff --stat HEAD~N..HEAD` si son muchos)

**Acciones externas para el owner:**
- [ ] Crear PR de `<branch>` → `main` (o merge directo si aplica)
- [ ] Crear label `<nombre>` en GitHub UI (si falta)
- [ ] Correr migración Alembic en Railway (`alembic upgrade head`)
- [ ] Subir landing/ a HostGator (o cualquier otro paso manual)
- [ ] Cerrar issue #N tras verificar el fix
- [ ] (ninguna, si todo quedó autoejecutable)
```

---

## Reglas

- **Bullets concisos**, una línea cada uno. Si una acción necesita más
  explicación, que viva en el commit message o en el comment del issue.
- **Lista de archivos siempre presente.** Si hay más de 15, usar
  `git diff --stat <rango>` en vez de enumerarlos.
- **Acciones externas con checkbox** `- [ ]` para que el owner las marque
  conforme las ejecuta. Si no hay ninguna, escribir explícitamente «ninguna» —
  nunca omitir el bloque.
- Si la ronda terminó con **commit + push**, incluir siempre el SHA corto y el
  nombre de la branch.
- Si la ronda fue puramente de **discusión o propuesta**, «Archivos modificados»
  dice `— ninguno —` y «Acciones externas» lista lo que el owner debe responder
  o decidir.
