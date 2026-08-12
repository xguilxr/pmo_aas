---
tipo: runbook
responsable: propietario
estado: vigente
revisado: 2026-08-12
revisar_cada: 90d
---

# Entornos y procedimiento de reversión

Cierra **MCS INF-02** («entornos separados para desarrollo y producción, con
paridad en las versiones de los servicios de datos») y **DES-02**
(«procedimiento de reversión documentado y ejecutable»).

---

## 1. Los entornos

| Entorno | Proveedor | Qué es |
|---|---|---|
| **producción** | Railway | El que atiende a los clientes |
| **desarrollo** | Railway | Copia del productivo. **Existe y hoy no se usa** (owner, 2026-08-06) |
| local | máquina de quien desarrolla | No es entorno del producto; no cuenta para INF-02 |

Que la copia de desarrollo esté sin usar no la descalifica: el requisito pide
que los entornos **existan y estén separados**, no que haya tráfico en ambos.
Lo que importa está abajo.

## 2. Paridad de versiones — la parte que se verifica

Las versiones se declaran en **[`servicios-datos.yml`](../../../servicios-datos.yml)**,
en la raíz. `scripts/check_entornos.py` comprueba en cada PR que el CI las
respeta.

**Por qué hacía falta un archivo para esto.** Sin un sitio que dijera qué
versión toca, «paridad» no se puede afirmar ni desmentir: solo se puede
suponer. Y la suposición estaba mal. El 2026-08-06, al correr a mano lo que
el CI no podía, la base local resultó ser **Postgres 16** contra el **15**
del workflow. Nadie lo eligió: era el que traía el sistema.

La migración `0101` se reescribió por miedo a una diferencia entre motores.
Esa era justo la divergencia que no debía existir.

**Lo que el gate no puede comprobar** es qué corre de verdad en Railway: este
repositorio no tiene acceso. Se declara aquí, con fecha, en vez de fingir que se
mide:

> **Declarado 2026-08-06:** Railway corre Postgres serie **15**. Al cambiarlo,
> se actualiza `servicios-datos.yml` **antes** de tocar el proveedor, para que
> el CI se rompa si alguien se olvida de la otra mitad.

### Alinear un entorno local

```bash
# Comprobar qué serie tenés
psql --version

# Si no es la declarada, el contenedor evita ensuciar el sistema
docker run --name pmo-pg -e POSTGRES_PASSWORD=pmo -p 5432:5432 -d postgres:15-alpine
```

---

## 3. Reversión (DES-02)

Tres capas, y **el orden importa**: la de código es reversible en un clic, la de
datos no siempre.

### 3.1 Decidir qué se revierte

| Síntoma | Qué revertir |
|---|---|
| Error en la aplicación, base intacta | **Solo el despliegue** (§3.2) |
| Migración que rompió el esquema | Despliegue **y** migración (§3.3) |
| Datos corrompidos o borrados | Restauración desde copia ([runbook](respaldo-restauracion.md)) |

**Revertir el despliegue no deshace una migración.** Es el error que convierte
un incidente de diez minutos en uno de dos horas: el código viejo se encuentra
un esquema nuevo que no conoce.

### 3.2 Revertir el despliegue

En Railway → servicio → **Deployments** → el despliegue anterior → **Redeploy**.

Railway conserva los despliegues anteriores: esto es un clic y no
requiere reconstruir. **Comprobar después:**

```bash
curl -s https://<host>/health | jq
```

Debe devolver `status: ok`, `database: ok` y `error_capture: ok`. Los tres: un
despliegue que responde pero sin captura de errores deja el siguiente fallo a
ciegas.

### 3.3 Revertir una migración

```bash
# Ver dónde está
alembic current

# Bajar UNA. Nunca `downgrade base` en producción: eso vacía el esquema entero.
alembic downgrade -1
```

**Antes de bajar, lee el `downgrade()` de esa migración.** Las de esquema
suelen revertir sin pérdida; **las de datos, no**. La `0101` renombra una llave
en `tenants.settings` y su reversión es simétrica. Una que hubiera
borrado una columna no puede devolver lo que había.

Si el `downgrade()` no puede devolver los datos, **la vía es la restauración**,
no la reversión.

### 3.4 Después, siempre

1. Confirma que `/health` responde `ok` en sus tres comprobaciones.
2. Mira Sentry: la reversión no borra los errores ya capturados, y ahí
   está la causa.
3. Anota qué pasó. Si la reversión fue por una migración, va a
   `docs/epics/DB-CHANGES.md` junto a la entrada de esa migración.

---

## 4. Ensayarlo

**Un procedimiento de reversión que nunca se ejecutó no es ejecutable**, que es
lo que DES-02 pide. Lo mismo que con las copias.

El ensayo barato: en el entorno de **desarrollo** (existe justamente para
esto), despliega, revierte al anterior y comprueba `/health`. Toma diez
minutos, y la primera vez no debe ser durante un incidente.
