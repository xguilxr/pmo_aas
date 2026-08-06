---
responsable: propietario
estado: vigente
revisado: 2026-05-08
revisar_cada: 180d
---

# Landing estático en HostGator

**ID:** `DOC-INFRA-LANDING`

Runbook para subir y mantener el contenido de marketing estático en HostGator.

---

## 1. Contenido del landing

El directorio `landing/` en la raíz del repo contiene:

```
landing/
├── index.html        # Página de inicio / features
├── assets/
│   ├── css/
│   │   └── main.css
│   ├── js/
│   │   └── main.js
│   └── img/
│       ├── logo.svg
│       ├── hero.png
│       └── ...
└── README.md         # Instrucciones locales
```

---

## 2. Compilación local (si aplica)

Si el landing usa un build tool (Vite, Webpack, etc.):

```bash
cd landing/
npm install
npm run build
# Genera: landing/dist/

# Output está en dist/, prepara para subir
```

Si es HTML puro, salta directamente al paso 3.

---

## 3. Subir a HostGator via cPanel

### 3.1 Login a cPanel

- URL: `https://<tu-dominio>.com:2083` (o similar).
- Usuario: `admin` o tu usuario de HostGator.
- Password: en tu email de HostGator.

### 3.2 Abrir File Manager

cPanel → **File Manager** → navega a **public_html**.

### 3.3 Subir archivos

Opción A (UI web):
1. Click derecho → **Upload** → selecciona archivos de `landing/` (o `landing/dist/` si compilado).
2. Espera que terminen.

Opción B (FTP — más rápido para múltiples archivos):

```bash
# Instalar cliente FTP (lftp, FileZilla, etc.)
# Ejemplo con lftp
lftp -u usuario:password ftp.pmo-aas.com
lftp usuario@ftp.pmo-aas.com> cd public_html
lftp usuario@pmo-aas.com:/public_html> mirror -R landing/
# mirror -R sube recursivamente
```

### 3.4 Estructura final esperada

```
public_html/
├── index.html
├── assets/
│   ├── css/main.css
│   ├── js/main.js
│   └── img/...
└── .htaccess (opcional, para rewrites)
```

---

## 4. SSL/TLS

### 4.1 Habilitar AutoSSL (recomendado)

cPanel → **SSL/TLS Status**:
- **Install** → automático, valida tu dominio.
- Espera ~5 min.

### 4.2 Verificar cert

```bash
curl -I https://www.pmo-aas.com
# Headers deben incluir: cert válido (no self-signed)
```

Si falla, revisar que:
- El dominio apunta correctamente a HostGator IP (ver Cloudflare).
- DNS propagó (~5 min típico).

---

## 5. Rewrite y redirects (.htaccess)

Si el landing necesita rewrite de URLs o redirects:

```apache
# landing/.htaccess (sube a public_html/.htaccess)
<IfModule mod_rewrite.c>
  RewriteEngine On

  # Redirect /index.html → /
  RewriteCond %{THE_REQUEST} ^.*/index\.html [NC]
  RewriteRule ^(.*)index.html$ /$1 [R=301,L]

  # Redirect HTTP → HTTPS
  RewriteCond %{HTTPS} off
  RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]

  # Servir index.html si file/dir no existe (SPA fallback)
  RewriteCond %{REQUEST_FILENAME} !-f
  RewriteCond %{REQUEST_FILENAME} !-d
  RewriteRule . /index.html [QSA,L]
</IfModule>
```

---

## 6. Caching (opcional pero recomendado)

Cloudflare automáticamente cachea assets. Opcionalmente en HostGator:

cPanel → **Optimize Website** (o similar):
- Compression: ON
- Browser caching: 1 año para `.css`, `.js`, `.png`, etc.

---

## 7. Monitoreo

### 7.1 Verificar que la landing está live

```bash
curl https://www.pmo-aas.com
# Debe retornar HTML de index.html

curl https://www.pmo-aas.com/assets/css/main.css
# Debe retornar CSS válido
```

### 7.2 Logs de acceso

cPanel → **Raw Access Logs** → descarga últimas 24h.
```bash
# Buscar errores
grep " 404 " access.log        # Not found
grep " 500 " access.log        # Server error
```

---

## 8. Actualizar landing

Cada vez que cambias contenido:

1. Edita en `landing/` locally.
2. Si hay build step: `npm run build`.
3. Sube cambios via cPanel File Manager o FTP.
4. Espera ~5 min para que Cloudflare cache expire.
5. Verifica en navegador (Cmd+Shift+R para hard refresh).

---

## 9. Rollback

Si algo se rompe:

1. **cPanel File Manager** → selecciona el archivo roto → **Delete**.
2. O sube una versión anterior de `index.html`.
3. Espera ~5 min para cache expire.

---

## 10. Checklist

- [ ] `landing/` contenido compilado o verificado (HTML válido).
- [ ] Archivos subidos a `public_html/` en HostGator.
- [ ] `https://www.pmo-aas.com` carga sin errores.
- [ ] Assets (`css`, `js`, `img`) accesibles.
- [ ] SSL cert válido (sin warnings).
- [ ] Cloudflare proxy `www.*` configurado (naranja).
- [ ] Apex `pmo-aas.com` redirige a `app.pmo-aas.com`.
- [ ] Links internos funcionales.
- [ ] Logo + hero image visibles.
- [ ] CTA ("Login", "Sign up") linkean a `app.pmo-aas.com`.

---

## 11. Troubleshooting

| Síntoma | Causa | Solución |
|---|---|---|
| 404 Not Found | Archivo no subido o mal path | Verificar en cPanel que existe. |
| CSS/JS no carga | MIME type incorrecto | Revisar en cPanel `conf/.htaccess`. |
| SSL error | Cert no válido | cPanel → SSL/TLS → re-install. |
| Muy lento | No hay caching | Cloudflare proxy debe estar ON (naranja). |
| Cambios no aparecen | Cache viejo | Cmd+Shift+R en navegador, esperar 5 min. |

---

## Referencias

- HostGator cPanel docs — https://support.hostgator.com/
- Cloudflare proxy — [`docs/runbooks/infra/dns-routing.md`](./dns-routing.md) §3
- Landing content — `/landing/README.md`
