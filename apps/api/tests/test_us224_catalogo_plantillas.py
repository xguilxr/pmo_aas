"""US-224 (EP021) — el catálogo de plantillas es de solo lectura y con contrato.

EP021 dejó cuatro decisiones escritas el 2026-08-20. Tres de ellas se pueden
romper sin que nada se ponga rojo, y son las que este archivo defiende:

- **(1) el prompt no es editable por el inquilino.** Si algún día la API
  devuelve el texto del prompt, la siguiente petición es «déjenme cambiar esta
  línea» — que es la opción (a) descartada, la que deja a `evaluacion-ia`
  midiendo unos prompts mientras corren otros.
- **(2) ninguna plantilla escribe.** Una plantilla que escriba convierte AM-03
  —instrucciones inyectadas en contenido subido— en una escritura.
- **el contrato de salida lo fija el producto.** Media respuesta se pinta en la
  pantalla como si estuviera completa, y el hueco lo descubre quien firma el
  documento.

Lo demás —que cada plantilla declare categoría, modo y contrato— son las
invariantes que hacen que el catálogo se pueda recorrer sin abrirlo.
"""

from __future__ import annotations

import pytest

from app.services.ai import catalogo


def test_hay_catalogo() -> None:
    assert len(catalogo.CATALOGO) >= 10


@pytest.mark.parametrize("plantilla", list(catalogo.CATALOGO.values()), ids=lambda p: p.id)
def test_cada_plantilla_declara_su_contrato(plantilla: catalogo.Plantilla) -> None:
    assert plantilla.id and plantilla.id == plantilla.id.lower()
    assert plantilla.nombre.strip()
    assert plantilla.proposito.strip()
    assert plantilla.categoria in catalogo.CATEGORIAS
    assert plantilla.modo_minimo in (catalogo.MODO_PLATAFORMA, catalogo.MODO_BYO)
    assert plantilla.claves_salida, "sin contrato de salida no se puede consumir"
    assert plantilla.version >= 1


@pytest.mark.parametrize("plantilla", list(catalogo.CATALOGO.values()), ids=lambda p: p.id)
def test_el_prompt_declara_las_claves_que_promete(
    plantilla: catalogo.Plantilla,
) -> None:
    """El contrato y el prompt no pueden divergir: es el fallo que nadie ve.

    `claves_salida` es lo que el producto lee; el prompt es lo que el modelo
    obedece. Si alguien añade una clave a una y no a la otra, la plantilla
    empieza a fallar con `AI_CONTRATO_INCUMPLIDO` en producción y en ningún
    sitio se ve por qué.
    """
    for clave in plantilla.claves_salida:
        assert f'"{clave}"' in plantilla.sistema, (
            f"{plantilla.id}: la clave «{clave}» está en el contrato pero el "
            "prompt no la pide"
        )


@pytest.mark.parametrize("plantilla", list(catalogo.CATALOGO.values()), ids=lambda p: p.id)
def test_el_prompt_exige_json_y_prohibe_inventar(
    plantilla: catalogo.Plantilla,
) -> None:
    assert "JSON" in plantilla.sistema
    assert "No inventas datos" in plantilla.sistema


@pytest.mark.parametrize("plantilla", list(catalogo.CATALOGO.values()), ids=lambda p: p.id)
def test_ninguna_plantilla_pide_escribir(plantilla: catalogo.Plantilla) -> None:
    """EP021 pregunta 2: las herramientas del catálogo solo leen.

    Se comprueba sobre el texto del prompt porque es donde alguien lo
    intentaría primero — «guarda el riesgo en el proyecto» es una línea, y el
    esquema de la respuesta no la delataría.
    """
    prohibidas = (
        "guarda en la base",
        "crea el registro",
        "actualiza el proyecto",
        "inserta en la tabla",
        "borra ",
    )
    bajo = plantilla.sistema.lower()
    encontradas = [f for f in prohibidas if f in bajo]
    assert not encontradas, (
        f"{plantilla.id} parece pedir una escritura: {encontradas}. "
        "El catálogo solo lee (EP021 P2)."
    )


def test_la_vista_publica_no_expone_el_prompt() -> None:
    """La decisión (a) se descartó; mostrar el prompt es el primer paso hacia ella."""
    for plantilla in catalogo.CATALOGO.values():
        publica = catalogo.plantilla_publica(plantilla)
        assert "sistema" not in publica
        assert plantilla.sistema not in str(publica)


def test_platform_no_ve_las_que_exigen_byo() -> None:
    """Ofrecer lo que va a dar 409 al pulsar convierte un límite en un ticket."""
    solo_plataforma = catalogo.listar(modo_tenant=catalogo.MODO_PLATAFORMA)
    assert solo_plataforma, "en modo plataforma debe quedar algo utilizable"
    assert all(p.modo_minimo == catalogo.MODO_PLATAFORMA for p in solo_plataforma)

    todas = catalogo.listar(modo_tenant=catalogo.MODO_BYO)
    assert len(todas) == len(catalogo.CATALOGO)
    assert len(todas) > len(solo_plataforma), (
        "si nada exige BYOK, el filtro no está defendiendo nada"
    )


def test_disabled_no_ve_nada() -> None:
    assert catalogo.listar(modo_tenant="disabled") == []


def test_validar_entradas_detecta_lo_que_falta_y_lo_vacio() -> None:
    p = catalogo.obtener("redaccion-de-cambio")
    assert p is not None
    assert catalogo.validar_entradas(p, {}) == list(p.entradas)
    # Una cadena vacía es tan inservible como la ausencia, y llega mucho más a
    # menudo: es lo que manda un formulario con el campo sin llenar.
    assert "descripcion_libre" in catalogo.validar_entradas(
        p, {"descripcion_libre": "", "proyecto": {"id": "x"}}
    )
    assert catalogo.validar_entradas(
        p, {"descripcion_libre": "mover la fecha", "proyecto": {"id": "x"}}
    ) == []


def test_validar_salida_detecta_media_respuesta() -> None:
    p = catalogo.obtener("explicacion-de-salud")
    assert p is not None
    assert catalogo.validar_salida(p, None) == list(p.claves_salida)
    assert catalogo.validar_salida(p, {"veredicto": "rojo"}) == [
        "causas",
        "acciones_sugeridas",
    ]
    completa = dict.fromkeys(p.claves_salida, "x")
    assert catalogo.validar_salida(p, completa) == []


def test_una_clave_extra_no_rompe_el_contrato() -> None:
    """El contrato dice qué se lee, no qué está prohibido traer."""
    p = catalogo.obtener("resumen-de-cartera")
    assert p is not None
    salida = dict.fromkeys(p.claves_salida, "x") | {"comentario_del_modelo": "hola"}
    assert catalogo.validar_salida(p, salida) == []


def test_no_hay_ruta_de_escritura_del_catalogo() -> None:
    """El catálogo se cambia por PR, no por API (política de prompts-catalog.md)."""
    from app.api.v1.endpoints import ai_plantillas

    metodos = {
        metodo
        for ruta in ai_plantillas.router.routes
        for metodo in getattr(ruta, "methods", set())
    }
    assert metodos <= {"GET", "POST"}, metodos
    caminos = {getattr(r, "path", "") for r in ai_plantillas.router.routes}
    # El único POST es ejecutar; no hay alta, edición ni borrado.
    assert not any(
        c.endswith("/plantillas") and "POST" in getattr(r, "methods", set())
        for r in ai_plantillas.router.routes
        for c in [getattr(r, "path", "")]
    )
    assert any("ejecutar" in c for c in caminos)
