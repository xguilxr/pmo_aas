"""MCS DEV-02 — la lógica de dominio, verificable sin base de datos.

> «La lógica de dominio DEBE ser verificable sin acceso a base de datos».

La auditoría lo dejó PARCIAL con el motivo escrito: «las pruebas usan SQLite en
memoria (`tests/conftest.py`): rápido, pero la lógica de dominio **sí** necesita
base de datos». Medido contra el árbol, 31 de los 66 módulos de `app/services`
importan SQLAlchemy o los modelos — y entre ellos estaban las reglas que
deciden de qué color sale un proyecto.

**No estaban mezcladas con las consultas**: `project_health.py` ya tenía sus
reglas como funciones puras. Lo que pasaba es que vivían en un archivo que
importa `AsyncSession`, con nombre privado, así que verificarlas sin base de
datos era posible y nadie lo había hecho — y «posible» no es lo que el
requisito pide.

Este paquete es la frontera. Lo que entra aquí **no puede importar SQLAlchemy
ni `app.models`**, y hay un trinquete que lo comprueba recorriendo el árbol. Lo
que queda fuera es acceso a datos, no dominio.

La diferencia práctica: `tests/test_dev02_dominio_sin_base.py` ejercita estas
reglas con valores sueltos, sin sesión y sin fixture. Si algún día alguien mete
una consulta aquí, la prueba deja de poder correr y el trinquete lo dice antes.
"""
