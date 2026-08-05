"""Deriva el registro de conformidad MCS desde los informes fechados.

`MCS-CORE` —el catálogo de los 126 requisitos— **no está en este repositorio**:
las sesiones que corrieron `MCS-P01` lo tenían en otro entorno. Lo que sí está
versionado son los informes, y traen lo suficiente para reconstruir el estado:

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
 "CFG-03":("PARCIAL","rama protegida, pero enforce_admins=false permite escritura directa"),
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
 "DAT-05":("CONFORME","Ola 0 — una sola paleta de salud y un solo vocabulario de fase"),
 "INT-03":("PARCIAL","verificaciones exigidas, pero un administrador puede saltarlas"),
 "ARQ-03":("EXCLUIDO","ADR-018, revisión 2027-02-04"),
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
