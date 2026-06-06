# Runbook · Storage de uploads (documentos + PDFs generados)

> **Scope:** configurar storage persistente para documentos subidos
> por el tenant (BUG-029/US-020) y PDFs generados por el worker
> (reports avance/seguimiento). Aplica a **US-066 (#113)** del
> Sprint 4 v1.3.

Tiempo estimado: **30–45 min** incluyendo smoke test.

---

## 0. Por qué NO usamos Railway Volumes

Railway Volumes **no pueden compartirse entre servicios**. Se montan
en un solo contenedor — el mount es exclusivo. Para PMO·aaS necesitamos
que **api** (recibe uploads) y **worker** (genera PDFs de reportes)
escriban en el mismo storage. Las opciones son:

| Opción | Compartido | Costo | Complejidad |
|---|---|---|---|
| ❌ Railway Volume en api **y** worker | No — Railway no lo permite | $0.25/GB/mes | baja pero no funciona |
| ❌ Volume solo en api + HTTP interno desde worker | Sí técnicamente | $0.25/GB + bandwidth interno | media, latencia extra |
| ✅ **Object storage S3-compatible (R2/B2)** | Sí | ~$0/mes MVP, $6/TB después | baja, estándar de industria |

Por eso el runbook usa **Cloudflare R2** como principal. Railway Volume
queda descartado para este caso de uso.

---

## 1. Pre-requisitos

- Cuenta **Cloudflare** activa (ya existe por DEC-012 — dominio `pmo-aas.com`).
- Acceso a **Railway Dashboard** con rol `Admin` del proyecto.
- Plan Cloudflare **R2 Free** o Workers Paid ($5/mes, incluye R2). El
  free tier da **10 GB storage + 1M requests/mes** — suficiente para
  el MVP (estimado 5000 docs × 2 MB promedio = 10 GB).
- Terminal con `aws` CLI o `rclone` para el smoke test (opcional).

---

## 2. Crear bucket R2

1. Cloudflare Dashboard → menú lateral → **R2 Object Storage** →
   **Create bucket**.
2. Configuración:
   - **Bucket name:** `pmo-aas-uploads`
   - **Location hint:** dejar default (automatic) — Cloudflare lo
     coloca cerca de tus usuarios.
   - **Default encryption:** activado (built-in).
3. Click **Create bucket**.

**Verificar:** el bucket aparece en la lista con 0 B used.

---

## 3. Crear API token con permisos mínimos

1. En la misma sección de R2 → pestaña **Manage R2 API Tokens** →
   **Create API Token**.
2. Configuración:
   - **Token name:** `pmo-aas-railway`
   - **Permissions:** `Object Read & Write`
   - **Specify bucket:** `Apply to specific buckets only` →
     seleccionar **solo** `pmo-aas-uploads`.
   - **TTL:** sin expiración (o 1 año si prefieres rotación regular).
3. Click **Create API Token**.
4. Copiar los 3 valores (solo se muestran una vez):
   - **Access Key ID** (empieza con letras)
   - **Secret Access Key** (larga)
   - **Endpoint URL** (formato: `https://<accountid>.r2.cloudflarestorage.com`)

> ⚠️ Guardar inmediatamente en gestor de secretos (1Password / Bitwarden).
> Si se pierde el Secret Access Key, hay que generar otro token y
> rotar env vars.

---

## 4. Configurar env vars en Railway

En Railway Dashboard → Proyecto `pmo-aas` → **Variables** (shared
variables, al nivel del proyecto).

Agregar **4 variables compartidas** que heredarán api + worker:

| Variable | Valor | Notas |
|---|---|---|
| `STORAGE_BACKEND` | `s3` | Enum para selector de backend en el código. |
| `S3_BUCKET` | `pmo-aas-uploads` | Nombre del bucket R2. |
| `S3_ENDPOINT_URL` | `https://<accountid>.r2.cloudflarestorage.com` | Endpoint copiado en §3. |
| `S3_ACCESS_KEY_ID` | `<access-key-id>` | Del token R2. |
| `S3_SECRET_ACCESS_KEY` | `<secret-access-key>` | Del token R2. |
| `S3_REGION` | `auto` | R2 acepta `auto`. Para B2/S3 cambia. |

**Alternativa Backblaze B2** (si prefieres B2 sobre R2):
- `S3_ENDPOINT_URL` = `https://s3.<region>.backblazeb2.com` (ver B2 dashboard).
- `S3_REGION` = tu región B2 (ej. `us-west-002`).
- Resto igual.

Click **Deploy** en cada servicio (`api` + `worker`) para que
recarguen las env vars.

---

## 5. Verificar acceso desde Railway

Smoke test desde Railway shell:

```bash
# Railway → servicio api → Data tab → shell icon.
python -c "
import boto3
import os
c = boto3.client(
    's3',
    endpoint_url=os.environ['S3_ENDPOINT_URL'],
    aws_access_key_id=os.environ['S3_ACCESS_KEY_ID'],
    aws_secret_access_key=os.environ['S3_SECRET_ACCESS_KEY'],
    region_name='auto',
)
# Listar bucket (debería devolver vacío).
r = c.list_objects_v2(Bucket=os.environ['S3_BUCKET'])
print('keys:', r.get('KeyCount', 0))
# Subir archivo prueba.
c.put_object(Bucket=os.environ['S3_BUCKET'], Key='_smoke.txt', Body=b'hello')
print('upload ok')
# Leerlo.
r = c.get_object(Bucket=os.environ['S3_BUCKET'], Key='_smoke.txt')
print('download ok:', r['Body'].read())
# Borrarlo.
c.delete_object(Bucket=os.environ['S3_BUCKET'], Key='_smoke.txt')
print('delete ok')
"
```

Esperado: `upload ok`, `download ok: b'hello'`, `delete ok`. Si falla
con `SignatureDoesNotMatch` → revisar que `S3_SECRET_ACCESS_KEY` no
tenga espacios invisibles al pegar.

Repetir el mismo comando desde la shell del servicio `worker` para
confirmar que también tiene acceso.

---

## 6. Cambios de código (scope de US-066)

Estos cambios se implementan **después** de que el owner confirme
el runbook + acceso funcional al bucket. Los hace Claude en commit
separado.

**`apps/api/app/services/document_storage.py`:**

- Nuevo selector por `settings.STORAGE_BACKEND`:
  - `"local"` (default dev) → filesystem como hoy.
  - `"s3"` (Railway prod) → `boto3.client('s3', endpoint_url=...)` con
    las env vars `S3_*`.
- `save_document()` sube a `s3://pmo-aas-uploads/documents/{tenant_id}/{project_id}/{doc_id}.{ext}`.
- `get_document_path()` → reemplazado por `get_document_stream()` que
  devuelve un stream del S3 `get_object`.
- `delete_document_file()` → llama `s3:DeleteObject`.

**`apps/api/app/api/v1/endpoints/modules.py`:**

- Endpoint `GET /documents/{id}/download` cambia: en vez de
  `FileResponse` con path local, hace `StreamingResponse` con el
  cuerpo de `get_document_stream()` + headers apropiados.

**`apps/api/app/core/config.py`:**

- Settings nuevas: `STORAGE_BACKEND`, `S3_BUCKET`, `S3_ENDPOINT_URL`,
  `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_REGION`.
- Default en dev: `STORAGE_BACKEND="local"` + `STORAGE_PATH="/tmp/pmo_uploads"`.

**`requirements.txt`:**

- Agregar `boto3==1.35.*` (~10 MB, pin minor).

**Tests:**

- `tests/test_us066_s3_storage.py` con `moto` para mockear S3 y
  verificar save/get/delete.

---

## 7. Migración de datos existentes (si aplica)

Si en dev ya hay documentos en `STORAGE_PATH` local que quieres
preservar en R2, correr **una sola vez** desde local:

```bash
# Requiere S3_* en .env + STORAGE_PATH viejo.
python -m app.scripts.migrate_uploads_to_s3
```

Script stub (se crea en US-066):

```python
# apps/api/app/scripts/migrate_uploads_to_s3.py
from pathlib import Path
import boto3
import os

client = boto3.client(
    's3',
    endpoint_url=os.environ['S3_ENDPOINT_URL'],
    aws_access_key_id=os.environ['S3_ACCESS_KEY_ID'],
    aws_secret_access_key=os.environ['S3_SECRET_ACCESS_KEY'],
)
bucket = os.environ['S3_BUCKET']
root = Path(os.environ['STORAGE_PATH']) / 'documents'

for f in root.rglob('*'):
    if not f.is_file():
        continue
    key = 'documents/' + str(f.relative_to(root))
    client.upload_file(str(f), bucket, key)
    print(f'uploaded {key}')
```

En prod (Railway) no hay nada que migrar — los archivos se perdieron
en redeploys previos. El owner sabe que hasta US-066 ejecutada, el
storage es efímero.

---

## 8. Backup y versioning

**R2 incluye:**
- **Object versioning**: se habilita en bucket settings → Versioning
  → Enable. Cada overwrite preserva la versión anterior (útil para
  recuperar docs borrados por error). Recomendado.
- **Lifecycle rules**: opcional. Ej. mover versiones antiguas a
  clase más barata o borrarlas tras 90 días.

**Backup externo (opcional para producción):**
- Cloudflare R2 ya es multi-AZ. No requiere backup cross-region para
  MVP.
- Si se quiere extra seguridad, agendar `rclone sync` nocturno a un
  bucket B2 secondary.

---

## 9. Costos esperados

**Escenario MVP (1 año, 10 tenants activos):**
- 5000 docs × 2 MB promedio = 10 GB → **dentro del free tier**.
- 10k requests/mes (PUT + GET combinados) → dentro del free tier
  (1M PUT/mes + 10M GET/mes en R2 free).
- **Costo total: $0/mes**.

**Escenario crecimiento (100 tenants, 100k docs):**
- 100 GB storage → R2 cobra $1.5/mes (Standard) o $0.40/mes
  (Infrequent Access, lo más probable para docs PMO).
- 100k requests/mes → dentro de free tier.
- **Costo total: ~$1.50/mes**.

Comparado con AWS S3 equivalente con 10 GB egress/mes: $1.50 storage
+ $0.90 egress = **$2.40/mes**. R2 tiene egress $0, por eso se paga
sola.

---

## 10. Rollback

Si algo se rompe tras mergear el código de US-066:

1. Setear `STORAGE_BACKEND=local` en Railway → redeploy → vuelve al
   flujo filesystem local (pierde persistencia pero no crashea).
2. Los archivos en R2 se mantienen.
3. Investigar el bug offline, volver a `STORAGE_BACKEND=s3` cuando
   se arregle.

Si hace falta desactivar R2 por completo:
- Cloudflare → R2 → token → **Revoke**.
- Railway → eliminar `S3_*` env vars.

---

## 11. Troubleshooting

**P:** Al subir un documento desde `/pmo/projects/*/documents (legacy /admin/* redirige)`,
error "No se pudo subir el documento" con status 500.

**R:** Revisar logs del api en Railway. Causas típicas:
- `S3_ACCESS_KEY_ID` / `S3_SECRET_ACCESS_KEY` con espacios o mal
  copiados.
- `S3_ENDPOINT_URL` sin `https://` al inicio.
- Token de R2 revocado o expirado.

---

**P:** Upload funciona pero `GET /documents/{id}/download` devuelve 404.

**R:** Verificar que `worker` y `api` están usando el **mismo
bucket**. Si el worker escribió el archivo y api lo busca, deben
compartir `S3_BUCKET` exacto.

---

**P:** Latencia alta en downloads (> 2 s para un PDF de 1 MB).

**R:** R2 tiene CDN-global pero puede estar lejos del región Railway.
Opciones:
1. Configurar un Custom Domain en R2 con Cloudflare CDN (gratis, 0
   egress) → serve directo al browser sin pasar por api.
2. Firma URLs prefirmadas con expiración corta (ej. 1 hora) para que
   el frontend descargue directo del bucket.

---

**P:** Railway shell no puede hacer `pip install boto3` para el
smoke test.

**R:** El smoke test de §5 asume que el Dockerfile ya tiene boto3
instalado (lo agregamos en US-066). Si todavía no se mergeó, correr
el smoke localmente con `.env` del servidor.

---

## 12. Checklist de deployment

- [ ] Bucket `pmo-aas-uploads` creado en Cloudflare R2.
- [ ] API Token `pmo-aas-railway` creado con permiso Object Read & Write.
- [ ] 6 env vars en Railway shared variables.
- [ ] Redeploy api + worker.
- [ ] Smoke test §5 pasa desde ambos servicios.
- [ ] US-066 mergeada (refactor de `document_storage.py`).
- [ ] Upload de prueba desde UI → aparece en el bucket.
- [ ] Redeploy → upload persiste (no se borra).
- [ ] (opcional) Versioning habilitado en el bucket.

---

## Referencias

- Cloudflare R2 docs: <https://developers.cloudflare.com/r2/>
- R2 Python/boto3 example: <https://developers.cloudflare.com/r2/api/s3/tokens/>
- Backblaze B2 S3 API: <https://www.backblaze.com/b2/docs/s3_compatible_api.html>
- DEC-012 — dominio + Cloudflare en el proyecto.
- US-066 #113 — implementación del refactor de código.
