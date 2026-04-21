# Setup en Railway (sin local, sin Linux)

Guía optimizada con **Shared Variables** para minimizar el esfuerzo de configuración.
Todas las variables comunes se definen **una sola vez** al nivel del project y se heredan.

---

## Requisitos previos

1. Cuenta en **Railway** (plan Hobby o Pro): https://railway.app
2. Cuenta en **GitHub** con acceso a `xguilxr/pmo_aas`.

No necesitas Docker, Node, Python ni WSL. Todo sucede en Railway.

---

## Paso 1 — Crear el project en Railway

1. https://railway.app/new → **Deploy from GitHub repo** → `xguilxr/pmo_aas`.
2. Renombra el project a `pmo-aas` (Settings → Name).
3. (Opcional) Crea dos **Environments**: `production` y `staging`.

---

## Paso 2 — Agregar los plugins

En la vista del project:

1. **`+ Create`** → `Database` → `Add PostgreSQL`. Nombre: `Postgres`.
2. **`+ Create`** → `Database` → `Add Redis`. Nombre: `Redis`.

Railway expone automáticamente `DATABASE_URL` y `REDIS_URL` como variables del plugin.

---

## Paso 3 — Crear los 3 servicios

Railway al importar el repo creó un servicio default. Bórralo y crea estos 3 desde cero (más limpio):

### Servicio `api`

- **`+ Create`** → `GitHub Repo` → `xguilxr/pmo_aas`
- Settings → **Service Name**: `api`
- Settings → **Root Directory**: `apps/api`
- Settings → **Watch Paths**: `apps/api/**`
- Settings → **Branch**: `claude/railway-setup-epics-gsKld` (o `main` cuando mergees)

### Servicio `worker`

- **`+ Create`** → `GitHub Repo` → `xguilxr/pmo_aas`
- Settings → **Service Name**: `worker`
- Settings → **Root Directory**: `apps/api`
- Settings → **Config file path**: `worker.railway.toml` ← importante
- Settings → **Watch Paths**: `apps/api/**`

### Servicio `web`

- **`+ Create`** → `GitHub Repo` → `xguilxr/pmo_aas`
- Settings → **Service Name**: `web`
- Settings → **Root Directory**: `apps/web`
- Settings → **Watch Paths**: `apps/web/**`, `packages/**`

---

## Paso 4 — Shared Variables (al nivel del project)

**Esto es el atajo clave.** En lugar de copiar variables a cada servicio, las pones una vez aquí y Railway las inyecta en los 3.

1. Click en el **nombre del project** (arriba-izquierda, no un servicio).
2. Pestaña **Variables**.
3. Clic `+ New Variable` → pega esta lista completa:

### Shared Variables — copia-pega

| Variable | Valor | Notas |
|---|---|---|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` | Reference al plugin |
| `REDIS_URL` | `${{Redis.REDIS_URL}}` | Reference al plugin |
| `JWT_SECRET` | → click **Generate** | 32 bytes random |
| `JWT_REFRESH_SECRET` | → click **Generate** | 32 bytes random |
| `ACCESS_TOKEN_TTL_SEC` | `3600` | 1 hora |
| `REFRESH_TOKEN_TTL_SEC` | `2592000` | 30 días |
| `BCRYPT_ROUNDS` | `12` | |
| `PYTHON_ENV` | `production` | |
| `LOG_LEVEL` | `INFO` | |
| `AI_MODE` | `disabled` | Después cambias a `gemini` o `ollama` |
| `STORAGE_PATH` | `/data/uploads` | Volume mount (post-MVP) |

> **Tip:** Railway tiene un botón "Raw Editor" en la pestaña Variables que te deja pegar
> varios `KEY=value` a la vez. Úsalo para ir rápido.

Estas 11 variables las heredan `api`, `worker` y `web` automáticamente (web ignora las
que no usa, sin error).

---

## Paso 5 — Variables específicas por servicio

Solo aquí agregas lo que es **único** de cada servicio.

### Servicio `api` → pestaña Variables → `+ New Variable`

| Variable | Valor |
|---|---|
| `ALLOWED_ORIGINS` | `https://${{web.RAILWAY_PUBLIC_DOMAIN}}` |
| `SEED_ON_STARTUP` | `true` (solo primera vez; después `false`) |

