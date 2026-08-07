---
tipo: runbook
responsable: propietario
estado: vigente
revisado: 2026-08-06
revisar_cada: 90d
---

# Copias de seguridad y restauración

Cierra **MCS INF-03** («DEBEN existir copias de seguridad automáticas») y da a
`DES-02` su procedimiento de vuelta atrás sobre datos.

> **Lo único que convierte un fichero en una copia de seguridad es haberlo
> restaurado.** El §4 de este documento es el que importa; el resto describe
> una máquina que produce archivos.

---

## 1. Qué corre, cuándo, y dónde acaba

| | |
|---|---|
| **Qué** | `pg_dump --format=custom` de la base entera |
| **Cuándo** | Diario, **03:30 UTC**, desde el planificador del worker |
| **Dónde** | Almacenamiento de objetos (Cloudflare R2), clave `respaldos/postgres/AAAA-MM-DD.dump` |
| **Retención** | **30 días**; lo más viejo se borra en la misma ejecución |
| **Código** | `apps/api/app/services/respaldo.py` · tarea `respaldo.diario` |

**Por qué no basta con las copias de Railway.** Son útiles y siguen ahí. No
bastan porque viven **en el mismo proveedor que la base** —un problema de
cuenta se lleva las dos a la vez— y porque este repositorio no puede
verificarlas. Esta copia va a otro proveedor y sí se puede comprobar.

**Media hora después del snapshot semanal** (02:00 UTC los lunes) para no
competir por E/S con él: los dos leen la base entera.

---

## 2. Requisitos que deben estar puestos

| Variable | Para qué |
|---|---|
| `DATABASE_URL` | De dónde se vuelca |
| `S3_BUCKET`, `S3_ENDPOINT_URL`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` | Dónde se guarda |

El binario `pg_dump` viene en la imagen (`postgresql-client` en el
`Dockerfile`). **Si desaparece de ahí, la copia falla entera** y hay un caso que
lo vigila.

---

## 3. Comprobar que la copia de anoche existe

```bash
aws s3 ls s3://$S3_BUCKET/respaldos/postgres/ \
  --endpoint-url "$S3_ENDPOINT_URL" | tail -5
```

Debe aparecer la fecha de hoy con un tamaño **parecido al de ayer**. Un archivo
que encoge de golpe es la señal de alarma: puede ser un volcado parcial, y eso
no lanza ningún error.

El tamaño también sale en los registros del worker, en el evento
`respaldo completado`, junto con `bytes` y `borradas`.

---

## 4. Restaurar — el procedimiento que hay que haber ensayado

> **Ensayarlo es parte del procedimiento, no una recomendación.** Una
> restauración que se hace por primera vez el día del incidente se hace mal.

### 4.1 Bajar la copia

```bash
FECHA=2026-08-06
aws s3 cp "s3://$S3_BUCKET/respaldos/postgres/$FECHA.dump" ./respaldo.dump \
  --endpoint-url "$S3_ENDPOINT_URL"
```

### 4.2 Restaurar sobre una base NUEVA, nunca sobre la que está en uso

```bash
createdb -h HOST -U USUARIO pmoaas_restauracion
pg_restore --dbname "postgresql://USUARIO:CLAVE@HOST:5432/pmoaas_restauracion" \
  --no-owner --no-acl ./respaldo.dump
```

**La URL no puede llevar el dialecto de SQLAlchemy.** Si copias `DATABASE_URL`
tal cual, trae `+psycopg` o `+asyncpg`, y `libpq` **no da error**: ignora lo que
no entiende y se conecta al socket local, que falla hablando de un rol
inexistente. El mensaje no menciona la causa. Quita el sufijo.

### 4.3 Comprobar antes de apuntar nada a ella

```sql
SELECT count(*) FROM tenants;
SELECT count(*) FROM projects WHERE deleted_at IS NULL;
SELECT max(occurred_at) FROM audit_log;
```

El último es el que dice **hasta qué momento llegan los datos**, que es la
pregunta real: no «¿se restauró?» sino «¿cuánto se perdió?».

### 4.4 Recién entonces, cambiar `DATABASE_URL`

Y correr `alembic upgrade head`: la copia trae el esquema del día que se hizo,
y puede faltarle migraciones posteriores.

---

## 5. Restauración parcial — una sola tabla

El formato custom permite sacar una tabla sin tocar el resto, que es lo que
hace falta cuando el incidente es «alguien borró un proyecto», no «se cayó la
base»:

```bash
pg_restore --dbname "$URL_SIN_DIALECTO" --data-only --table=projects ./respaldo.dump
```

**Cuidado con `--data-only` sobre una tabla que ya tiene filas**: inserta, no
reemplaza, y las claves primarias repetidas romperán la carga a mitad. Para un
rescate quirúrgico, restaurá a la base nueva y copiá las filas que hagan falta.

---

## 6. Qué NO cubre esta copia

- **Los documentos subidos.** Viven en el mismo almacenamiento de objetos;
  volcarlos ahí no añadiría nada. Su durabilidad es la de R2 (multizona), y
  está en [`uploads-storage.md`](uploads-storage.md).
- **Redis.** Es caché y cola: lo que hay ahí se puede reconstruir. Un preview
  de importación a medias se vuelve a generar.
- **Las variables de entorno.** No están versionadas a propósito (`CFG-01`
  prohíbe secretos en el repositorio). Consérvalas donde guardes tus
  credenciales.

---

## 7. Cuándo esto deja de valer

Revisar este documento si cambia el proveedor de almacenamiento, si la base
crece hasta que el volcado supere los 30 minutos del tope, o si entra un
segundo servicio con datos propios.
