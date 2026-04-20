# Runbook — Ollama local + Cloudflare Tunnel + nssm (Windows)

**ID:** `DOC-AI-LOCAL-OLLAMA`
**Alcance:** EP016 — US-NEW-044
**Dependencias:** [DOC-AI-LOCAL](./local-model-setup.md) (elección de modelo)

Este runbook documenta **paso a paso** cómo montar Ollama en una PC Windows,
exponerlo al backend PMO productivo vía un Cloudflare Tunnel autenticado con
Service Token, y persistirlo como servicio de Windows con `nssm`. Ideal para
el host local del owner corriendo 24/7 y alimentando las minutas del EP014
US-NEW-040 sin costo por token y sin sacar transcripciones del perímetro.

> Tiempo estimado: **~30 min** con la red estable y un dominio Cloudflare ya
> administrado.

---

## 0. Topología

```
+------------------+           +-----------------+          +------------------+
|  PC local        |           | Cloudflare Edge |          |  Backend PMO     |
|  (Windows)       |           | (Zero Trust)    |          |  (Railway/HG)    |
|                  |           |                 |          |                  |
|  Ollama          |<--tunnel--| ollama.tu.do    |<--https--| worker EP008     |
|  127.0.0.1:11434 |   cloudflared (HTTPS)      |          |                  |
|  (nssm service)  |           | CF-Access-*     |          |                  |
+------------------+           +-----------------+          +------------------+
```

- **PC local**: Ollama escucha en `localhost:11434` (sin exponer puerto al
  router).
- **cloudflared**: corre como servicio (vía `nssm`), abre un túnel
  outbound-only hasta Cloudflare Edge y publica `https://ollama.tu-dominio`.
- **Cloudflare Access**: exige un **Service Token** (Client-Id + Secret) en
  cada request; sin ese token → 401. Protege el endpoint contra terceros.
- **Backend PMO**: incluye los dos headers al llamar al túnel desde el worker.

---

## 1. Pre-requisitos

| Ítem | Mínimo recomendado |
|---|---|
| SO | Windows 10 x64 / Windows 11 |
| RAM | 16 GB (8 GB libre para Ollama + 7B Q4) |
| Disco libre | 15 GB |
| Conexión | 20 Mbps symmetric estable (el túnel no hace streaming pesado, pero los transcripts pueden pesar) |
| Dominio Cloudflare | Administrado desde dashboard; plan Free es suficiente |
| Acceso | Windows con permisos de admin para instalar servicios |
| Herramientas | PowerShell 5.1+ (viene con Windows), 7-Zip opcional |

**Dependencias que instalamos** en los pasos siguientes:

- `Ollama` (motor de inferencia local).
- `cloudflared` (cliente de Cloudflare Tunnel).
- `nssm` (Non-Sucking Service Manager).

---

## 2. Instalar Ollama y jalar el modelo

### 2.1 Descargar e instalar

- URL: <https://ollama.com/download/OllamaSetup.exe>.
- Ejecutar el MSI con privilegios de admin.
- Al finalizar, Ollama deja un ícono en system tray y el binario disponible en
  PowerShell como `ollama`.

> Alternativa (si está habilitado): `winget install Ollama.Ollama`.

### 2.2 Verificar que el API está vivo

```powershell
curl http://localhost:11434
# Respuesta: "Ollama is running"
```

### 2.3 Descargar el modelo default MVP

```powershell
ollama pull qwen2.5:7b-instruct-q4_K_M
```

Esto baja ~4.4 GB. Ver [DOC-AI-LOCAL](./local-model-setup.md) para otros
modelos según hardware. Para generar minutas corporativas en ES/EN, el
`qwen2.5:7b-instruct-q4_K_M` cumple con los criterios de EP008/EP014.

### 2.4 Smoke test local

```powershell
curl -X POST http://localhost:11434/api/generate `
  -H "Content-Type: application/json" `
  -d '{"model":"qwen2.5:7b-instruct-q4_K_M","prompt":"Responde OK","stream":false}'
```

Debe regresar un JSON con `"response": "OK"` (o similar) en menos de 5 s.

---

## 3. Instalar `cloudflared` y loguearte

### 3.1 Descargar

- Instalador Windows (64-bit):
  <https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/install-and-setup/tunnel-guide/local/#windows>
- Después de instalar, abre PowerShell y verifica:

```powershell
cloudflared --version
```

### 3.2 Login con el dominio

```powershell
cloudflared tunnel login
```

- Abre el browser → autentica con tu cuenta Cloudflare.
- Selecciona el **dominio** que vas a usar (ej. `tu-dominio.com`).
- Guarda un archivo `cert.pem` en `C:\Users\<user>\.cloudflared\cert.pem`.

---

## 4. Crear el túnel y configurar ingress

### 4.1 Crear túnel nombrado

```powershell
cloudflared tunnel create pmoaas-ollama
```

La salida muestra:
- `Tunnel ID` (UUID).
- Ruta del archivo de credenciales
  `C:\Users\<user>\.cloudflared\<tunnel-id>.json`. **No compartir**.

