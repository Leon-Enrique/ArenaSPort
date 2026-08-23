"""permiso de cambio de roster con el torneo ya empezado

Al sortear una fase el plantel queda congelado, que es lo correcto: cambiarlo
a mitad de torneo es la via para meter un refuerzo antes de la final. Pero el
caso legitimo existe y es comun —a un titular se le rompe el celular en
cuartos— y no habia forma de resolverlo: el bloqueo no tenia excepcion ni
siquiera para el organizador, y el mensaje de error mandaba a hacerlo
"directamente" cuando ningun endpoint lo permitia.

Se agrega:
  - `inscripciones.cambio_roster_hasta` / `_motivo`: la ventana que el
    organizador abre para UN equipo puntual.
  - `cambios_de_roster`: el rastro de cada cambio hecho con el torneo en
    marcha. Append-only, mismo espiritu que `reportes_resultado`. Cambiar un
    roster en cuartos es justo lo que se discute despues, y sin registro
    queda la palabra de uno contra la del otro.

Revision ID: cec247b6e3d6
Revises: b25513457704
Create Date: 2026-08-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import app.db.database  # DateTimeUTC, usado abajo
from app.db.migraciones import tabla_existe


# revision identifiers, used by Alembic.
revision: str = 'cec247b6e3d6'
down_revision: Union[str, Sequence[str], None] = 'b25513457704'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # En desarrollo `create_all` ya pudo haber creado esta tabla antes de que
    # corriera la migracion; ver app/db/migraciones.py.
    if not tabla_existe("cambios_de_roster"):
        op.create_table('cambios_de_roster',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('inscripcion_id', sa.Integer(), nullable=False),
        sa.Column('entraron', sa.Text(), nullable=True),
        sa.Column('salieron', sa.Text(), nullable=True),
        sa.Column('motivo_autorizacion', sa.Text(), nullable=True),
        sa.Column('autorizado_por_usuario_id', sa.Integer(), nullable=True),
        sa.Column('aplicado_por_usuario_id', sa.Integer(), nullable=True),
        sa.Column('created_at', app.db.database.DateTimeUTC(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['aplicado_por_usuario_id'], ['usuarios.id'], ),
        sa.ForeignKeyConstraint(['autorizado_por_usuario_id'], ['usuarios.id'], ),
        sa.ForeignKeyConstraint(['inscripcion_id'], ['inscripciones.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_cambios_de_roster_created_at', 'cambios_de_roster', ['created_at'])
        op.create_index('ix_cambios_de_roster_inscripcion_id', 'cambios_de_roster', ['inscripcion_id'])

    with op.batch_alter_table('inscripciones', schema=None) as batch_op:
        batch_op.add_column(sa.Column('cambio_roster_hasta', app.db.database.DateTimeUTC(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('cambio_roster_motivo', sa.Text(), nullable=True))



def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('inscripciones', schema=None) as batch_op:
        batch_op.drop_column('cambio_roster_motivo')
        batch_op.drop_column('cambio_roster_hasta')

    with op.batch_alter_table('cambios_de_roster', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_cambios_de_roster_inscripcion_id'))
        batch_op.drop_index(batch_op.f('ix_cambios_de_roster_created_at'))

    op.drop_table('cambios_de_roster')
