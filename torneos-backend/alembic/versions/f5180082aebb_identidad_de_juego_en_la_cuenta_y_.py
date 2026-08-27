"""identidad de juego en la cuenta, y roster permanente

Hasta ahora la identidad de juego se tipeaba de nuevo en cada inscripcion, y
la tipeaba el capitan. De ahi salian dos problemas: IDs mal copiados que
nadie podia corregir sin pedirselo al capitan, y que salirse de un equipo
dependiera de que el capitan quisiera sacarte.

identidades_de_juego mueve el ID a la cuenta de la persona: se carga una vez
por juego y sirve para siempre. El UNIQUE global por (juego, clave) tapa algo
que antes era invisible — la misma cuenta de MLBB declarada por dos usuarios
distintos de la plataforma.

miembros_equipo es el roster permanente, y solo guarda el vinculo: sin
identidad adentro, corregir tu ID lo arregla en todos tus equipos de una vez.
Entrar no requiere aceptar (el capitan suma directo, con notificacion al
sumado) pero salir no requiere permiso de nadie.

invitaciones_equipo NO es el camino normal: cubre al que todavia no tiene
cuenta. En tabla y no en memoria como app/core/tickets.py porque tiene que
seguir viva si el jugador abre el link manana.

Ninguna toca datos existentes: los equipos y rosters actuales siguen igual.


Revision ID: f5180082aebb
Revises: 398edc0fea5d
Create Date: 2026-08-27 13:54:50.139837

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import app.db.database  # DateTimeUTC
from app.db.migraciones import tabla_existe


# revision identifiers, used by Alembic.
revision: str = 'f5180082aebb'
down_revision: Union[str, Sequence[str], None] = '398edc0fea5d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # En desarrollo `create_all` pudo crearlas antes; ver app/db/migraciones.py
    if tabla_existe("miembros_equipo"):
        return

    op.create_table('identidades_de_juego',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('juego_id', sa.Integer(), nullable=False),
    sa.Column('identidad', sa.JSON(), nullable=False),
    sa.Column('clave_identidad', sa.String(length=200), nullable=False),
    sa.Column('created_at', app.db.database.DateTimeUTC(timezone=True), nullable=False),
    sa.Column('actualizada_at', app.db.database.DateTimeUTC(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['juego_id'], ['juegos.id'], ),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('juego_id', 'clave_identidad', name='uq_identidad_por_juego'),
    sa.UniqueConstraint('usuario_id', 'juego_id', name='uq_identidad_usuario_juego')
    )
    with op.batch_alter_table('identidades_de_juego', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_identidades_de_juego_clave_identidad'), ['clave_identidad'], unique=False)
        batch_op.create_index(batch_op.f('ix_identidades_de_juego_juego_id'), ['juego_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_identidades_de_juego_usuario_id'), ['usuario_id'], unique=False)

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
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('agregado_por_usuario_id', sa.Integer(), nullable=True),
    sa.Column('esta_activo', sa.Boolean(), server_default='1', nullable=False),
    sa.Column('salio_at', app.db.database.DateTimeUTC(timezone=True), nullable=True),
    sa.Column('created_at', app.db.database.DateTimeUTC(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['agregado_por_usuario_id'], ['usuarios.id'], ),
    sa.ForeignKeyConstraint(['equipo_id'], ['equipos.id'], ),
    sa.ForeignKeyConstraint(['juego_id'], ['juegos.id'], ),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('equipo_id', 'juego_id', 'usuario_id', name='uq_miembro_equipo_usuario')
    )
    with op.batch_alter_table('miembros_equipo', schema=None) as batch_op:
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

    op.drop_table('miembros_equipo')
    with op.batch_alter_table('invitaciones_equipo', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_invitaciones_equipo_usuario_destino_id'))
        batch_op.drop_index(batch_op.f('ix_invitaciones_equipo_token'))
        batch_op.drop_index(batch_op.f('ix_invitaciones_equipo_juego_id'))
        batch_op.drop_index(batch_op.f('ix_invitaciones_equipo_estado'))
        batch_op.drop_index(batch_op.f('ix_invitaciones_equipo_equipo_id'))
        batch_op.drop_index(batch_op.f('ix_invitaciones_equipo_creada_por_usuario_id'))

    op.drop_table('invitaciones_equipo')
    with op.batch_alter_table('identidades_de_juego', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_identidades_de_juego_usuario_id'))
        batch_op.drop_index(batch_op.f('ix_identidades_de_juego_juego_id'))
        batch_op.drop_index(batch_op.f('ix_identidades_de_juego_clave_identidad'))

    op.drop_table('identidades_de_juego')
    # ### end Alembic commands ###