### Servicio `worker` → pestaña Variables

**Ninguna.** Las shared variables ya le bastan para operar Celery + DB + Redis.

### Servicio `web` → pestaña Variables → `+ New Variable`

| Variable | Valor |
|---|---|
| `NEXT_PUBLIC_API_URL` | `https://${{api.RAILWAY_PUBLIC_DOMAIN}}` |
| `NEXTAUTH_URL` | `https://${{web.RAILWAY_PUBLIC_DOMAIN}}` |
| `NEXTAUTH_SECRET` | → click **Generate** |
| `NODE_ENV` | `production` |

---

## Paso 6 — Generar dominios públicos

- `api` → Settings → **Networking** → `Generate Domain`
- `web` → Settings → **Networking** → `Generate Domain`
- `worker` → **NO** lleva dominio (no expone HTTP).

---

## Paso 7 — Primer deploy

Railway ya auto-deployó al guardar variables. Espera a que los 3 servicios salgan en verde.

### Qué verificar inmediatamente

1. **`api`** → pestaña **Deploy Logs** → busca este banner:

   ```
   ========================================================================
   [seed] CREDENCIALES INICIALES — cópialas AHORA, no se vuelven a mostrar
   ========================================================================
     admin tenant=acme      email=admin@acme.pmoaas.local     temp_password=Xyz...
     admin tenant=globex    email=admin@globex.pmoaas.local   temp_password=Abc...
     superadmin global      email=superadmin@pmoaas.local     temp_password=Def...
   ========================================================================
   ```

   **Copia los 3 passwords a tu gestor de passwords. No se vuelven a mostrar.**

2. `https://<api-domain>/health` → debe devolver `{"status":"ok",...}`.
3. `https://<api-domain>/docs` → Swagger UI con todos los endpoints.
4. `https://<web-domain>/api/health` → `{"ok":true, "api_ok":true, ...}`.
5. Test login: `POST /api/v1/auth/login` con:
   ```json
   { "identifier": "superadmin@pmoaas.local", "password": "<el temp>" }
   ```
   Debes recibir `access_token` + `user.must_change_password=true`.

---

## Paso 8 — Apagar el seed

Después de confirmar login y cambiar passwords:

1. Servicio `api` → Variables → edita `SEED_ON_STARTUP` → cambia a `false` → Save.
2. Railway auto-redeploya. Ya no ejecutará el seed en futuros arranques.

> Si por error dejas `SEED_ON_STARTUP=true`, no pasa nada: el seed detecta que los
> users ya existen y no hace nada (es idempotente).

---

## Paso 9 — Dominios personalizados (opcional)

Cuando compres `pmoaas.com`:

1. `web` → Settings → Networking → `+ Custom Domain` → `app.pmoaas.com`.
2. `api` → `+ Custom Domain` → `api.pmoaas.com`.
3. Copia el CNAME que Railway te da → pégalo en tu DNS (Cloudflare, etc.).
4. Actualiza las shared/service variables para reflejar los nuevos dominios.

---

## Paso 10 — Auto-deploy desde GitHub

Ya está configurado. Cada push a la rama conectada re-despliega el servicio cuyo
`Watch Paths` matchea los archivos cambiados.

Branches recomendadas:
- `main` → production (apúntalo cuando hagas merge)
- `claude/railway-setup-epics-gsKld` → desarrollo activo (rama actual)

---

## Troubleshooting

