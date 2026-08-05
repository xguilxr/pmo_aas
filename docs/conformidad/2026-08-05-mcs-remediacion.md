# Remediación posterior a R1 — MCS

| Campo | Valor |
|---|---|
| Marco | MCS 2.0.0 |
| Fecha | 2026-08-05 |
| Alcance | Lo que R1 dejó etiquetado como barato, más dos amenazas del modelo |
| Método | Ejecutar, no medir. Cada cierre lleva su comprobación y su verificación por mutación |

Esto **no es una auditoría**: es el registro de lo que se arregló después de la
R1 del 2026-08-04, con la evidencia de que funciona. La medición formal la hará
la próxima reauditoría; aquí solo se declara lo que cambió y cómo se comprobó.

---

## Qué cerró

| ID | Antes | Ahora | Evidencia |
|---|---|---|---|
| **SUM-02** | NO CONFORME | **CONFORME** | `apps/api/Dockerfile` corre como `appuser`. `test_sum02_contenedor_sin_privilegios.py` |
| **DES-03** | PARCIAL | **CONFORME** | `/health` hace `SELECT 1` acotado y devuelve 503. `test_des03_health_verifica.py` |
| **DIS-02** | NO CONFORME | **CONFORME** | 34 de 34 pares AA en los dos temas. Job `contraste-wcag` |
| **SEG-07** | PARCIAL — «no se verificó la inmutabilidad» | **CONFORME con residual** | Migración `0097` + guardián del ORM. `test_am08_auditoria_solo_anexa.py` |
| **AM-08** | SIN CONTROL | **CONTROLADA** | Ídem. Modelo de amenazas actualizado |
| **AM-09** | PARCIAL | **CONTROLADA** | Límite por IP en el login. `test_am09_login_limite_por_ip.py` |
| **D-7** | Aprobada, sin hacer | **Hecha** | Una sola paleta de salud. `test_d7_paleta_de_salud.py` |
| **D-9** | Aprobada, sin hacer | **Hecha** | `is_milestone ⟹ duration_days = 0`. `test_d9_hito_duracion_cero.py` |

## Qué NO cerró, con su número

| ID | Estado | Lo que falta, medido |
|---|---|---|
| **LEN-02** | Sigue **PARCIAL** | Ver abajo |
| **SEG-01** | Sigue **PARCIAL** | Dos de los tres huecos nombrados están cerrados (AM-09, AM-08). Queda `python-jose`, y sigue faltando el mapeo completo de ASVS L1 |

---

## Lo que se aprendió, que es más útil que la lista

### El `REVOKE` que el modelo de amenazas proponía no habría funcionado

AM-08 decía: «`REVOKE UPDATE, DELETE` al rol de la aplicación. Lo segundo es
barato y no requiere código.» Es barato, y **no alcanza**: en Railway la
aplicación se conecta con el rol dueño de las tablas, y en PostgreSQL el dueño
conserva sus privilegios haga lo que haga el `REVOKE`.

Comprobado contra Postgres 16 antes de decidir:

```
REVOKE UPDATE, DELETE al dueño, sin disparador  →  UPDATE 1   (pasa)
UPDATE / DELETE / TRUNCATE con disparador       →  ERROR      (no pasa)
tras `downgrade`                                →  UPDATE 1   (reversible)
```

Habría sido un control declarado que no actúa, y encima habría cerrado la ficha.
Es el tipo de cosa que solo aparece al ejecutar: la medición no la ve.

### DIS-02 tenía dos agujeros que R1 no vio, y uno era el propio verificador

- **`scripts/check_contraste.py` llevaba los valores copiados a mano.** Su
  encabezado lo admitía. Un control que puede desincronizarse de lo que vigila no
  es un control — y era justo el caso que el script existe para evitar. Ahora lee
  `globals.css`.
- **El tema oscuro no se había medido.** R1 midió 19 pares, todos claros. El
  oscuro traía su propio fallo (`tertiary` sobre `muted`, 4.08).

