# PMO-aaS — landing `www.pmo-aas.com`

**US-050** · Bloque 15 del sprint · DEC-012 (HostGator solo landing).

Sitio estático de marketing que se sirve desde HostGator en
`https://www.pmo-aas.com`. No tiene conexión a BD ni llamadas al API:
único objetivo es presentar la marca PMO-aaS y empujar al usuario al
login en `https://app.pmo-aas.com/login`.

---

## Estructura

```
landing/
├── README.md              ← este archivo
├── index.html             ← página única
└── assets/
    ├── styles.css         ← estilos minimalistas, paleta chrome
    └── favicon.svg        ← marca PMO en #182e4e
```

Todo el código es HTML/CSS vanilla: no requiere build, no hay JS más
allá de un `document.getElementById("year").textContent = …` para el
copyright. Funciona en cualquier hosting shared.

---

## Vista local (opcional)

```bash
cd landing
python3 -m http.server 8080
# abrir http://localhost:8080
```

O arrastra `index.html` al browser.

---

## Deploy a HostGator

> Pre-requisito: el DNS ya debe apuntar `www.pmo-aas.com` a HostGator
> con proxy Cloudflare (ver `docs/runbooks/infra/dns-routing.md` §3).

### Opción A — cPanel File Manager

1. Login cPanel HostGator → **Files → File Manager**.
2. Navegar a `public_html/` (si el dominio está como addon, a
   `public_html/<dominio>/`).
3. **Upload** → seleccionar `index.html`.
4. Dentro de `public_html/`, crear carpeta `assets/` → **Upload** los
   dos archivos (`styles.css`, `favicon.svg`).
5. Permisos default (644 archivos, 755 carpetas) son correctos.

### Opción B — FTP / SFTP

```bash
# con lftp (ejemplo)
lftp -u <cpanel_user>,<cpanel_password> ftp.pmo-aas.com <<'EOF'
set ssl:verify-certificate no
cd public_html
mirror -R --delete ./landing/ ./
bye
EOF
```

O con cualquier cliente FTP (FileZilla, Cyberduck) arrastrando el
contenido de `landing/` al root de `public_html/`.

### Smoke test post-deploy

```bash
curl -I https://www.pmo-aas.com
# HTTP/2 200
# content-type: text/html; charset=utf-8
# server: cloudflare

curl -I https://www.pmo-aas.com/assets/styles.css
# HTTP/2 200
# content-type: text/css
```

En el browser:

1. `https://www.pmo-aas.com/` → landing visible.
2. Click en "Iniciar sesión" → redirige a `https://app.pmo-aas.com/login`.
3. `https://pmo-aas.com/` (apex) → 301 a `https://app.pmo-aas.com/`
   (cubierto por la Redirect Rule del Bloque 15 US-049).

---

## Cambios futuros

- Copy y CTA están en `index.html`. Editar y re-subir los archivos
  tocados.
- Si se agrega pricing, pricing page, blog, etc., estructurar bajo
  `landing/<sección>/index.html` y re-sincronizar a HostGator.
- El landing **nunca** debe necesitar el API; si aparece necesidad de
  un formulario de contacto real, usar un servicio externo (Formspree,
  Netlify Forms, HostGator mail forwarder) — no endpoints propios.

---

## Licencia / referencias

- Colores y marca alineados al chrome de la app (DEC-006, `#182e4e`).
- Copy revisado por el owner antes del release v1.0.
