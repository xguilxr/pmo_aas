"""US-216 — Importación masiva de proyectos y recursos.

Del artboard «Onboarding masivo — Importación» y del bloque B5: «cubre la carga
inicial de 23 proyectos sin captura manual». Un cliente que llega con una cartera
hecha no la va a teclear proyecto por proyecto, y si tiene que hacerlo, no llega.

Lo que estos tests cuidan:

1. **Una fila mala no tumba el archivo.** 23 proyectos con un error en el 7 tienen
   22 filas buenas; abortar entero obliga a arreglar y resubir a ciegas.
2. **Una duplicada se salta y NO se actualiza.** Es la decisión con más
   consecuencias: actualizar en silencio pisaría lo que alguien editó a mano
   después de la primera corrida.
3. **Los duplicados dentro del mismo archivo cuentan igual.** Un Excel con la
   misma fila dos veces crearía dos proyectos, y es el mismo problema una línea
   antes.
4. **El preview no escribe.** Es lo que hace segura la operación menos reversible
   del producto.
5. **Los tres números van juntos.** «18 creados» sin decir que 5 quedaron fuera es
   mentir por omisión.
"""
import io
import time

import pytest

from app.dominio.importacion import (
    COLUMNAS_DE_PROYECTO,
    emparejar_columnas,
    marcar_duplicadas,
    normalizar,
    resumen,
    validar_fila,
)
from app.services import import_job_store
from tests.factories import create_admin_role, create_tenant, create_user, login


class _FakeRedis:
    """Mismo stub que `test_us070_import_wizard.py`: el store es el mismo."""

    def __init__(self):
        self._store: dict[str, tuple[str, float]] = {}

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        self._store[key] = (value, time.monotonic() + ex if ex else float("inf"))

    def get(self, key: str) -> str | None:
        row = self._store.get(key)
        if row is None:
            return None
        value, expiry = row
        if time.monotonic() > expiry:
            del self._store[key]
            return None
        return value

    def delete(self, key: str) -> int:
        return int(bool(self._store.pop(key, None)))


