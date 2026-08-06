"""Deriva el registro de conformidad MCS desde los informes fechados.

`MCS-CORE` —el catálogo de los 126 requisitos— **llegó al repositorio el
2026-08-05** y vive en `docs/conformidad/marco/MCS-CORE.md`. Este derivador se
escribió antes, cuando no estaba, reconstruyendo el estado desde los informes;
por eso sigue leyéndolos y no al catálogo. Se mantiene así a propósito: los
informes son los que traen el **estado medido**, y el catálogo trae el texto
normativo, que es otra cosa. Las fuentes son:

- `2026-08-03-mcs.md` — tabla detallada, 117 filas `ID · Estado · Evidencia ·
  Gravedad`, más el §5 que enumera los bloqueantes de N1 uno a uno.
- `2026-08-04-mcs.md` — seguimiento, con columna de NIVEL (la única fuente de
  N1/N2 que existe fuera del §5).
- `2026-08-04-mcs-r1.md` — los 13 que estaban NO VERIFICABLE, ya medidos.
- Los cierres posteriores, que se listan abajo con su fuente documental.

**Se guarda el derivador y no su salida** (MCA CTX-03). Un registro almacenado
envejece en cuanto alguien cierra un requisito y se olvida de tocarlo — que es
exactamente el fallo que este archivo existe para no repetir: el ledger daba
`OPS-02` por casi cerrado y estaba a medias, y daba `ARQ-02` por abierto cuando
ya había 24 ADR.

Uso:

    python scripts/registro_conformidad.py            # resumen
    python scripts/registro_conformidad.py --tabla    # tabla markdown de lo abierto

Los cierres de `CIERRES` son la parte que hay que mantener a mano: cada vez que
un requisito cierre, se añade su fila con la fuente. Es una línea por cierre, y
es el precio de no tener el catálogo.
"""

import re, json, pathlib

D = pathlib.Path(__file__).resolve().parents[1] / "docs" / "conformidad"
FILA = re.compile(r"^\|\s*\*{0,2}([A-Z]{2,3}-\d{2})\*{0,2}\s*\|(.+)$")

def limpiar(x): return re.sub(r"\*+", "", x).strip()

def parsear(ruta, cols_estado):
    """cols_estado: índice (0-based, tras el ID) de la columna de estado."""
    out = {}
    for linea in (D / ruta).read_text(encoding="utf-8").splitlines():
        m = FILA.match(linea)
        if not m: continue
        rid, resto = m.group(1), m.group(2)
        celdas = [limpiar(c) for c in resto.split("|")]
        if len(celdas) <= cols_estado: continue
        est = celdas[cols_estado]
        if est not in {"CONFORME","PARCIAL","NO CONFORME","NO VERIFICABLE",
                       "NO APLICABLE","EXCLUIDO"}: continue
        out[rid] = {"estado": est, "celdas": celdas}
    return out

base = parsear("2026-08-03-mcs.md", 0)                 # ID | Estado | Evidencia | Gravedad
seg  = parsear("2026-08-04-mcs.md", 2)                 # ID | Nivel | Antes | Ahora | ...
r1   = parsear("2026-08-04-mcs-r1.md", 1)              # ID | Requisito | Estado | Coste

# Nivel, donde el informe de seguimiento lo declara
nivel = {}
for linea in (D / "2026-08-04-mcs.md").read_text(encoding="utf-8").splitlines():
    m = re.match(r"^\|\s*\*{0,2}([A-Z]{2,3}-\d{2})\*{0,2}\s*\|\s*(N[12])\s*\|", linea)
    if m: nivel[m.group(1)] = m.group(2)

# Bloqueantes de N1 enumerados en el informe base (§5)
txt = (D / "2026-08-03-mcs.md").read_text(encoding="utf-8")
sec = txt[txt.index("Requisitos de **N1** en estado distinto"):txt.index("**Distancia a N1")]
n1_bloq = set(re.findall(r"\b([A-Z]{2,3}-\d{2})\b", sec))
for r in n1_bloq: nivel.setdefault(r, "N1")

