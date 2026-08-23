"""Ayudas para escribir migraciones que convivan con `create_all`.

Por qué hace falta esto
-----------------------
En desarrollo (SQLite) el arranque de la app llama a `create_all`
(`app/main.py`), que crea de una todas las tablas que declaran los modelos.
En producción (Postgres) `create_all` está deshabilitado y el esquema lo
gobierna Alembic y nada más.

Esa asimetría es deliberada y cómoda —permite iterar sin migrar a cada
cambio— pero tiene una consecuencia que muerde siempre igual: **cuando se
agrega una tabla nueva, la base de desarrollo ya la tiene antes de que su
migración corra**. Al aplicar la migración, `create_table` falla con "table
already exists", y esa base queda trabada sin poder avanzar.

Pasó con `mensajes_partida` y volvió a pasar con `cambios_de_roster`. Es
sistemático, no mala suerte, así que la respuesta vive acá en vez de
copiarse en cada revisión.

Cómo se usa
-----------
En una migración que crea una tabla nueva::

    from app.db.migraciones import tabla_existe

    def upgrade():
        if not tabla_existe("mi_tabla"):
            op.create_table("mi_tabla", ...)

No aplica a `add_column`: `create_all` solo crea tablas faltantes, nunca
altera una que ya existe. Por eso una tabla nueva puede aparecer ya creada
mientras las columnas nuevas de una tabla vieja no.
"""

import sqlalchemy as sa
from alembic import context, op


def tabla_existe(nombre: str) -> bool:
    """Si la tabla ya está en la base que se está migrando.

    En modo offline (`alembic upgrade --sql`, que genera el script sin
    conectarse) devuelve False: no hay base que inspeccionar —la conexión es
    simulada y `sa.inspect` levantaría— y además un script SQL se genera para
    aplicar sobre una base limpia, donde la tabla efectivamente no existe.
    """
    if context.is_offline_mode():
        return False
    return nombre in set(sa.inspect(op.get_bind()).get_table_names())
