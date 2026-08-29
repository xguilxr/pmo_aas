---
tipo: gestion
responsable: propietario
estado: vigente
revisado: 2026-08-28
revisar_cada: 30d
---

# HANDOFF.md — puente a la próxima sesión

**2026-08-28** · rama `claude/platform-rundown-indexation-pn4a1q` · lo derivado:
`python scripts/estado.py`

## Qué se estaba haciendo, y por qué

Auditoría de la memoria del proyecto. 40 de 91 documentos vivos no tenían ruta
de entrada desde el contexto permanente —glosario y fichas de indicador entre
ellos—, así que cada sesión los re-derivaba del código. Se indexó por sección
(US-243), léxico y no vectorial: el corpus tiene vocabulario controlado y un
vector no se revisa en un PR. Salió además US-224, el catálogo de plantillas.

## Dónde retomar

Abrir PR de esta rama contra `main` (suite en verde) y resolver lo de
ESPERANDO en `SPRINT.md`.

## Qué va a morder

`proximo_id.py` **se queda corto sin `gh`**: dijo US-240 cuando #599–601 ya la
habían tomado. Avisa, pero el aviso se pasa por alto.

Los 40 documentos con deriva **no se arreglan con un gate**: `check_docs.py`
define `revisado` como declaración humana, y sincronizarlo con git automatiza
la mentira que el campo existe para impedir.

## Decisiones del owner

- **Las migraciones no se «despliegan» aparte**: el `CMD` del contenedor `api`
  las corre al arrancar, así que `0105`–`0115` se aplicaron al mergear. Queda
  **leer el registro** de `0110`, `0111` y `0115`.
- **El revamp v2 sigue abierto**: el styling está, el diseño no.
