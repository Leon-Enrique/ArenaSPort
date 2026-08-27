"""miembros permanentes de equipo e invitaciones

Hasta ahora un jugador era texto que tipeaba el capitan dentro de UNA
inscripcion: no tenia cuenta, no podia editar sus propios datos y no podia
irse del equipo si el capitan no queria sacarlo.

`miembros_equipo` es la gente del equipo entre torneos, con cuenta
obligatoria (`usuario_id` NOT NULL). Va por juego porque `clave_identidad`
se deriva de los campos que cada juego declara como clave: la identidad de
MLBB no es la de otro juego.

`invitaciones_equipo` es el unico camino para entrar a un equipo, ahora que
el capitan no puede cargar a nadie a mano. En tabla y no en memoria como
app/core/tickets.py: un ticket de stream dura un minuto, una invitacion
tiene que seguir viva si el jugador la abre manana.

Ninguna de las dos toca datos existentes: los equipos y rosters actuales
siguen exactamente como estan.


Revision ID: 1cf89ee90970
Revises: 398edc0fea5d
Create Date: 2026-08-27 13:39:34.579121

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import app.db.database  # DateTimeUTC
from app.db.migraciones import tabla_existe


# revision identifiers, used by Alembic.
revision: str = '1cf89ee90970'
down_revision: Union[str, Sequence[str], None] = '398edc0fea5d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # En desarrollo `create_all` pudo crearlas antes; ver app/db/migraciones.py
    if tabla_existe("miembros_equipo"):
        return

    op.create_table('invitaciones_equipo',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('equipo_id', sa.Integer(), nullable=False),
    sa.Column('juego_id', sa.Integer(), nullable=False),
    sa.Column('token', sa.String(length=64), nullable=False),
    sa.Column('creada_por_usuario_id', sa.Integer(), nullable=False),
    sa.Column('usuario_destino_id', sa.Integer(), nullable=True),
    sa.Column('estado', sa.String(length=20), nullable=False),
    sa.Column('expira_at', app.db.database.DateTimeUTC(timezone=True), nullable=False),
    sa.Column('aceptada_por_usuario_id', sa.Integer(), nullable=True),
    sa.Column('aceptada_at', app.db.database.DateTimeUTC(timezone=True), nullable=True),
    sa.Column('created_at', app.db.database.DateTimeUTC(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['aceptada_por_usuario_id'], ['usuarios.id'], ),
    sa.ForeignKeyConstraint(['creada_por_usuario_id'], ['usuarios.id'], ),
    sa.ForeignKeyConstraint(['equipo_id'], ['equipos.id'], ),
    sa.ForeignKeyConstraint(['juego_id'], ['juegos.id'], ),
    sa.ForeignKeyConstraint(['usuario_destino_id'], ['usuarios.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('invitaciones_equipo', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_invitaciones_equipo_creada_por_usuario_id'), ['creada_por_usuario_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_invitaciones_equipo_equipo_id'), ['equipo_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_invitaciones_equipo_estado'), ['estado'], unique=False)
        batch_op.create_index(batch_op.f('ix_invitaciones_equipo_juego_id'), ['juego_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_invitaciones_equipo_token'), ['token'], unique=True)
        batch_op.create_index(batch_op.f('ix_invitaciones_equipo_usuario_destino_id'), ['usuario_destino_id'], unique=False)

    op.create_table('miembros_equipo',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('equipo_id', sa.Integer(), nullable=False),
    sa.Column('juego_id', sa.Integer(), nullable=False),
    sa.Column('identidad', sa.JSON(), nullable=False),
    sa.Column('clave_identidad', sa.String(length=200), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('esta_activo', sa.Boolean(), server_default='1', nullable=False),
    sa.Column('created_at', app.db.database.DateTimeUTC(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['equipo_id'], ['equipos.id'], ),
    sa.ForeignKeyConstraint(['juego_id'], ['juegos.id'], ),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('equipo_id', 'juego_id', 'clave_identidad', name='uq_miembro_equipo_identidad'),
    sa.UniqueConstraint('equipo_id', 'juego_id', 'usuario_id', name='uq_miembro_equipo_usuario')
    )
    with op.batch_alter_table('miembros_equipo', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_miembros_equipo_clave_identidad'), ['clave_identidad'], unique=False)
        batch_op.create_index(batch_op.f('ix_miembros_equipo_equipo_id'), ['equipo_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_miembros_equipo_juego_id'), ['juego_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_miembros_equipo_usuario_id'), ['usuario_id'], unique=False)

    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('miembros_equipo', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_miembros_equipo_usuario_id'))
        batch_op.drop_index(batch_op.f('ix_miembros_equipo_juego_id'))
        batch_op.drop_index(batch_op.f('ix_miembros_equipo_equipo_id'))
        batch_op.drop_index(batch_op.f('ix_miembros_equipo_clave_identidad'))

    op.drop_table('miembros_equipo')
    with op.batch_alter_table('invitaciones_equipo', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_invitaciones_equipo_usuario_destino_id'))
        batch_op.drop_index(batch_op.f('ix_invitaciones_equipo_token'))
        batch_op.drop_index(batch_op.f('ix_invitaciones_equipo_juego_id'))
        batch_op.drop_index(batch_op.f('ix_invitaciones_equipo_estado'))
        batch_op.drop_index(batch_op.f('ix_invitaciones_equipo_equipo_id'))
        batch_op.drop_index(batch_op.f('ix_invitaciones_equipo_creada_por_usuario_id'))

    op.drop_table('invitaciones_equipo')
    # ### end Alembic commands ###
