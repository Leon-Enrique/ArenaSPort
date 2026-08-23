"""check-in de torneo: confirmacion de asistencia antes del sorteo

Distinto del check-in de cada partida (que vive en `partidas`): este se hace
una vez, antes de sortear, y sirve para depurar equipos fantasma. Entre que un
equipo se inscribe y arranca el torneo pasan dias, y siempre hay algunos que
no aparecen; sortear con ellos deja el cuadro lleno de walkovers desde la
primera ronda.

Las tres columnas son nullables y arrancan vacias, asi que ninguna edicion
existente cambia de comportamiento: sin `checkin_abre_at`, el sorteo sigue
tomando a todos los aprobados como siempre.


Revision ID: ffdcba36d86d
Revises: cec247b6e3d6
Create Date: 2026-08-23 14:59:35.355840

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import app.db.database  # DateTimeUTC


# revision identifiers, used by Alembic.
revision: str = 'ffdcba36d86d'
down_revision: Union[str, Sequence[str], None] = 'cec247b6e3d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('ediciones', schema=None) as batch_op:
        batch_op.add_column(sa.Column('checkin_abre_at', app.db.database.DateTimeUTC(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('checkin_cierra_at', app.db.database.DateTimeUTC(timezone=True), nullable=True))

    with op.batch_alter_table('inscripciones', schema=None) as batch_op:
        batch_op.add_column(sa.Column('checkin_at', app.db.database.DateTimeUTC(timezone=True), nullable=True))



def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('inscripciones', schema=None) as batch_op:
        batch_op.drop_column('checkin_at')

    with op.batch_alter_table('ediciones', schema=None) as batch_op:
        batch_op.drop_column('checkin_cierra_at')
        batch_op.drop_column('checkin_abre_at')

