# Setup en Railway (sin local, sin Linux)

Guía paso-a-paso para desplegar PMO-aaS 100% en Railway usando solo el navegador.
Todo el código de este repo está configurado para que Railway lo construya con Nixpacks
automáticamente al detectar los `railway.toml` por servicio.

---

## Requisitos previos

1. Cuenta en **Railway** (plan Hobby o Pro): https://railway.app
2. Cuenta en **GitHub** con acceso a `xguilxr/pmo_aas`.
3. (Opcional) Cuenta gratis en **Google AI Studio** para la key de Gemini: https://aistudio.google.com/apikey
4. (Opcional) Cuenta en **Resend** para envío de emails (3k emails/mes free): https://resend.com

No necesitas Docker, Node, Python ni WSL en tu máquina. Todo sucede en Railway.

---

## Paso 1 — Crear el proyecto en Railway

1. Entra a https://railway.app/new.
2. **"Deploy from GitHub repo"** → autoriza GitHub si no lo has hecho → selecciona `xguilxr/pmo_aas`.
3. Railway crea un **Project** vacío. Renómbralo a `pmo-aas` (Settings → Name).
4. Crea dos **Environments** dentro del mismo project:
   - `production` (default)
   - `staging` (botón `+ New Environment` → Duplicate from production cuando quieras promover).

---

## Paso 2 — Agregar los plugins (Postgres + Redis)

En la vista del project:

1. **`+ Create`** → `Database` → `Add PostgreSQL`. Nombre: `postgres`.
2. **`+ Create`** → `Database` → `Add Redis`. Nombre: `redis`.

Railway expone automáticamente las variables `DATABASE_URL` y `REDIS_URL` internas al proyecto.

> Tip: en el plugin Postgres, abre la pestaña `Data` → `Query` para ejecutar SQL sin herramientas locales.

---

## Paso 3 — Crear el servicio `api` (FastAPI)

1. **`+ Create`** → `GitHub Repo` → selecciona `xguilxr/pmo_aas` de nuevo.
2. En el servicio nuevo, pestaña **Settings**:
   - **Service Name**: `api`
   - **Root Directory**: `apps/api`
   - **Watch Paths**: `apps/api/**`
   - **Branch**: `main` para production / `claude/railway-setup-epics-gsKld` para la rama actual de desarrollo
3. Railway detectará `apps/api/railway.toml` y `apps/api/nixpacks.toml` automáticamente.
4. Pestaña **Variables** → clic `+ New Variable` y agrega:

   | Nombre | Valor |
   |---|---|
   | `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (reference) |
   | `REDIS_URL` | `${{Redis.REDIS_URL}}` (reference) |
   | `JWT_SECRET` | genera 32 bytes aleatorios (Railway → `+ New` → `Generate`) |
   | `JWT_REFRESH_SECRET` | idem |
   | `ACCESS_TOKEN_TTL_SEC` | `3600` |
   | `REFRESH_TOKEN_TTL_SEC` | `2592000` |
   | `BCRYPT_ROUNDS` | `12` |
   | `AI_MODE` | `disabled` (para arranque; `gemini` después) |
   | `ALLOWED_ORIGINS` | `https://${{web.RAILWAY_PUBLIC_DOMAIN}}` |
   | `PYTHON_ENV` | `production` |
   | `LOG_LEVEL` | `INFO` |
   | `SEED_ON_STARTUP` | `true` (solo primera vez, luego `false`) |

5. Pestaña **Settings** → **Networking** → **Generate Domain**. Copia el dominio, lo usarás en el frontend.

---

## Paso 4 — Crear el servicio `worker` (Celery)

1. **`+ Create`** → `GitHub Repo` → `xguilxr/pmo_aas`.
2. Settings:
   - **Service Name**: `worker`
   - **Root Directory**: `apps/api`
   - **Config file path**: `worker.railway.toml`  ← importante, así usa start command distinto
   - **Watch Paths**: `apps/api/**`
3. Variables: copia **las mismas** que `api` (Railway permite `Copy from` en el menú de variables).
4. **No** generes dominio (el worker no expone HTTP).

