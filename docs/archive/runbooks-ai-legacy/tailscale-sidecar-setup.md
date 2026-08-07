---
tipo: archivo
responsable: propietario
estado: archivado
revisado: 2026-05-08
revisar_cada: nunca
---

# Runbook — Tailscale + Ollama local → Railway worker — **ARCHIVADO**

> ## ⚠️ Runbook archivado (ENH-023, 2026-04-23)
>
> Este runbook describía el **sidecar Tailscale** en el worker de
> Railway (US-048). Tras **DEC-017** (IA multi-modo con Groq hosteado)
> el sidecar dejó de ser necesario y se retiró en **ENH-023** (#103):
>
> - `apps/api/start-worker.sh` eliminado.
> - `apps/api/Dockerfile` sin Tailscale install ni `iptables`.
> - `apps/api/worker.railway.toml` arranca celery directo.
> - Env vars `TS_AUTHKEY` / `TS_HOSTNAME` retirables del worker en
>   Railway (acción manual post-merge).
>
> **Archivo conservado** como referencia histórica del diseño
> CF Tunnel → Tailscale → Groq. Si un tenant legacy quiere reactivar
> Ollama propio como BYO, este runbook sigue siendo útil — pero el
> setup sería **en la infra del tenant**, no en el worker productivo
> de la plataforma.
>
> Ver también:
> - [`docs/archive/cancelled-epics/EP016-local-ai-tunnel.md`](../cancelled-epics/EP016-local-ai-tunnel.md)
> - [`docs/archive/runbooks-ai-legacy/local-ollama-setup.md`](./local-ollama-setup.md)
> - `docs/epics/DECISIONS.md` — DEC-011 (Tailscale), DEC-017, DEC-019.

---

**ID:** `DOC-NETWORK-TAILSCALE` (archivado)  
**Alcance original:** EP016 — US-046 (reemplazaba US-044)  
**Dependencias originales:** `docs/archive/runbooks-ai-legacy/local-model-setup.md` (elección de modelo)

Este runbook documenta cómo montar Ollama en una PC Windows y exponerlo
al worker de Railway a través de un **tailnet privado de Tailscale**. El
canal es WireGuard end-to-end: no hay endpoint público, no hay Service
Token que rotar y el firewall del router del owner no necesita abrir
ningún puerto.

Reemplaza al runbook previo que usaba Cloudflare Tunnel + Cloudflare
Access (`docs(ai): US-044`). La versión CF queda en historial de git
(commit de US-044) por si se requiere consulta; el diseño actual es
Tailscale por DEC-011 (ver `docs/epics/DECISIONS.md`).

> Tiempo estimado: **~20 min** si Ollama ya está instalado y hay cuenta
> Tailscale; ~35 min desde cero.

---

## 0. Topología

```
+--------------------------+                     +---------------------------+
|  PC local (Windows)      |                     |  Railway worker           |
|  hostname: ollama-host   |                     |  hostname: pmo-worker-   |
|                          |                     |           railway         |
|  Ollama 0.0.0.0:11434    |                     |  celery + sidecar         |
|  tailscaled (service)    |                     |  tailscaled --tun=        |
|  tailnet IP 100.x.y.z    |<==== WireGuard ====>|    userspace-networking   |
|                          |   (NAT traversal    |  hostname MagicDNS:       |
|  Firewall: 11434 inbound |    o DERP relay)    |    pmo-worker-railway.   |
|  solo 100.64.0.0/10      |                     |    <tailnet>.ts.net:      |
|                          |                     |    11434                  |
+--------------------------+                     +---------------------------+
```

Propiedades:

- **PC local**: Ollama en `0.0.0.0:11434` (no `127.0.0.1`), pero el
  Windows Firewall limita el puerto a la subnet tailnet `100.64.0.0/10`.
  No hay exposición al internet público.
- **Tailscale**: tailnet privado WireGuard. El MagicDNS `ollama-host.<tailnet>.ts.net`
  se resuelve dentro del tailnet. Tráfico prefiere rutas directas (NAT
  traversal); si falla, DERP relay cifrado.
- **Worker Railway**: corre `tailscaled` en user-space (Railway no da
  `/dev/net/tun`) como sidecar antes de `celery`. Ver US-048.
- **PMO config por-tenant**: `base_url = http://ollama-host.<tailnet>.ts.net:11434`.
  No se guardan credenciales ni headers de auth (US-047 eliminó el
  flujo CF-Access).

---

## 1. Pre-requisitos

| Ítem | Mínimo recomendado |
|---|---|
| SO | Windows 10 x64 / Windows 11 |
| RAM | 16 GB (8 GB libre para Ollama + 7B Q4) |
| Disco libre | 15 GB |
| Conexión | 20 Mbps estable (Tailscale usa WireGuard UDP; no necesita ancho simétrico) |
| Cuenta Tailscale | Free tier alcanza (100 devices, 3 users) |
| Acceso | Windows con permisos de admin para instalar servicios |
| Herramientas | PowerShell 5.1+ |

**Dependencias que se instalan en este runbook:**

- `Ollama` (motor de inferencia local).
- `Tailscale for Windows` (tailnet privado).
- `nssm` (opcional, para arranque pre-login de `tailscaled` si se
  requiere que el tailnet esté vivo antes de que el owner inicie sesión).

---

## 2. Instalar Ollama y jalar el modelo

Si ya lo hiciste en el runbook anterior, salta al paso 3 — solo revisa
el **2.5** para reabrir Ollama al tailnet.

### 2.1 Descargar e instalar

- URL: <https://ollama.com/download/OllamaSetup.exe>.
- Ejecutar el MSI con privilegios de admin.
- Al finalizar, Ollama deja un ícono en system tray y el binario
  disponible en PowerShell como `ollama`.

> Alternativa: `winget install Ollama.Ollama`.

### 2.2 Verificar que el API local responde

```powershell
curl http://localhost:11434
# Respuesta esperada: "Ollama is running"
```

### 2.3 Descargar el modelo default MVP

```powershell
ollama pull qwen2.5:7b-instruct-q4_K_M
```

Esto baja ~4.4 GB. Ver [`docs/runbooks/ai/local-model-setup.md`](../ai/local-model-setup.md)
para otras opciones según hardware.

### 2.4 Smoke test local

```powershell
$body = @{
  model  = "qwen2.5:7b-instruct-q4_K_M"
  prompt = "Responde OK"
  stream = $false
} | ConvertTo-Json -Depth 5

$response = Invoke-RestMethod `
  -Uri "http://localhost:11434/api/generate" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body

$response
```

Debe regresar JSON con `"response": "OK"` en < 5 s.

### 2.5 Exponer Ollama al tailnet (0.0.0.0 en lugar de localhost)

Por default Ollama sólo escucha en `127.0.0.1:11434`. Para que lo
alcancen otros devices del tailnet hay que abrirlo a todas las
interfaces y reiniciarlo.

En PowerShell del usuario owner (no admin):

```powershell
[System.Environment]::SetEnvironmentVariable("OLLAMA_HOST", "0.0.0.0:11434", "User")
```

Luego:

1. Botón derecho en el ícono de Ollama del system tray → **Quit Ollama**.
2. Abrir Ollama de nuevo desde el menú Inicio (hereda la nueva env).

Verifica con:

```powershell
netstat -ano | Select-String "11434"
# Debe mostrar 0.0.0.0:11434 LISTENING
```

---

## 3. Instalar Tailscale en la PC local

### 3.1 Descargar e instalar

- URL oficial: <https://tailscale.com/download/windows>.
- Ejecutar el MSI con privilegios de admin.
- Al terminar queda en system tray.

### 3.2 Login y alta del hostname

> **Antes de ejecutar `tailscale up`:** el MSI deja el binario en
> `C:\Program Files\Tailscale\` y agrega esa ruta al PATH **del
> sistema**, pero las ventanas de PowerShell que estaban abiertas
> **antes** del install **no** recogen el cambio — siguen operando con
> el PATH de su sesión inicial. Si intentas el comando en una terminal
> vieja obtendrás `tailscale : The term 'tailscale' is not recognized`.
>
> Para evitarlo:
>
> 1. Verifica que el binario y el servicio existen (PowerShell normal):
>    ```powershell
>    Test-Path "C:\Program Files\Tailscale\tailscale.exe"  # True
>    Get-Service Tailscale                                  # Running / Stopped
>    ```
>    Si `Test-Path` devuelve `False`, reinstala el MSI. Si el servicio
>    está `Stopped`, `Start-Service Tailscale` (admin).
> 2. **Cierra y vuelve a abrir** PowerShell **como administrador** —
>    así la nueva sesión hereda el PATH actualizado.
>
> Alternativas si no quieres cerrar la sesión:
>
> - Usar la ruta completa: `& "C:\Program Files\Tailscale\tailscale.exe" up --hostname=ollama-host`.
> - Refrescar el PATH en la sesión actual:
>   ```powershell
>   $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
>   ```

En la PowerShell **como administrador** (recién abierta o con PATH
refrescado):

```powershell
tailscale up --hostname=ollama-host
```

- Se abre browser con flujo de login (GitHub / Google / Microsoft /
  email). Autentícate con la **cuenta owner del tailnet PMO**.
- Aprueba el device desde el browser → regresa a la terminal.

Verifica:

```powershell
tailscale status
# ollama-host  100.x.y.z  user@...  windows  active; direct ...

tailscale ip -4
# 100.x.y.z
```

El hostname MagicDNS queda como `ollama-host.<tu-tailnet>.ts.net`.
Identifícalo con:

```powershell
tailscale status --json | ConvertFrom-Json | Select-Object -ExpandProperty MagicDNSSuffix
# tu-tailnet.ts.net
```

> Si piensas correr también el worker en el mismo tailnet
> (recomendado, ver US-048), **no cambies de tailnet** entre devices.

---

## 4. Firewall — limitar 11434 al tailnet

Ollama quedó en `0.0.0.0:11434`. Restringe el puerto para que solo el
tailnet pueda llegar (defensa en profundidad: aunque el router no haga
port-forward, bloqueamos por si se activa Wi-Fi pública).

> **⚠️ BUG-020 (2026-04-21):** la versión anterior de este runbook
> creaba **dos** reglas (`Allow tailnet only` + `Block non-tailnet`).
> Windows Firewall evalúa **todas las reglas aplicables** y si hay un
> Block que matchea, Block gana — incluyendo el tráfico tailnet que el
> Allow intentaba permitir. Síntoma: `ConnectTimeout` desde el peer
> Tailscale con el puerto escuchando y DNS OK. El fix es crear **solo**
> la regla Allow y dejar que el default "block inbound unless allowed"
> de Windows Firewall cubra el resto.

PowerShell admin — primero limpia reglas previas (idempotente):

```powershell
# Limpia cualquier regla Ollama* previa que pueda shadow-blockear
Get-NetFirewallRule -DisplayName "Ollama*" -ErrorAction SilentlyContinue |
  Remove-NetFirewallRule

# Única regla: permite solo desde el rango CGNAT del tailnet
New-NetFirewallRule `
  -DisplayName "Ollama allow tailnet" `
  -Direction Inbound `
  -LocalPort 11434 `
  -Protocol TCP `
  -Action Allow `
  -RemoteAddress 100.64.0.0/10
```

`100.64.0.0/10` es el rango CGNAT que Tailscale usa para el tailnet —
cubre todos los peers.

Por qué **no** crear una regla Block complementaria:

- El default de Windows Firewall para inbound es "deny unless allowed".
  Con la regla Allow restringida al tailnet, cualquier IP fuera de ese
  rango ya queda bloqueada por default — no hace falta una regla Block.
- Si se agrega `-Action Block -RemoteAddress Any`, esa regla **también**
  hace match con tráfico tailnet (Any incluye 100.64.x.x) y Block gana
  sobre Allow en reglas con Action conflictivo para el mismo port/protocol.

Verifica:

```powershell
Get-NetFirewallRule -DisplayName "Ollama*" | Format-Table DisplayName, Enabled, Direction, Action
# Debe aparecer exactamente 1 regla: "Ollama allow tailnet" / Allow / Inbound
```

---

## 5. Smoke test desde otro device del tailnet

Desde otro peer del tailnet (tu laptop secundaria, celular con Tailscale
iOS, o el propio worker de Railway después de US-048):

```bash
# Por IP tailnet:
curl http://100.x.y.z:11434
# "Ollama is running"

# Por MagicDNS:
curl http://ollama-host.<tu-tailnet>.ts.net:11434
# "Ollama is running"

curl http://ollama-host.<tu-tailnet>.ts.net:11434/api/tags
# { "models": [ { "name": "qwen2.5:7b-instruct-q4_K_M", ... } ] }
```

Si falla la resolución MagicDNS: `tailscale status` en el peer origen;
debe listar `ollama-host` como peer `active`. Si no, revisa que los dos
devices estén en el mismo tailnet.

---

## 6. Generar `TS_AUTHKEY` para el worker de Railway

El worker de Railway (US-048) necesita unirse al tailnet sin
intervención humana. Tailscale soporta **auth keys** reutilizables.

### 6.1 En Tailscale Admin

1. Abrir <https://login.tailscale.com/admin/settings/keys>.
2. Click **Generate auth key**.
3. Configurar:
   - **Reusable**: ON (el worker puede redeployarse N veces con la misma
     key).
   - **Ephemeral**: ON (cuando el container muere, Tailscale borra el
     peer del admin console — evita acumular peers muertos en cada
     redeploy).
   - **Pre-approved**: ON (no requiere aprobar en admin cada rearranque).
   - **Expiration**: 90 días (rota al cerrar sprint; anota en calendar).
   - **Tags**: `tag:railway-worker` (obliga a definir ese tag en ACLs).
4. Copiar el valor `tskey-auth-...` al password manager del owner.

> **Importante:** antes de usar el tag `tag:railway-worker` hay que
> definirlo en el archivo ACL del tailnet:
> Admin console → **Access controls → Edit ACL** → agregar:
> ```json
> {
>   "tagOwners": {
>     "tag:railway-worker": ["autogroup:admin"],
>     "tag:ollama": ["autogroup:admin"]
>   }
> }
> ```
> Sin eso, `tailscale up --authkey=...` falla con "tag not allowed".

### 6.2 En Railway

El valor de la auth key se guarda como **variable de entorno** en el
servicio `worker`:

- **Nombre**: `TS_AUTHKEY`
- **Valor**: `tskey-auth-...` (la key generada)

Ídem **`TS_HOSTNAME`** para que el worker tenga nombre en el tailnet:

- **Nombre**: `TS_HOSTNAME`
- **Valor**: `pmo-worker-railway` (o similar, debe ser único en el tailnet)

Ver [`docs/runbooks/railway/SETUP.md`](../railway/SETUP.md) §3.3 para
agregar variables al servicio `worker`.

---

## 7. Registrar el endpoint en PMO (por-tenant)

> El formulario y endpoint de test-connection quedan en US-047.
> Esta sección asume ese refactor aplicado (ya no hay campos
> CF-Access).

- Login al tenant con rol admin / senior PMO.
- Navegar a `/admin/tenant?tab=config`.
- Sección **Proveedor IA local (Ollama)**:
  - `base_url` = `http://ollama-host.<tu-tailnet>.ts.net:11434`
    - (Alternativa IP directa: `http://100.x.y.z:11434`. MagicDNS es
      preferible porque la IP puede cambiar si reinstalas Tailscale.)
  - `model` = `qwen2.5:7b-instruct-q4_K_M`.
  - `timeout_sec` = `60`.
- Click **Probar conexión**.
  - **Si el worker ya tiene el sidecar Tailscale arriba (US-048)**:
    devuelve latencia en ms y `model_present=true`.
  - **Si el worker aún no tiene sidecar**: el endpoint corre desde `api`
    (que NO está en el tailnet) y va a fallar con timeout/unreachable.
    Es esperado; la verificación real la hace el worker al procesar una
    minuta.
- Guardar.

---

## 8. Troubleshooting

| Síntoma | Causa probable | Solución |
|---|---|---|
| `tailscale : The term 'tailscale' is not recognized` en PowerShell tras instalar MSI | PATH del sistema no refrescado en la sesión actual de PowerShell | Cerrar y reabrir PowerShell (admin); o usar ruta completa `& "C:\Program Files\Tailscale\tailscale.exe" up ...`; o refrescar PATH con `$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")` |
| `tailscale status` no lista peers | No hiciste login o el device está logged out | `tailscale up` + flujo de browser |
| `tailscale ip -4` vacío | Servicio `Tailscale` detenido | `Start-Service Tailscale` |
| Otro device del tailnet no resuelve `ollama-host.*.ts.net` | MagicDNS deshabilitado en el tailnet | Admin console → **DNS → Enable MagicDNS** |
| `curl http://100.x.y.z:11434` desde peer da timeout | Windows Firewall tira el paquete / Ollama solo en `127.0.0.1` | Paso 2.5 + paso 4 |
| `ConnectTimeout` desde el worker a Ollama con `netstat` mostrando `0.0.0.0:11434 LISTENING` y `dig` / resolución DNS OK (BUG-020) | Existen 2 reglas Windows Firewall "Ollama*": una Allow tailnet + una Block Any. Block gana porque Any incluye 100.64.x.x. | `Get-NetFirewallRule -DisplayName "Ollama*" \| Remove-NetFirewallRule` y recrear solo la Allow (§4). Nunca dejar una regla Block cubriendo el mismo puerto. |
| `curl http://ollama-host.*.ts.net` resuelve pero conecta a 127.0.0.1 | El peer origen tiene `accept-dns=false` y resolvió localmente | `tailscale up --accept-dns=true` en el peer origen |
| `401` / `403` al probar desde el worker | — | Ya no aplica: sin CF-Access no hay auth. Si ves un 403, revisa que no haya un proxy intermedio (no debería haberlo) |
| `tailscale ping ollama-host` alto (> 200 ms) | DERP relay en vez de ruta directa | Revisa NAT del router; considera habilitar UPnP o configurar port forwarding de Tailscale (opcional) |
| Ollama 500 al generar | RAM insuficiente / modelo corrupto | `ollama list`; `ollama pull qwen2.5:7b-instruct-q4_K_M`; revisar memoria libre |
| El PMO cae a Gemini/Claude constantemente | Timeout al resolver MagicDNS desde el worker | `tailscale status` dentro del container del worker; `timeout_sec` más alto; ver US-048 |

### Logs útiles

- **Tailscale Windows**: `C:\ProgramData\Tailscale\Logs\tailscaled.log`
- **Tailscale diagnóstico**: `tailscale bugreport` (genera ID de soporte)
- **Ollama**: `C:\Users\<user>\.ollama\server.log`
- **Tailscale admin console**: <https://login.tailscale.com/admin/machines>
  muestra última vez que cada peer se conectó + rutas usadas.

---

## 9. Rollback / desinstalación

En orden inverso (PowerShell admin):

```powershell
# 1. Salir del tailnet desde esta PC
tailscale logout

# 2. Detener servicio nssm si se creó (opcional)
nssm stop TailscaledService 2>$null; nssm remove TailscaledService confirm 2>$null

# 3. Desinstalar Tailscale (panel de Control → Programas)

# 4. Revocar TS_AUTHKEY
#    - Admin console → Settings → Keys → encontrar la key y click "Revoke"
#    - Borrar la variable TS_AUTHKEY de Railway

# 5. Revocar device del tailnet
#    - Admin console → Machines → ollama-host → menú → "Delete"

# 6. Revertir firewall rules
Get-NetFirewallRule -DisplayName "Ollama*" -ErrorAction SilentlyContinue |
  Remove-NetFirewallRule

# 7. Restaurar Ollama a localhost
[System.Environment]::SetEnvironmentVariable("OLLAMA_HOST", $null, "User")
# Reabrir Ollama desde menú Inicio

# 8. (Opcional) Desinstalar Ollama si no se usa
```

---

## 10. Checklist final

- [ ] Ollama responde en `0.0.0.0:11434` (no solo `127.0.0.1`).
- [ ] Modelo `qwen2.5:7b-instruct-q4_K_M` descargado.
- [ ] Tailscale instalado; `tailscale status` muestra `ollama-host` como
      device `active`.
- [ ] Firewall rules Ollama limitadas a `100.64.0.0/10` (solo 1 regla Allow).
- [ ] Desde otro peer del tailnet, `curl http://ollama-host.<tailnet>.ts.net:11434/api/tags`
      devuelve la lista de modelos.
- [ ] `TS_AUTHKEY` reutilizable + ephemeral + tag `tag:railway-worker`
      generado y guardado en password manager.
- [ ] Tags `tag:railway-worker` y `tag:ollama` definidos en ACL del tailnet.
- [ ] `TS_AUTHKEY` + `TS_HOSTNAME=pmo-worker-railway` configurados en
      Railway `worker`.
- [ ] Config en `/admin/tenant?tab=config` con `base_url` MagicDNS
      guardado (después de US-047).
- [ ] Worker de Railway con sidecar `tailscaled` resuelve el hostname
      (US-048 — dependencia aparte).

---

## Referencias

- Ollama — <https://ollama.com/docs>
- Tailscale Windows — <https://tailscale.com/kb/1022/install-windows>
- Tailscale Docker / sidecar — <https://tailscale.com/kb/1282/docker>
- Tailscale ACLs + tags — <https://tailscale.com/kb/1068/acl-tags>
- Tailscale auth keys — <https://tailscale.com/kb/1085/auth-keys>
- nssm — <https://nssm.cc/usage>
- Runbook modelo local (archivado) — [`docs/archive/runbooks-ai-legacy/local-model-setup.md`](../../archive/runbooks-ai-legacy/local-model-setup.md)
- Epic de integración (superseded por DEC-017) — [`docs/archive/cancelled-epics/EP016-local-ai-tunnel.md`](../../archive/cancelled-epics/EP016-local-ai-tunnel.md)