### D-7 no eran dos paletas, eran cuatro

La decisión nombraba las dos de `scoped_status.py`. Al unificarlas aparecieron
otras dos en las plantillas PDF. De regalo cerró un defecto que nadie había
reportado: el mapa de árbol pintaba texto blanco sobre `#eab308`, ~1.9:1.

### El caso que incumplía D-9 era el caso normal

`compute_duration_days` cuenta días inclusivos, así que un hito con la misma
fecha de inicio y fin daba **1**, no 0. No hacía falta un dato raro para
contradecir la regla: bastaba crear un hito de la forma corriente.

---

## LEN-02 — por qué sigue PARCIAL, con la cifra

Los cuatro textos por defecto del catálogo dicen ahora qué pasó, por qué y qué
hacer, y las tres partes se guardan **como datos y no como prosa**, así que no se
pueden rellenar a medias. Eso cubre todos los sitios que no pasan texto propio.

Los que sí lo pasan, medidos hoy sobre `app/`:

| | |
|---|---|
| Mensajes con texto explícito | **159** |
| …que nombran campos internos (`project_id`, `role_ids`) | **21** |
| …que no proponen ninguna acción | **152** |

Declararlo CONFORME con 152 de 159 mensajes diciendo solo qué pasó sería repetir
el error que este expediente ya cometió dos veces con los recuentos. **Sigue
PARCIAL**, y ahora la distancia tiene número en vez de impresión.

El grueso son mensajes de regla de negocio, uno por uno, sin palanca común. Es
trabajo de tanda, no de tarde.

---

## Lo que quedó nombrado y no se tocó

Cada uno está anotado en el código o en la prueba que lo bordea, para que sea
trabajo pendiente y no descuido:

1. **La paleta de gráficos** —líneas de tendencia, barras del Gantt,
   `actual_color` de la curva-S— arrastra los colores de Tailwind que D-7 retiró
   del semáforo. Decidir si la línea de «avance promedio» lleva el verde del
   semáforo es una decisión de diseño, no la que D-7 tomó. Declarado en
   `test_d7_paleta_de_salud.py`.
2. **`docs/design-system/tokens.md` describe una paleta anterior** —otros hues,
   otra tipografía— y lleva tiempo desincronizado. Queda declarado obsoleto con
   la fuente de verdad apuntada, no corregido a medias.
3. **El rociado lento** —bajo el umbral de AM-09, o repartido entre muchas IP—
   sigue siendo posible. Pide detección por patrón, no un contador.
4. **Un DBA puede quitar el disparador de `audit_log`.** Cerrarlo pide
   encadenamiento por hash o envío a un almacén externo.
5. **El guardián del ORM no ve las sentencias masivas.** En PostgreSQL las para
   el disparador; en SQLite no las para nada. Hay un caso que lo comprueba a
   propósito, con el mensaje de qué hacer el día que deje de ser cierto.
6. **AM-10** —el bloqueo por cuenta como denegación de servicio— sigue sin
   control, y AM-09 no la toca.

---

## Cómo se comprobó

Un requisito no se declara cerrado por leer el diff. Cada uno lleva su
verificación por mutación: se deshace el arreglo y se comprueba que las pruebas
se ponen rojas.

| Arreglo | Al deshacerlo |
|---|---|
| `USER` del Dockerfile | 1 caso |
| `/health` que declara `checks` sin consultar | 2 casos |
| Verde viejo del semáforo en `globals.css` | 2 pares y el job |
| Comprobación de entrada del límite por IP | 2 casos |
| Normalizador de hitos | 6 casos |

Además: **suite completa de API en verde** (1094 casos), lint `exit 0`,
typecheck de web `exit 0`, y el verificador de contraste `exit 0` con 34 de 34.

La migración `0097` **no se ejecutó por Alembic** —el guard de acciones
irreversibles lo impide y la corre el owner—, pero su SQL sí se ejercitó contra
un Postgres 16 real, incluido el `downgrade`.