---

## Paso 5 — Crear el servicio `web` (Next.js)

1. **`+ Create`** → `GitHub Repo` → `xguilxr/pmo_aas`.
2. Settings:
   - **Service Name**: `web`
   - **Root Directory**: `apps/web`
   - **Watch Paths**: `apps/web/**`, `packages/**`
3. Variables:

   | Nombre | Valor |
   |---|---|
   | `NEXT_PUBLIC_API_URL` | `https://${{api.RAILWAY_PUBLIC_DOMAIN}}` |
   | `NEXTAUTH_URL` | `https://${{web.RAILWAY_PUBLIC_DOMAIN}}` |
   | `NEXTAUTH_SECRET` | generado random 32 bytes |
   | `NODE_ENV` | `production` |

4. Settings → Networking → **Generate Domain**.

---

## Paso 6 — Primera migración y seed

La primera vez, Railway corre `alembic upgrade head` en el buildCommand (ver `apps/api/railway.toml`),
y si `SEED_ON_STARTUP=true` el `api` creará:

- Tenant demo `acme`
- Super admin global con password temporal (visible solo en logs del primer arranque)
- Roles de sistema (`Administrador`, `PMO Manager`, `Project Manager`, `Viewer`)

**Dónde ver el password del superadmin la primera vez:**
Servicio `api` → pestaña **Deploy Logs** → busca la línea `[seed] superadmin created: email=...  temp_password=...`
Copia el password, haz login y cámbialo. Luego pon `SEED_ON_STARTUP=false`.

---

## Paso 7 — Verificación

Una vez que `api` y `web` estén en estado **Success** (verde):

1. Abre `https://<api-domain>/health` → debe responder `{"status":"ok",...}`.
2. Abre `https://<api-domain>/docs` → Swagger UI con todos los endpoints.
3. Abre `https://<web-domain>/` → landing de login.

---

## Paso 8 — Auto-deploy desde GitHub

Railway ya queda enlazado: cada push a la rama configurada re-despliega.

Branches recomendadas:
- `main` → production
- `claude/railway-setup-epics-gsKld` → desarrollo activo (puedes conectarla al environment `staging`)

Para promover staging → production: Railway UI → Deployments → botón **Promote**.

---

## Paso 9 — Dominios personalizados (opcional)

Cuando compres `pmoaas.com` en Cloudflare/otro registrador:

1. Servicio `web` → Settings → Networking → `+ Custom Domain` → `app.pmoaas.com`.
2. Servicio `api` → `+ Custom Domain` → `api.pmoaas.com`.
3. Railway te da un CNAME que debes agregar en tu DNS. TLS lo emite automático.
4. Actualiza las variables `NEXT_PUBLIC_API_URL`, `NEXTAUTH_URL` y `ALLOWED_ORIGINS` a los nuevos dominios.

---

## Troubleshooting

| Problema | Causa probable | Solución |
|---|---|---|
| `api` falla con `relation "users" does not exist` | La migración no corrió | Revisa logs de build, ejecuta el Redeploy del servicio |
| `web` da error CORS | `ALLOWED_ORIGINS` no incluye el dominio del web | Actualiza la variable en `api` y redeploy |
| `Connection refused` a Redis/Postgres | Falta la reference variable | Pon `${{Postgres.DATABASE_URL}}` exactamente así, no el valor copiado |
| Build de Next.js OOM | Memoria insuficiente | Sube el plan del servicio `web` a 1 GB |
| Logs del seed no muestran superadmin | El seed ya corrió antes | Conéctate al Postgres plugin: `SELECT email FROM users WHERE is_superadmin=true;` |

---

## Costos esperados

| Servicio | USD/mes (Railway Hobby) |
|---|---:|
| `api` (512 MB) | ~$5 |
| `worker` (512 MB) | ~$5 |
| `web` (1 GB) | ~$10 |
| `postgres` | ~$5 (plan starter) |
| `redis` | ~$5 |
| **Total** | **~$30/mes** |

Escala solo si necesitas producción real con varios tenants.
