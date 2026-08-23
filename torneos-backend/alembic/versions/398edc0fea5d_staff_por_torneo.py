"""staff por torneo: ayudar a correr UN torneo sin ser organizador global

`usuarios.es_organizador` es una bandera global: quien la tiene administra
TODOS los torneos. Eso hacia imposible pedir una mano puntual — para que
alguien te ayudara en una copa habia que darle acceso a toda la plataforma,
o hacerlo vos.

Dos roles: ADMINISTRADOR opera el torneo completo (inscripciones, sorteo,
partidas); ARBITRO es el dia de partido (programar, check-in, disputas,
correcciones). Ninguno de los dos puede borrar el torneo ni repartir roles:
delegar la operacion no puede incluir delegar quien mas entra.


Revision ID: 398edc0fea5d
Revises: a5f07601fd8a
Create Date: 2026-08-23 15:11:18.787259

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import app.db.database  # DateTimeUTC
from app.db.migraciones import tabla_existe


# revision identifiers, used by Alembic.
revision: str = '398edc0fea5d'
down_revision: Union[str, Sequence[str], None] = 'a5f07601fd8a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # En desarrollo `create_all` pudo crearla antes; ver app/db/migraciones.py
    if tabla_existe("staff_de_torneo"):
        return

    op.create_table('staff_de_torneo',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('torneo_id', sa.Integer(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('rol', sa.Enum('ADMINISTRADOR', 'ARBITRO', name='rolstaff', native_enum=False, length=40), nullable=False),
    sa.Column('created_at', app.db.database.DateTimeUTC(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['torneo_id'], ['torneos.id'], ),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('torneo_id', 'usuario_id', name='uq_staff_torneo_usuario')
    )
    with op.batch_alter_table('staff_de_torneo', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_staff_de_torneo_torneo_id'), ['torneo_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_staff_de_torneo_usuario_id'), ['usuario_id'], unique=False)



def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('staff_de_torneo', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_staff_de_torneo_usuario_id'))
        batch_op.drop_index(batch_op.f('ix_staff_de_torneo_torneo_id'))

    op.drop_table('staff_de_torneo')
