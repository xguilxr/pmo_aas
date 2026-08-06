---
tipo: informe
responsable: propietario
estado: historico
revisado: 2026-08-05
revisar_cada: nunca
---

# Ola 0 — recuento contra el código de hoy

| Campo | Valor |
|---|---|
| Fecha | 2026-08-05 |
| Qué es | **Medición, no construcción.** No se escribió código de producto |
| Antes | 45 bloquean N1 |
| Después | **41 bloquean N1** |

---

## Por qué existe esta ola

El expediente lleva **cinco errores de recuento documentados**. Los cuatro
primeros iban en la misma dirección —el estado real era peor que el registrado—
y el quinto, `OPS-02`, también: figuraba como «lo más barato que queda, solo
falta la variable de entorno» y el worker no reportaba nada.

Esta ola comprueba la dirección contraria: **el trabajo de producto cierra
requisitos y nadie los remide**. Cuatro de los cuatro sospechados cerraron.

Ninguno costó una línea de código nuevo. Estaban cerrados desde hace horas o
días y el registro no se había enterado.

---

## Grupo A — los que el trabajo de esta sesión pudo cerrar

| ID | Lo que decía la auditoría (2026-08-03) | Medido hoy | Estado |
|---|---|---|---|
| `ARQ-02` | «25 decisiones en `DECISIONS.md`; **ningún ADR** en `docs/adr/`» | **24 ADR** | ✅ **CONFORME** |
| `GOB-02` | Lo mismo, más «las exclusiones de requisitos no están registradas» | 24 ADR y la exclusión de `ARQ-03` registrada en **ADR-018**, con fecha de revisión | ✅ **CONFORME** |
| `LEN-01` | «el glosario existe pero declara **borrador, nada adoptado**» | **Aprobado y completo**: nueve decisiones ejecutadas, umbral calibrado | ✅ **CONFORME** |
| `DAT-05` | «**dos paletas** de salud y **dos vocabularios** de fase conviviendo» | Una paleta (`HEALTH_COLOR`, los dos nombres viejos son alias) y un vocabulario (`support` solo sobrevive en la ventana de compatibilidad) | ✅ **CONFORME** |
| `DAT-06` | «`yellow`/`amber`/`Amarillo` para el mismo valor; `support` como fase inexistente» | La mitad de la fase cerró; **`amber` sobrevive** — ver abajo | ❌ sigue abierto |
| `DIS-01` | «25 literales `#rrggbb`, incluidas las dos paletas divergentes» | Las paletas divergentes ya no están; **siguen 25 literales** | ❌ sigue abierto, acotado |
| `OPS-02` | «sin Sentry ni equivalente» | Cableado en los **dos** procesos; espera confirmación en Railway | ⏳ PARCIAL declarado |

### `DAT-06` — dónde sobrevive `amber`, y cuál de los sitios no es mecánico

1. **`services/reports/engine.py:403`** — traduce `health_status` a la vuelta:
   `{"green":"green","yellow":"amber","red":"red"}`. **No es un olvido**, es una
   traducción deliberada en la frontera con la plantilla; pero es el tercer
   nombre para el mismo valor, que es justo lo que D-1 resolvió.
2. **`templates/pdf/sections/s-03.html:9`** — `data.status_rag or 'amber'` como
   valor por defecto.
3. **`templates/pdf/base.html:89`** — la clase CSS `.dot.amber`. Cosmético.
4. **`services/tenant_settings.py`** — `task_load_thresholds` usa **`amber_max`
   como clave de settings**. Este **no es mecánico**: es una llave guardada en
   `tenant.settings`, o sea contrato con datos existentes. Renombrarla necesita
   ventana de compatibilidad, igual que `wbs` o `portfolio_function`.

El cuarto sitio es la razón de medir antes de disparar: `DAT-06` parecía un
`sed` sobre cuatro literales y trae un cambio de contrato dentro.

---

## Grupo B — los seis que nunca se midieron

| ID | Medido hoy | Estado |
|---|---|---|
| `CON-04` | Tiene trinquete propio, `test_mcs_con04_corpus_fechado.py`, **5 pruebas verdes**. Sigue PARCIAL a propósito, ya declarado | PARCIAL |
| `DIS-05` | «Sin pruebas de teclado.» Confirmado: **cero pruebas de frontend** en todo el repositorio, ni de teclado ni de nada | **NO CONFORME** |
| `DIS-06` | Patrones WAI-ARIA: **6 de 12** componentes de `components/ui` usan `role=` o `aria-`. No es cero, pero es la mitad | **NO CONFORME** |
| `DES-04` | Hay tres runbooks que hablan de reversión, ninguno **mide el tiempo**. El requisito pide la medida | **NO CONFORME** |
| `DAT-08` | **No medible sin `MCS-CORE`** — ver abajo | sin medir |
| `DAT-16` | **No medible sin `MCS-CORE`** — ver abajo | sin medir |

### Los dos que no se pudieron medir, y por qué se dice

`DAT-08` y `DAT-16` llegan del informe base con la evidencia en blanco: fueron
NO VERIFICABLE desde el principio y nadie escribió qué exigen. Sin el catálogo
no hay forma de saber contra qué medirlos — no es que se midieran y salieran
mal, es que **no se sabe qué preguntar**.

Se dejan explícitamente sin medir en vez de suponerles un estado. Suponerlo es
lo que produjo los cinco errores de recuento anteriores.

---

## Resultado

**De 45 a 41 bloqueantes de N1.** Cuatro cerraron sin escribir una línea, y dos
—`DAT-06` y `DIS-01`— quedan abiertos pero **acotados**: se sabe exactamente
qué sitios tocar y cuál de ellos esconde un cambio de contrato.

Los estados de este recuento están en `scripts/registro_conformidad.py`, que los
deriva. La cifra no se almacena.
