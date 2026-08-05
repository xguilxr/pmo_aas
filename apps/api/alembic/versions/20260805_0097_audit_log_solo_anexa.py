"""AM-08 / MCS SEG-07 — `audit_log` pasa a ser de solo anexado.

`audit_log` era una tabla ordinaria: nada impedía un `UPDATE`, un `DELETE` o un
`TRUNCATE` desde la aplicación o desde una conexión con sus credenciales. Importa
más de lo que parece porque **AM-06 se apoya en este registro como único
control**, y un control que descansa sobre otro que no existe no es un control.

El modelo de amenazas proponía `REVOKE UPDATE, DELETE` al rol de la aplicación y
lo llamaba barato. Lo es, y **no basta**: en Railway la aplicación se conecta con
el rol dueño de las tablas, y en PostgreSQL el dueño conserva sus privilegios
haga lo que haga el `REVOKE`. Sería un control que se declara y no actúa, que es
peor que ninguno.

Por eso van los dos:

1. **Disparadores que rechazan `UPDATE`, `DELETE` y `TRUNCATE`.** Actúan
   independientemente de quién sea el dueño y cubren también el SQL crudo.
2. **`REVOKE` a `PUBLIC`**, que sí surte efecto y cuesta una línea. El día que
   la aplicación deje de conectarse como dueño —lo correcto— empieza a sumar
   sola.

**Comprobado contra Postgres 16 antes de escribir esto**, no deducido:

```
REVOKE UPDATE, DELETE al dueño, sin disparador   →  UPDATE 1     (pasa)
UPDATE / DELETE / TRUNCATE con disparador        →  ERROR        (no pasa,
                                                    ni siendo superusuario)
INSERT y SELECT con disparador                   →  funcionan
tras `downgrade`                                 →  UPDATE 1     (reversible)
```

**Lo que esto NO detiene, dicho claro:** un superusuario puede quitar el
disparador. Es una defensa contra la aplicación, contra un fallo que permita
ejecutar SQL con sus credenciales y contra el borrado accidental; no contra
quien administra la base. Cerrar eso pide encadenamiento por hash o envío a un
almacén externo, y es otra decisión.

El guardián equivalente en la capa ORM vive en `app/models/audit.py`: cubre el
camino de la aplicación también en SQLite, donde no hay disparadores.
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "20260805_0097"
down_revision: str | None = "20260718_0096"
branch_labels = None
depends_on = None

_FUNCION = """
CREATE OR REPLACE FUNCTION audit_log_rechaza_modificacion() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION
        'audit_log es de solo anexado (AM-08 / MCS SEG-07): % denegado', TG_OP
        USING ERRCODE = 'insufficient_privilege';
END;
$$ LANGUAGE plpgsql;
"""

# Dos disparadores y no uno: PostgreSQL exige que el de TRUNCATE sea por
# sentencia, y los de UPDATE/DELETE tienen que ser por fila para poder
# nombrar la operación en el mensaje.
_POR_FILA = """
CREATE TRIGGER audit_log_sin_modificacion
    BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION audit_log_rechaza_modificacion();
"""

_POR_SENTENCIA = """
CREATE TRIGGER audit_log_sin_truncado
    BEFORE TRUNCATE ON audit_log
    FOR EACH STATEMENT EXECUTE FUNCTION audit_log_rechaza_modificacion();
"""


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        # SQLite (suite de pruebas) no tiene ni disparadores de TRUNCATE ni
        # roles. Ahí el control lo pone el guardián del ORM.
        return

    op.execute(sa.text(_FUNCION))
    op.execute(sa.text(_POR_FILA))
    op.execute(sa.text(_POR_SENTENCIA))
    op.execute(sa.text("REVOKE UPDATE, DELETE, TRUNCATE ON TABLE audit_log FROM PUBLIC"))


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(sa.text("DROP TRIGGER IF EXISTS audit_log_sin_truncado ON audit_log"))
    op.execute(sa.text("DROP TRIGGER IF EXISTS audit_log_sin_modificacion ON audit_log"))
    op.execute(sa.text("DROP FUNCTION IF EXISTS audit_log_rechaza_modificacion()"))
    op.execute(sa.text("GRANT UPDATE, DELETE, TRUNCATE ON TABLE audit_log TO PUBLIC"))