# Cierres posteriores, con su fuente documental
CIERRES = {
 "ARQ-01":("CONFORME","nunca estuvo abierto; §C4 tenía los diagramas"),
 "CFG-02":("CONFORME","Tanda A — gitleaks en CI"),
 "IA-03":("CONFORME","Tanda B"), "IA-05":("CONFORME","Tanda B"),
 "INT-02":("CONFORME","Tanda A — bandit + pip-audit + pnpm audit"),
 "SEG-03":("CONFORME","Tanda A — cabeceras de seguridad"),
 "SEG-06":("CONFORME","Tanda B — modelo de amenazas"),
 "SEG-08":("CONFORME","Tanda B"),
 "IA-07":("CONFORME","Tanda B — conjunto de evaluación"),
 "IA-08":("CONFORME","Tanda B"), "IA-09":("CONFORME","Tanda B"),
 "IA-11":("CONFORME","Tanda B"), "IA-04":("CONFORME","R1"),
 "SUM-02":("CONFORME","remediación 2026-08-05 — contenedor sin privilegios"),
 "DES-03":("CONFORME","remediación 2026-08-05 — /health verifica la base"),
 "DIS-02":("CONFORME","remediación 2026-08-05 — 34/34 pares AA + job en CI"),
 "SEG-07":("CONFORME","remediación 2026-08-05 — audit_log de solo anexado"),
 "IA-01":("NO APLICABLE","R1 — cuenta para el nivel"),
 # 2026-08-05 — el owner protegió `main`. Los dos eran el mismo hecho.
 # Residual ACEPTADO por el owner, al modo de AM-08: `enforce_admins` se queda
 # en `false`, así que un administrador —hoy, el único que trabaja en el repo—
 # puede saltarse ambos. El control protege del mal día, no de la voluntad, y
 # con un solo desarrollador la salida de emergencia vale más que el trinquete.
 # No es un pendiente: es una decisión, y se revisa si entra alguien más.
 # CORREGIDO con MCS-CORE en mano (2026-08-05). Se habían dado por CONFORME sin
 # leer el texto del requisito. CFG-03 exige la rama protegida «SIN ESCRITURA
 # DIRECTA» e INT-03 que la integración NO se permita con verificaciones en
 # fallo. Con `enforce_admins: false` un administrador puede las dos cosas, así
 # que se cumplen en parte del alcance: PARCIAL (§6.1), y un PARCIAL impide
 # alcanzar su nivel (§6.2). Los dos son N1.
 "CFG-03":("CONFORME","owner activó enforce_admins 2026-08-05; ADR-029 retirada"),
 # Ola 0 (2026-08-05) — remedidos contra el código de hoy, no contra la
 # evidencia del 08-03. Los cierra el trabajo de producto, no una tanda.
 # ARQ-02 exige que TODA decisión irreversible esté en un ADR. Pasar de cero a
 # 24 es el salto grande, pero `DECISIONS.md` conserva 25 entradas `DEC-` y
 # algunas son irreversibles de manual: DEC-003 (tablas separadas en vez de
 # JSONB) y DEC-008 (charter como tabla propia) son forma de esquema.
 "ARQ-02":("CONFORME","29 ADR; las 5 decisiones irreversibles de DECISIONS.md promovidas (ADR-024..028)"),
 "GOB-02":("CONFORME","Ola 0 — 24 ADR y la exclusión de ARQ-03 registrada (ADR-018)"),
 "LEN-01":("CONFORME","Ola 0 — glosario aprobado y completo, era borrador"),
 # Medibles solo desde que MCS-CORE está en el repo (2026-08-05). Los dos son
 # N2, así que no bloquean N1, pero dejan de figurar como «sin medir».
 "DAT-08":("NO CONFORME","26 constantes de conversión inline en app/ (N2)"),
 "DAT-16":("NO CONFORME","el periodo en curso no se señala en analíticas ni gráficos (N2)"),
 # REABIERTO Y VUELTO A CERRAR el 2026-08-05. Estaba CONFORME sobre una lista
 # escrita a mano de cuatro sitios «que pintan salud», y había un QUINTO:
 # `charter_generator._RAG_RGB` usaba `#16a34a` y `#dc2626`, dos de los
 # colores que la propia prueba de D-7 lista como retirados. El acta en .docx
 # —el documento que más se imprime y se firma— salía con la paleta anterior a
 # DIS-02. También los `.pill` del PDF, que en el mismo archivo llevaban un
 # color distinto que los `.dot`. Ahora la comprobación DERIVA los sitios del
 # código y lo que se declara son las excepciones, con razón escrita.
 "DAT-05":("CONFORME","Ola 2 — quinto sitio corregido (acta .docx) y la prueba deriva los sitios en vez de enumerarlos"),
 "INT-03":("CONFORME","owner activó enforce_admins 2026-08-05; ADR-029 retirada"),
 "ARQ-03":("EXCLUIDO","ADR-018, revisión 2027-02-04"),
 # Ola 2 (2026-08-05) — los mecánicos. El hueco estaba medido y el criterio es
 # el conteo, así que cada uno cierra con su trinquete propio en la suite.
 "SEG-05":("CONFORME","Ola 2 — SECURITY.md con canal privado, plazos, alcance y puerto seguro; trinquete en test_seg05_divulgacion.py"),
 "OPS-01":("CONFORME","Ola 2 — structlog formatea el logging estándar: JSON a stdout en los DOS procesos, y celery ya no secuestra el raíz"),
 # CRITERIO DECLARADO (el plan avisa de que para esto no hay vara escrita):
 # se cuenta CONFORME porque `mypy --strict` se ejecuta ENTERO en CI y bloquea
 # todo error nuevo. El pasivo del día del enchufe —1.163 errores, ocho de cada
 # diez anotaciones que faltan— va nominal en `.mypy-baseline` y solo puede
 # encoger. Mismo precedente que INT-02 con `.pip-audit-ignore`. Un auditor
 # externo puede leer «modo estricto» como «cero errores» y discrepar: es el
 # cierre de la Ola 2 con más margen de discusión, y por eso se escribe aquí.
 "CFG-04":("CONFORME","Ola 2 — job `commits` valida el rango del PR + hook versionado en .githooks/; el hábito ya estaba (97,5% de 400), faltaba el control"),
 "DIS-01":("CONFORME","Ola 2 — cero literales de color y de espaciado en components/app/lib/hooks; el gate exige además que el token citado exista en la paleta base"),
 "CFG-14":("CONFORME","Ola 2 — mismo gate que DIS-01: los 25 literales hexadecimales ya no están y check_tokens.py impide el siguiente"),
 # DAT-06 NO cierra, y es deliberado. Los cuatro restos EN CÓDIGO se fueron
 # —la traducción del motor de informes, la etiqueta «Ámbar» del PDF, la clase
 # CSS y el alias del generador DOCX— con trinquete que mira el árbol entero.
 # Queda `tenant.settings.task_load_thresholds.amber_max`, que es una llave
 # guardada en datos de inquilinos reales: renombrarla es cambio de contrato y
 # necesita ventana, como `wbs`. Un PARCIAL impide alcanzar su nivel (§6.2), y
 # así debe figurar: darlo por cerrado con el resto vivo sería repetir el error
 # de medir contra la evidencia anotada en vez de contra el requisito.
 # CIERRA el 2026-08-06 con ADR-030. El quinto resto era de contrato —una llave
 # en `tenant.settings` de inquilinos reales— y fue con el molde de wbs→wbs_code:
 # migración 0101 sobre los datos + ventana de compatibilidad. De paso salió que
 # la etiqueta del formulario de ajustes también decía «Ámbar».
 "DAT-06":("CONFORME","Ola 3 — amber_max→yellow_max (ADR-030, migración 0101); 0 restos en código, datos e interfaz"),
 "DOC-01":("CONFORME","Ola 2 — 130 documentos con encabezado (responsable/estado/revisado/revisar_cada); gate en `contexto-permanente`"),
 "ARQ-04":("CONFORME","2026-08-06 — los tres factores que el requisito nombra, con trinquete: configuración en el entorno (cero lecturas de os.environ fuera de Settings, seis migradas), procesos sin estado (producción NO ARRANCA con STORAGE_BACKEND=local, más barrido AST de estado mutable a nivel de módulo) y registros a stdout en los dos procesos. test_arq04_doce_factores.py"),
 "DAT-10":("CONFORME","2026-08-06 — docs/dominio/07-FICHAS-INDICADORES.md, firmadas por el owner. Fórmula, grano, inclusiones, exclusiones, zona horaria, nulos y responsable por familia; derivadas del código con función y línea. Tres respuestas cambiaron producto: progress_avg y budget_total dejan de decir cero cuando quieren decir nada, y el coalesce que lo causaba en SQL desapareció"),
 "SEG-02":("CONFORME","2026-08-06 — ADR-031: el almacén de variables de Railway ES un almacén dedicado (fuera del repositorio, control de acceso propio, no versionado). Lo que el requisito prohíbe —secreto en el repositorio— lo verifica gitleaks sobre el historial completo en cada PR. Residuales escritos en el ADR"),
 "SUM-01":("CONFORME","2026-08-06 — ADR-031: Railway construye desde la rama, que es canalización automática. El requisito prohíbe construir en equipos locales, y nadie despliega desde su máquina. La falta de artefacto inmutable queda como consecuencia declarada"),
 "DEV-03":("CONFORME","2026-08-06 — ADR-031: alcance reducido declarado. Niveles sostenidos: unitaria y de integración (suite de API). El de extremo a extremo se declara AUSENTE en vez de fingirse, con su consecuencia escrita: un fallo de frontend llega a producción sin que nada lo detenga"),
 "REQ-03":("CONFORME","2026-08-06 — docs/dominio/05-DATOS-PERSONALES.md, derivado del esquema real: users, stakeholders, actors, audit_log (ip/user_agent) y password_reset_tokens. Declara lo que NO se trata (cero datos de pago: no hay modelo de suscripción), el reparto responsable/encargado, y como carencias abiertas la retención y el procedimiento de derechos"),
 "CON-01":("CONFORME","2026-08-06 — docs/dominio/06-COMPETENCIA.md: materia (PMBOK 7 + PRINCE2 7 + Agile, combinados por decisión del owner), jurisdicciones (ninguna, con el motivo: el producto no emite afirmaciones sujetas a jurisdicción) y frontera con seis exclusiones"),
 "CON-03":("CONFORME","2026-08-06 — 06-COMPETENCIA.md §2: el producto no emite afirmaciones normativas, así que no hay afirmación a la que exigirle fuente/jurisdicción/vigencia. Las fuentes de marco sí van con edición declarada. Queda escrito el disparador que invalida esta lectura"),
 "LEN-03":("CONFORME","2026-08-06 — docs/dominio/04-GUIA-ESTILO.md fija tratamiento (informal en tercera persona), anglicismos (lista medida sobre la interfaz), números (miles coma, decimal punto, 2 decimales, porcentajes 0) y fechas (dd-mm-aaaa, 24h). Decisiones del owner; la divergencia de fecha/hora queda declarada como trabajo, no como excepción"),
 "CFG-06":("NO APLICABLE","2026-08-06 — decisión del owner: el producto es SaaS continuo y no publica versión. SemVer versiona una interfaz que se distribuye y se elige; aquí no hay artefacto que alguien instale ni versión que nadie pueda quedarse. Se reevalúa si se publica API pública o cliente descargable"),
 "DOC-02":("CONFORME","2026-08-06 — `tipo` exigido contra un esquema de 10 clases derivado del árbol, cada una con su propósito escrito (`TIPOS` en check_docs.py); 130 documentos declarados y barrido que impide el 131 sin tipo"),
 "DOC-03":("CONFORME","Ola 2 — el ER se genera de Base.metadata (scripts/generar_er.py) y la suite falla si se desfasa; database.md decía 49 tablas con 56 en el modelo"),
 # DAT-04 y DAT-08 miraban el mismo hecho desde lados distintos: la auditoría
 # contó «6 sitios» de conversión y DAT-08 anotó «26 constantes en línea».
 # Eran 26, en tres familias. Con las fronteras nombradas cierran los dos.
 "DAT-04":("CONFORME","Ola 2 — app/core/unidades.py concentra las 3 familias (pct, mebibytes, ms); trinquete que mira el árbol"),
 "DAT-08":("CONFORME","Ola 2 — las 26 constantes en línea pasaron a la frontera nombrada (N2)"),
 # LEN-02 sigue PARCIAL, con la cifra medida y bajando. Los cinco textos por
 # defecto ya dicen qué, por qué y qué hacer; de los 201 mensajes explícitos,
 # 184 no sugerían ninguna acción. Reescribir 184 de un tirón produciría 184
 # textos plausibles y ninguno pensado: escribir el porqué de una regla de
 # negocio exige saber qué regla es. Lo que faltaba era el mecanismo, y ahora
 # está: `mensaje()` con tres argumentos sin defecto + línea base que encoge.
 "LEN-02":("PARCIAL","Ola 2 — 177→166 con texto suelto; `errors.mensaje()` hace estructural el requisito y `check_mensajes.py` impide el 170"),
 # DAT-12: la auditoría midió «77 puntos» y el conteo bruto de `?? 0` daba 84,
 # pero 67 de esos eran de CÁLCULO —`map.get(k) ?? 0` al sumar es correcto—.
 # Los de PRESENTACIÓN eran 17, y quedaron en cero. El producto ya usaba «—»
 # para huecos de texto en 43 archivos: lo que faltaba era no taparlo con un
 # cero en los números.
 "DAT-12":("CONFORME","Ola 2 — 17 sitios de presentación a `@/lib/sin-dato`, con etiqueta accesible; gate en check_tokens.py"),
 # SEG-04 era la única CRÍTICA viva, y el hueco era explotable dentro del
 # mismo inquilino: el alcance por asignación se aplicaba al listado y a
 # ningún detalle. Nueve copias del resolvedor de proyecto, dos órdenes de
 # argumentos y dos sin filtrar `deleted_at`. Ahora una sola comprobación.
 "SEG-04":("CONFORME","Ola 3 — core/autorizacion.proyecto_autorizado; 18 casos verificados por mutación; AM-15 en el modelo de amenazas"),
 "DEV-04":("CONFORME","Ola 2 — mypy --strict en CI (job tipos-python) con línea base que solo encoge; ruff ya cubría el análisis estático"),
}

