"""
routers/
--------
Un archivo por tema. Cada uno define su propio APIRouter con un `prefix`, y
main.py los conecta con app.include_router(...). Si falta esa línea en
main.py, los endpoints existen en el código pero la API responde 404 — es el
olvido más común al agregar un router nuevo.

Nada de lógica de negocio compartida acá: si dos routers necesitan la misma
regla, va a un módulo aparte, no a este __init__.
"""