### 4.2 Crear `config.yml`

Crea `C:\Users\<user>\.cloudflared\config.yml` con el siguiente contenido
(reemplaza `<tunnel-id>` y el hostname):

```yaml
tunnel: <tunnel-id>
credentials-file: C:\Users\<user>\.cloudflared\<tunnel-id>.json

ingress:
  - hostname: ollama.tu-dominio.com
    service: http://localhost:11434
  - service: http_status:404
```

### 4.3 Apuntar DNS al túnel

```powershell
cloudflared tunnel route dns pmoaas-ollama ollama.tu-dominio.com
```

Esto crea un registro CNAME `ollama.tu-dominio.com → <tunnel-id>.cfargotunnel.com`.

### 4.4 Arranque temporal para probar

```powershell
cloudflared tunnel --config C:\Users\<user>\.cloudflared\config.yml run
```

En otra terminal, verifica desde internet:

```powershell
curl https://ollama.tu-dominio.com
# "Ollama is running"
```

Si ves un error 1033 / DNS no propagado, espera 1-2 min y reintenta.

Detén el túnel con Ctrl+C; en el siguiente paso lo dejamos como servicio.

---

## 5. Cloudflare Access — Service Token

En este punto, `https://ollama.tu-dominio.com` es **público**. Vamos a
protegerlo con Cloudflare Access.

### 5.1 Habilitar Zero Trust

- Dashboard Cloudflare → Zero Trust.
- Si es la primera vez, acepta los términos y crea el equipo.

### 5.2 Crear aplicación Self-hosted

- Zero Trust → **Access → Applications → Add application → Self-hosted**.
- Application name: `PMO-aaS Ollama`.
- Application domain: `ollama.tu-dominio.com`.
- Session duration: 24h (o a tu gusto).
- Siguiente.

### 5.3 Policy "Service Token Only"

- Policy name: `Service token`.
- Action: **Service Auth**.
- Configure rule: **Include → Service Token**.
- (Creas el service token en el siguiente paso y lo seleccionas aquí, o lo
  editas después.)
- Guardar.

### 5.4 Emitir Service Token

- Zero Trust → Access → **Service Auth → Service Tokens → Create Service
  Token**.
- Name: `pmoaas-prod` (o por-tenant si los clientes son distintos).
- Duration: sin vencer (para prod) o 1 año.
- Cliente genera **Client ID** y **Client Secret**.
- **Guarda ambos valores ahora**. El Secret **no se vuelve a mostrar**.

Regresa a la policy (5.3) y selecciona el service token recién creado →
guardar.

### 5.5 Smoke test externo autenticado

```powershell
$CF_ID = "<CF-Access-Client-Id>"
$CF_SECRET = "<CF-Access-Client-Secret>"

curl -H "CF-Access-Client-Id: $CF_ID" -H "CF-Access-Client-Secret: $CF_SECRET" `
  https://ollama.tu-dominio.com/api/tags
```

Debe regresar una lista JSON con el modelo `qwen2.5:7b-instruct-q4_K_M`.
Sin los headers, Cloudflare debe responder `401`/página de Access.

---

## 6. Registrar `cloudflared` como servicio con `nssm`

### 6.1 Instalar nssm

- Descargar desde <https://nssm.cc/download>.
- Descomprimir a `C:\Tools\nssm\` y agregar al PATH (o usar ruta absoluta).

### 6.2 Crear el servicio

Abre PowerShell **como administrador**:

```powershell
nssm install CloudflaredOllama "C:\Program Files (x86)\cloudflared\cloudflared.exe"
nssm set CloudflaredOllama AppParameters "tunnel --config C:\Users\<user>\.cloudflared\config.yml run"
nssm set CloudflaredOllama AppDirectory "C:\Users\<user>\.cloudflared"
nssm set CloudflaredOllama Start SERVICE_AUTO_START
nssm set CloudflaredOllama Description "Cloudflare Tunnel — Ollama para PMO-aaS"
nssm set CloudflaredOllama AppStdout "C:\Users\<user>\.cloudflared\cloudflared.out.log"
nssm set CloudflaredOllama AppStderr "C:\Users\<user>\.cloudflared\cloudflared.err.log"
nssm start CloudflaredOllama
```

Verifica con `Get-Service CloudflaredOllama` — debe estar en `Running`.

### 6.3 Registrar Ollama como servicio (opcional pero recomendado)

Ollama ya corre en segundo plano cuando el usuario está logueado, pero para
que arranque con el sistema (antes de login) conviene envolverlo con `nssm`:

```powershell
nssm install OllamaService "C:\Users\<user>\AppData\Local\Programs\Ollama\ollama.exe"
nssm set OllamaService AppParameters "serve"
nssm set OllamaService Start SERVICE_AUTO_START
nssm set OllamaService AppStdout "C:\Users\<user>\.ollama\ollama.out.log"
nssm set OllamaService AppStderr "C:\Users\<user>\.ollama\ollama.err.log"
nssm start OllamaService
```

> Si el instalador MSI ya registró "Ollama" como servicio, omite este paso y
> confirma con `Get-Service Ollama`.

### 6.4 Validar arranque auto

- Reiniciar la PC.
- Al terminar el reinicio (aún sin login, si la PC tiene "inicio automático"),
  ejecuta desde otra máquina el smoke test del paso 5.5 — debe seguir
  respondiendo.

---

## 7. Registrar la URL en PMO (por-tenant)

> Este paso lo cubre en profundidad **US-NEW-045** (EP016). Resumen para
> cerrar el loop del runbook:

- Login al tenant con rol admin / senior PMO.
- Navegar a `/admin/tenant?tab=config`.
- Sección **Proveedor IA local (Ollama)** (disponible tras US-NEW-045):
  - `base_url` = `https://ollama.tu-dominio.com`.
  - `model` = `qwen2.5:7b-instruct-q4_K_M` (o el que descargaste).
  - `timeout_sec` = `60`.
  - `CF-Access-Client-Id` = valor del paso 5.4.
  - `CF-Access-Client-Secret` = valor del paso 5.4 (se guarda cifrado, no se
    muestra después).