@pytest.fixture(autouse=True)
def _stub_redis(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(import_job_store, "_get_client", lambda: fake)
    yield fake


# ---------------------------------------------------------------------------
# TC-216.1 — La regla, sin base de datos (MCS DEV-02)
# ---------------------------------------------------------------------------


def test_normalizar_iguala_lo_que_una_persona_llamaria_igual():
    """«Migración ERP» y «migracion erp  » son el mismo proyecto escrito por dos
    personas. Tratarlos como distintos duplica media cartera."""
    assert normalizar("Migración ERP") == normalizar("migracion erp  ")
    assert normalizar("  Dos   espacios ") == "dos espacios"
    assert normalizar(None) == ""


def test_los_encabezados_se_emparejan_por_alias():
    """Sin alias, la primera pantalla es un mapeo manual de doce columnas, y ahí
    es donde se abandona."""
    mapeo = emparejar_columnas(
        ["Nombre", "Tipo", "prioridad", "Cartera", "Columna rara"], "projects"
    )
    assert mapeo["name"] == "Nombre"
    assert mapeo["type"] == "Tipo"
    assert mapeo["priority"] == "prioridad"
    assert mapeo["portfolio"] == "Cartera"
    # Lo que no reconoce queda en None para que una persona lo mapee: fallar a la
    # columna parecida sería peor que no emparejar.
    assert mapeo["sponsor"] is None


def test_una_fila_completa_es_valida():
    f = validar_fila(
        2,
        {
            "name": "ERP",
            "type": "Transformación",
            "priority": "3",
            "portfolio": "Core",
            "start_date": "2026-09-01",
            "end_date": "2026-12-31",
        },
        "projects",
    )
    assert f.estado == "valida"
    # El vocabulario se compara normalizado: quien exporta de otra herramienta
    # escribe «Transformación» y el dominio dice «transformacion».
    assert f.valores["type"] == "transformacion"
    assert f.valores["priority"] == 3


def test_falta_una_obligatoria_y_el_mensaje_dice_cual():
    f = validar_fila(5, {"name": "ERP", "priority": "3"}, "projects")
    assert f.estado == "invalida"
    columnas = {p.columna for p in f.problemas}
    assert "type" in columnas and "portfolio" in columnas
    assert any("obligatoria" in p.mensaje for p in f.problemas)


def test_un_valor_fuera_del_vocabulario_se_rechaza_nombrando_los_admitidos():
    f = validar_fila(
        3,
        {"name": "X", "type": "invento", "priority": "3", "portfolio": "C"},
        "projects",
    )
    assert f.estado == "invalida"
    problema = next(p for p in f.problemas if p.columna == "type")
    assert "transformacion" in problema.mensaje


def test_el_fin_antes_del_inicio_se_rechaza():
    f = validar_fila(
        4,
        {
            "name": "X",
            "type": "operacion",
            "priority": "1",
            "portfolio": "C",
            "start_date": "2026-12-31",
            "end_date": "2026-01-01",
        },
        "projects",
    )
    assert f.estado == "invalida"
    assert any(p.columna == "end_date" for p in f.problemas)


def test_la_prioridad_va_de_uno_a_cinco():
    f = validar_fila(
        4, {"name": "X", "type": "bau", "priority": "9", "portfolio": "C"}, "projects"
    )
    assert f.estado == "invalida"
    assert any(p.columna == "priority" for p in f.problemas)


def test_una_tarifa_sin_unidad_avisa_pero_no_invalida_la_persona():
    """La persona sí se puede crear; lo que no se puede es calcular su costo
    (US-215). Rechazar la fila entera perdería el recurso por un dato opcional."""
    f = validar_fila(2, {"name": "Ana", "fte_cost_rate": "1200"}, "resources")
    assert f.estado == "valida"
    assert any(p.columna == "cost_rate_period" for p in f.problemas)


def test_una_duplicada_del_catalogo_se_marca_y_dice_con_que_choca():
    filas = [
        validar_fila(
            2, {"name": "ERP", "type": "bau", "priority": "1", "portfolio": "C"}, "projects"
        )
    ]
    marcar_duplicadas(filas, {normalizar("erp"): "ERP (existente)"}, "projects")
    assert filas[0].estado == "duplicada"
    assert filas[0].choca_con == "ERP (existente)"


def test_dos_filas_iguales_en_el_mismo_archivo_tambien_son_duplicado():
    """Un Excel con la misma fila dos veces crearía dos proyectos: es el mismo
    problema una línea antes."""
    filas = [
        validar_fila(
            n, {"name": "ERP", "type": "bau", "priority": "1", "portfolio": "C"}, "projects"
        )
        for n in (2, 3)
    ]
    marcar_duplicadas(filas, {}, "projects")
    # La primera entra y la segunda se salta, no al revés: quien lee el reporte
    # espera que la de arriba sea la que pasó.
    assert filas[0].estado == "valida"
    assert filas[1].estado == "duplicada"
    assert "fila 2" in (filas[1].choca_con or "")


def test_una_fila_invalida_no_se_marca_ademas_como_duplicada():
    """Marcar «duplicada» una fila a la que además le falta el nombre esconde el
    error que hay que arreglar primero."""
    filas = [validar_fila(2, {"priority": "1"}, "projects")]
    marcar_duplicadas(filas, {"": "algo"}, "projects")
    assert filas[0].estado == "invalida"


def test_el_resumen_cuenta_los_tres_estados():
    filas = [
        validar_fila(2, {"name": "A", "type": "bau", "priority": "1", "portfolio": "C"}, "projects"),
        validar_fila(3, {"name": "B"}, "projects"),
    ]
    marcar_duplicadas(filas, {}, "projects")
    r = resumen(filas)
    assert r == {"total": 2, "valid": 1, "invalid": 1, "duplicate": 0}


def test_las_obligatorias_son_la_plantilla_pequena():
    """El artboard pide «plantilla simplificada según tamaño». Es esta misma lista
    filtrada, no otra plantilla — así no puede desincronizarse de la grande."""
    obligatorias = [c.clave for c in COLUMNAS_DE_PROYECTO if c.obligatoria]
    assert obligatorias == ["name", "type", "priority", "portfolio"]
    # Y toda columna, obligatoria u opcional, explica para qué sirve.
    for c in COLUMNAS_DE_PROYECTO:
        assert len(c.ayuda) > 20, c.clave


# ---------------------------------------------------------------------------
# TC-216.2 — Contra la API
# ---------------------------------------------------------------------------


def _csv(lineas: list[str]) -> tuple[str, io.BytesIO, str]:
    contenido = "\n".join(lineas).encode("utf-8")
    return ("carga.csv", io.BytesIO(contenido), "text/csv")


async def _escenario(client, db_session):
    t = await create_tenant(db_session)
    admin_role = await create_admin_role(db_session, t)
    await create_user(
        db_session,
        tenant=t,
        username="admin",
        email="admin@acme.example.com",
        password="Str0ng-Admin-1!",
        roles=[admin_role],
    )
    auth = await login(client, "admin", "Str0ng-Admin-1!")
    h = auth["_authz"]
    org = (
        await client.post("/api/v1/organizations", json={"name": "OrgA"}, headers=h)
    ).json()["id"]

    async def preview(lineas, kind="projects"):
        return await client.post(
            "/api/v1/imports/preview",
            data={"kind": kind, "organization_id": org},
            files={"file": _csv(lineas)},
            headers=h,
        )

    return {"h": h, "org": org, "preview": preview}


@pytest.mark.asyncio
async def test_las_columnas_esperadas_se_sirven_desde_el_backend(client, db_session):
    """El vocabulario cerrado vive en el dominio: dos listas separadas divergen en
    cuanto se añade un tipo de proyecto."""
    e = await _escenario(client, db_session)
    r = await client.get("/api/v1/imports/columns?kind=projects", headers=e["h"])
    assert r.status_code == 200, r.text
    claves = {c["key"] for c in r.json()["columns"]}
    assert {"name", "type", "priority", "portfolio"} <= claves
    tipo = next(c for c in r.json()["columns"] if c["key"] == "type")
    assert "transformacion" in tipo["values"]


@pytest.mark.asyncio
async def test_una_clase_que_no_existe_se_rechaza_nombrando_las_que_si(
    client, db_session
):
    e = await _escenario(client, db_session)
    r = await client.get("/api/v1/imports/columns?kind=planes", headers=e["h"])
    assert r.status_code == 422, r.text
    assert "proyectos y recursos" in r.text


@pytest.mark.asyncio
async def test_el_preview_valida_todo_y_no_escribe(client, db_session):
    """Una fila mala no tumba el archivo: 23 proyectos con un error en el 7
    tienen 22 filas buenas."""
    e = await _escenario(client, db_session)
    r = await e["preview"](
        [
            "Nombre,Tipo,Prioridad,Portafolio",
            "ERP,transformacion,3,Core",
            "Sin tipo,,2,Core",
            "CRM,operacion,1,Core",
        ]
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["summary"] == {"total": 3, "valid": 2, "invalid": 1, "duplicate": 0}
    mala = next(f for f in d["rows"] if f["state"] == "invalida")
    # El número es la línea real del archivo: encabezado = 1, ERP = 2, esta = 3.
    # Es lo único que hace útil el número — «revisa la fila 3» tiene que apuntar
    # a la fila 3 del Excel.
    assert mala["row"] == 3
    assert any(p["column"] == "type" for p in mala["problems"])

    # El preview no escribe: sigue sin haber proyectos.
    listado = (await client.get("/api/v1/projects", headers=e["h"])).json()
    filas = listado["items"] if isinstance(listado, dict) else listado
    assert filas == [] or len(filas) == 0


@pytest.mark.asyncio
async def test_confirmar_crea_solo_las_validas(client, db_session):
    e = await _escenario(client, db_session)
    d = (
        await e["preview"](
            [
                "Nombre,Tipo,Prioridad,Portafolio,Programa",
                "ERP,transformacion,3,Core,Finanzas",
                "Sin tipo,,2,Core,",
                "CRM,operacion,1,Core,",
            ]
        )
    ).json()

    r = await client.post(
        f"/api/v1/imports/{d['job_id']}/confirm", headers=e["h"]
    )
    assert r.status_code == 201, r.text
    res = r.json()
    assert res["created_count"] == 2
    # Los tres números van juntos: «2 creados» sin decir que 1 quedó fuera es
    # mentir por omisión.
    assert res["skipped_invalid"] == 1
    assert res["skipped_duplicate"] == 0
    assert {c["name"] for c in res["created"]} == {"ERP", "CRM"}
    # El folio lo genera la plataforma; el archivo no lo trae.
    assert all(c["folio"].startswith("PRJ") for c in res["created"])

    # El portafolio y el programa se crearon con el nombre que traía la fila: un
    # Excel heredado trae los nombres que el cliente usa, no identificadores de
    # esta plataforma, y exigir que existan antes convertiría la importación en
    # dos pasos de los que el primero se hace a ciegas.
    carteras = (
        await client.get(
            f"/api/v1/organizations/{e['org']}/portfolios", headers=e["h"]
        )
    ).json()
    assert "Core" in [c["name"] for c in carteras]
    programas = (await client.get("/api/v1/programs", headers=e["h"])).json()
    assert "Finanzas" in [
        p["name"] for p in (programas if isinstance(programas, list) else programas["items"])
    ]


@pytest.mark.asyncio
async def test_correr_la_importacion_dos_veces_no_duplica_la_cartera(
    client, db_session
):
    """La decisión con más consecuencias de esta US. Una importación se corre dos
    veces —se cayó la red, alguien la repitió— y duplicar convertiría 23
    proyectos en 46 sin forma barata de deshacerlo."""
    e = await _escenario(client, db_session)
    lineas = [
        "Nombre,Tipo,Prioridad,Portafolio",
        "ERP,transformacion,3,Core",
        "CRM,operacion,1,Core",
    ]
    primero = (await e["preview"](lineas)).json()
    r1 = await client.post(
        f"/api/v1/imports/{primero['job_id']}/confirm", headers=e["h"]
    )
    assert r1.json()["created_count"] == 2

    segundo = (await e["preview"](lineas)).json()
    assert segundo["summary"]["duplicate"] == 2
    assert segundo["summary"]["valid"] == 0
    fila = segundo["rows"][0]
    assert fila["state"] == "duplicada"
    assert fila["conflicts_with"]

    r2 = await client.post(
        f"/api/v1/imports/{segundo['job_id']}/confirm", headers=e["h"]
    )
    assert r2.json() == {
        "created": [],
        "created_count": 0,
        "skipped_invalid": 0,
        "skipped_duplicate": 2,
    }


@pytest.mark.asyncio
async def test_una_duplicada_no_se_actualiza(client, db_session):
    """El caso concreto: se importa, el PM corrige las fechas en la aplicación,
    alguien resube el Excel original. Las fechas NO vuelven atrás."""
    e = await _escenario(client, db_session)
    d = (
        await e["preview"](
            [
                "Nombre,Tipo,Prioridad,Portafolio,Fecha inicio",
                "ERP,transformacion,3,Core,2026-01-01",
            ]
        )
    ).json()
    creado = (
        await client.post(f"/api/v1/imports/{d['job_id']}/confirm", headers=e["h"])
    ).json()["created"][0]["id"]

    # Alguien corrige a mano.
    assert (
        await client.patch(
            f"/api/v1/projects/{creado}",
            json={"start_date": "2026-06-15"},
            headers=e["h"],
        )
    ).status_code == 200

    # Se resube el archivo original.
    otra = (
        await e["preview"](
            [
                "Nombre,Tipo,Prioridad,Portafolio,Fecha inicio",
                "ERP,transformacion,3,Core,2026-01-01",
            ]
        )
    ).json()
    await client.post(f"/api/v1/imports/{otra['job_id']}/confirm", headers=e["h"])

    proyecto = (
        await client.get(f"/api/v1/projects/{creado}", headers=e["h"])
    ).json()
    assert proyecto["start_date"] == "2026-06-15"


@pytest.mark.asyncio
async def test_sin_las_columnas_obligatorias_el_error_es_del_archivo(
    client, db_session
):
    """Decirlo así evita un reporte de 23 filas inválidas por la misma causa."""
    e = await _escenario(client, db_session)
    r = await e["preview"](["Nombre,Sponsor", "ERP,Ana"])
    assert r.status_code == 422, r.text
    assert "Tipo" in r.text and "Prioridad" in r.text


@pytest.mark.asyncio
async def test_importar_recursos_con_tarifa_y_unidad(client, db_session):
    e = await _escenario(client, db_session)
    d = (
        await e["preview"](
            [
                "Nombre,Correo,Empresa,Tarifa,Unidad tarifa",
                "Ana Ruiz,ana@acme.example.com,Acme,2100,mes",
                "Sin correo,,Acme,,",
            ],
            kind="resources",
        )
    ).json()
    assert d["summary"]["valid"] == 2
    r = await client.post(
        f"/api/v1/imports/{d['job_id']}/confirm", headers=e["h"]
    )
    assert r.status_code == 201, r.text
    assert r.json()["created_count"] == 2

    actores = (await client.get("/api/v1/actors", headers=e["h"])).json()
    filas = actores if isinstance(actores, list) else actores["items"]
    ana = next(a for a in filas if a["name"] == "Ana Ruiz")
    assert ana["fte_cost_rate"] == 2100.0
    assert ana["cost_rate_period"] == "mes"


@pytest.mark.asyncio
async def test_un_job_de_otro_inquilino_no_se_puede_confirmar(client, db_session):
    """Un `job_id` es un UUID, no un secreto: sin la comprobación de inquilino,
    quien lo adivinara escribiría en otro."""
    e = await _escenario(client, db_session)
    d = (
        await e["preview"](
            ["Nombre,Tipo,Prioridad,Portafolio", "ERP,transformacion,3,Core"]
        )
    ).json()

    otro = await create_tenant(db_session, name="Otro", slug="otro-216")
    rol = await create_admin_role(db_session, otro)
    await create_user(
        db_session,
        tenant=otro,
        username="ajeno",
        email="ajeno@otro.example.com",
        password="Str0ng-Ajeno-1!",
        roles=[rol],
    )
    ajeno = (await login(client, "ajeno", "Str0ng-Ajeno-1!"))["_authz"]
    r = await client.post(f"/api/v1/imports/{d['job_id']}/confirm", headers=ajeno)
    assert r.status_code == 404, r.text


@pytest.mark.asyncio
async def test_confirmar_dos_veces_el_mismo_job_no_duplica(client, db_session):
    """El preview se borra al confirmar: sin eso, confirmar dos veces daría el
    doble de proyectos, y es el error que la detección de duplicados no puede
    atrapar dentro de la misma transacción."""
    e = await _escenario(client, db_session)
    d = (
        await e["preview"](
            ["Nombre,Tipo,Prioridad,Portafolio", "ERP,transformacion,3,Core"]
        )
    ).json()
    assert (
        await client.post(f"/api/v1/imports/{d['job_id']}/confirm", headers=e["h"])
    ).status_code == 201
    segunda = await client.post(
        f"/api/v1/imports/{d['job_id']}/confirm", headers=e["h"]
    )
    assert segunda.status_code == 404, segunda.text


@pytest.mark.asyncio
async def test_un_archivo_vacio_lo_dice(client, db_session):
    e = await _escenario(client, db_session)
    r = await client.post(
        "/api/v1/imports/preview",
        data={"kind": "projects", "organization_id": e["org"]},
        files={"file": ("vacio.csv", io.BytesIO(b""), "text/csv")},
        headers=e["h"],
    )
    assert r.status_code in (422, 400), r.text


@pytest.mark.asyncio
async def test_un_formato_no_soportado_apunta_al_importador_correcto(
    client, db_session
):
    e = await _escenario(client, db_session)
    r = await client.post(
        "/api/v1/imports/preview",
        data={"kind": "projects", "organization_id": e["org"]},
        files={"file": ("plan.mpp", io.BytesIO(b"x"), "application/vnd.ms-project")},
        headers=e["h"],
    )
    assert r.status_code == 415, r.text
    assert "plan" in r.text.lower()