reg = {}
for rid, v in base.items():
    reg[rid] = {"estado": v["estado"], "evidencia": v["celdas"][1] if len(v["celdas"])>1 else "",
                "gravedad": v["celdas"][2] if len(v["celdas"])>2 else "", "fuente": "base 08-03"}
for fuente, d, idx in (("seguimiento 08-04", seg, 2), ("R1 08-04", r1, 1)):
    for rid, v in d.items():
        reg.setdefault(rid, {"evidencia":"", "gravedad":""})
        reg[rid]["estado"] = v["estado"]; reg[rid]["fuente"] = fuente
for rid, (est, por) in CIERRES.items():
    reg.setdefault(rid, {"evidencia":"", "gravedad":""})
    reg[rid]["estado"] = est; reg[rid]["fuente"] = por

# Medidos en R1 y contados hacia N1 por el propio expediente (54 -> 50 al
# cerrar cuatro de ellos). El §5 los omitió porque estaban NO VERIFICABLE.
N1_DESDE_R1 = {"DAT-04", "DAT-11", "DAT-12", "DIS-03", "LEN-02", "SEG-01"}
for rid in reg:
    reg[rid]["nivel"] = "N1" if rid in N1_DESDE_R1 else nivel.get(rid, "?")

from collections import Counter
print("requisitos en el registro:", len(reg))
print("por estado:", dict(Counter(v["estado"] for v in reg.values())))
print("nivel conocido:", dict(Counter(v["nivel"] for v in reg.values())))
abiertos_n1 = [r for r,v in reg.items() if v["nivel"]=="N1" and v["estado"] not in ("CONFORME","NO APLICABLE","EXCLUIDO")]
print(f"\nBLOQUEAN N1 hoy: {len(abiertos_n1)}")
print(sorted(abiertos_n1))
