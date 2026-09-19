"""US-285 — los valores de catálogo que cada inquilino define por su cuenta.

## Qué guarda

Hoy, dos catálogos del proyecto: `tipo_proyecto` y `fase_proyecto`. Hasta
US-202 los dos eran un enum cerrado en `app/dominio/proyecto.py`, con cuatro
tipos y cinco fases iguales para todos.

## Por qué una tabla y no `tenants.settings`

`tenants.settings` es un JSON y ya guarda configuración del inquilino, así que
meter aquí una lista más parece lo barato. No lo es (DEC-040): un catálogo se
consulta por fila —«dame los tipos activos, en orden»—, se ordena, se
referencia desde `projects.type` y se audita cuando alguien lo cambia. Un JSON
no hace ninguna de las cuatro cosas sin código que lo emule.

## Por qué genérica y hasta dónde

`catalogo` es una columna y no dos tablas, para que un tercer catálogo no
obligue a una migración nueva. Eso es **todo** lo que se generaliza: no hay
jerarquía de catálogos, ni tipos de valor, ni reglas declarativas. La
validación de cada catálogo vive en su servicio, donde se puede leer.

## `metadata` en la base, `datos` en Python

La columna se llama `metadata` —es el nombre del criterio de aceptación— pero
el atributo no puede llamarse así: `metadata` está tomado por SQLAlchemy en
toda clase declarativa y la definición fallaría al importar el módulo. Se mapea
con el nombre de columna explícito.

Lo que lleva depende del catálogo. `fase_proyecto` guarda ahí sus banderas
`activa` y `terminal` (US-287), que gobiernan KPIs y cortes; `tipo_proyecto`
hoy no guarda nada.
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid

#: Los catálogos que existen. Una clave que no esté aquí se rechaza en el
#: servicio: sin esta lista, un error de dedo crea un catálogo fantasma que
#: nadie lista y que nadie descubre hasta que falta un valor.
CATALOGO_TIPO_PROYECTO = "tipo_proyecto"
CATALOGO_FASE_PROYECTO = "fase_proyecto"

CATALOGOS: tuple[str, ...] = (CATALOGO_TIPO_PROYECTO, CATALOGO_FASE_PROYECTO)


class TenantCatalogValue(Base, TimestampMixin):
    __tablename__ = "tenant_catalog_values"
    __table_args__ = (
        # La clave es única **por inquilino y catálogo**: dos inquilinos pueden
        # llamar `mantenimiento` a cosas distintas, y eso está bien.
        UniqueConstraint(
            "tenant_id", "catalogo", "clave", name="uq_catalogo_valor_clave"
        ),
        Index("ix_tenant_catalog_values_tenant_catalogo", "tenant_id", "catalogo"),
    )

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    tenant_id: Mapped[UUID] = mapped_column(
        String(36),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    catalogo: Mapped[str] = mapped_column(String(32), nullable=False)
    #: Lo que se guarda en `projects.type` / `projects.phase`. No se edita
    #: nunca: renombrar una clave dejaría huérfano a todo lo que la referencia.
    #: Lo que se edita es la etiqueta.
    clave: Mapped[str] = mapped_column(String(64), nullable=False)
    #: Lo que se lee en pantalla.
    etiqueta: Mapped[str] = mapped_column(String(120), nullable=False)
    #: El orden importa: lo consumen los desplegables y los ejes de los
    #: gráficos por fase, que sin él salen alfabéticos. En `fase_proyecto` es
    #: además el ciclo de vida.
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    #: Desactivar y no borrar: un valor en uso no se puede quitar sin dejar
    #: proyectos apuntando a nada.
    activo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    datos: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSON, nullable=False, default=dict
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
