---
id: SECURITY
titulo: Política de divulgación responsable
estado: vigente
idioma: es
responsable: propietario
revisado: 2026-08-05
revisar_cada: 180d
uso: puntual
---

# Política de divulgación responsable

> **English:** this is the security policy for PMO-aaS. Report vulnerabilities
> privately through **[GitHub Security Advisories][advisories]** — never in a
> public issue. We acknowledge within **2 business days**, triage within **5**,
> and coordinate publication with you. Good-faith research under the rules in
> §5 will not be met with legal action. The full text below is authoritative.

[advisories]: https://github.com/xguilxr/pmo_aas/security/advisories/new

`pmo_aas` es una plataforma multiinquilino: un mismo despliegue guarda los
proyectos, presupuestos y actas de organizaciones distintas que no deben verse
entre sí. Un fallo aquí no expone «una cuenta», expone la cartera de un cliente
a otro. Por eso hay un canal privado y por eso tiene plazos escritos.

Esta política cubre **cómo se reporta** un fallo de seguridad y **qué hace el
proyecto con él**. Lo que el producto considera amenaza y cómo se defiende está
en [`docs/architecture/modelo-amenazas.md`](docs/architecture/modelo-amenazas.md);
esta política es la puerta de entrada, no el inventario.

---

## 1. Cómo se reporta

**Canal único y privado: [abrir un aviso de seguridad][advisories]** en la
pestaña *Security* del repositorio (GitHub Security Advisories). El hilo queda
visible solo para quien reporta y para el responsable, y de él sale el CVE si
hace falta.

**NO abras un issue público, ni un pull request, ni lo comentes en un PR
existente.** El repositorio es público: un issue con los pasos de reproducción
es una publicación, no un reporte. Si ya lo hiciste, no borres nada —avisa por
el canal privado y se coordina desde ahí; borrar deja el rastro en el historial
y quita la evidencia.

Si el canal de GitHub no te sirve —cuenta suspendida, reporte anónimo—,
escribe al propietario por el perfil [github.com/xguilxr](https://github.com/xguilxr)
pidiendo un canal privado, **sin detalles del fallo en ese primer mensaje**.

## 2. Qué incluir

Un reporte se puede triar cuando trae, como mínimo:

| Campo | Por qué hace falta |
|---|---|
| Componente afectado | `apps/api`, `apps/web`, el worker, la infraestructura o el despliegue |
| Versión o commit | El `sha` contra el que reprodujiste; la rama por defecto es `main` |
| Impacto | Qué consigue quien lo explota: leer datos de otro inquilino, elevar rol, ejecutar código, denegar servicio |
| Reproducción | Pasos numerados, petición HTTP cruda o guion. Un vídeo sin los pasos no basta |
| Alcance de la prueba | Contra qué lo probaste: tu propio despliegue, un entorno local, o producción |

Si lo tienes, añade la mitigación que propondrías. No es obligatorio y no
cambia los plazos.

## 3. Qué está dentro del alcance

- El código de este repositorio: `apps/api`, `apps/web`, `packages/`, `scripts/`
  y los flujos de trabajo de `.github/`.
- El aislamiento entre inquilinos, la autenticación y la autorización.
- La canalización de integración y despliegue, y los secretos que maneja.
- El comportamiento de los componentes de IA cuando procesan contenido subido
  por un usuario (inyección de instrucciones, fuga de datos a terceros).

**Fuera de alcance**, salvo que demuestres impacto concreto:

- Resultados de un escáner sin explotación demostrada.
- Ausencia de cabeceras que no conduce a nada explotable en este producto.
- Ingeniería social, acceso físico, y ataques contra las cuentas del personal.
- Denegación de servicio por volumen bruto, y cualquier prueba de carga.
- Vulnerabilidades de servicios de terceros (Railway, Cloudflare R2, los
  proveedores de IA). Repórtalas a quien corresponda; si el fallo está en
  **cómo los usamos**, eso sí es de aquí.
- Prácticas de dependencia ya declaradas con fecha objetivo en
  [`apps/api/.pip-audit-ignore`](apps/api/.pip-audit-ignore).

## 4. Plazos

Días **hábiles**, contados desde que el aviso llega al canal privado.

| Hito | Plazo |
|---|---|
| Acuse de recibo | 2 días |
| Triaje: confirmado o descartado, con severidad | 5 días |
| Corrección de severidad crítica o alta | 30 días |
| Corrección de severidad media o baja | 90 días |
| Publicación coordinada | Al desplegar la corrección, o a los 90 días del acuse |

La severidad se asigna con CVSS v3.1, y en el hilo se escribe el vector, no
solo la etiqueta.

**Si un plazo se va a incumplir, se dice antes de que venza**, con la razón y
la fecha nueva. Un plazo que se pasa en silencio convierte esta tabla en
decoración.

**Este es un proyecto con un solo responsable.** Los plazos están puestos para
poder cumplirse en esa condición, no para lucir cortos.

## 5. Puerto seguro

Si investigas **de buena fe** y respetas las reglas de abajo, el proyecto **no
emprenderá acciones legales** contra ti ni pedirá a terceros que lo hagan, y
tratará tu investigación como autorizada a efectos de las leyes de acceso no
autorizado aplicables.

Las reglas:

1. Prueba contra **tu propio despliegue** o un entorno local. El repositorio
   trae lo necesario para levantarlo.
2. Si tocas producción, limítate a lo mínimo para demostrar el fallo: **no
   accedas a datos de terceros, no los descargues, no los modifiques y no los
   conserves**. Si tropiezas con datos ajenos, para, y dilo en el reporte.
3. No degrades el servicio: nada de pruebas de carga, de fuerza bruta ni de
   agotamiento de recursos.
4. No uses el acceso obtenido para nada más que documentar el fallo.
5. Dale al proyecto los plazos de §4 antes de publicar.

El puerto seguro **no** cubre la extorsión, la exfiltración de datos ni el
acceso a cuentas ajenas, y no te exime frente a terceros: si pruebas contra el
despliegue de un cliente, ese cliente no ha firmado esto.

## 6. Reconocimiento

**No hay recompensa económica.** Se dice de frente para que nadie invierta
tiempo esperando una.

Lo que sí hay: crédito con tu nombre o alias en el aviso publicado y en las
notas de la versión, salvo que prefieras el anonimato. Se pregunta antes de
publicar.

## 7. Versiones cubiertas

| Versión | Cubierta |
|---|---|
| `main` (lo desplegado) | Sí |
| Cualquier commit anterior | No — se corrige hacia adelante |

No hay ramas de mantenimiento: el producto se despliega desde `main` y una
corrección se entrega avanzando, nunca retroportada.

## 8. Qué hace el proyecto con un reporte confirmado

1. Se abre el aviso privado y se le asigna severidad con su vector CVSS.
2. **Si el fallo corresponde a una amenaza del modelo, se anota ahí**; si no
   corresponde a ninguna, entra al modelo como amenaza nueva antes de cerrarse
   — un fallo real que el modelo no preveía es primero un hueco del modelo.
3. La corrección lleva **prueba de regresión** que falla sin ella. Es la regla
   general del repositorio y aquí no se relaja.
4. Al desplegar se publica el aviso, con crédito si lo hay.

---

## Historial

| Fecha | Cambio |
|---|---|
| 2026-08-05 | Primera versión. Cierra `SEG-05` del marco MCS |
