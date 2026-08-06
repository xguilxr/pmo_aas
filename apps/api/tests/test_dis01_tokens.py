"""DIS-01 y CFG-14 — los valores visuales van a tokens, y un token citado existe.

La auditoría contó **25 literales `#rrggbb`** en `apps/web/components` y
`apps/web/app`; `CFG-14` repitió la cifra. `globals.css` ya centralizaba la
paleta — lo que faltaba era que nada impidiera escribir el color al lado.

Lo interesante apareció al enchufar el gate. Los literales sueltos eran los
menos: **once citas a tokens que no existen**, la mayoría con respaldo, o sea
invisibles. La página de documentos del proyecto llevaba meses pintando ámbar y
rojo de tema claro en modo oscuro porque citaba `--color-warning-soft` y
`--color-danger-soft`, que nunca se declararon. `--color-bg` y `--color-border`,
sin respaldo, hacían que la tabla de permisos se renderizara sin fondo ni borde.

Por eso `var(--token, respaldo)` se prohíbe además del literal: el respaldo es
lo que convierte un token roto en un fallo que nadie ve.

Esta suite prueba el verificador con entradas sintéticas —el gate real corre en
CI sobre el árbol entero— más un caso sobre el árbol de verdad, porque el
verificador puede ser correcto y estar apuntando a un directorio que se movió.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[3]

sys.path.insert(0, str(RAIZ / "scripts"))
from check_tokens import (  # noqa: E402
    AMBITOS,
    FRONTERAS,
    GLOBALS_CSS,
    revisar,
    tokens_definidos,
)

DEFINIDOS = {"--color-danger-bg", "--color-danger-fg", "--spacing"}


@pytest.mark.parametrize(
    ("fragmento", "esperado"),
    [
        ('className="bg-[#fee2e2]"', "color literal"),
        ('className="text-[#f00]"', "color literal"),
        ("const c = '#1F1D17';", "color literal"),
        ('className="px-[18px]"', "espaciado literal"),
        ('className="gap-[6px]"', "espaciado literal"),
    ],
)
def test_rechaza_el_valor_escrito_a_mano(fragmento: str, esperado: str) -> None:
    motivos = revisar("components/x.tsx", fragmento, DEFINIDOS)
    assert any(esperado in m for m in motivos), motivos


def test_rechaza_citar_un_token_que_no_existe() -> None:
    """El hallazgo que justifica el gate entero.

    Sin respaldo el navegador descarta la declaración y el elemento sale sin
    fondo; con respaldo sale bien y el token está muerto igual. Las dos formas
    son fallos, y la segunda es peor porque no se ve.
    """
    motivos = revisar("components/x.tsx", "bg-[var(--color-inventado)]", DEFINIDOS)
    assert any("no está definido" in m and "se descarta" in m for m in motivos), motivos

    # El respaldo trae además su propio literal, así que salen dos motivos: el
    # que importa aquí es el del token, no el del `#fee`.
    motivos = revisar("components/x.tsx", "bg-[var(--color-inventado,#fee)]", DEFINIDOS)
    assert any("no está definido" in m and "el respaldo" in m for m in motivos), motivos


def test_rechaza_el_respaldo_aunque_el_token_exista() -> None:
    """El respaldo tapa el fallo el día que el token se renombre.

    Es exactamente cómo `--info-fg` sobrevivió a un renombrado a
    `--color-info-fg`: tres componentes lo citaban con respaldo y se veían bien.
    """
    motivos = revisar("components/x.tsx", "text-[var(--color-danger-fg,#991b1b)]", DEFINIDOS)
    assert any("lleva respaldo" in m for m in motivos), motivos


def test_acepta_la_cita_limpia() -> None:
    assert revisar("components/x.tsx", 'className="bg-[var(--color-danger-bg)] px-4.5"', DEFINIDOS) == []


def test_no_confunde_un_comentario_con_una_infraccion() -> None:
    """Un comentario que explica por qué NO se usa un token no es un literal.

    Contarlo como tal empuja a no documentar, que es el peor incentivo posible
    en un control cuyo valor está en que se entienda.
    """
    assert revisar("components/x.tsx", "// nada de #fee2e2 ni de var(--inventado)\n", DEFINIDOS) == []
    assert revisar("components/x.tsx", "/* usa var(--token) del anfitrión */\n", DEFINIDOS) == []


def test_las_fronteras_llevan_razon_escrita() -> None:
    """Una excepción sin motivo es una excepción que crece.

    Es el mismo trato que `.pip-audit-ignore`: cada entrada con su porqué.
    """
    assert FRONTERAS, "Sin fronteras declaradas el diccionario sobra; con ellas, van con razón."
    for ruta, razon in FRONTERAS.items():
        assert (RAIZ / "apps" / "web" / ruta).is_file(), f"Frontera sobre un archivo que no existe: {ruta}"
        assert len(razon) > 40, f"La razón de `{ruta}` no explica nada: {razon!r}"


def test_el_ambito_cubre_mas_que_components() -> None:
    """Si solo se mirara `components/`, mover el literal un directorio lo
    borraría del radar sin quitarlo del producto.
    """
    assert {"components", "app", "lib", "hooks"} <= set(AMBITOS)


def test_el_arbol_real_no_tiene_literales() -> None:
    """El verificador puede ser correcto y apuntar a un directorio que se movió.

    Este caso mira el árbol de verdad: si `AMBITOS` deja de resolver, aquí no
    se revisa ningún archivo y el conteo lo delata.
    """
    definidos = tokens_definidos(GLOBALS_CSS.read_text(encoding="utf-8"))
    assert len(definidos) > 50, f"Solo {len(definidos)} tokens leídos de globals.css: ¿cambió el formato?"

    web = RAIZ / "apps" / "web"
    revisados, fallos = 0, []
    for ambito in AMBITOS:
        for patron in ("*.ts", "*.tsx"):
            for archivo in (web / ambito).rglob(patron):
                if "node_modules" in archivo.parts:
                    continue
                revisados += 1
                motivos = revisar(
                    archivo.relative_to(web).as_posix(),
                    archivo.read_text(encoding="utf-8"),
                    definidos,
                )
                if motivos:
                    fallos.append((archivo.relative_to(web).as_posix(), motivos))

    assert revisados > 100, f"Solo {revisados} archivos revisados: el ámbito dejó de resolver."
    assert not fallos, f"Valores visuales fuera del sistema: {fallos}"


# ---------------------------------------------------------------------------
# DAT-12 — la ausencia de dato se distingue del cero
# ---------------------------------------------------------------------------

def test_rechaza_pintar_un_cero_donde_no_hay_dato() -> None:
    """Un proyecto sin presupuesto cargado y uno con presupuesto cero son
    estados distintos y piden acciones distintas: al primero le falta un dato,
    el segundo está mal planificado. Con `?? 0` los dos salían «$0».
    """
    for fragmento in (
        "<KpiCard value={kpis?.budget_total ?? 0} />",
        "<RaidCard count={project.module_counts.risks ?? 0} />",
        "<p>{kpis.overdue ?? 0}</p>",
    ):
        motivos = revisar("components/x.tsx", fragmento, DEFINIDOS)
        assert any("DAT-12" in m for m in motivos), (fragmento, motivos)


def test_no_estorba_al_cero_de_calculo() -> None:
    """`map.get(k) ?? 0` al sumar es correcto y frecuente.

    La distinción entre calcular y pintar es lo que hace usable el control: sin
    ella salían 84 avisos y 67 eran legítimos, y un gate con 80% de ruido se
    desactiva la primera semana.
    """
    for fragmento in (
        "const count = map.get(`${p}:${im}`) ?? 0;",
        "const total = (src.risks?.length ?? 0) + (src.issues?.length ?? 0);",
        "if ((confidence[idx] ?? 0) < 0.7) return;",
    ):
        assert revisar("components/x.tsx", fragmento, DEFINIDOS) == [], fragmento


def test_el_hueco_tiene_etiqueta_accesible() -> None:
    """El guion largo lo lee un lector de pantalla como una pausa, o no lo lee.

    Sin la etiqueta, «Presupuesto —» suena a «Presupuesto» y el hueco
    desaparece justo para quien menos puede inferirlo del contexto visual.
    """
    kpi = (RAIZ / "apps" / "web" / "components" / "kpi-card.tsx").read_text(encoding="utf-8")
    # Que la etiqueta esté EN el `aria-label`, no solo en el archivo: la
    # primera versión comprobaba las dos cadenas por separado y sobrevivía a
    # vaciar el atributo, porque la constante seguía importada más arriba.
    assert re.search(r"aria-label=\{[^}]*SIN_DATO_ETIQUETA", kpi), (
        "El hueco del KPI perdió su etiqueta accesible: un lector de pantalla "
        "lee «Presupuesto» y el hueco desaparece."
    )


def test_la_convencion_del_hueco_esta_declarada() -> None:
    """El guion largo ya era la convención — en 43 archivos, para huecos de
    TEXTO. Lo que faltaba era aplicarla a los números.

    Ese es el hallazgo que reencuadra el requisito: no había que enseñarle al
    producto a decir «no hay dato», había que dejar de taparlo con un cero.
    Por eso esta prueba NO exige que los 43 importen la constante —migrarlos
    sería una campaña sin más valor que el que ya tienen—, sino que exista un
    solo sitio donde cambiar la convención y que las superficies numéricas
    convertidas lo usen.
    """
    modulo = RAIZ / "apps" / "web" / "lib" / "sin-dato.ts"
    assert modulo.is_file(), "Se fue `@/lib/sin-dato`, que es donde vive la convención."
    fuente = modulo.read_text(encoding="utf-8")
    assert 'SIN_DATO = "—"' in fuente

    for componente in ("components/kpi-card.tsx", "app/(app)/pmo/projects/[id]/page.tsx"):
        texto = (RAIZ / "apps" / "web" / componente).read_text(encoding="utf-8")
        assert "@/lib/sin-dato" in texto, (
            f"`{componente}` dejó de usar la convención central y volvió a "
            f"decidir por su cuenta qué se ve cuando no hay dato."
        )
