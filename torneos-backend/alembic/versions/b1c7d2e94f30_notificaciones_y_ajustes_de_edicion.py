"""notificaciones, webhook de discord e inscripcion abierta

Revision ID: b1c7d2e94f30
Revises: 577928b6f4ed
Create Date: 2026-08-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import app.db.database  # necesario para el tipo DateTimeUTC usado abajo


# revision identifiers, used by Alembic.
revision: str = 'b1c7d2e94f30'
down_revision: Union[str, Sequence[str], None] = '577928b6f4ed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'notificaciones',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=False),
        sa.Column('tipo', sa.String(length=40), nullable=False),
        sa.Column('titulo', sa.String(length=160), nullable=False),
        sa.Column('cuerpo', sa.Text(), nullable=False),
        sa.Column('url', sa.String(length=500), nullable=True),
        sa.Column('edicion_id', sa.Integer(), nullable=True),
        sa.Column('leida_at', app.db.database.DateTimeUTC(timezone=True), nullable=True),
        sa.Column('created_at', app.db.database.DateTimeUTC(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['edicion_id'], ['ediciones.id']),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_notificaciones_usuario_id', 'notificaciones', ['usuario_id'])
    op.create_index('ix_notificaciones_edicion_id', 'notificaciones', ['edicion_id'])
    op.create_index('ix_notificaciones_created_at', 'notificaciones', ['created_at'])
    # El badge de no leídas se pide en cada carga de página: tiene que
    # resolverse por índice y no escaneando la tabla entera.
    op.create_index(
        'ix_notificacion_usuario_leida', 'notificaciones', ['usuario_id', 'leida_at']
    )

    with op.batch_alter_table('ediciones', schema=None) as batch_op:
        batch_op.add_column(sa.Column('discord_webhook_url', sa.String(length=500), nullable=True))
        # server_default para que las ediciones que ya existen queden con el
        # comportamiento de siempre (revisión manual). Se retira abajo: de acá
        # en adelante el valor lo pone el modelo, no la base.
        batch_op.add_column(
            sa.Column(
                'requiere_aprobacion',
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )

    with op.batch_alter_table('ediciones', schema=None) as batch_op:
        batch_op.alter_column('requiere_aprobacion', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('ediciones', schema=None) as batch_op:
        batch_op.drop_column('requiere_aprobacion')
        batch_op.drop_column('discord_webhook_url')

    op.drop_index('ix_notificacion_usuario_leida', table_name='notificaciones')
    op.drop_index('ix_notificaciones_created_at', table_name='notificaciones')
    op.drop_index('ix_notificaciones_edicion_id', table_name='notificaciones')
    op.drop_index('ix_notificaciones_usuario_id', table_name='notificaciones')
    op.drop_table('notificaciones')
