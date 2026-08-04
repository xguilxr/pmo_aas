"""El destino del proveedor de IA lo elige el inquilino; la red interna no.

**Modelo de amenazas B5, amenaza AM-01 (MCS SEG-06).** El modo BYO deja que un
administrador de inquilino configure `base_url` para los proveedores `custom` y
`azure`. Hasta esta defensa el campo se validaba como `str | None` con
`max_length=500` y nada más, y `POST /api/v1/admin/ai/provider/test` lo usaba
para hacer una petición **desde dentro de la plataforma** devolviendo al que
llama el código de estado, 120 caracteres del cuerpo y la latencia.

Eso no es una petición a un proveedor: es un oráculo. Comprobado contra
servidores locales antes de escribir esto:

    http://127.0.0.1:<abierto>  →  "HTTP 418: {cuerpo del servicio interno}"
    http://127.0.0.1:1          →  "All connection attempts failed"
    http://no-existe.interno    →  "getaddrinfo failed"

Las tres respuestas se distinguen entre sí, así que el administrador de
CUALQUIER inquilino podía barrer puertos de la red privada de Railway, saber qué
nombres internos existen y leer un trozo de lo que contestaran. En un producto
multiinquilino eso cruza una frontera que el cliente no debería poder cruzar.

**Lo que esta defensa hace y lo que no.** Rechaza por FORMA: esquema, literales
de IP en rangos no enrutables, nombres reservados y sufijos de red interna. Y
resuelve el nombre para rechazar el que apunte a un rango privado.

Lo que **no** cierra, dicho aquí para que no se lea como una garantía:

- **Reasignación de DNS (rebinding).** Entre esta comprobación y la petición
  real hay dos resoluciones distintas. Un servidor autoritativo hostil puede
  contestar público a la primera y privado a la segunda. Cerrarlo del todo exige
  fijar la IP validada en el transporte, y eso es otra pieza.
- **La fuga de 120 caracteres sigue existiendo** para destinos públicos. Es
  deliberada: BUG-083 la añadió porque sin ella un 4xx del proveedor no se podía
  diagnosticar. Con el destino acotado a hosts públicos, lo que se filtra es la
  respuesta de un servidor que el propio inquilino eligió.
- **Que el inquilino mande sus datos a donde quiera es el propósito de BYO**, no
  un fallo. Lo que se cierra es que ese «donde quiera» incluya nuestra red.
"""
from __future__ import annotations

import asyncio
import ipaddress
import socket
from urllib.parse import urlsplit

# Solo TLS. Un endpoint de IA recibe nombres de proyecto, minutas y RAID; que
# viaje en claro no es aceptable ni aunque el destino sea público. Y de paso
# cierra la mayoría de servicios internos, que hablan HTTP plano.
ESQUEMAS_PERMITIDOS: frozenset[str] = frozenset({"https"})

# Nombres que nunca son un proveedor de IA de terceros.
NOMBRES_BLOQUEADOS: frozenset[str] = frozenset({
    "localhost", "localhost.localdomain", "ip6-localhost", "ip6-loopback",
    "metadata", "metadata.google.internal", "instance-data",
})

# Sufijos de red interna. `.railway.internal` es la red privada de nuestro
# propio proveedor de infraestructura: es el vecindario que hay que proteger.
SUFIJOS_BLOQUEADOS: tuple[str, ...] = (
    ".internal", ".local", ".localdomain", ".localhost",
    ".cluster.local", ".svc", ".svc.cluster.local",
)


def _ip_no_enrutable(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """¿Es una dirección que no debería alcanzarse desde aquí?

    `is_global` cubriría casi todo, pero se enumeran las clases una por una
    porque el motivo del rechazo es lo que se le devuelve al administrador, y
    «no es global» no le dice qué corregir.
    """
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return (
        ip.is_private          # 10/8, 172.16/12, 192.168/16, fc00::/7
        or ip.is_loopback      # 127/8, ::1
        or ip.is_link_local    # 169.254/16 — endpoints de metadatos de nube
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def motivo_url_insegura(url: str | None) -> str | None:
    """Motivo por el que `url` no sirve como destino externo, o None si sirve.

    Sin DNS: es la comprobación barata, la que puede correr dentro de un
    validador de esquema sin bloquear el bucle de eventos. La que resuelve el
    nombre es `asegurar_url_externa`.
    """
    crudo = (url or "").strip()
    if not crudo:
        return "la URL viene vacía"
    partes = urlsplit(crudo)
    if partes.scheme.lower() not in ESQUEMAS_PERMITIDOS:
        return (
            f"el esquema debe ser https, no {partes.scheme or '(ninguno)'!r}. "
            "Un endpoint de IA recibe datos del proyecto y no puede ir en claro"
        )
    host = (partes.hostname or "").strip().lower().rstrip(".")
    if not host:
        return "la URL no lleva host"
    if host in NOMBRES_BLOQUEADOS:
        return f"{host!r} no es un proveedor externo"
    if any(host.endswith(s) for s in SUFIJOS_BLOQUEADOS):
        return f"{host!r} apunta a una red interna"
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return None  # es un nombre; lo resuelve `asegurar_url_externa`
    if _ip_no_enrutable(ip):
        return f"{host} pertenece a un rango que no es alcanzable desde fuera"
    return None


def _resuelve_a_privada(host: str) -> str | None:
    """Motivo si ALGUNA de las direcciones del nombre no es enrutable.

    Se miran todas, no la primera: un nombre con un registro público y otro
    privado serviría para lo mismo que uno solo privado.

    Un fallo de resolución NO es un rechazo. Si el nombre no resuelve, la
    petición tampoco va a llegar a ninguna parte, y rechazar aquí convertiría
    cualquier hipo del DNS en un error de configuración que el administrador no
    puede explicarse.
    """
    try:
        infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    except OSError:
        return None
    for info in infos:
        direccion = info[4][0]
        try:
            ip = ipaddress.ip_address(direccion)
        except ValueError:
            continue
        if _ip_no_enrutable(ip):
            return f"{host!r} resuelve a {direccion}, que está en la red interna"
    return None


async def asegurar_url_externa(url: str | None) -> None:
    """Lanza `ValueError` si `url` no puede usarse como destino externo.

    La resolución va a un hilo: `getaddrinfo` es bloqueante y esto se llama
    desde rutas asíncronas.
    """
    motivo = motivo_url_insegura(url)
    if motivo is None:
        host = (urlsplit((url or "").strip()).hostname or "").lower().rstrip(".")
        try:
            ipaddress.ip_address(host)
        except ValueError:
            motivo = await asyncio.to_thread(_resuelve_a_privada, host)
    if motivo:
        raise ValueError(f"base_url rechazada: {motivo}")
