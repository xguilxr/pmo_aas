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

D = pathlib.Path(__file__).resolve().parents[1] / "docs" / "archive" / "conformidad"
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
 "INF-03":("CONFORME","2026-08-06 — copia diaria 03:30 UTC del worker: pg_dump formato custom a Cloudflare R2 (proveedor DISTINTO al de la base), retención 30 días con limpieza en la misma ejecución. postgresql-client añadido a la imagen. Runbook con procedimiento de restauración y prueba que restaura de verdad contra Postgres — lo único que convierte un fichero en una copia"),
 "OPS-02":("CONFORME","2026-08-06 — la captura se anuncia ENCENDIDA Y APAGADA (antes devolvía False en silencio mientras su docstring afirmaba lo contrario) y `/health` publica `checks.error_capture`, así que se vigila desde fuera sin leer registros. Lo reportó el owner: veía OPS-01 en Railway y ninguna línea de Sentry"),
 "DIS-04":("CONFORME","2026-08-06 — los 18 avisos destructivos pasan por `lib/confirmar.ts`, que exige objeto, consecuencia y reversibilidad SIN valor por defecto. Pasivo a CERO. Dos avisos quedan declarados NO destructivos con motivo escrito (guarda de navegación y envío de correo). La consecuencia no la escribía ninguno antes"),
 "IA-02":("CONFORME","2026-08-06 — audit_log.actor_type (migración 0102) distingue lo que ejecuta el modelo. La IA YA auditaba; lo que faltaba era el dato: module=ai significa el módulo, no el actor, y el prefijo ai. era inconsistente (report.draft lo redacta el modelo y no lo lleva). Trinquete doble por ubicación y por nombre de acción"),
 "CFG-01":("CONFORME","2026-08-06 — las nueve categorías de §5.2.2 versionadas y comprobadas una a una, más el lado negativo (cero .env versionados; gitleaks sobre historial completo en el trabajo `seguridad`). i18n declarada NO APLICA con motivo: producto monolingüe. Dos categorías —fichas de métrica y reglas de estilo— se cerraron el mismo día por DAT-10 y LEN-03"),
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
 "LEN-02":("CONFORME","2026-08-07 — los 166 barridos: cada mensaje pasa por errors.mensaje(que=, porque=, accion=), tres argumentos con nombre y NINGUNO con defecto. El texto que ya existía es el «qué» y estaba bien; lo que faltaba era la regla violada y qué hacer. La línea base pasa de 166 a CERO, así que el trinquete deja de tolerar pasivo y solo puede quedarse en cero. Reescritos por transformación sobre el ÁRBOL (posiciones exactas del argumento), no por sustitución de texto, y cada uno con su porqué y su acción escritos a mano por familia de regla de negocio — un texto genérico habría producido 166 mensajes plausibles y ninguno pensado. mypy caza el que pierda una de las tres partes: `Missing named argument porque`"),
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
 "DAT-01":("CONFORME","2026-08-06 — glosario §7: once magnitudes con unidad canónica, rango y el porqué de cada una. app/core/magnitudes.py la refleja y una prueba falla si se separan. El trinquete DERIVA los 56 campos numéricos del árbol de modelos: uno nuevo sin unidad no entra. El importe se declara MXN —lo que el producto hace— con el disparador escrito, no «la moneda del inquilino», que es lo que el formulario promete y ningún sitio de presentación lee"),
 "DAT-02":("CONFORME","2026-08-06 — 56 campos numéricos medidos: 40 llevan la unidad en el NOMBRE (sufijo _pct/_days/_ms/_bytes, conteos cuyo sustantivo es la unidad, ordinales y coordenadas de calendario) y los 16 restantes la llevan ahora en el TIPO —Importe, Porcentaje, Escala, Severidad de app/core/magnitudes—, que es la segunda vía que el requisito admite. Se elige el tipo porque renombrar budget a budget_mxn es cambio de contrato, y ya se pagó dos veces (wbs_code, yellow_max). El esquema sale idéntico y una prueba lo comprueba. De paso: MetricSnapshot declaraba budget_plan/budget_actual como Mapped[float] sobre columnas Numeric —dinero anotado en coma flotante, y los consumidores lo delataban llamando a float() encima—"),
 "CON-02":("CONFORME","2026-08-06 — contraste de las 4 instrucciones de sistema contra glosario/modelos/ADR (lo pedía 06-COMPETENCIA §5). El grueso es contrato de salida, que no es dominio. Dos hallazgos: la taxonomía RAID estaba en código pero el glosario NO definía «Decisión» —una de las cuatro que el producto implementa—, y el MAPA DE SEÑALES («se acordó»→Decisión) vivía solo en la cadena del prompt, que es el caso exacto que el requisito nombra. Ahora en app/services/ai/corpus.py, declarado en el glosario §3, y la instrucción SE GENERA desde ahí; trinquete que impide reescribir la correspondencia en prompts.py"),
 "CON-05":("CONFORME","2026-08-06 — los tres pasos que 06-COMPETENCIA §4 pedía: la instrucción declara la frontera GENERADA desde frontera.py (que refleja la tabla del §3), aplicar_frontera corre DESPUÉS de la respuesta sobre la consulta de quien pregunta —sin pedirle permiso al modelo, porque un prompt es una petición y no una garantía—, y EV-S-10..15 + EV-C-37 la miden en el conjunto. El caso literal del documento («despedir por bajo desempeño») es una prueba. Residual escrito: detección por señales léxicas, con falsos negativos declarados"),
 "DAT-09":("CONFORME","2026-08-06 — auditados los indicadores de las fichas contra el código: 4 reimplementaciones. UNA YA HABÍA ROTO: la ficha firmada dice «sin proyectos → null, cero proyectos no es cero por ciento», se corrigió en dashboard.py y analytics/snapshots.py calculaba el MISMO indicador con su propia división y su propio else 0 — el tablero decía «—» y la instantánea del mismo día guardaba 0, así que la gráfica de tendencia dibujaba una caída a cero. app/services/indicadores.py es ahora la definición única (avance_de_cartera, promedio_de_avance, dias_de_retraso, porcentaje_a_tiempo) + migración 0103 para que la instantánea PUEDA guardar la ausencia. La salud se queda en project_health.py: ya era única, y DAT-09 pide una definición por indicador, no un archivo que las junte"),
 "DAT-11":("CONFORME","2026-08-06 — 12 superficies de indicador declaran periodo y frescura con `<MarcaDeDatos>`; 7 quedan fuera de alcance con motivo escrito (iconos de navegación, atributos DECLARADOS como allocation_pct que no se calculan, previsualización de importación). Vocabulario CERRADO de cuatro periodos en lib/frescura.ts y ninguna propiedad con valor por defecto: un defecto es lo que nadie rellena. useLectura se ata al DATO pintado y no a la llamada, así que la marca refresca sola al cambiar un filtro. La cifra no es la «10 de 87» del plan y se explica: DAT-11 vive en §5.7.2 «Métricas y presentación», así que el sujeto es el indicador con ficha (DAT-10), no un contador de caracteres. Gate check_frescura.py en CI"),
 "DIS-03":("CONFORME","2026-08-06 — remedido por estado (el «3 de 75» era un proxy y avisaba de serlo): 12 sin carga, 20 sin error, 31 «sin vacío» y 60 sin «sin permiso». Los tres primeros se definen UNA VEZ en la frontera del segmento —loading.tsx, error.tsx y FronteraDePermiso en el layout—, que es la respuesta del propio framework: definir un estado una vez para el segmento ES definirlo, repetirlo 70 veces es otra cosa. El 403 va por evento y no por boundary porque las pantallas piden datos en useEffect y una excepción ahí NO llega a ninguna frontera de React. El vacío sí es por pantalla y se hizo: de los 31, 30 recorrían constantes que no pueden estar vacías; los que quedaban se trataron uno a uno con texto propio. Gate check_estados.py, con la comprobación del vacío atada a la COLECCIÓN concreta"),
 "DEV-02":("CONFORME","2026-08-06 — medido: 31 de 66 módulos de app/services importaban SQLAlchemy o los modelos, y entre ellos estaban las reglas del semáforo. NO estaban mezcladas con las consultas —project_health ya las tenía puras— pero vivían en un archivo que importa AsyncSession, con nombre privado: verificarlas sin base era POSIBLE y nadie lo había hecho, y «posible» no es lo que el requisito pide. app/dominio/ es la frontera y no puede importar sqlalchemy/app.models/app.db (trinquete sobre el ÁRBOL, no sobre el texto: el docstring de salud.py menciona SQLAlchemy explicando de dónde vino). test_dev02_dominio_sin_base.py: 36 casos sin una sola fixture, y una prueba que comprueba sobre su propio árbol que ningún caso pida `db` — si el archivo dejara de poder correr, DEV-02 dejaría de estar demostrado"),
 "REQ-01":("CONFORME","2026-08-07 — regla declarada en docs/project-management/CRITERIOS-DE-ACEPTACION.md: el criterio de aceptación de un cambio ES LA PRUEBA QUE LO NOMBRA, no un párrafo que lo describa. Cierra el hueco que la auditoría nombró —los lotes por chat sin issue— sin retroceder sobre el principio 0.1. check_criterios.py deriva los IDs del registro y los busca en el árbol de pruebas. La primera versión decía 59/59 y era falso: incluía el propio registro en el corpus, así que cada requisito se encontraba a sí mismo (SEXTA vez que un control se valida contra su documentación; lo destapó la mutación). Real: 12 sin prueba. Ocho cubiertos con test_req01_criterios.py y cuatro declarados verificables solo en GitHub/Railway con el dónde escrito"),
 "REQ-02":("CONFORME","2026-08-07 — cuatro escenarios con medida numérica en docs/dominio/08-ESCENARIOS-CALIDAD.md. El atasco era real (los tres candidatos eran percentiles y un P95 necesita muestra) y lo desatascó releer el requisito: pide MEDIDA DE RESPUESTA NUMÉRICA, no percentil de latencia. El producto ya imponía tres números que nadie había escrito como escenario — tope de 60 s al análisis de un plan, RPO menor o igual a 24 h con retención de 30 días y volcado abortado a 1800 s, y retardo creciente del inicio de sesión desde el intento 5 con base 2 s y tope 300 s más 30 fallos/hora por IP. Son mejores que un P95 improvisado: YA SE CUMPLEN y se comprueban sin esperar tráfico. test_req02_escenarios.py exige que el número del documento sea el del código, así que subir un tope sin actualizar el escenario falla. Los percentiles siguen declarados como deuda abierta y la prueba impide borrarlos sin pagarlos"),
 "SEG-01":("PARCIAL","2026-08-07 — MEDIDO ENTERO: los 127 controles ASVS 4.0.3 L1 uno por uno (asvs-l1.yaml; catálogo vendorizado desde la fuente de OWASP). Resultado tras la decisión del owner: 97 CUMPLE / 13 NO APLICA / 2 ACEPTADO / 15 HUECO. ADR-032 resuelve el grupo de contraseñas: 2.1.1 y 2.1.9 quedan ACEPTADO —el owner se queda en 8 con reglas, sabiendo que ASVS pide 12 sin ellas— y 2.1.2/2.1.3 CIERRAN porque eran defecto y no postura: bcrypt truncaba a 72 bytes en silencio y dos contraseñas de 103 y 108 caracteres abrían la misma cuenta. SIGUE PARCIAL con 15 huecos reales; los dos mayores son el token en localStorage. check_asvs.py exige mapeo completo, evidencia por control, motivo en cada NO APLICA, ADR en cada ACEPTADO, y que los huecos no crezcan"),
 "DEV-04":("CONFORME","Ola 2 — mypy --strict en CI (job tipos-python) con línea base que solo encoge; ruff ya cubría el análisis estático"),
 # Los entornos existían; lo que no existía era la paridad DECLARADA, y sin
 # declaración «paridad» no se puede afirmar ni desmentir. La suposición estaba
 # mal: la base local era Postgres 16 contra el 15 del CI, con la migración
 # 0101 en juego —que se reescribió por miedo a una diferencia entre motores—.
 "INF-02":("CONFORME","2026-08-06 — servicios-datos.yml declara Postgres 15 y Redis 7 con razón escrita; check_entornos.py lo verifica contra el workflow en cada PR. Lo que corre en Railway no es medible desde el repositorio y se declara con fecha en el runbook en vez de fingirse. Owner confirma que la copia de desarrollo existe y hoy no se usa: INF-02 pide que existan separados, no tráfico en los dos"),
 # DES-02 pedía «documentado Y EJECUTABLE». Lo segundo no lo puede garantizar
 # un documento sobre sí mismo: son dos hechos del código.
 "DES-02":("CONFORME","2026-08-06 — runbook entornos-y-reversion.md con las tres capas (despliegue por Redeploy, migración bajando una revisión, datos por restauración) y el aviso de que revertir el despliegue NO deshace la migración. La parte ejecutable con trinquete: /health publica las comprobaciones que el runbook manda mirar, y toda migración con vuelta atrás vacía dice por qué —las 9 de datos por irreversibles, las 2 de fusión exentas derivando del árbol, no de una lista—"),
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
