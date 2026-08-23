"""tabla faltante de mensajes de partida (chat de coordinacion)

`MensajePartida` se agregó al modelo pero nunca a una migración. En SQLite
local no se notó porque el lifespan de app/main.py llama a `create_all`, que
la crea sola; en Postgres, donde Alembic es la única fuente de verdad y
`create_all` no corre, la tabla no existe y los dos endpoints de chat
(`/partidas/{id}/mensajes`) fallan con "relation does not exist".

Esta revisión es de recuperación (catch-up): tiene que poder correr tanto
sobre una base donde la tabla NO existe (Postgres, o SQLite creada solo por
migraciones) como sobre una donde YA existe porque `create_all` se adelantó
(cualquier base de desarrollo con la que se venía trabajando). Por eso
inspecciona antes de crear, en vez de asumir.

Revision ID: c3a8e5b17d24
Revises: b1c7d2e94f30
Create Date: 2026-08-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import app.db.database  # necesario para el tipo DateTimeUTC usado abajo
from app.db.migraciones import tabla_existe


# revision identifiers, used by Alembic.
revision: str = 'c3a8e5b17d24'
down_revision: Union[str, Sequence[str], None] = 'b1c7d2e94f30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLA = 'mensajes_partida'


def upgrade() -> None:
    """Upgrade schema."""
    if tabla_existe(TABLA):
        # Ya la creó create_all en una base de desarrollo. No hay nada que
        # hacer y volver a crearla sería un error — la revisión solo queda
        # registrada para que esta base quede alineada con las demás.
        return

    op.create_table(
        TABLA,
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('partida_id', sa.Integer(), nullable=False),
        sa.Column('equipo_id', sa.Integer(), nullable=True),
        sa.Column('autor_nombre', sa.String(length=120), nullable=False),
        sa.Column('texto', sa.Text(), nullable=False),
        sa.Column('created_at', app.db.database.DateTimeUTC(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['equipo_id'], ['equipos.id']),
        sa.ForeignKeyConstraint(['partida_id'], ['partidas.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_mensajes_partida_partida_id', TABLA, ['partida_id'])
    op.create_index('ix_mensajes_partida_created_at', TABLA, ['created_at'])


def downgrade() -> None:
    """Downgrade schema."""
    if not tabla_existe(TABLA):
        return
    op.drop_index('ix_mensajes_partida_created_at', table_name=TABLA)
    op.drop_index('ix_mensajes_partida_partida_id', table_name=TABLA)
    op.drop_table(TABLA)
