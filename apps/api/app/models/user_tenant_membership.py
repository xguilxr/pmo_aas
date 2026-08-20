"""US-214 — La membresía de una persona en un inquilino.

Hasta aquí, un usuario pertenecía a uno: `users.tenant_id`. Los mockups piden un
selector de inquilino en el encabezado, y para eso hace falta que la relación sea
de muchos a muchos — un consultor que trabaja para dos clientes, una PMO que
gestiona varias cuentas.

## Por qué una tabla y no una lista en el JWT

Es la amenaza **AM-16** del modelo. Hasta US-214 el cambio de inquilino se
autorizaba contra el claim `tenant_ids` del token; con un solo inquilino por
usuario la lista era de un elemento y el defecto no tenía consecuencia. Con dos,
**revocar una membresía no surtiría efecto hasta que el token caduque** — una
hora, o treinta días si la renovación reemite los claims sin mirar la tabla.

La tabla es la fuente de verdad, y se consulta en el cambio **y en cada petición**.
El claim solo pinta el desplegable.

## Por qué `users.tenant_id` no desaparece

Sigue siendo el inquilino **de origen** de la persona: dónde se creó su cuenta y
quién la administra. Retirarlo obligaría a reescribir todas las consultas que hoy
lo usan para resolver el inquilino por defecto, y a decidir qué pasa con un
usuario cuya única membresía se revoca —¿se queda sin inquilino, o se borra?—.
Esta US no abre ese frente: la membresía **añade** inquilinos, no reemplaza el de
origen. El de origen se siembra como membresía en la migración para que las dos
lecturas coincidan desde el primer día.
"""
from datetime import UTC, datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid
from app.models.user import User


class UserTenantMembership(Base, TimestampMixin):
    __tablename__ = "user_tenant_memberships"
    __table_args__ = (
        # Una persona no puede tener dos membresías al mismo inquilino: la
        # segunda no significaría nada y duplicaría la entrada del desplegable.
        UniqueConstraint(
            "user_id", "tenant_id", name="uq_membership_user_tenant"
        ),
        # La consulta de cada petición es «¿este usuario tiene membresía viva en
        # este inquilino?». Va por aquí.
        Index("ix_membership_user_tenant", "user_id", "tenant_id"),
    )

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    tenant_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    #: Quién la concedió. Sin clave ajena para que borrar al superadministrador
    #: que la concedió no borre la traza de que se concedió.
    #:
    #: Anotada `str` y no `UUID` a propósito: la columna es `String(36)` y estas
    #: dos se asignan por atributo, no por constructor. Con la anotación en `UUID`
    #: el tipador pide convertir, y el objeto convertido es justo lo que el
    #: controlador de SQLite no sabe enlazar.
    granted_by_user_id: Mapped[str | None] = mapped_column(String(36))
    #: Cuándo se revocó. Se marca en vez de borrar la fila: la pregunta «¿quién
    #: tuvo acceso a este cliente y cuándo se le quitó?» no se puede contestar
    #: con una fila borrada, y es exactamente la pregunta de una auditoría.
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_by_user_id: Mapped[str | None] = mapped_column(String(36))


# ---------------------------------------------------------------------------
# US-214 — la membresía de origen se crea con el usuario
# ---------------------------------------------------------------------------
#
# `get_current_user` comprueba la membresía en **cada** petición (AM-16), así que
# un usuario creado sin ella no puede entrar a ningún sitio. Y los usuarios se
# crean desde cinco caminos: el alta de administrador, el alta de inquilino del
# superadministrador, dos siembras y las factorías de las pruebas.
#
# Vive aquí y no en cada endpoint por la misma razón que `normalizar_hito` vive en
# el modelo de tareas: una regla que hay que aplicar en uno de cinco sitios no es
# una regla, es una costumbre — y el sexto camino nace sin ella.
#
# Es `after_insert` y no `before_insert` porque hace falta el `id` del usuario, que
# la base asigna al insertar. Se escribe por la conexión del propio `flush` en vez
# de añadir un objeto a la sesión: añadir durante un `flush` reentra en el flush.


def _sembrar_membresia_de_origen(
    _mapper: object, conexion: sa.Connection, usuario: User
) -> None:
    """Da al usuario nuevo la membresía de su inquilino de origen.

    Un usuario **sin** `tenant_id` no gana ninguna: es el superadministrador, cuyo
    acceso viene de `join-as-admin` (FC-4) y no de una membresía. Inventarle una
    lo ataría a un inquilino que no es suyo.
    """
    if not usuario.tenant_id:
        return
    ahora = datetime.now(UTC)
    conexion.execute(
        sa.text(
            "INSERT INTO user_tenant_memberships "
            "(id, user_id, tenant_id, created_at, updated_at) "
            "VALUES (:id, :u, :t, :c, :c)"
        ),
        {
            "id": str(uuid4()),
            "u": str(usuario.id),
            "t": str(usuario.tenant_id),
            "c": ahora,
        },
    )


sa.event.listen(User, "after_insert", _sembrar_membresia_de_origen)