| Problema | Causa | Fix |
|---|---|---|
| `api` no aparece | Servicio no conectado al repo | Settings → Source → selecciona el repo |
| `relation "users" does not exist` | Migración no corrió | Logs del startCommand; revisa `DATABASE_URL` |
| `web` healthcheck timeout | — | Ya no pasa: el health devuelve 200 sin depender del api |
| CORS error en browser | `ALLOWED_ORIGINS` no incluye el web domain | En `api` Variables, verifica que sea `https://${{web.RAILWAY_PUBLIC_DOMAIN}}` |
| Connection refused a DB | Falta la reference | Variable debe ser `${{Postgres.DATABASE_URL}}` exactamente |
| Seed no mostró credenciales | Users ya existen | Conéctate al Postgres → `SELECT email FROM users;` |
| Login dice "credenciales inválidas" | El temp_password ya caducó o `must_change_password` | Resetea desde otro admin o vuelve a correr seed con DB vacía |

### Caso: Railway no redeploya tras merge a `main` (US-BUG-004)

Síntoma: se mergeó un PR a `main` (ej. PR #20, commit `62b16f8` tocando
`apps/api/**`) y los servicios `api`/`worker`/`web` no redeployaron
automáticamente. El deploy listado en cada servicio siguió apuntando al
commit anterior.

Causas verificadas por orden de probabilidad:

1. **Auto-Deploy apagado en el servicio.** Settings → Deploy → toggle
   **Auto-Deploy** en OFF. Railway ignora los webhooks de push.
2. **Branch conectada ≠ `main`.** Al crear el servicio se dejó apuntando a
   la rama de desarrollo (ej. `claude/railway-setup-epics-gsKld`) y nunca
   se repuntó a `main` tras el merge.
3. **Watch Paths no matchean.** Si el servicio tiene Watch Paths estrictos
   que no incluyen los archivos del PR, Railway skipea el deploy.
4. **Railway tardó en sincronizar el webhook.** Raro, pero sucede cuando
   GitHub o Railway están degradados. Se auto-resuelve en <10 min.

Checklist de fix (aplicar en este orden a cada servicio `api`, `worker`, `web`):

1. Railway UI → project `pmo-aas` → abrir servicio.
2. Settings → **Source** → **Branch**: confirmar que es `main`.
3. Settings → **Deploy** → **Auto-Deploy**: toggle ON.
4. Settings → **Deploy** → **Watch Paths**: confirmar contra §3 de esta
   guía (`apps/api/**` para `api`/`worker`; `apps/web/**`, `packages/**`
   para `web`).
5. Deployments → botón **Deploy** → **Redeploy latest commit** para forzar
   un deploy al HEAD de `main`. Alternativa: push de un commit vacío
   (`git commit --allow-empty -m "chore: trigger redeploy"`).
6. Verificar el deploy:
   - `api` logs deben mostrar seed idempotente + migrations aplicadas.
   - `GET /health` del `api` responde `{"status":"ok",...}`.
   - `GET /api/health` del `web` responde `{"ok":true, "api_ok":true, ...}`.

Prevención: al mergear a `main` por primera vez desde una rama de
desarrollo, recorrer los 3 servicios y validar puntos 2–4 de arriba antes
de cerrar el ticket.

---

## Costos esperados (plan Hobby)

| Servicio | USD/mes |
|---|---:|
| `api` (512 MB) | ~$5 |
| `worker` (512 MB) | ~$5 |
| `web` (1 GB) | ~$10 |
| Postgres | ~$5 |
| Redis | ~$5 |
| **Total** | **~$30** |

---

## Resumen del esfuerzo

| Paso | Variables a definir | Tiempo |
|---|---:|---|
| Shared (proyecto) | 11 | 3 min |
| `api` específicas | 2 | 30 s |
| `worker` específicas | 0 | 0 |
| `web` específicas | 4 | 1 min |
| **Total** | **17 variables** | **~5 min** |

vs. el enfoque antiguo de copiar ~12 variables a cada servicio (~36 definiciones).
