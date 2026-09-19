"""US-274 — trinquete del inventario de vaciado.

`app/services/vaciado.py` declara a mano qué tablas se vacían y cuáles
sobreviven. Escrito a mano se desactualiza, así que esto compara lo declarado
contra el metadata de SQLAlchemy: una tabla nueva rompe la suite hasta que
alguien decida por escrito de qué lado va.

Es el control que hace que el inventario declarado sea mejor que la reflexión y
no solo más largo. Sin él, las dos listas serían una copia que envejece.
"""
from __future__ import annotations

import pytest

import app.models  # noqa: F401  — registra todos los modelos en el metadata
from app.db.base import Base
from app.services.vaciado import (
    FKS_A_ANULAR,
    HIJAS_POR_PADRE,
    SOBREVIVEN,
    TABLAS_A_VACIAR,
)


def test_us274_toda_tabla_esta_clasificada():
    """Ninguna tabla queda sin decidir.

    Este es el criterio de aceptación literal: una tabla nueva con `tenant_id`
    que nadie sumó al inventario tiene que poner la suite roja, no pasar
    inadvertida hasta que un vaciado la deje con datos.
    """
    todas = set(Base.metadata.tables)
    clasificadas = set(TABLAS_A_VACIAR) | set(SOBREVIVEN)
    sin_clasificar = todas - clasificadas
    assert not sin_clasificar, (
        "Tablas sin decidir en app/services/vaciado.py: "
        f"{sorted(sin_clasificar)}. Agregá cada una a TABLAS_A_VACIAR (con su "
        "posición en el orden de borrado) o a SOBREVIVEN (con el motivo)."
    )
    inventadas = clasificadas - todas
    assert not inventadas, (
        f"El inventario nombra tablas que no existen: {sorted(inventadas)}."
    )


def test_us274_ninguna_tabla_esta_en_las_dos_listas():
    repetidas = set(TABLAS_A_VACIAR) & set(SOBREVIVEN)
    assert not repetidas, f"En las dos listas a la vez: {sorted(repetidas)}"


def test_us274_el_orden_no_repite_tablas():
    """Una tabla dos veces en el orden no rompe nada y esconde un error de edición."""
    assert len(TABLAS_A_VACIAR) == len(set(TABLAS_A_VACIAR))


def test_us274_toda_tabla_del_inventario_se_puede_alcanzar():
    """O tiene `tenant_id`, o declara por qué padre se llega a ella."""
    huerfanas = [
        t
        for t in TABLAS_A_VACIAR
        if "tenant_id" not in Base.metadata.tables[t].c and t not in HIJAS_POR_PADRE
    ]
    assert not huerfanas, (
        f"Sin `tenant_id` y sin padre declarado: {huerfanas}. Agregalas a "
        "HIJAS_POR_PADRE o el vaciado no sabe qué filas son de quién."
    )


def test_us274_los_padres_declarados_existen_y_se_vacian_despues():
    """Una hija se borra antes que su padre, o la clave foránea lo impide."""
    posicion = {t: i for i, t in enumerate(TABLAS_A_VACIAR)}
    for hija, pares in HIJAS_POR_PADRE.items():
        assert hija in posicion, f"{hija} declara padre pero no está en el orden"
        for columna, padre in pares:
            assert padre in Base.metadata.tables, f"{padre} no existe"
            assert columna in Base.metadata.tables[hija].c, (
                f"{hija}.{columna} no existe"
            )
            assert "tenant_id" in Base.metadata.tables[padre].c, (
                f"{padre} no tiene tenant_id: no sirve para alcanzar a {hija}"
            )
            if padre in posicion:
                assert posicion[hija] < posicion[padre], (
                    f"{hija} se borra después de {padre}"
                )


def test_us274_el_orden_respeta_las_claves_foraneas():
    """Cada tabla se borra antes que aquella a la que apunta.

    Menos las referencias de `FKS_A_ANULAR`, que el vaciado pone en nulo antes
    de empezar precisamente porque forman un ciclo que ningún orden resuelve.
    """
    posicion = {t: i for i, t in enumerate(TABLAS_A_VACIAR)}
    anuladas = set(FKS_A_ANULAR)
    violaciones = []
    for tabla in TABLAS_A_VACIAR:
        t = Base.metadata.tables[tabla]
        for columna in t.c:
            for fk in columna.foreign_keys:
                destino = fk.column.table.name
                if destino not in posicion or destino == tabla:
                    continue
                if (tabla, columna.name) in anuladas:
                    continue
                if posicion[tabla] > posicion[destino]:
                    violaciones.append(
                        f"{tabla}.{columna.name} -> {destino}: {tabla} se borra "
                        f"después de {destino}"
                    )
    assert not violaciones, "Orden de borrado inválido:\n  " + "\n  ".join(violaciones)


def test_us274_las_fks_a_anular_son_nulables():
    """Poner en nulo una columna obligatoria falla en la base, no aquí."""
    for tabla, columna in FKS_A_ANULAR:
        c = Base.metadata.tables[tabla].c[columna]
        assert c.nullable, f"{tabla}.{columna} no es nulable: no se puede anular"
        assert "tenant_id" in Base.metadata.tables[tabla].c, (
            f"{tabla} no tiene tenant_id: el UPDATE de anulado no sabría a "
            "quién acotarse y tocaría filas de otro inquilino"
        )


def test_us274_toda_tabla_con_tenant_id_se_vacia_o_dice_por_que_no():
    """El caso que importa: una tabla del inquilino que sobrevive sin motivo."""
    con_tenant = {
        t.name for t in Base.metadata.tables.values() if "tenant_id" in t.c
    }
    supervivientes = con_tenant & set(SOBREVIVEN)
    sin_motivo = [t for t in supervivientes if not SOBREVIVEN[t].strip()]
    assert not sin_motivo, (
        f"Sobreviven sin motivo escrito: {sin_motivo}. El motivo es parte del "
        "dato: sin él nadie sabe si está ahí por decisión o por descuido."
    )


def test_us274_audit_log_sobrevive_porque_no_se_puede_borrar():
    """AM-08 lo hace de solo anexado. Meterlo en el inventario rompería el vaciado.

    Se comprueba explícito porque es la exclusión que más se parece a un olvido:
    quien lea la lista y no lo encuentre va a querer «arreglarla».
    """
    assert "audit_log" not in TABLAS_A_VACIAR
    assert "AM-08" in SOBREVIVEN["audit_log"]


@pytest.mark.parametrize(
    "tabla", ["users", "user_tenant_memberships", "tenants"]
)
def test_us274_lo_que_dec045_conserva_no_esta_en_el_inventario(tabla: str):
    assert tabla not in TABLAS_A_VACIAR
    assert tabla in SOBREVIVEN