- Click **Probar conexión**: si todo va bien, muestra latencia en ms.
- Guardar. La próxima minuta IA del tenant usa este endpoint.

---

## 8. Troubleshooting

| Síntoma | Causa probable | Solución |
|---|---|---|
| `cloudflared: connection refused` | Ollama no está arriba | `Get-Service OllamaService`; `curl http://localhost:11434` |
| `Error 1033` al pegarle al dominio | DNS aún propagándose | Esperar 1-3 min; verificar CNAME con `nslookup ollama.tu-dominio.com` |
| `401 Unauthorized` con service token válido | Policy no selecciona el token correcto | Re-abrir la policy en Zero Trust → Include → Service Token → seleccionar el token; guardar |
| El servicio `CloudflaredOllama` no arranca tras reinicio | `AppDirectory` o rutas mal escritas | `nssm edit CloudflaredOllama` → revisar paths; `nssm restart CloudflaredOllama` |
| Ollama devuelve 500 al generar | RAM insuficiente o modelo mal jalado | `ollama list`; volver a `ollama pull …`; verificar RAM libre |
| El PMO cae a Gemini/Claude constantemente | El worker detecta timeout del túnel | Aumentar `timeout_sec` en config; revisar latencia `cf-ray` en logs |
| Port 11434 ocupado por otra app | Otro Ollama corriendo o LM Studio | Detener el conflicto o cambiar el puerto (`OLLAMA_HOST`) y el `config.yml` |

### Logs útiles

- `cloudflared`: `C:\Users\<user>\.cloudflared\cloudflared.out.log` + `.err.log`.
- `ollama`: `C:\Users\<user>\.ollama\server.log` (o lo que expongas con nssm).
- Cloudflare: dashboard Zero Trust → Logs → Access (requests autenticados).

---

## 9. Rollback / desinstalación

En orden inverso (admin PowerShell):

```powershell
# 1. Detener y remover servicios
nssm stop CloudflaredOllama; nssm remove CloudflaredOllama confirm
nssm stop OllamaService;    nssm remove OllamaService confirm

# 2. Borrar túnel de Cloudflare
cloudflared tunnel delete pmoaas-ollama

# 3. Eliminar DNS record (dashboard Cloudflare) y la Access Application

# 4. Desinstalar binarios
# - Ollama: panel de Control → Programas → desinstalar
# - cloudflared: panel de Control o borrar carpeta instalada
# - nssm: borrar la carpeta donde se extrajo
```

Revocar el Service Token desde Zero Trust si ya no se usa.

---

## 10. Checklist final

- [ ] Ollama responde en `localhost:11434`.
- [ ] Modelo `qwen2.5:7b-instruct-q4_K_M` (o equivalente) descargado.
- [ ] `cloudflared tunnel run` pasa el smoke test desde internet.
- [ ] Cloudflare Access exige Service Token — sin token: 401.
- [ ] Servicio `CloudflaredOllama` corre con `nssm` y arranca tras reinicio.
- [ ] (Opcional) Servicio `OllamaService` con nssm.
- [ ] Config en `/admin/tenant?tab=config` con `base_url` + token guardados.
- [ ] Generación de minuta de prueba termina en ≤ 60 s y el formatter de
      EP014 US-NEW-040 produce el `.md` / `.docx` estandarizado.

---

## Referencias

- Ollama — <https://ollama.com/docs>
- Cloudflare Tunnel — <https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/>
- Cloudflare Access Service Tokens — <https://developers.cloudflare.com/cloudflare-one/identity/service-tokens/>
- nssm — <https://nssm.cc/usage>
- Runbook relacionado (elección de modelo) — [DOC-AI-LOCAL](./local-model-setup.md)
- Epic de integración — [EP016](../epics/EP016-local-ai-tunnel.md)
- Post-procesamiento de minuta — [EP014 US-NEW-040](../epics/EP014-operational-deliverables.md)
